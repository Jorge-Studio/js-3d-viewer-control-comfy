import { app } from "../../../scripts/app.js";

const VIEWER_NODES = ["JS3D_Load3DController", "JS3D_Preview3D"];
const VIEWER_HEIGHT_LOADER = 680;
const VIEWER_HEIGHT_PREVIEW = 550;

function getExtensionBaseUrl() {
    try {
        return new URL("..", import.meta.url).href.replace(/\/$/, "");
    } catch (_) {
        return "/extensions/js-3d-viewer-control-comfy";
    }
}

function buildViewUrl(filePath) {
    if (!filePath) return "";
    if (filePath.startsWith("http")) return filePath;

    let relPath = filePath;

    if (filePath.startsWith("/") || /^[A-Z]:\\/.test(filePath)) {
        const normalized = filePath.replace(/\\/g, "/");
        const inputIdx = normalized.indexOf("/input/");
        if (inputIdx >= 0) {
            relPath = normalized.substring(inputIdx + 7);
        } else {
            const outputIdx = normalized.indexOf("/output/");
            if (outputIdx >= 0) {
                const afterOutput = normalized.substring(outputIdx + 8);
                const parts = afterOutput.split("/");
                const filename = parts.pop();
                const subfolder = parts.join("/");
                return `/view?filename=${encodeURIComponent(filename)}&type=output&subfolder=${encodeURIComponent(subfolder)}`;
            }
            relPath = normalized.split("/").pop();
        }
    }

    const parts = relPath.replace(/\\/g, "/").split("/");
    const filename = parts.pop();
    const subfolder = parts.join("/");
    return `/view?filename=${encodeURIComponent(filename)}&type=input&subfolder=${encodeURIComponent(subfolder)}`;
}

function findBackgroundImageUrl(loaderNode) {
    try {
        const graph = app.graph;
        if (!graph || !loaderNode.outputs) return null;

        for (const output of loaderNode.outputs) {
            if (!output.links) continue;
            for (const linkId of output.links) {
                const link = graph.links[linkId];
                if (!link) continue;
                const targetNode = graph.getNodeById(link.target_id);
                if (!targetNode || targetNode.type !== "JS3D_CompositeOnImage")
                    continue;

                const bgInput = targetNode.inputs?.find(
                    (inp) => inp.name === "background"
                );
                if (!bgInput || !bgInput.link) continue;

                const bgLink = graph.links[bgInput.link];
                if (!bgLink) continue;
                const bgSourceNode = graph.getNodeById(bgLink.origin_id);
                if (!bgSourceNode) continue;

                if (bgSourceNode.type === "LoadImage") {
                    const imgWidget = bgSourceNode.widgets?.find(
                        (w) => w.name === "image"
                    );
                    if (imgWidget && imgWidget.value) {
                        return `/view?filename=${encodeURIComponent(imgWidget.value)}&type=input&subfolder=`;
                    }
                }
            }
        }
    } catch (_) {}
    return null;
}

app.registerExtension({
    name: "JS3D.ViewerControl",

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (!VIEWER_NODES.includes(nodeData.name)) return;

        const isLoader = nodeData.name === "JS3D_Load3DController";
        const viewerHeight = isLoader ? VIEWER_HEIGHT_LOADER : VIEWER_HEIGHT_PREVIEW;

        const origOnCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origOnCreated?.apply(this, arguments);

            const container = document.createElement("div");
            container.style.cssText = `
                width: 100%;
                height: ${viewerHeight}px;
                position: relative;
                border-radius: 8px;
                overflow: hidden;
                background: #111;
            `;

            const iframe = document.createElement("iframe");
            iframe.style.cssText = `
                width: 100%;
                height: 100%;
                border: none;
                border-radius: 8px;
            `;
            iframe.setAttribute("sandbox", "allow-scripts allow-same-origin");

            const baseUrl = getExtensionBaseUrl();
            iframe.src = baseUrl + "/html/viewer3d.html";
            container.appendChild(iframe);

            const resizeHandle = document.createElement("div");
            resizeHandle.style.cssText = `
                position: absolute; bottom: 0; left: 0; right: 0; height: 6px;
                cursor: ns-resize; background: transparent; z-index: 200;
            `;
            resizeHandle.addEventListener("mouseenter", () => {
                resizeHandle.style.background = "rgba(106,158,255,0.4)";
            });
            resizeHandle.addEventListener("mouseleave", () => {
                resizeHandle.style.background = "transparent";
            });
            let startY = 0, startH = 0;
            const onMouseMove = (e) => {
                const newH = Math.max(300, startH + (e.clientY - startY));
                container.style.height = newH + "px";
                this.setSize?.([this.size[0], this.computeSize()[1]]);
                app.graph?.setDirtyCanvas?.(true);
            };
            const onMouseUp = () => {
                document.removeEventListener("mousemove", onMouseMove);
                document.removeEventListener("mouseup", onMouseUp);
            };
            resizeHandle.addEventListener("mousedown", (e) => {
                e.preventDefault();
                e.stopPropagation();
                startY = e.clientY;
                startH = container.offsetHeight;
                document.addEventListener("mousemove", onMouseMove);
                document.addEventListener("mouseup", onMouseUp);
            });
            container.appendChild(resizeHandle);

            const widget = this.addDOMWidget("js3d_viewer", "custom", container, {
                serialize: false,
                hideOnZoom: false,
            });

            this._js3dIframe = iframe;
            this._js3dContainer = container;
            this._js3dCurrentFile = null;
            this._js3dBaseUrl = baseUrl;
            this._js3dSnapshotData = null;

            const self = this;

            window.addEventListener("message", (e) => {
                if (e.source !== iframe.contentWindow) return;
                const msg = e.data;
                if (!msg || !msg.type) return;

                if (msg.type === "js3d_snapshot") {
                    self._js3dSnapshotData = JSON.stringify({
                        image: msg.image || "",
                        mask: msg.mask || "",
                        normal: msg.normal || "",
                        camera: msg.camera || {},
                    });
                    const snapWidget = self.widgets?.find(
                        (w) => w.name === "snapshot_data"
                    );
                    if (snapWidget) {
                        snapWidget.value = self._js3dSnapshotData;
                    }
                }

                if (msg.type === "js3d_ready") {
                    self._tryLoadCurrentFile();
                }
            });

            this._js3dLastBgUrl = null;

            this._pollInterval = setInterval(() => {
                self._tryLoadCurrentFile();

                if (isLoader) {
                    const bgUrl = findBackgroundImageUrl(self);
                    if (bgUrl !== self._js3dLastBgUrl) {
                        self._js3dLastBgUrl = bgUrl;
                        self._js3dIframe?.contentWindow?.postMessage(
                            { type: "js3d_set_background", url: bgUrl },
                            "*"
                        );
                    }
                }
            }, 1500);
        };

        nodeType.prototype._tryLoadCurrentFile = function () {
            if (!this._js3dIframe?.contentWindow) return;

            let filePath = "";
            if (isLoader) {
                const fileWidget = this.widgets?.find(
                    (w) => w.name === "model_file"
                );
                if (fileWidget) filePath = fileWidget.value;
            } else {
                const pathWidget = this.widgets?.find(
                    (w) => w.name === "mesh_path"
                );
                if (pathWidget) filePath = pathWidget.value;
            }

            if (!filePath || filePath === "none" || filePath === this._js3dCurrentFile)
                return;

            this._js3dCurrentFile = filePath;

            const ext = filePath.split(".").pop().toLowerCase();
            const baseUrl = this._js3dBaseUrl;

            let viewerUrl;
            if (ext === "splat") {
                viewerUrl = baseUrl + "/html/splat_viewer.html";
            } else {
                viewerUrl = baseUrl + "/html/viewer3d.html";
            }

            const currentSrc = this._js3dIframe.src || "";
            const targetPage = viewerUrl.split("/").pop();
            const needsSwitch = !currentSrc.includes(targetPage);

            if (needsSwitch) {
                this._js3dIframe.src = viewerUrl;
                this._js3dIframe.onload = () => {
                    setTimeout(() => {
                        this._sendLoadCommand(filePath, ext);
                    }, 800);
                };
            } else {
                this._sendLoadCommand(filePath, ext);
            }
        };

        nodeType.prototype._sendLoadCommand = function (filePath, ext) {
            if (!this._js3dIframe?.contentWindow) return;

            const fileUrl = buildViewUrl(filePath);
            if (!fileUrl) return;

            this._js3dIframe.contentWindow.postMessage(
                {
                    type: "js3d_load",
                    url: fileUrl,
                    format: ext,
                    filename: filePath,
                },
                "*"
            );
        };

        nodeType.prototype.onExecuted = function (output) {
            if (!isLoader) {
                const data = output?.js3d_preview;
                if (data && data[0]) {
                    try {
                        const info = JSON.parse(data[0]);
                        if (info.mesh_path) {
                            const pathWidget = this.widgets?.find(
                                (w) => w.name === "mesh_path"
                            );
                            if (pathWidget) {
                                pathWidget.value = info.mesh_path;
                            }
                            this._js3dCurrentFile = null;
                            this._tryLoadCurrentFile();
                        }
                        if (info.camera_info && info.camera_info !== "{}") {
                            const self = this;
                            setTimeout(() => {
                                try {
                                    const cam = typeof info.camera_info === "string"
                                        ? JSON.parse(info.camera_info) : info.camera_info;
                                    self._js3dIframe?.contentWindow?.postMessage({
                                        type: "js3d_set_camera",
                                        camera: cam,
                                    }, "*");
                                } catch (_) {}
                            }, 1500);
                        }
                    } catch (_) {}
                }
            }
        };

        const origOnRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            if (this._pollInterval) clearInterval(this._pollInterval);
            origOnRemoved?.apply(this, arguments);
        };
    },
});

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

async function resolveViewerUrl(htmlFile) {
    const candidates = [
        `/js3d/viewer/${htmlFile}`,
        `${getExtensionBaseUrl()}/html/${htmlFile}`,
        `/extensions/js-3d-viewer-control-comfy/html/${htmlFile}`,
    ];
    for (const url of candidates) {
        try {
            const r = await fetch(url, { method: "HEAD" });
            if (r.ok) return url;
        } catch (_) {}
    }
    return candidates[0];
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

    async setup() {
        try {
            const orig = app.graphToPrompt;
            if (typeof orig === "function") {
                app.graphToPrompt = async function (...args) {
                    try {
                        const nodes = app.graph?._nodes?.filter(
                            (n) =>
                                n.type === "JS3D_Load3DController" &&
                                n._js3dIframe?.contentWindow
                        );
                        if (nodes && nodes.length > 0) {
                            await Promise.all(
                                nodes.map(
                                    (node) =>
                                        new Promise((resolve) => {
                                            let done = false;
                                            const handler = (e) => {
                                                if (done) return;
                                                if (
                                                    e.source !==
                                                    node._js3dIframe?.contentWindow
                                                )
                                                    return;
                                                if (e.data?.type !== "js3d_snapshot")
                                                    return;
                                                done = true;
                                                window.removeEventListener(
                                                    "message",
                                                    handler
                                                );
                                                const snap = JSON.stringify({
                                                    image: e.data.image || "",
                                                    mask: e.data.mask || "",
                                                    normal: e.data.normal || "",
                                                    camera: e.data.camera || {},
                                                });
                                                node._js3dSnapshotData = snap;
                                                const w = node.widgets?.find(
                                                    (w) => w.name === "snapshot_data"
                                                );
                                                if (w) w.value = snap;
                                                resolve();
                                            };
                                            window.addEventListener("message", handler);
                                            const wWidget = node.widgets?.find(
                                                (w) => w.name === "width"
                                            );
                                            const hWidget = node.widgets?.find(
                                                (w) => w.name === "height"
                                            );
                                            node._js3dIframe.contentWindow.postMessage(
                                                {
                                                    type: "js3d_capture",
                                                    width: wWidget
                                                        ? parseInt(wWidget.value)
                                                        : undefined,
                                                    height: hWidget
                                                        ? parseInt(hWidget.value)
                                                        : undefined,
                                                },
                                                "*"
                                            );
                                            setTimeout(() => {
                                                if (!done) {
                                                    done = true;
                                                    window.removeEventListener(
                                                        "message",
                                                        handler
                                                    );
                                                    resolve();
                                                }
                                            }, 3000);
                                        })
                                )
                            );
                        }
                    } catch (_) {}
                    return orig.apply(this, args);
                };
            }
        } catch (e) {
            console.warn("[JS3D] setup hook skipped:", e);
        }
    },

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

            resolveViewerUrl("viewer3d.html").then((url) => {
                iframe.src = url;
            });
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

            const htmlFile = ext === "splat" ? "splat_viewer.html" : "viewer3d.html";

            const currentSrc = this._js3dIframe.src || "";
            const targetPage = htmlFile;
            const needsSwitch = !currentSrc.includes(targetPage);

            if (needsSwitch) {
                resolveViewerUrl(htmlFile).then((url) => {
                    this._js3dIframe.src = url;
                    this._js3dIframe.onload = () => {
                        setTimeout(() => {
                            this._sendLoadCommand(filePath, ext);
                        }, 800);
                    };
                });
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

app.registerExtension({
    name: "JS3D.ExportDownload",

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (nodeData.name !== "JS3D_ExportFormat") return;

        const origOnExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (output) {
            origOnExecuted?.apply(this, arguments);

            const data = output?.js3d_export;
            if (!data || !data[0]) return;

            const info = data[0];
            const downloadUrl = `/view?filename=${encodeURIComponent(info.filename)}&type=${info.type}&subfolder=${encodeURIComponent(info.subfolder || "")}`;

            let dlWidget = this.widgets?.find((w) => w.name === "_js3d_download");
            if (dlWidget) {
                dlWidget.value = info.filename;
                if (dlWidget._btn) dlWidget._btn.onclick = () => {
                    const a = document.createElement("a");
                    a.href = downloadUrl;
                    a.download = info.filename;
                    a.click();
                };
                return;
            }

            const container = document.createElement("div");
            container.style.cssText =
                "display:flex; gap:8px; align-items:center; padding:4px 0;";

            const btn = document.createElement("button");
            btn.textContent = `Download ${info.filename}`;
            btn.style.cssText = `
                flex:1; padding:8px 12px; border:1px solid #6a9eff; border-radius:6px;
                background:rgba(80,120,200,0.2); color:#9ac0ff; font-size:12px;
                cursor:pointer; font-weight:500; text-align:center;
            `;
            btn.addEventListener("mouseenter", () => {
                btn.style.background = "rgba(80,120,200,0.4)";
            });
            btn.addEventListener("mouseleave", () => {
                btn.style.background = "rgba(80,120,200,0.2)";
            });
            btn.onclick = () => {
                const a = document.createElement("a");
                a.href = downloadUrl;
                a.download = info.filename;
                a.click();
            };
            container.appendChild(btn);

            const sizeLabel = document.createElement("span");
            sizeLabel.style.cssText = "font-size:10px; color:#666; white-space:nowrap;";
            if (info.size) {
                const kb = (info.size / 1024).toFixed(1);
                sizeLabel.textContent = kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`;
            } else if (info.note) {
                sizeLabel.textContent = info.note;
            }
            container.appendChild(sizeLabel);

            const widget = this.addDOMWidget("_js3d_download", "custom", container, {
                serialize: false,
                hideOnZoom: false,
            });
            widget._btn = btn;
            widget.value = info.filename;

            this.setSize?.(this.computeSize());
            app.graph?.setDirtyCanvas?.(true);
        };
    },
});

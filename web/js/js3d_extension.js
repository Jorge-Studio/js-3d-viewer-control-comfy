import { app } from "../../../scripts/app.js";

const VIEWER_NODES = ["JS3D_Load3DController", "JS3D_Preview3D"];

function getExtensionBaseUrl() {
    try {
        return new URL("..", import.meta.url).href.replace(/\/$/, "");
    } catch (_) {
        return "/extensions/js-3d-viewer-control-comfy";
    }
}

app.registerExtension({
    name: "JS3D.ViewerControl",

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (!VIEWER_NODES.includes(nodeData.name)) return;

        const isLoader = nodeData.name === "JS3D_Load3DController";

        const origOnCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origOnCreated?.apply(this, arguments);

            const container = document.createElement("div");
            container.style.cssText = `
                width: 100%;
                height: 500px;
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

            this._pollInterval = setInterval(() => {
                self._tryLoadCurrentFile();
            }, 1000);
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
            const isSplat = ext === "splat";

            let viewerUrl;
            if (isSplat) {
                viewerUrl = baseUrl + "/html/splat_viewer.html";
            } else if (ext === "ply") {
                viewerUrl = baseUrl + "/html/viewer3d.html";
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
                    }, 500);
                };
            } else {
                this._sendLoadCommand(filePath, ext);
            }
        };

        nodeType.prototype._sendLoadCommand = function (filePath, ext) {
            if (!this._js3dIframe?.contentWindow) return;

            let fileUrl;
            if (filePath.startsWith("/") || filePath.startsWith("http")) {
                fileUrl = filePath;
            } else {
                fileUrl = `/view?filename=${encodeURIComponent(filePath)}&type=input&subfolder=`;
            }

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

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("repoBlueprintDesktop", {
  apiBaseUrl: "http://127.0.0.1:8002/api",
  isDesktop: true,
  platform: "macos",
  saveFile: (options) => ipcRenderer.invoke("desktop:save-file", options),
});

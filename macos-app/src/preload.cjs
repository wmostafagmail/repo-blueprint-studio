const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("repoBlueprintDesktop", {
  apiBaseUrl: "http://127.0.0.1:8002/api",
  isDesktop: true,
  platform: "macos",
});

const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const path = require("path");

const APP_ROOT = path.resolve(__dirname, "..", "..");
const FRONTEND_ROOT = path.join(APP_ROOT, "frontend");
const BACKEND_ROOT = path.join(APP_ROOT, "backend");
const FRONTEND_DIST = path.join(FRONTEND_ROOT, "dist", "index.html");
const BACKEND_PORT = 8002;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const FRONTEND_DEV_URL = process.env.REPO_BLUEPRINT_DESKTOP_URL || "http://127.0.0.1:3000/";

let backendProcess = null;

ipcMain.handle("desktop:save-file", async (_event, { base64, defaultFileName }) => {
  const { canceled, filePath } = await dialog.showSaveDialog({
    defaultPath: defaultFileName,
    filters: [{ name: "Markdown", extensions: ["md"] }],
  });

  if (canceled || !filePath) {
    return false;
  }

  const buffer = Buffer.from(base64, "base64");
  fs.writeFileSync(filePath, buffer);
  return true;
});

function isBackendReachable() {
  return new Promise((resolve) => {
    const request = http.get(`${BACKEND_URL}/api/health`, (response) => {
      response.resume();
      resolve(response.statusCode && response.statusCode < 500);
    });

    request.on("error", () => resolve(false));
    request.setTimeout(1200, () => {
      request.destroy();
      resolve(false);
    });
  });
}

function resolvePythonExecutable() {
  const candidates = [
    path.join(BACKEND_ROOT, ".venv", "bin", "python3"),
    path.join(BACKEND_ROOT, ".venv", "bin", "python"),
    "python3",
  ];

  for (const candidate of candidates) {
    if (candidate.includes(path.sep)) {
      if (fs.existsSync(candidate)) {
        return candidate;
      }
      continue;
    }
    return candidate;
  }

  return "python3";
}

async function startBackend() {
  if (backendProcess) {
    return;
  }

  if (await isBackendReachable()) {
    return;
  }

  const pythonExecutable = resolvePythonExecutable();
  backendProcess = spawn(
    pythonExecutable,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(BACKEND_PORT)],
    {
      cwd: BACKEND_ROOT,
      env: {
        ...process.env,
        PYTHONPATH: BACKEND_ROOT,
      },
      stdio: "inherit",
    }
  );

  backendProcess.on("exit", () => {
    backendProcess = null;
  });
}

async function createMainWindow() {
  await startBackend();

  const mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 760,
    title: "Repo Blueprint Studio",
    backgroundColor: "#f8fafc",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  const useDevServer = !app.isPackaged && process.env.REPO_BLUEPRINT_DESKTOP_USE_DEV_SERVER !== "false";

  if (useDevServer) {
    await mainWindow.loadURL(FRONTEND_DEV_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
    return;
  }

  if (!fs.existsSync(FRONTEND_DIST)) {
    await dialog.showMessageBox(mainWindow, {
      type: "error",
      title: "Frontend build missing",
      message: "The desktop app could not find frontend/dist/index.html.",
      detail: "Run `npm --prefix ../frontend run build` from `macos-app/` before starting the packaged desktop shell.",
    });
    return;
  }

  await mainWindow.loadFile(FRONTEND_DIST);
}

app.whenReady().then(async () => {
  await createMainWindow();

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createMainWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill("SIGTERM");
    backendProcess = null;
  }
});

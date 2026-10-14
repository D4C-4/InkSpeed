const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("node:child_process");
const path = require("node:path");

const projectRoot = path.resolve(__dirname, "..", "..");
const python = path.join(projectRoot, ".venv", "Scripts", "python.exe");
const apiUrl = "http://127.0.0.1:5000/api/health";
const webUrl = "http://127.0.0.1:5173";

let apiProcess;
let webProcess;

function startProcess(command, args, cwd) {
  const child = spawn(command, args, {
    cwd,
    env: { ...process.env, BROWSER: "none" },
    shell: false,
    windowsHide: true,
    stdio: "pipe",
  });
  child.stdout.on("data", (data) => process.stdout.write(data));
  child.stderr.on("data", (data) => process.stderr.write(data));
  child.on("error", (error) => console.error(`Unable to start ${command}:`, error));
  return child;
}

async function waitFor(url, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The child process may still be starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function createWindow() {
  apiProcess = startProcess(python, ["main.py"], projectRoot);
  const npmCommand = process.platform === "win32" ? process.env.ComSpec : "npm";
  const npmArgs = process.platform === "win32"
    ? ["/d", "/s", "/c", "npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort"]
    : ["run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"];
  webProcess = startProcess(
    npmCommand,
    npmArgs,
    path.resolve(__dirname, ".."),
  );

  try {
    await waitFor(apiUrl);
    await waitFor(webUrl);
  } catch (error) {
    dialog.showErrorBox("InkSpeed could not start", error.message);
    app.quit();
    return;
  }

  const window = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    backgroundColor: "#f4efe0",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  await window.loadURL(webUrl);
}

function stopProcess(child) {
  if (child && !child.killed) child.kill();
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => {
  stopProcess(apiProcess);
  stopProcess(webProcess);
  if (process.platform !== "darwin") app.quit();
});
app.on("before-quit", () => {
  stopProcess(apiProcess);
  stopProcess(webProcess);
});

/**
 * PSO2NGS LCT — Electron Main Process
 * + System Tray support
 * + Auto-update via electron-updater + GitHub Releases
 */

const { app, BrowserWindow, ipcMain, dialog, Tray, Menu } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const { autoUpdater } = require('electron-updater')

let mainWindow    = null
let serverProcess = null
let tray          = null

// ── Auto-Updater Config ───────────────────────────────────────────────────────
autoUpdater.autoDownload         = true   // ดาวน์โหลดอัตโนมัติเลย
autoUpdater.autoInstallOnAppQuit = false  // ไม่ install เองตอนปิด ให้ user กดเอง

autoUpdater.on('update-available', () => {
  mainWindow?.webContents.send('update-available')
})

autoUpdater.on('update-downloaded', () => {
  mainWindow?.webContents.send('update-downloaded')
  tray?.displayBalloon({
    title: 'PSO2NGS LCT — มีอัพเดทใหม่!',
    content: 'ดาวน์โหลดเสร็จแล้ว กด "รีสตาร์ทและอัพเดท" ใน App',
    iconType: 'info'
  })
})

autoUpdater.on('error', (err) => {
  console.error('[AutoUpdater] Error:', err.message)
})

// ── Server Path Helpers ───────────────────────────────────────────────────────
function getServerExe() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'app.asar.unpacked', 'server', 'PSO2NGS_LCT_server.exe')
  }
  return null
}

function getServerPy() {
  return path.join(__dirname, 'server_files', 'PSO2NGS_LCT_server.py')
}

function getIconPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'app.asar.unpacked', 'app', 'server.ico')
  }
  return path.join(__dirname, 'server.ico')
}

// ── Start Python/EXE Server ───────────────────────────────────────────────────
function startServer() {
  const exe = getServerExe()
  if (exe) {
    serverProcess = spawn(exe, [], { detached: false, stdio: 'ignore', windowsHide: true })
  } else {
    serverProcess = spawn('python', [getServerPy()], { detached: false, stdio: 'inherit' })
  }
  serverProcess.on('error', (err) => console.error('[Server] Failed:', err.message))
  serverProcess.on('exit',  (code) => console.log('[Server] Exit:', code))
}

// ── System Tray ───────────────────────────────────────────────────────────────
function createTray() {
  tray = new Tray(getIconPath())
  tray.setToolTip('PSO2NGS LCT')
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Show', click: () => { mainWindow.show(); mainWindow.focus() } },
    { type: 'separator' },
    { label: 'Quit', click: () => { app.isQuitting = true; app.quit() } }
  ]))
  tray.on('double-click', () => { mainWindow.show(); mainWindow.focus() })
}

// ── Main Window ───────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 800, minWidth: 900, minHeight: 600,
    frame: false, backgroundColor: '#010a18',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, nodeIntegration: false,
    },
    show: false, autoHideMenuBar: true,
    icon: path.join(__dirname, 'server.ico'),
  })

  mainWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault()
      mainWindow.hide()
      tray.displayBalloon({ title: 'PSO2NGS LCT', content: 'Still running in the system tray.', iconType: 'info' })
    }
  })

  mainWindow.on('maximize',   () => mainWindow.webContents.send('win-state', { maximized: true }))
  mainWindow.on('unmaximize', () => mainWindow.webContents.send('win-state', { maximized: false }))

  const tryLoad = (attempt = 0) => {
    const http = require('http')
    http.get('http://127.0.0.1:5000', () => {
      mainWindow.loadURL('http://127.0.0.1:5000')
    }).on('error', () => {
      if (attempt < 30) setTimeout(() => tryLoad(attempt + 1), 500)
      else mainWindow.loadURL(`data:text/html,<h2 style="color:red;font-family:sans-serif;padding:40px">Cannot connect to server.<br><small>Please restart the app.</small></h2>`)
    })
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    // เช็คอัพเดทหลัง window โชว์ (เฉพาะตอน packaged จริง)
    if (app.isPackaged) {
      setTimeout(() => autoUpdater.checkForUpdates(), 3000)
    }
  })

  tryLoad()
}

// ── IPC — Window Controls ─────────────────────────────────────────────────────
ipcMain.handle('win-minimize',     () => mainWindow?.minimize())
ipcMain.handle('win-maximize',     () => { if (mainWindow?.isMaximized()) mainWindow.unmaximize(); else mainWindow?.maximize() })
ipcMain.handle('win-is-maximized', () => mainWindow?.isMaximized() ?? false)
ipcMain.handle('win-close',        () => mainWindow?.hide())

// ── IPC — Folder Picker ───────────────────────────────────────────────────────
ipcMain.handle('pick-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select PSO2NGS Chat Log Folder',
  })
  return result.canceled ? null : result.filePaths[0]
})

// ── IPC — File Picker ─────────────────────────────────────────────────────────
ipcMain.handle('pick-file', async (e, opts) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    title: opts?.title || 'Select File',
    filters: opts?.filters || [{ name: 'All Files', extensions: ['*'] }],
  })
  return result.canceled ? null : result.filePaths[0]
})

// ── IPC — Auto Update ─────────────────────────────────────────────────────────
ipcMain.handle('install-update', () => {
  app.isQuitting = true
  autoUpdater.quitAndInstall()
})

ipcMain.handle('check-for-updates', () => {
  if (app.isPackaged) autoUpdater.checkForUpdates()
})

// ── App Events ────────────────────────────────────────────────────────────────
app.isQuitting = false

app.whenReady().then(() => {
  startServer()
  createTray()
  createWindow()
})

app.on('window-all-closed', () => {})

app.on('before-quit', () => {
  app.isQuitting = true
  if (serverProcess) {
    try {
      const { execSync } = require('child_process')
      execSync(`taskkill /pid ${serverProcess.pid} /T /F`, { stdio: 'ignore' })
    } catch (e) {}
    serverProcess = null
  }
})

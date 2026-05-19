import { app, BrowserWindow, ipcMain } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'
import { spawn } from 'child_process'
import type { ChildProcess } from 'child_process'
import { isDev } from './util.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

let flaskProcess: ChildProcess | null = null

function startFlask(): void {
  const scriptPath = isDev()
    ? path.join(process.cwd(), 'python', 'app.py')
    : path.join(process.resourcesPath, 'python', 'app.py')

  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'

  flaskProcess = spawn(pythonCmd, [scriptPath], {
    stdio: 'pipe',
    env: { ...process.env },
  })

  flaskProcess.stdout?.on('data', (data: Buffer) => {
    console.log(`[Flask] ${data.toString().trim()}`)
  })

  flaskProcess.stderr?.on('data', (data: Buffer) => {
    console.error(`[Flask] ${data.toString().trim()}`)
  })

  flaskProcess.on('close', (code: number | null) => {
    console.log(`[Flask] process exited with code ${code}`)
    flaskProcess = null
  })
}

function stopFlask(): void {
  if (flaskProcess?.pid) {
    // On Windows, kill() only kills the parent — use taskkill to kill the full process tree
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(flaskProcess.pid), '/f', '/t'])
    } else {
      flaskProcess.kill('SIGTERM')
    }
    flaskProcess = null
  }
}

app.on('ready', () => {
  // In dev, Flask is started by `npm run dev` — only auto-spawn in production
  if (!isDev()) startFlask()

  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (isDev()) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(app.getAppPath(), '/dist-react/index.html'))
  }

  ipcMain.handle('get-app-version', () => app.getVersion())
})

app.on('before-quit', stopFlask)

app.on('window-all-closed', () => {
  stopFlask()
  if (process.platform !== 'darwin') app.quit()
})

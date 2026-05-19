import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electron', {
  flaskUrl: 'http://localhost:5000',
  getAppVersion: (): Promise<string> => ipcRenderer.invoke('get-app-version'),
  onFlaskReady: (cb: () => void) => {
    ipcRenderer.on('flask-ready', cb)
    return () => ipcRenderer.removeListener('flask-ready', cb)
  },
})

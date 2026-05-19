declare interface Window {
  electron: {
    flaskUrl: string
    getAppVersion: () => Promise<string>
    onFlaskReady: (cb: () => void) => () => void
  }
}

const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('widgetApi', {
  get:     ()   => ipcRenderer.invoke('widget:get'),
  onData:  cb   => ipcRenderer.on('widget:data', (_e, d) => cb(d)),
  close:   ()   => ipcRenderer.invoke('widget:close'),
  openApp: ()   => ipcRenderer.invoke('widget:focus')
});

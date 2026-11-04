const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('desktopAuth', {
  login:   hint => ipcRenderer.invoke('gauth:login', hint || ''),
  refresh: ()   => ipcRenderer.invoke('gauth:refresh'),
  logout:  ()   => ipcRenderer.invoke('gauth:logout')
});

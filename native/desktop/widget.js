// Виджет для компьютера: маленькое окошко поверх окон. Данные ему присылает главное окно (снимок из приложения).
const { app, BrowserWindow, ipcMain, screen } = require('electron');
const fs = require('fs');
const path = require('path');

let ctx = null, wwin = null, lastSnap = null, saveTimer = null;
const stateFile = () => path.join(app.getPath('userData'), 'widget.json');
function readState(){ try { return JSON.parse(fs.readFileSync(stateFile(), 'utf8')); } catch(_) { return {}; } }
function writeState(patch){ try { fs.writeFileSync(stateFile(), JSON.stringify(Object.assign(readState(), patch))); } catch(_) {} }

// Положение окошка запоминаем, но не даём ему оказаться за пределами экрана (например, после смены монитора)
function safeBounds(b){
  const def = { width: 300, height: 230 };
  if (!b || !Number.isFinite(b.x) || !Number.isFinite(b.y)) {
    const wa = screen.getPrimaryDisplay().workArea;
    return Object.assign(def, { x: wa.x + wa.width - def.width - 24, y: wa.y + 24 });
  }
  const vis = screen.getAllDisplays().some(d => {
    const a = d.workArea; return b.x + 40 < a.x + a.width && b.x + b.width - 40 > a.x && b.y + 20 < a.y + a.height && b.y + b.height - 20 > a.y;
  });
  return vis ? { x: b.x, y: b.y, width: Math.max(220, b.width || def.width), height: Math.max(140, b.height || def.height) }
             : safeBounds(null);
}

function openWidget(){
  if (wwin && !wwin.isDestroyed()) return;
  const b = safeBounds(readState().bounds);
  wwin = new BrowserWindow(Object.assign({}, b, {
    minWidth: 220, minHeight: 140, frame: false, alwaysOnTop: true, skipTaskbar: true, resizable: true,
    maximizable: false, fullscreenable: false, title: 'Мой универ — виджет', backgroundColor: '#f0f0f6', show: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, preload: path.join(__dirname, 'widget-preload.js') }
  }));
  wwin.setMenu(null);
  wwin.setAlwaysOnTop(true, 'floating');
  wwin.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  wwin.webContents.on('will-navigate', e => e.preventDefault());
  ctx.load(wwin, 'widget.html');
  wwin.once('ready-to-show', () => wwin && wwin.showInactive());
  const remember = () => { clearTimeout(saveTimer); saveTimer = setTimeout(() => { if (wwin && !wwin.isDestroyed()) writeState({ bounds: wwin.getBounds() }); }, 400); };
  wwin.on('moved', remember); wwin.on('resized', remember);
  wwin.on('closed', () => { wwin = null; });
  writeState({ open: true });
}
function closeWidget(){ if (wwin && !wwin.isDestroyed()) wwin.close(); wwin = null; }

function setup(c){
  ctx = c;   // { load(win, file), showMain() }
  // Главное окно присылает снимок и желаемое состояние (показывать окошко или нет)
  ipcMain.on('widget:update', (_e, snap, open) => {
    if (snap && typeof snap === 'object') lastSnap = snap;
    if (open) openWidget(); else if (wwin) { closeWidget(); writeState({ open: false }); }
    if (wwin && !wwin.isDestroyed() && lastSnap) wwin.webContents.send('widget:data', lastSnap);
  });
  ipcMain.handle('widget:get', () => lastSnap);
  ipcMain.handle('widget:close', () => { closeWidget(); writeState({ open: false }); ctx.notifyMain('widget:closed'); return true; });
  ipcMain.handle('widget:focus', () => { ctx.showMain(); return true; });
}
// при запуске приложения окошко возвращаем, если оно было включено
function restore(){ if (readState().open) openWidget(); }
const isOpen = () => !!(wwin && !wwin.isDestroyed());
module.exports = { setup, restore, isOpen };

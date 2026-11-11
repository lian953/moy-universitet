// Оболочка «Мой универ» для компьютера: окно + встроенный мини-сервер, который отдаёт сайт из папки www.
// Страница открывается по адресу http://localhost:47821 (так, как её ждёт вход Google), а не как файл.
const { app, BrowserWindow, shell, Menu, ipcMain } = require('electron');
const gauth = require('./gauth');
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 47821;
const ROOT = path.resolve(path.join(__dirname, 'www'));
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.webmanifest': 'application/manifest+json', '.png': 'image/png',
  '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.txt': 'text/plain; charset=utf-8'
};

function startServer(){
  return new Promise(resolve => {
    const server = http.createServer((req, res) => {
      let p;
      try { p = decodeURIComponent((req.url || '/').split('?')[0]); }
      catch(_) { res.writeHead(400); return res.end('Bad request'); }       // кривой адрес (например, «%») не должен ронять приложение
      if (p.includes('\0')){ res.writeHead(400); return res.end(); }
      if (p.endsWith('/')) p += 'index.html';
      const file = path.normalize(path.join(ROOT, p));
      if (file !== ROOT && !file.startsWith(ROOT + path.sep)){ res.writeHead(403); return res.end(); }
      fs.readFile(file, (err, data) => {
        if (err){ res.writeHead(404); return res.end('Not found'); }
        res.writeHead(200, { 'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream' });
        res.end(data);
      });
    });
    server.on('error', () => resolve(false));          // порт занят: откроем файл напрямую
    server.listen(PORT, '127.0.0.1', () => resolve(true));
  });
}

ipcMain.handle('gauth:login', (_e, hint) => gauth.login(String(hint || '')).catch(e => { throw new Error(e.message); }));
ipcMain.handle('gauth:refresh', () => gauth.refresh());
ipcMain.handle('gauth:logout', () => gauth.logout());

let win;
async function createWindow(){
  const served = await startServer();
  win = new BrowserWindow({
    width: 1100, height: 820, minWidth: 360, minHeight: 560,
    title: 'Мой универ', backgroundColor: '#f0f0f6', autoHideMenuBar: true,
    icon: path.join(__dirname, 'build', 'icon.png'),
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, preload: path.join(__dirname, 'preload.js') }
  });
  Menu.setApplicationMenu(null);
  // Внешние ссылки (и окно входа Google) — не наши: ссылки открываем в обычном браузере, окно Google разрешаем
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https:\/\/accounts\.google\.com\//.test(url)) return { action: 'allow' };
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  if (served) win.loadURL('http://localhost:' + PORT + '/index.html');
  else win.loadFile(path.join(ROOT, 'index.html'));
}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (win){ if (win.isMinimized()) win.restore(); win.focus(); } });
  app.whenReady().then(createWindow);
  app.on('window-all-closed', () => app.quit());
}

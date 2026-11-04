// Вход Google для приложения на компьютере: системный браузер + возврат на 127.0.0.1 (OAuth для «Desktop app», PKCE).
// Долгоживущий ключ (refresh token) хранится зашифрованным средствами ОС (safeStorage) в папке данных приложения.
const { app, shell, safeStorage } = require('electron');
const http = require('http');
const https = require('https');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const CFG = JSON.parse(fs.readFileSync(path.join(__dirname, 'google-desktop.json'), 'utf8'));
const SCOPE = 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile';
const b64u = b => b.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const storeFile = () => path.join(app.getPath('userData'), 'google-refresh.bin');

function saveRefresh(tok){
  try {
    const buf = safeStorage.isEncryptionAvailable() ? safeStorage.encryptString(tok) : Buffer.from(tok, 'utf8');
    fs.writeFileSync(storeFile(), buf);
  } catch(_) {}
}
function loadRefresh(){
  try {
    const buf = fs.readFileSync(storeFile());
    return safeStorage.isEncryptionAvailable() ? safeStorage.decryptString(buf) : buf.toString('utf8');
  } catch(_) { return ''; }
}
function clearRefresh(){ try { fs.unlinkSync(storeFile()); } catch(_) {} }

function post(params){
  const body = new URLSearchParams(Object.assign({ client_id: CFG.client_id, client_secret: CFG.client_secret }, params)).toString();
  return new Promise((resolve, reject) => {
    const req = https.request('https://oauth2.googleapis.com/token', {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': Buffer.byteLength(body) }
    }, res => {
      let d = ''; res.on('data', c => d += c);
      res.on('end', () => { try { const j = JSON.parse(d); res.statusCode >= 400 ? reject(Object.assign(new Error(j.error || 'http'), { body: j })) : resolve(j); } catch(e){ reject(e); } });
    });
    req.on('error', reject); req.write(body); req.end();
  });
}

const PAGE = t => `<!doctype html><meta charset="utf-8"><title>Мой универ</title><body style="font:18px system-ui;display:grid;place-items:center;height:100vh;margin:0;background:#f0f0f6;color:#222"><div style="text-align:center"><h2>${t}</h2><p>Эту вкладку можно закрыть и вернуться в приложение.</p></div>`;

let pending = null;
async function login(hint){
  if (!CFG.client_secret) throw new Error('config');
  if (pending) pending.close();
  const verifier = b64u(crypto.randomBytes(48)), state = b64u(crypto.randomBytes(16));
  const challenge = b64u(crypto.createHash('sha256').update(verifier).digest());
  const code = await new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      const u = new URL(req.url, 'http://127.0.0.1');
      if (u.pathname !== '/') { res.writeHead(404); return res.end(); }
      const err = u.searchParams.get('error'), got = u.searchParams.get('code');
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      if (u.searchParams.get('state') !== state || err || !got){
        res.end(PAGE('Вход не выполнен')); finish(); return reject(new Error(err === 'access_denied' ? 'access_denied' : 'popup_failed'));
      }
      res.end(PAGE('Готово! Вход выполнен')); finish(); resolve(got);
    });
    const timer = setTimeout(() => { finish(); reject(new Error('popup_timeout')); }, 5 * 60 * 1000);
    function finish(){ clearTimeout(timer); try { server.close(); } catch(_) {} pending = null; }
    pending = { close: () => { finish(); reject(new Error('popup_replaced')); } };
    server.listen(0, '127.0.0.1', () => {
      const redirect = 'http://127.0.0.1:' + server.address().port;
      server.redirect = redirect;
      const q = new URLSearchParams({
        client_id: CFG.client_id, redirect_uri: redirect, response_type: 'code', scope: SCOPE, state,
        code_challenge: challenge, code_challenge_method: 'S256', access_type: 'offline', prompt: 'consent'
      });
      if (hint) q.set('login_hint', hint);
      login.redirect = redirect;
      shell.openExternal('https://accounts.google.com/o/oauth2/v2/auth?' + q.toString());
    });
  });
  const tok = await post({ code, code_verifier: verifier, grant_type: 'authorization_code', redirect_uri: login.redirect });
  if (tok.refresh_token) saveRefresh(tok.refresh_token);
  return { access_token: tok.access_token, expires_in: tok.expires_in };
}

async function refresh(){
  const rt = loadRefresh();
  if (!rt || !CFG.client_secret) return null;
  try {
    const tok = await post({ refresh_token: rt, grant_type: 'refresh_token' });
    return { access_token: tok.access_token, expires_in: tok.expires_in };
  } catch(e){
    if (e.message === 'invalid_grant') clearRefresh();      // доступ отозван или истёк: нужен новый вход
    return null;
  }
}

async function logout(){
  const rt = loadRefresh();
  clearRefresh();
  if (rt) try { await new Promise(r => { const q = https.request('https://oauth2.googleapis.com/revoke?token=' + encodeURIComponent(rt), { method: 'POST' }, r); q.on('error', r); q.end(); }); } catch(_) {}
  return true;
}

module.exports = { login, refresh, logout };

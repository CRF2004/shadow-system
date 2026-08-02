/* ── Shadow CLI API + Auth ─────────────────────────────── */
const API = '/api';
const TOKEN_KEY = 'shadow_token';

function getToken(){ return localStorage.getItem(TOKEN_KEY) || ''; }
function setToken(t){ if(t){ localStorage.setItem(TOKEN_KEY, t); } else { localStorage.removeItem(TOKEN_KEY); } }
function isLoggedIn(){ return !!getToken(); }
function authHeaders(){
  const h = {'Content-Type':'application/json'};
  const t = getToken();
  if(t) h['Authorization'] = 'Bearer ' + t;
  return h;
}
async function apiGet(path){
  const r = await fetch(API + path, {headers: authHeaders()});
  if(!r.ok) throw new Error('HTTP '+r.status);
  return r.json();
}
async function apiPost(path, body){
  const r = await fetch(API + path, {
    method:'POST', headers: authHeaders(), body: JSON.stringify(body)
  });
  if(!r.ok) throw new Error('HTTP '+r.status);
  return r.json();
}
async function apiPostRaw(path, body){
  const r = await fetch(API + path, {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)
  });
  return r.json();
}

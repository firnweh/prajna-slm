// PRAJNA Auth Guard — include in every protected page
const AUTH = (() => {
  const KEY = 'prajna_token';

  function getToken()  { return localStorage.getItem(KEY); }
  function setToken(t) { localStorage.setItem(KEY, t); }
  function clearToken(){ localStorage.removeItem(KEY); }

  function parseJWT(token) {
    try { return JSON.parse(atob(token.split('.')[1])); }
    catch { return null; }
  }

  function getUser() {
    const t = getToken();
    if (!t) return null;
    const payload = parseJWT(t);
    if (!payload || payload.exp * 1000 < Date.now()) { clearToken(); return null; }
    return payload;
  }

  function requireAuth(allowedRoles) {
    const user = getUser();
    if (!user) { window.location.href = '/login.html'; return null; }
    if (allowedRoles && !allowedRoles.includes(user.role)) {
      window.location.href = '/portal.html';
      return null;
    }
    return user;
  }

  async function apiFetch(url, opts = {}) {
    const token = getToken();
    const res = await fetch(url, {
      ...opts,
      headers: {
        ...(opts.headers || {}),
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    });
    if (res.status === 401) { clearToken(); window.location.href = '/login.html'; }
    return res;
  }

  function logout() { clearToken(); window.location.href = '/login.html'; }

  return { getToken, setToken, clearToken, getUser, requireAuth, apiFetch, logout };
})();

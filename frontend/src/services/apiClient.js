import { invoke } from '@tauri-apps/api/core';

const DEFAULT_WEB_API_URL = 'http://localhost:8000';
const DESKTOP_TOKEN_HEADER = 'X-Emovest-Desktop-Token';

const normalizeBaseUrl = (value) => String(value || '').trim().replace(/\/+$/, '');

export let API_BASE_URL = normalizeBaseUrl(
  import.meta.env.VITE_API_URL || DEFAULT_WEB_API_URL,
);

let runtimeInfo = {
  mode: 'web-dev',
  apiBaseUrl: API_BASE_URL,
  appVersion: null,
  desktopToken: null,
};

const hasTauriRuntime = () => (
  typeof window !== 'undefined'
  && typeof window.__TAURI_INTERNALS__ === 'object'
);

const wait = (milliseconds) => new Promise((resolve) => {
  window.setTimeout(resolve, milliseconds);
});

export const isDesktopRuntime = () => runtimeInfo.mode === 'desktop';

export const getRuntimeApiInfo = () => ({
  mode: runtimeInfo.mode,
  apiBaseUrl: runtimeInfo.apiBaseUrl,
  appVersion: runtimeInfo.appVersion,
});

export const initializeApiRuntime = async () => {
  if (!hasTauriRuntime()) {
    return getRuntimeApiInfo();
  }

  const deadline = Date.now() + 35_000;
  let desktopInfo;
  while (!desktopInfo && Date.now() < deadline) {
    try {
      desktopInfo = await invoke('desktop_backend_info');
    } catch (error) {
      if (!String(error).includes('backend_not_ready')) throw error;
      await wait(150);
    }
  }
  if (!desktopInfo) {
    throw new Error('El servicio local agotó el tiempo de arranque.');
  }
  const apiBaseUrl = normalizeBaseUrl(desktopInfo?.apiBaseUrl);
  const desktopToken = String(desktopInfo?.desktopToken || '');

  if (!apiBaseUrl.startsWith('http://127.0.0.1:')) {
    throw new Error('El backend local devolvió una dirección no válida.');
  }
  if (desktopToken.length < 32) {
    throw new Error('El backend local no proporcionó una credencial válida.');
  }

  API_BASE_URL = apiBaseUrl;
  runtimeInfo = {
    mode: 'desktop',
    apiBaseUrl,
    appVersion: desktopInfo?.appVersion || null,
    desktopToken,
  };

  return getRuntimeApiInfo();
};

export const apiUrl = (path = '') => {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  const normalizedPath = String(path).startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
};

export const apiFetch = (path, init = {}) => {
  const url = apiUrl(path);
  const headers = new Headers(init.headers || {});

  if (
    runtimeInfo.mode === 'desktop'
    && runtimeInfo.desktopToken
    && (url === API_BASE_URL || url.startsWith(`${API_BASE_URL}/`))
  ) {
    headers.set(DESKTOP_TOKEN_HEADER, runtimeInfo.desktopToken);
  }

  return fetch(url, {
    ...init,
    headers,
  });
};

export const createAuthenticatedObjectUrl = async (path, { signal } = {}) => {
  if (!path) return null;
  if (/^(blob:|data:)/i.test(path)) return path;

  const token = sessionStorage.getItem('token');
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const resolvedUrl = apiUrl(path);
  if (!(resolvedUrl === API_BASE_URL || resolvedUrl.startsWith(`${API_BASE_URL}/`))) {
    return path;
  }

  const response = await apiFetch(resolvedUrl, { headers, signal });

  if (!response.ok) {
    throw new Error(`No se pudo cargar la imagen (${response.status}).`);
  }

  return URL.createObjectURL(await response.blob());
};

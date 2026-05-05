
const getApiBaseUrl = () => {
  if (import.meta.env.DEV) {
    return '';
  }
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  return `http://${hostname}:8000`;
};

export const API_BASE_URL = getApiBaseUrl();
export const SOCKET_URL = import.meta.env.DEV ? '' : getApiBaseUrl();

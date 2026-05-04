
const getApiBaseUrl = () => {
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  // 局域网访问时，使用相同的 IP 但端口固定为 8000
  return `http://${hostname}:8000`;
};

export const API_BASE_URL = getApiBaseUrl();
export const SOCKET_URL = getApiBaseUrl();


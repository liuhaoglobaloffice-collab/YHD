const API_BASE = import.meta.env?.VITE_API_BASE ?? '';

export async function apiGet(path: string) {
  const response = await fetch(`${API_BASE}${path}`);
  return response.json();
}

export async function apiPost(path: string, payload: Record<string, unknown>, token = '') {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  return response.json();
}

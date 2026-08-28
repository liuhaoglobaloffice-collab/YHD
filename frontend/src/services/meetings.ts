const API_BASE = import.meta.env?.VITE_API_BASE ?? '';
const API_PREFIX = '/api/v1';

function getToken(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export interface Meeting {
  id: string;
  title: string;
  date: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  meeting_id: string;
  sender: string;
  role: 'admin' | 'member';
  content: string;
  time: string;
}

export async function fetchMeetings(status?: string): Promise<{ meetings: Meeting[]; total: number }> {
  const params = status ? `?status=${status}` : '';
  const res = await fetch(`${API_BASE}${API_PREFIX}/meetings${params}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch meetings: ${res.status}`);
  return res.json();
}

export async function createMeeting(title: string, date: string): Promise<Meeting> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/meetings`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ title, date }),
  });
  if (!res.ok) throw new Error(`Failed to create meeting: ${res.status}`);
  return res.json();
}

export async function fetchMessages(meetingId: string): Promise<{ messages: Message[]; total: number }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/meetings/${meetingId}/messages`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch messages: ${res.status}`);
  return res.json();
}

export async function sendMessage(meetingId: string, sender: string, role: string, content: string): Promise<Message> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/meetings/${meetingId}/messages`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ sender, role, content }),
  });
  if (!res.ok) throw new Error(`Failed to send message: ${res.status}`);
  return res.json();
}

export async function generateSummary(meetingId: string): Promise<{ summary: string }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/meetings/${meetingId}/summary`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to generate summary: ${res.status}`);
  return res.json();
}

export async function updateMeeting(meetingId: string, patch: { title?: string; status?: string }): Promise<Meeting> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/meetings/${meetingId}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`Failed to update meeting: ${res.status}`);
  return res.json();
}

export async function updateMessage(meetingId: string, messageId: string, content: string): Promise<Message> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/meetings/${meetingId}/messages/${messageId}`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(`Failed to update message: ${res.status}`);
  return res.json();
}

export async function deleteMessage(meetingId: string, messageId: string): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/meetings/${meetingId}/messages/${messageId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to delete message: ${res.status}`);
}

export async function deleteMeeting(meetingId: string): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/meetings/${meetingId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to delete meeting: ${res.status}`);
}
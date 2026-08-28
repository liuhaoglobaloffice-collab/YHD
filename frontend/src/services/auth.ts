const AUTH_KEY = 'liuhao_auth_token';
const USER_KEY = 'liuhao_auth_user';

export interface AuthUser {
  id: number;
  username: string;
  full_name?: string | null;
  role: string;
  account_type?: string | null;
  tenant_id?: string | null;
}

export function saveAuthToken(token: string) {
  localStorage.setItem(AUTH_KEY, token);
}

export function getAuthToken() {
  return localStorage.getItem(AUTH_KEY) ?? '';
}

export function clearAuthToken() {
  localStorage.removeItem(AUTH_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isLoggedIn() {
  return Boolean(getAuthToken());
}

export function saveUser(user: AuthUser) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

/** 是否为子账号（受限只读） */
export function isSubAccount(): boolean {
  return getUser()?.account_type === 'sub';
}

/** 是否只读模式（子账号不可执行写操作） */
export function isReadonly(): boolean {
  return isSubAccount();
}

/** 拉取当前用户信息并缓存 */
export async function fetchMe(): Promise<AuthUser> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const res = await fetch(
      `${import.meta.env?.VITE_API_BASE ?? ''}/api/v1/auth/me`,
      {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
        signal: controller.signal,
      }
    );
    if (!res.ok) throw new Error(`Failed to fetch me: ${res.status}`);
    const user = await res.json();
    saveUser(user);
    return user;
  } finally {
    clearTimeout(timeoutId);
  }
}
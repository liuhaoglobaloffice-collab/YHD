import { apiGet, apiPost } from './api';
import { saveAuthToken, getAuthToken } from './auth';

export interface OnboardingPayload {
  enterprise_name: string;
  tenant_name: string;
  provider: string;
  model: string;
}

export async function registerUser(username: string, email: string, password: string) {
  return apiPost('/api/v1/productization/register', {
    username,
    email,
    password,
  });
}

export async function loginUser(username: string, password: string) {
  const token = await apiPost('/api/v1/productization/login', {
    username,
    password,
  });
  if (token?.access_token) {
    saveAuthToken(token.access_token);
  }
  return token;
}

export async function getCurrentUser() {
  return apiGet('/api/v1/productization/current-user');
}

export async function createEnterprise(payload: OnboardingPayload) {
  return apiPost('/api/v1/productization/enterprise', {
    enterprise_name: payload.enterprise_name,
    tenant_name: payload.tenant_name,
  }, getAuthToken());
}

export async function createTenant(payload: OnboardingPayload) {
  return apiPost('/api/v1/productization/tenant', {
    tenant_id: 'tenant-demo',
    tenant_name: payload.tenant_name,
    enterprise_name: payload.enterprise_name,
    admin_user: 'admin',
  }, getAuthToken());
}

export async function configureProvider(payload: OnboardingPayload) {
  return apiPost('/api/v1/productization/provider', {
    provider: payload.provider,
    model: payload.model,
    enabled: true,
  }, getAuthToken());
}

export async function createEmployee(name: string) {
  return apiPost('/api/v1/productization/employee', {
    name,
    role: 'assistant',
  }, getAuthToken());
}

export async function importKnowledge(documentName: string) {
  return apiPost('/api/v1/productization/knowledge', {
    document_name: documentName,
    source: 'demo',
  }, getAuthToken());
}

export async function runWorkflowDemo(workflowName: string) {
  return apiPost('/api/v1/productization/workflow-demo', {
    workflow_name: workflowName,
    demo: true,
  }, getAuthToken());
}

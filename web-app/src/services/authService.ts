import { apiClient } from '@/lib/apiClient';

export interface LoginPayload {
  email: string;
  password: string;
}

export const authService = {
  async getCsrfToken() {
    const response = await apiClient.get('/auth/csrf');
    return response.data;
  },

  async login(payload: LoginPayload) {
    const response = await apiClient.post('/auth/login', payload);
    return response.data;
  },

  async logout() {
    const response = await apiClient.post('/auth/logout');
    return response.data;
  },

  async getCurrentUser() {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },
};

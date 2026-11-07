import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true, // รองรับ Session Cookie ของ Backend
  headers: {
    'Content-Type': 'application/json',
  },
});

// แนบ CSRF Token อัตโนมัติจาก Cookie
apiClient.interceptors.request.use((config) => {
  if (typeof document !== 'undefined') {
    const match = document.cookie.match(new RegExp('(^| )csrf_access_token=([^;]+)'));
    if (match && config.headers) {
      config.headers['X-CSRF-Token'] = match[2];
    }
  }
  return config;
});

export const deviceService = {
  // ดึงรายการอุปกรณ์ทั้งหมดตาม Workspace
  getDevices: async (workspaceId: string) => {
    const response = await apiClient.get(`/workspaces/${workspaceId}/devices`);
    return response.data;
  },

  // ส่งคำสั่งควบคุมอุปกรณ์ (Device Command)
  controlDevice: async (workspaceId: string, deviceId: string, state: Record<string, any>) => {
    const response = await apiClient.post(`/workspaces/${workspaceId}/devices/${deviceId}/control`, state);
    return response.data;
  },
};

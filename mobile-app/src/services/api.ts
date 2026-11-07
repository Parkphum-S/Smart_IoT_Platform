import axios from 'axios';

export const mobileApi = axios.create({
  baseURL: 'http://192.168.1.73:8000/api/v1',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

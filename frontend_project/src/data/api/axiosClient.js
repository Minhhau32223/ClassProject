import axios from 'axios';
import { API_BASE_URL, STORAGE_KEYS } from '../../core/constants';

// Tạo axios instance dùng chung cho cả app
const axiosClient = axios.create({
    baseURL: API_BASE_URL,
    headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: tự động gắn JWT vào mỗi request
axiosClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

export default axiosClient;

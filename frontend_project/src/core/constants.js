// Các hằng số toàn cục của ứng dụng
// Dùng đường dẫn tương đối để khi expose frontend qua ngrok,
// Vite dev server có thể proxy API về backend local.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const ROUTES = {
    LOGIN: 'login',
    REGISTER: 'register',
    DASHBOARD: 'dashboard',
    CLASS_DETAIL: 'class_detail',
};

export const STORAGE_KEYS = {
    ACCESS_TOKEN: 'access_token',
    REFRESH_TOKEN: 'refresh_token',
    USERNAME: 'username',
    USER_ID: 'user_id',
};

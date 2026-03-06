import axiosClient from '../api/axiosClient';

// Service xử lý xác thực: đăng ký, đăng nhập
const authService = {
    login: (credentials) => axiosClient.post('/auth/login/', credentials),
    register: (userData) => axiosClient.post('/auth/register/', userData),
};

export default authService;

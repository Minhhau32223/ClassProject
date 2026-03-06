import { STORAGE_KEYS } from '../../core/constants';

// Custom hook quản lý trạng thái xác thực và thông tin người dùng
export function useAuth() {
    const isLoggedIn = () => !!localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);

    const getUser = () => ({
        username: localStorage.getItem(STORAGE_KEYS.USERNAME) || '',
        userId: localStorage.getItem(STORAGE_KEYS.USER_ID) || '',
    });

    const saveLogin = (accessToken, refreshToken, username) => {
        localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
        localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
        // Giải mã userId từ JWT payload
        try {
            const payload = JSON.parse(atob(accessToken.split('.')[1]));
            localStorage.setItem(STORAGE_KEYS.USER_ID, payload.user_id);
        } catch (_) { }
        localStorage.setItem(STORAGE_KEYS.USERNAME, username);
    };

    const logout = () => {
        Object.values(STORAGE_KEYS).forEach(k => localStorage.removeItem(k));
    };

    return { isLoggedIn, getUser, saveLogin, logout };
}

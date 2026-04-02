import axiosClient from '../api/axiosClient';

// Service quản lý điểm danh
const attendanceService = {
    // Giáo viên tạo phiên điểm danh mới
    createSession: (classId, data) =>
        axiosClient.post(`/classes/${classId}/attendance/sessions/`, data),

    // Lấy toàn bộ phiên (dùng cho giáo viên xem lịch sử)
    getSessions: (classId) =>
        axiosClient.get(`/classes/${classId}/attendance/sessions/`),

    // Lấy phiên đang Active (dùng cho học viên check-in)
    getActiveSessions: (classId) =>
        axiosClient.get(`/classes/${classId}/attendance/sessions/?active=true`),

    // Học viên check-in bằng ảnh khuôn mặt
    checkIn: (classId, sessionId, formData) =>
        axiosClient.post(`/classes/${classId}/attendance/sessions/${sessionId}/checkin/`, formData),

    // Lấy thống kê điểm danh của lớp
    getStats: (classId) => axiosClient.get(`/classes/${classId}/attendance/stats/`),
};

export default attendanceService;

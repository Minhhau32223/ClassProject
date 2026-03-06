import axiosClient from '../api/axiosClient';

// Service quản lý điểm danh
const attendanceService = {
    createSession: (classId, data) =>
        axiosClient.post(`/classes/${classId}/attendance/sessions/`, data),
    checkIn: (classId, sessionId, formData) =>
        axiosClient.post(
            `/classes/${classId}/attendance/sessions/${sessionId}/checkin/`,
            formData,
            { headers: { 'Content-Type': 'multipart/form-data' } }
        ),
    getStats: (classId) => axiosClient.get(`/classes/${classId}/attendance/stats/`),
};

export default attendanceService;

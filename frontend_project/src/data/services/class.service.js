import axiosClient from '../api/axiosClient';

// Service quản lý lớp học
const classService = {
    create: (data) => axiosClient.post('/classes/create/', data),
    join: (data) => axiosClient.post('/classes/join/', data),
    myClasses: () => axiosClient.get('/classes/my/'),
    getMembers: (classId) => axiosClient.get(`/classes/${classId}/members/`),
    validateFaceImage: (classId, formData) =>
        axiosClient.post(`/classes/${classId}/validate-face/`, formData),
    registerFace: (classId, formData) =>
        axiosClient.post(`/classes/${classId}/register-face/`, formData),
};

export default classService;

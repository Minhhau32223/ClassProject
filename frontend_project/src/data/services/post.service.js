import axiosClient from '../api/axiosClient';

// Service quản lý bài viết và bình luận
const postService = {
    list: (classId) => axiosClient.get(`/classes/${classId}/posts/`),
    create: (classId, data) => axiosClient.post(`/classes/${classId}/posts/`, data),
    addComment: (classId, postId, data) =>
        axiosClient.post(`/classes/${classId}/posts/${postId}/comments/`, data),
    uploadDocument: (classId, postId, data) =>
        axiosClient.post(`/classes/${classId}/posts/${postId}/documents/upload/`, data),
    getDocuments: (classId, postId) =>
        axiosClient.get(`/classes/${classId}/posts/${postId}/documents/`),
};

// Service quản lý tài liệu
const documentService = {
    list: (classId, postId) =>
        axiosClient.get(`/classes/${classId}/posts/${postId}/documents/`),
    upload: (classId, postId, data) =>
        axiosClient.post(`/classes/${classId}/posts/${postId}/documents/upload/`, data),
};

export { postService, documentService };

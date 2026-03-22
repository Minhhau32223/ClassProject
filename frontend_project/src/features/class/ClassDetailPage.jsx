import { useState, useEffect } from 'react';
import { postService } from '../../data/services/post.service';
import classService from '../../data/services/class.service';
import attendanceService from '../../data/services/attendance.service';
import {vi} from 'date-fns/locale';
import { formatDistanceToNow, set } from 'date-fns';

// Component hiển thị 1 bài viết + bình luận
function PostItem({ post, classId }) {
    const [expanded, setExpanded] = useState(false);
    const [comments, setComments] = useState(post.comments || []);
    const [comment, setComment] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [documents, setDocuments] = useState(post.documents || []);
    const [loadingDocs, setLoadingDocs] = useState(false);

    // Load documents when component mounts
    useEffect(() => {
        if (documents.length === 0 && !loadingDocs) {
            setLoadingDocs(true);
            postService.getDocuments(classId, post.id)
                .then(r => setDocuments(r.data))
                .catch(() => setDocuments([]))
                .finally(() => setLoadingDocs(false));
        }
    }, []);

    const submitComment = async (e) => {
        e.preventDefault();
        if (!comment.trim()) return;
        setSubmitting(true);
        try {
            const res = await postService.addComment(classId, post.id, { content: comment });
            setComments(prev => [...prev, res.data]);
            setComment('');
        } catch { }
        setSubmitting(false);
    };

    return (
        <div className="post-card">
            <div className="post-meta">
                <strong>{post.author_name}</strong> · <span style={{ color: '#64748b', marginLeft: 4 }}>
                {formatDistanceToNow(new Date(post.created_at), { addSuffix: true, locale: vi })}
            </span>
            </div>
            <div className="post-content">{post.content}</div>
            {/* Hiển thị documents if have any */}
            {documents && documents.length > 0 && (
                <div>
                    {documents.map(doc => (
                        <div key={doc.id} style={{ 
                            marginBottom: 15, 
                            padding: '10px 14px', 
                            background: '#f8fafc', 
                            borderRadius: 8, 
                            border: '1px solid #e2e8f0',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10
                        }}>
                            <span style={{ fontSize: 18 }}>📄</span>
                            <a 
                                href={doc.file_path} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                style={{ 
                                    textDecoration: 'none', 
                                    color: '#2563eb', 
                                    fontSize: 13, 
                                    fontWeight: 600,
                                    wordBreak: 'break-all' 
                                }}
                            >
                                {doc.file_name}
                            </a>
                        </div>
                    ))}
                </div>
            )}
            <div className="post-actions">
                <button
                    style={{ background: '#f1f5f9', border: 'none', borderRadius: 6, padding: '6px 12px', cursor: 'pointer', color: '#64748b', fontSize: 13 }}
                    onClick={() => setExpanded(!expanded)}
                >
                    💬 {comments.length} bình luận
                </button>
            </div>
            {expanded && (
                <>
                    <div className="comment-list">
                        {comments.length === 0 && <p style={{ color: '#94a3b8', fontSize: 13 }}>Chưa có bình luận.</p>}
                        {comments.map(c => (
                            <div className="comment-item" key={c.id}>
                                <span className="comment-user">{c.user_name}: </span>{c.content}
                                <small style={{ color: '#94a3b8', fontSize: 11, marginLeft: 10 }}>
                                    {formatDistanceToNow(new Date(c.created_at), { addSuffix: true, locale: vi })}
                                </small>
                            </div>
                        ))}
                    </div>
                    <form onSubmit={submitComment} style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                        <input
                            value={comment}
                            onChange={e => setComment(e.target.value)}
                            placeholder="Viết bình luận..."
                            style={{ flex: 1, padding: '7px 12px', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 13 }}
                        />
                        <button className="btn-sm btn-filled" type="submit" disabled={submitting}>Gửi</button>
                    </form>
                </>
            )}
        </div>
    );
}

// Component tab thống kê điểm danh
function StatsTab({ classId }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        attendanceService.getStats(classId)
            .then(res => setStats(res.data))
            .catch(() => setStats(null))
            .finally(() => setLoading(false));
    }, [classId]);

    if (loading) return <div className="loading">Đang tải thống kê...</div>;
    if (!stats) return <div className="card" style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>Không có dữ liệu hoặc bạn chưa đăng ký khuôn mặt.</div>;

    return (
        <div className="card">
            <p style={{ marginBottom: 16 }}><strong>Tổng số buổi học:</strong> {stats.class_sessions}</p>
            {stats.role === 'teacher' ? (
                <table>
                    <thead>
                        <tr><th>Sinh viên</th><th>Có mặt</th><th>Vắng</th><th>Tỷ lệ</th></tr>
                    </thead>
                    <tbody>
                        {stats.stats?.map((s, i) => (
                            <tr key={i}>
                                <td><strong>{s.student_name}</strong></td>
                                <td><span className="badge badge-green">{s.present_count}</span></td>
                                <td><span className="badge badge-gray">{s.absent_count}</span></td>
                                <td><strong>{s.attendance_rate}</strong></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            ) : (
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                    {[
                        { label: 'Buổi có mặt', value: stats.present_count, color: '#22c55e', bg: '#f0fdf4' },
                        { label: 'Buổi vắng', value: stats.absent_count, color: '#f97316', bg: '#fff7ed' },
                        { label: 'Tỷ lệ đi học', value: stats.attendance_rate, color: '#3B5BDB', bg: '#eff2ff' },
                    ].map(item => (
                        <div key={item.label} className="card" style={{ flex: 1, textAlign: 'center', background: item.bg }}>
                            <div style={{ fontSize: 26, fontWeight: 700, color: item.color }}>{item.value}</div>
                            <div style={{ color: '#64748b', fontSize: 13 }}>{item.label}</div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// Trang chi tiết lớp học
export default function ClassDetailPage({ cls, onBack, username }) {
    const [tab, setTab] = useState('posts');
    const [posts, setPosts] = useState([]);
    const [members, setMembers] = useState([]);
    const [loadingTab, setLoadingTab] = useState(false);
    const [newPost, setNewPost] = useState('');
    const [posting, setPosting] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null); //Luu filw

    const isCreator = cls.creator?.username === username || cls.role === 'Người tạo';

    useEffect(() => {
        setLoadingTab(true);
        if (tab === 'posts') {
            postService.list(cls.id).then(r => setPosts(r.data)).catch(() => { }).finally(() => setLoadingTab(false));
        } else if (tab === 'members') {
            classService.getMembers(cls.id).then(r => setMembers(r.data)).catch(() => { }).finally(() => setLoadingTab(false));
        } else {
            setLoadingTab(false);
        }
    }, [tab]);

    const handlePostSubmit = async (e) => {
        e.preventDefault();
        if (!newPost.trim() && !selectedFile) return;
        setPosting(true);
        try {
            // Step 1: Create the post with just content
            const r = await postService.create(cls.id, { content: newPost });
            
            // Step 2: If file selected, upload it as a document
            if (selectedFile && r.data.id) {
                const docFormData = new FormData();
                docFormData.append('file_name', selectedFile.name);
                docFormData.append('file_path', `/uploads/${selectedFile.name}`);
                docFormData.append('file', selectedFile);
                
                try {
                    await postService.uploadDocument(cls.id, r.data.id, docFormData);
                } catch (docErr) {
                    console.warn('Document upload failed, but post was created:', docErr);
                }
            }
            
            // Add the new post to the list with empty documents array
            setPosts(prev => [{ ...r.data, documents: [] }, ...prev]);
            setNewPost('');
            setSelectedFile(null);
        } catch { }
        setPosting(false);
    };

    const tabStyle = (t) => ({
        flex: 1,
        textAlign: 'center',
        padding: '10px 16px',
        border: 'none',
        borderRadius: 999,
        background: tab === t ? '#ffffff' : 'transparent',
        color: '#334155',
        fontWeight: 600,
        cursor: 'pointer',
        fontSize: 14,
        boxShadow: tab === t ? '0 2px 6px rgba(0,0,0,0.25)' : 'none',
        transition: '0.2s'
    });

    return (
        <div>
            <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#000000', fontSize: 16,fontWeight: 700 , cursor: 'pointer', marginBottom: 12 }}>
                ←     Quay lại
            </button>
        {/* Header lớp học */}
        <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            padding: '20px 24px',
            background: '#ffffff',
            borderRadius: 16,
            boxShadow: '0 6px 20px rgba(0,0,0,0.06)',
            marginBottom: 20
        }}>
            {/* LEFT */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                
                {/* Tên lớp + role */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>
                        {cls.class_name}
                    </h1>

                <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    background: isCreator ? '#e0edff' : '#dcfce7',
                    color: isCreator ? '#1d4ed8' : '#16a34a',
                    fontSize: 12,
                    padding: '5px 12px',
                    borderRadius: 999,
                    fontWeight: 600
                }}>
                    {isCreator ? 'Người tạo' : 'Thành viên'}
                </span>

                </div>

                {/* Mã lớp + số thành viên */}
                <div style={{ display: 'flex', gap: 16, fontSize: 15 }}>
                    <span>
                        Mã lớp: 
                        <span style={{
                            background: '#f1f5f9',
                            padding: '2px 8px',
                            borderRadius: 6,
                            marginLeft: 6,
                            fontWeight: 600
                        }}>
                            {cls.class_code}
                        </span>
                    </span>

                    <span style={{ color: '#64748b' }}>
                        {cls.member_count || 1} thành viên
                    </span>
                </div>
            </div>
        </div>

            {/* Tabs */}
            <div style={{display: 'inline-flex',background: '#d6dce3', borderRadius: 12,padding: 4, marginBottom: 20,  width: '100%' }}>
                <button style={tabStyle('posts')} onClick={() => setTab('posts')}>📋 Bài viết</button>
                <button style={tabStyle('members')} onClick={() => setTab('members')}>👥 Thành viên</button>
                <button style={tabStyle('stats')} onClick={() => setTab('stats')}>📊 Thống kê</button>
            </div>

            {/* Tab Bài viết */}
            {tab === 'posts' && (
                <>
                    {isCreator && (
                        <form onSubmit={handlePostSubmit} style={{ marginBottom: 20 }}>
                            <div className="card" style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
                                <textarea
                                    value={newPost}
                                    onChange={e => setNewPost(e.target.value)}
                                    placeholder="Đăng thông báo cho lớp học..."
                                    rows={3}
                                    style={{ flex: 1, padding: '10px 14px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, resize: 'vertical' }}
                                />
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                {/* Nút tải lên tài liệu giả lập bằng nhãn label */}
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                        <label style={{ 
                                            padding: '8px 12px', 
                                            background: '#f1f5f9', 
                                            borderRadius: 6, 
                                            cursor: 'pointer',
                                            fontSize: 13,
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 6,
                                            color: '#475569',
                                            border: '1px solid #e2e8f0'
                                        }}>
                                            📁 {selectedFile ? 'Đổi file' : 'Đính kèm tài liệu'}
                                            <input 
                                                type="file" 
                                                style={{ display: 'none' }} 
                                                onChange={(e) => setSelectedFile(e.target.files[0])} 
                                            />
                                        </label>
                                         <button className="btn-sm btn-filled" type="submit" disabled={posting}>
                                            {posting ? 'Đang đăng' : 'Đăng bài'}
                                        </button>
                                        
                                        {selectedFile && (
                                            <span style={{ fontSize: 12, color: '#22c55e', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                ✅ {selectedFile.name}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </form>
                    )}
                    {loadingTab ? (
                        <div className="loading">Đang tải bài viết...</div>
                    ) : posts.length === 0 ? (
                        <div className="card" style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>Chưa có bài viết nào.</div>
                    ) : (
                        posts.map(p => <PostItem key={p.id} post={p} classId={cls.id} />)
                    )}
                </>
            )}

            {/* Tab Thành viên */}
            {tab === 'members' && (
                <div className="card">
                    {loadingTab ? (
                        <div className="loading">Đang tải...</div>
                    ) : (
                        <>
                        <p style={{ marginBottom: 12 }}>
                            <strong>Tổng thành viên:</strong> {members.length}
                        </p>
                        
                        <table>
                            <thead>
                                <tr><th>Họ tên</th><th>Username</th><th>Khuôn mặt</th><th>Ngày tham gia</th></tr>
                            </thead>
                            <tbody>
                                {members.map(m => (
                                    <tr key={m.id}>
                                        <td><strong>{m.user.full_name}</strong></td>
                                        <td style={{ color: '#64748b' }}>@{m.user.username}</td>
                                        <td>
                                            <span
                                                style={{
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    gap: 6,
                                                    padding: '4px 10px',
                                                    borderRadius: 999,
                                                    fontSize: 12,
                                                    fontWeight: 600,
                                                    background: m.face_registered ? '#f0fdf4' : '#fef2f2',
                                                    color: m.face_registered ? '#16a34a' : '#dc2626'
                                                }}
                                            >
                                                {m.face_registered ? '✔ Đã xác thực' : '✖ Chưa xác thực'}
                                            </span>
                                        </td>
                                        <td style={{ color: '#94a3b8' }}>{new Date(m.joined_at).toLocaleDateString('vi-VN')}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        </>
                    )}
                </div>
            )}

            {/* Tab Thống kê */}
            {tab === 'stats' && <StatsTab classId={cls.id} />}
        </div>
    );
}

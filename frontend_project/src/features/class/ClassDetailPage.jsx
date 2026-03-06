import { useState, useEffect } from 'react';
import { postService } from '../../data/services/post.service';
import classService from '../../data/services/class.service';
import attendanceService from '../../data/services/attendance.service';

// Component hiển thị 1 bài viết + bình luận
function PostItem({ post, classId }) {
    const [expanded, setExpanded] = useState(false);
    const [comments, setComments] = useState(post.comments || []);
    const [comment, setComment] = useState('');
    const [submitting, setSubmitting] = useState(false);

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
                <strong>{post.author_name}</strong> · {new Date(post.created_at).toLocaleString('vi-VN')}
            </div>
            <div className="post-content">{post.content}</div>
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
        if (!newPost.trim()) return;
        setPosting(true);
        try {
            const r = await postService.create(cls.id, { content: newPost });
            setPosts(prev => [r.data, ...prev]);
            setNewPost('');
        } catch { }
        setPosting(false);
    };

    const tabStyle = (t) => ({
        padding: '9px 18px', border: 'none',
        background: tab === t ? '#eff2ff' : 'transparent',
        color: tab === t ? '#3B5BDB' : '#64748b',
        fontWeight: tab === t ? 700 : 500,
        borderRadius: 8, cursor: 'pointer', fontSize: 13,
    });

    return (
        <div>
            <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#3B5BDB', fontSize: 13, cursor: 'pointer', marginBottom: 12 }}>
                ← Quay lại
            </button>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 20 }}>
                <div style={{ flex: 1 }}>
                    <span className="class-card-code">{cls.class_code}</span>
                    <h1 style={{ fontSize: 20, fontWeight: 700 }}>{cls.class_name}</h1>
                    <p style={{ color: '#94a3b8', fontSize: 13 }}>Người tạo: {cls.creator?.full_name}</p>
                </div>
                <span className={`badge ${isCreator ? 'badge-blue' : 'badge-green'}`}>
                    {isCreator ? '👨‍🏫 Người tạo' : '🎓 Thành viên'}
                </span>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
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
                                <button className="btn-sm btn-filled" type="submit" disabled={posting}>
                                    {posting ? '...' : 'Đăng bài'}
                                </button>
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
                                            <span className={`badge ${m.face_registered ? 'badge-green' : 'badge-gray'}`}>
                                                {m.face_registered ? '✅ Đã đăng ký' : '⏳ Chưa'}
                                            </span>
                                        </td>
                                        <td style={{ color: '#94a3b8' }}>{new Date(m.joined_at).toLocaleDateString('vi-VN')}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            {/* Tab Thống kê */}
            {tab === 'stats' && <StatsTab classId={cls.id} />}
        </div>
    );
}

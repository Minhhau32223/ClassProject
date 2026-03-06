import { useState, useEffect } from 'react';
import classService from '../../data/services/class.service';
import Modal from '../../shared/components/Modal';

// Form tạo lớp học
function CreateClassForm({ onCreated, onClose }) {
    const [name, setName] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await classService.create({ class_name: name });
            onCreated(res.data);
            onClose();
        } catch {
            setError('Không thể tạo lớp. Vui lòng thử lại.');
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            {error && <div className="error-msg">{error}</div>}
            <div className="form-group">
                <label>Tên lớp học</label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="VD: Lập trình Web - SE101" required />
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading}>
                {loading ? 'Đang tạo...' : 'Tạo lớp'}
            </button>
        </form>
    );
}

// Form tham gia lớp học
function JoinClassForm({ onJoined, onClose }) {
    const [code, setCode] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await classService.join({ class_code: code.trim().toUpperCase() });
            onJoined(res.data);
            onClose();
        } catch (err) {
            setError(err.response?.data?.message || 'Mã lớp không hợp lệ.');
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            {error && <div className="error-msg">{error}</div>}
            <div className="form-group">
                <label>Mã lớp học</label>
                <input
                    value={code}
                    onChange={e => setCode(e.target.value)}
                    placeholder="VD: ABCD12"
                    maxLength={10}
                    required
                    style={{ textTransform: 'uppercase', letterSpacing: 2, fontWeight: 700 }}
                />
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading}>
                {loading ? 'Đang tham gia...' : 'Tham gia'}
            </button>
        </form>
    );
}

export default function DashboardPage({ onSelectClass, username }) {
    const [classes, setClasses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [showJoin, setShowJoin] = useState(false);

    useEffect(() => {
        classService.myClasses().then(res => {
            const { created_classes, joined_classes } = res.data;
            const all = [
                ...created_classes.map(c => ({ ...c, role: 'Người tạo' })),
                ...joined_classes.map(c => ({ ...c, role: 'Thành viên' })),
            ].filter((v, i, a) => a.findIndex(t => t.id === v.id) === i);
            setClasses(all);
        }).finally(() => setLoading(false));
    }, []);

    return (
        <div>
            <div className="page-header">
                <h1>Xin chào, {username}! 👋</h1>
                <p>Quản lý các lớp học của bạn tại đây</p>
            </div>

            <div className="actions-row">
                <button className="btn-outline" onClick={() => setShowCreate(true)}>＋ Tạo lớp học</button>
                <button className="btn-outline" style={{ borderColor: '#64748b', color: '#64748b' }} onClick={() => setShowJoin(true)}>
                    🔑 Tham gia lớp
                </button>
            </div>

            {loading ? (
                <div className="loading">Đang tải danh sách lớp học...</div>
            ) : classes.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '40px 24px', color: '#94a3b8' }}>
                    <div style={{ fontSize: 48, marginBottom: 12 }}>📚</div>
                    <p>Bạn chưa tham gia hoặc tạo lớp học nào.</p>
                </div>
            ) : (
                <div className="class-grid">
                    {classes.map(cls => (
                        <div className="class-card" key={cls.id} onClick={() => onSelectClass(cls)}>
                            <span className="class-card-code">{cls.class_code}</span>
                            <h3>{cls.class_name}</h3>
                            <p className="meta">Người tạo: {cls.creator?.full_name}</p>
                            <div style={{ marginTop: 10 }}>
                                <span className={`badge ${cls.role === 'Người tạo' ? 'badge-blue' : 'badge-green'}`}>
                                    {cls.role}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {showCreate && (
                <Modal title="Tạo lớp học mới" onClose={() => setShowCreate(false)}>
                    <CreateClassForm
                        onCreated={(c) => setClasses(prev => [...prev, { ...c, role: 'Người tạo' }])}
                        onClose={() => setShowCreate(false)}
                    />
                </Modal>
            )}
            {showJoin && (
                <Modal title="Tham gia lớp học" onClose={() => setShowJoin(false)}>
                    <JoinClassForm
                        onJoined={(data) => setClasses(prev => [...prev, { ...data.class_room, role: 'Thành viên' }])}
                        onClose={() => setShowJoin(false)}
                    />
                </Modal>
            )}
        </div>
    );
}

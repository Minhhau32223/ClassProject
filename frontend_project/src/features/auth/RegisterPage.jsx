import { useState } from 'react';
import authService from '../../data/services/auth.service';

export default function RegisterPage({ onGoLogin }) {
    const [form, setForm] = useState({
        full_name: '', username: '', email: '', password: '', password2: '',
    });
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (form.password !== form.password2) {
            setError('Mật khẩu xác nhận không khớp.');
            return;
        }
        setLoading(true);
        try {
            await authService.register({
                username: form.username,
                email: form.email,
                full_name: form.full_name,
                password: form.password,
            });
            setSuccess('Đăng ký thành công! Đang chuyển hướng...');
            setTimeout(onGoLogin, 1200);
        } catch (err) {
            const data = err.response?.data;
            if (data?.username) setError('Tên đăng nhập: ' + data.username.join(', '));
            else if (data?.email) setError('Email: ' + data.email.join(', '));
            else setError('Đăng ký thất bại. Vui lòng kiểm tra lại.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-logo">🎓</div>
                <h2>Đăng ký tài khoản</h2>
                <p className="subtitle">Tạo tài khoản mới để sử dụng hệ thống</p>

                {error && <div className="error-msg">{error}</div>}
                {success && <div style={{ color: 'green', fontSize: 13, marginBottom: 12 }}>{success}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Họ và tên</label>
                        <input name="full_name" placeholder="Nguyễn Văn A" value={form.full_name} onChange={handleChange} required />
                    </div>
                    <div className="form-group">
                        <label>Tên đăng nhập</label>
                        <input name="username" placeholder="username" value={form.username} onChange={handleChange} required />
                    </div>
                    <div className="form-group">
                        <label>Email</label>
                        <input name="email" type="email" placeholder="example@email.com" value={form.email} onChange={handleChange} required />
                    </div>
                    <div className="form-group">
                        <label>Mật khẩu</label>
                        <input name="password" type="password" placeholder="••••••••" value={form.password} onChange={handleChange} required />
                    </div>
                    <div className="form-group">
                        <label>Xác nhận mật khẩu</label>
                        <input name="password2" type="password" placeholder="••••••••" value={form.password2} onChange={handleChange} required />
                    </div>
                    <button className="btn btn-primary" type="submit" disabled={loading}>
                        {loading ? 'Đang đăng ký...' : 'Đăng ký'}
                    </button>
                </form>

                <p className="auth-toggle">
                    Đã có tài khoản? <a onClick={onGoLogin}>Đăng nhập</a>
                </p>
            </div>
        </div>
    );
}

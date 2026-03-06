import { useState } from 'react';
import authService from '../../data/services/auth.service';
import { useAuth } from '../../shared/hooks/useAuth';

export default function LoginPage({ onLogin, onGoRegister }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { saveLogin } = useAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const res = await authService.login({ username, password });
            saveLogin(res.data.access, res.data.refresh, username);
            onLogin();
        } catch {
            setError('Tên đăng nhập hoặc mật khẩu không đúng.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-logo">🎓</div>
                <h2>Đăng nhập</h2>
                <p className="subtitle">Đăng nhập để tiếp tục sử dụng hệ thống</p>

                {error && <div className="error-msg">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Email</label>
                        <input
                            type="text"
                            placeholder="example@email.com"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>Mật khẩu</label>
                        <input
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button className="btn btn-primary" type="submit" disabled={loading}>
                        {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
                    </button>
                </form>

                <p className="auth-toggle">
                    Chưa có tài khoản?{' '}
                    <a onClick={onGoRegister}>Đăng ký ngay</a>
                </p>
            </div>
        </div>
    );
}

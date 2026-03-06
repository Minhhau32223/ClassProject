import { ROUTES } from '../../core/constants';

// Sidebar điều hướng chính của ứng dụng
export default function Sidebar({ activeRoute, onNavigate, onLogout, username }) {
    const navItems = [
        { icon: '🏠', label: 'Lớp học của tôi', route: ROUTES.DASHBOARD },
    ];

    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="logo-icon">🎓</div>
                <span>EduApp</span>
            </div>

            <nav className="sidebar-nav">
                {navItems.map((item) => (
                    <div
                        key={item.route}
                        className={`nav-item ${activeRoute === item.route ? 'active' : ''}`}
                        onClick={() => onNavigate(item.route)}
                    >
                        <span className="nav-icon">{item.icon}</span>
                        {item.label}
                    </div>
                ))}
            </nav>

            <div className="sidebar-footer">
                <div className="user-info">
                    <div className="user-avatar">
                        {username ? username[0].toUpperCase() : 'U'}
                    </div>
                    <div>
                        <div className="user-name">{username || 'Người dùng'}</div>
                        <div className="user-email">Đã đăng nhập</div>
                    </div>
                </div>
                <button className="btn-logout" onClick={onLogout}>
                    🚪 Đăng xuất
                </button>
            </div>
        </aside>
    );
}

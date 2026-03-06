import { useState } from 'react';
import './index.css';

// Tầng features — mỗi feature độc lập
import LoginPage from './features/auth/LoginPage';
import RegisterPage from './features/auth/RegisterPage';
import DashboardPage from './features/dashboard/DashboardPage';
import ClassDetailPage from './features/class/ClassDetailPage';

// Shared components
import Sidebar from './shared/components/Sidebar';

// Core constants
import { ROUTES, STORAGE_KEYS } from './core/constants';
import { useAuth } from './shared/hooks/useAuth';

export default function App() {
  const { isLoggedIn, getUser, logout } = useAuth();
  const [route, setRoute] = useState(isLoggedIn() ? ROUTES.DASHBOARD : ROUTES.LOGIN);
  const [selectedClass, setSelectedClass] = useState(null);

  const user = getUser();

  const handleLogin = () => setRoute(ROUTES.DASHBOARD);

  const handleLogout = () => {
    logout();
    setRoute(ROUTES.LOGIN);
    setSelectedClass(null);
  };

  const handleSelectClass = (cls) => {
    setSelectedClass(cls);
    setRoute(ROUTES.CLASS_DETAIL);
  };

  const handleBack = () => {
    setSelectedClass(null);
    setRoute(ROUTES.DASHBOARD);
  };

  // ===== AUTH PAGES (không có Sidebar) =====
  if (route === ROUTES.LOGIN) {
    return <LoginPage onLogin={handleLogin} onGoRegister={() => setRoute(ROUTES.REGISTER)} />;
  }
  if (route === ROUTES.REGISTER) {
    return <RegisterPage onGoLogin={() => setRoute(ROUTES.LOGIN)} />;
  }

  // ===== MAIN APP (có Sidebar) =====
  const activeRoute = route === ROUTES.CLASS_DETAIL ? ROUTES.DASHBOARD : route;

  return (
    <div className="app-layout">
      <Sidebar
        activeRoute={activeRoute}
        onNavigate={(r) => { setRoute(r); setSelectedClass(null); }}
        onLogout={handleLogout}
        username={user.username}
      />
      <main className="main-content">
        {route === ROUTES.DASHBOARD && (
          <DashboardPage onSelectClass={handleSelectClass} username={user.username} />
        )}
        {route === ROUTES.CLASS_DETAIL && selectedClass && (
          <ClassDetailPage cls={selectedClass} onBack={handleBack} username={user.username} />
        )}
      </main>
    </div>
  );
}

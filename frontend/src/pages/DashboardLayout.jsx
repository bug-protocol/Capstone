import React, { useState, useEffect } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { MessageSquare, Plus, Activity, FileWarning, Moon, Sun, User, Trash2 } from 'lucide-react';
import api from '../api';
import './DashboardLayout.css';

const DashboardLayout = () => {
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');
  const [user, setUser] = useState(null);
  const [sessions, setSessions] = useState([]);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await api.get('/auth/me');
        setUser(res.data);
      } catch (err) {
        navigate('/auth');
      }
    };
    fetchUser();
  }, [navigate]);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await api.get('/chat/sessions');
        setSessions(res.data || []);
      } catch (err) {
        console.error("Failed to load sessions");
      }
    };
    fetchSessions();
  }, [location.pathname]); // Refresh sessions occasionally (naive way)

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    navigate('/auth');
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this chat session?")) return;

    try {
      await api.delete(`/chat/sessions/${sessionId}`);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (location.pathname === `/chat/${sessionId}`) {
        navigate('/');
      }
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-navbar">
        <h1 className="navbar-title">Capstone Agent</h1>
        <div className="navbar-right">
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
          </button>
          <div className="user-info">
            <User size={20} />
            <span>{user?.username || 'User'}</span>
          </div>
          <button onClick={handleLogout} className="logout-button">Logout</button>
        </div>
      </header>
      
      <div className="dashboard-content">
        <aside className="dashboard-sidebar">
          <button className="new-chat-btn" onClick={() => navigate('/')}>
            <Plus size={18} /> New Chat
          </button>
          
          <nav className="sidebar-nav">
            <NavLink to="/adverse-events" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <FileWarning size={18} /> Adverse Events
            </NavLink>
            <NavLink to="/triage-cases" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Activity size={18} /> Triage Cases
            </NavLink>
          </nav>

          <div className="history-section">
            <h3>Recent Chats</h3>
            <div className="session-list">
              {sessions.map(s => (
                <div key={s.id} className="session-item-wrapper">
                  <NavLink 
                    to={`/chat/${s.id}`} 
                    className={({ isActive }) => `session-item ${isActive ? 'active' : ''}`}
                  >
                    <MessageSquare size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle', flexShrink: 0 }}/>
                    <span className="session-title">{s.title}</span>
                  </NavLink>
                  <button 
                    className="delete-session-btn" 
                    onClick={(e) => handleDeleteSession(e, s.id)}
                    title="Delete chat session"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </aside>


        <main className="dashboard-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;

import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import logo from '../assets/logoEmoVest.png';

const menuItems = [
  {
    id: 'dashboard',
    name: 'Tablero',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
    path: '/dashboard'
  },
  {
    id: 'operaciones',
    name: 'Operaciones de Trading',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    path: '/trading'
  },
  {
    id: 'estadisticas',
    name: 'Estadísticas Emocionales',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
      </svg>
    ),
    path: '/estadisticas'
  }
];

const Sidebar = ({ sidebarOpen, onToggle }) => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    localStorage.setItem('sidebarOpen', JSON.stringify(sidebarOpen));
  }, [sidebarOpen]);

  return (
    <aside className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-black/30 backdrop-blur-xl border-r border-white/10 transition-all duration-300 flex flex-col sticky top-0 h-screen`}>
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <img src={logo} alt="Logo" className="h-10 w-auto object-contain" />
          {sidebarOpen && <h1 className="font-cinzel text-xl font-bold tracking-widest text-white">EmoVest</h1>}
        </div>
      </div>

      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center justify-start gap-3 px-3 py-3 rounded-lg transition-all duration-300 ${
                  location.pathname === item.path
                    ? 'bg-blue-600/30 text-blue-400 border border-blue-500/30'
                    : 'text-gray-300 hover:bg-white/10 hover:text-white'
                }`}
              >
                <span className="flex-shrink-0 flex items-center justify-center">{item.icon}</span>
                {sidebarOpen && <span className="font-medium pl-1 text-left">{item.name}</span>}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="p-4 border-t border-white/10">
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-center gap-3 px-4 py-2 rounded-lg text-gray-300 hover:bg-white/10 transition-all duration-300"
        >
          <span className="text-xl">{sidebarOpen ? '›' : '‹'}</span>
          {sidebarOpen && <span className="font-medium">Contraer</span>}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;

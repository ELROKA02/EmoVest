import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import logo from '../assets/logoEmoVest.png';
import CustomSelect from './CustomSelect';
import { fetchAndStoreUserName } from '../utils/userSession';

const EstadisticasEmocionales = () => {
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const navigate = useNavigate();
  const location = useLocation();

  const [userName, setUserName] = useState(localStorage.getItem('userName') || 'Usuario');

  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;

  const [cuentas, setCuentas] = useState([]);
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState('');
  const [year, setYear] = useState(currentYear.toString());
  const [month, setMonth] = useState(currentMonth.toString());
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const meses = [
    { id: '1', nombre: '1 - Enero' }, { id: '2', nombre: '2 - Febrero' },
    { id: '3', nombre: '3 - Marzo' }, { id: '4', nombre: '4 - Abril' },
    { id: '5', nombre: '5 - Mayo' }, { id: '6', nombre: '6 - Junio' },
    { id: '7', nombre: '7 - Julio' }, { id: '8', nombre: '8 - Agosto' },
    { id: '9', nombre: '9 - Septiembre' }, { id: '10', nombre: '10 - Octubre' },
    { id: '11', nombre: '11 - Noviembre' }, { id: '12', nombre: '12 - Diciembre' }
  ];

  const emocionesColors = {
    confianza: '#3b82f6', // blue
    duda: '#f59e0b',      // orange
    euforia: '#10b981',   // green
    miedo: '#ef4444',     // red
    neutral: '#8b5cf6'    // purple
  };

  useEffect(() => {
    localStorage.setItem('sidebarOpen', JSON.stringify(sidebarOpen));
  }, [sidebarOpen]);

  useEffect(() => {
    let isMounted = true;
    const loadCurrentUser = async () => {
      try {
        const name = await fetchAndStoreUserName();
        if (name && isMounted) setUserName(name);
      } catch (err) {
        console.error('Error al cargar usuario actual:', err);
      }
    };
    loadCurrentUser();
    return () => { isMounted = false; };
  }, []);

  useEffect(() => {
    const cargarCuentas = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch('http://localhost:8000/cuentas/vercuentas', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setCuentas(data);
          if (data.length > 0) setCuentaSeleccionada(data[0].id.toString());
        } else if (response.status !== 404) {
          setError('Error al cargar cuentas de trading');
        }
      } catch (error) {
        setError('Error de conexión con el servidor',error);
      }
    };
    cargarCuentas();
  }, []);

  useEffect(() => {
    const cargarEstadisticas = async () => {
      if (!cuentaSeleccionada) return;
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`http://localhost:8000/cuentas/${cuentaSeleccionada}/estadisticas/emociones?year=${year}&month=${month}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setStats(data);
        } else {
          setError('No se pudieron cargar las estadísticas emocionales');
        }
      } catch (error) {
        setError('Error de conexión al cargar estadísticas', error);
      } finally {
        setLoading(false);
      }
    };
    cargarEstadisticas();
  }, [cuentaSeleccionada, year, month]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('rememberedEmail');
    localStorage.removeItem('userName');
    navigate('/login');
  };

  const menuItems = [
    {
      id: 'dashboard',
      name: 'Tablero',
      icon: <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>,
      path: '/dashboard'
    },
    {
      id: 'operaciones',
      name: 'Operaciones de Trading',
      icon: <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
      path: '/trading'
    },
    {
      id: 'estadisticas',
      name: 'Estadísticas Emocionales',
      icon: <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>,
      path: '/estadisticas'
    }
  ];

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  // Pie Chart Generation Logic
  let pieStyle = { background: '#1f2937' }; // Default gray
  let winrateEntries = [];
  
  if (stats && stats.winrate_emociones) {
    winrateEntries = Object.entries(stats.winrate_emociones);
    const sumWinrates = winrateEntries.reduce((acc, [ , val]) => acc + val, 0);
    
    if (sumWinrates > 0) {
      let currentPercent = 0;
      const gradientStops = winrateEntries.map(([emocion, val]) => {
        if (val === 0) return null;
        const percentage = (val / sumWinrates) * 100;
        const start = currentPercent;
        const end = currentPercent + percentage;
        currentPercent = end;
        return `${emocionesColors[emocion]} ${start}% ${end}%`;
      }).filter(Boolean).join(', ');
      
      pieStyle = { background: `conic-gradient(${gradientStops})` };
    }
  }

  return (
    <div className="min-h-screen flex" style={bgGradient}>
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-black/30 backdrop-blur-xl border-r border-white/10 transition-all duration-300 flex flex-col`}>
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
                <button onClick={() => navigate(item.path)} className={`w-full flex items-center justify-start gap-3 px-3 py-3 rounded-lg transition-all duration-300 ${location.pathname === item.path ? 'bg-blue-600/30 text-blue-400 border border-blue-500/30' : 'text-gray-300 hover:bg-white/10 hover:text-white'}`}>
                  <span className="flex-shrink-0 flex items-center justify-center">{item.icon}</span>
                  {sidebarOpen && <span className="font-medium pl-1 text-left">{item.name}</span>}
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <div className="p-4 border-t border-white/10">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="w-full flex items-center justify-center gap-3 px-4 py-2 rounded-lg text-gray-300 hover:bg-white/10 transition-all duration-300">
            <span className="text-xl">{sidebarOpen ? '›' : '‹'}</span>
            {sidebarOpen && <span className="font-medium">Contraer</span>}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <header className="bg-black/30 backdrop-blur-xl border-b border-white/10 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-gray-300 hover:text-white transition-colors">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
            </button>
            <h2 className="text-xl font-semibold text-white">Estadísticas Emocionales</h2>
          </div>
          <div className="flex items-center gap-8">
            <div onClick={() => navigate('/perfil')} className="flex items-center gap-2 text-gray-300 hover:text-white cursor-pointer transition-colors" title="Ver perfil">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
              <span className="font-medium">{userName}</span>
            </div>
            <button onClick={handleLogout} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-full transition-all duration-300 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
              Cerrar Sesión
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-8">
          <div className="max-w-6xl mx-auto space-y-6">
            {error && <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300">{error}</div>}

            {/* Filtros */}
            <div className="relative z-50 bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10 flex flex-col md:flex-row gap-4 items-center justify-between">
              <div className="w-full md:w-1/3">
                <label className="text-sm text-gray-400 block mb-2">Cuenta Trading</label>
                <CustomSelect
                  value={cuentaSeleccionada ? cuentas.find(c => c.id.toString() === cuentaSeleccionada)?.nombre_cuenta : 'Cargando...'}
                  onChange={(val) => {
                    const acc = cuentas.find(c => c.nombre_cuenta === val);
                    if (acc) setCuentaSeleccionada(acc.id.toString());
                  }}
                  options={cuentas.map(c => c.nombre_cuenta)}
                />
              </div>
              <div className="flex gap-4 w-full md:w-auto">
                <div className="w-full md:w-40">
                  <label className="text-sm text-gray-400 block mb-2">Mes</label>
                  <CustomSelect
                    value={meses.find(m => m.id === month)?.nombre}
                    onChange={(val) => setMonth(meses.find(m => m.nombre === val)?.id)}
                    options={meses.map(m => m.nombre)}
                  />
                </div>
                <div className="w-full md:w-32">
                  <label className="text-sm text-gray-400 block mb-2">Año</label>
                  <CustomSelect
                    value={year}
                    onChange={(val) => setYear(val)}
                    options={['2023', '2024', '2025', '2026', '2027']}
                  />
                </div>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-12 text-gray-400">Cargando estadísticas emocionales...</div>
            ) : stats ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Pie Chart Winrate */}
                <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/10 flex flex-col items-center shadow-xl">
                  <h3 className="text-xl font-bold text-white mb-8">Winrate por Emoción</h3>
                  <div className="relative w-64 h-64 rounded-full mb-8 shadow-[0_0_40px_rgba(0,0,0,0.5)] border-4 border-white/5" style={pieStyle}>
                    <div className="absolute inset-0 bg-black/20 rounded-full"></div>
                    <div className="absolute inset-4 bg-[#141b2d] rounded-full flex items-center justify-center">
                      <span className="text-gray-400 text-sm font-medium">Winrate %</span>
                    </div>
                  </div>
                  <div className="w-full grid grid-cols-2 gap-4">
                    {winrateEntries.map(([emocion, val]) => (
                      <div key={emocion} className="flex items-center gap-3">
                        <div className="w-4 h-4 rounded-full shadow-sm" style={{ backgroundColor: emocionesColors[emocion] }}></div>
                        <div className="flex flex-col">
                          <span className="text-gray-300 text-sm capitalize">{emocion}</span>
                          <span className="text-white font-bold">{val.toFixed(1)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Beneficios List */}
                <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/10 shadow-xl">
                  <h3 className="text-xl font-bold text-white mb-6">Beneficio Total por Emoción</h3>
                  <div className="space-y-4">
                    {Object.entries(stats.beneficio_total_emociones || {}).map(([emocion, beneficio]) => (
                      <div key={emocion} className="flex items-center justify-between p-4 bg-black/20 rounded-xl border border-white/5 hover:bg-white/5 transition-colors">
                        <div className="flex items-center gap-3">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: emocionesColors[emocion] }}></div>
                          <span className="text-gray-200 capitalize font-medium text-lg">{emocion}</span>
                        </div>
                        <div className={`text-xl font-bold tracking-wider ${beneficio > 0 ? 'text-green-400' : beneficio < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                          {beneficio > 0 ? '+' : ''}{beneficio.toFixed(2)}$
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            ) : (
              <div className="text-center py-12 text-gray-400 border border-dashed border-white/10 rounded-2xl">
                No hay datos emocionales disponibles para este período.
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default EstadisticasEmocionales;
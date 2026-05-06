import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import CustomSelect from './CustomSelect';
import { fetchAndStoreUserName } from '../utils/userSession';
import { formatCurrency } from '../utils/currency';

const EstadisticasEmocionales = () => {
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const navigate = useNavigate();

  const [userName, setUserName] = useState(localStorage.getItem('userName') || 'Usuario');

  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;

  const [cuentas, setCuentas] = useState([]);
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState(() => {
    const saved = localStorage.getItem('selectedAccountId');
    return saved ? saved : '';
  });
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
    confianza: '#10bd55', // verde esmeralda
    duda: '#e7e71f',      // blanco roto
    euforia: '#c026d3',   // morado chillón
    miedo: '#ef4444',     // rojo
    neutral: '#9ca3af'    // gris
  };

  const selectedAccount = cuentas.find(cuenta => cuenta.id.toString() === cuentaSeleccionada);
  const selectedDivisa = selectedAccount?.divisa || 'USD';

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

  // Guardar cuenta seleccionada en localStorage cuando cambia
  useEffect(() => {
    if (cuentaSeleccionada) {
      localStorage.setItem('selectedAccountId', cuentaSeleccionada);
    }
  }, [cuentaSeleccionada]);

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
          if (data.length > 0) {
            const savedAccountId = localStorage.getItem('selectedAccountId');
            const accountToSelect = savedAccountId
              ? data.find(acc => acc.id.toString() === savedAccountId)?.id
              : data[0].id;
            setCuentaSeleccionada((accountToSelect || data[0].id).toString());
          }
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

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  // Pie Chart Generation Logic
  let winrateEntries = [];
  const getEmotionPieStyle = (val, color) => {
    const percentage = Math.max(0, Math.min(100, val));
    return {
      background: `conic-gradient(${color} 0% ${percentage}%, rgba(255,255,255,0.08) ${percentage}% 100%)`,
    };
  };

  if (stats && stats.winrate_emociones) {
    winrateEntries = Object.entries(stats.winrate_emociones);
  }

  return (
    <div className="min-h-screen flex" style={bgGradient}>
      {/* Sidebar */}
      <Sidebar sidebarOpen={sidebarOpen} onToggle={() => setSidebarOpen(prev => !prev)} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <header className="sticky top-0 z-40 bg-black/30 backdrop-blur-xl border-b border-white/10 px-6 py-4 flex justify-between items-center">
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

        <main className="flex-1 overflow-auto p-14">
          <div className="max-w-6xl mx-auto space-y-6">
            {error && <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300">{error}</div>}

            {/* Filtros */}
            <div className="relative z-10 bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10 flex flex-col md:flex-row gap-4 items-center justify-between">
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
                <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/10 shadow-xl">
                  <h3 className="text-xl font-bold text-white mb-8">Winrate por Emoción</h3>
                  <div className="grid grid-cols-[150px_150px_150px] grid-rows-[150px_150px_150px] gap-4 justify-center items-center mx-auto w-full max-w-[470px]">
                    {winrateEntries.map(([emocion, val]) => {
                      const sizeClass = 'w-40 aspect-square';
                      const cellPosition = {
                        confianza: 'row-start-1 col-start-2',
                        duda: 'row-start-2 col-start-3',
                        euforia: 'row-start-2 col-start-1',
                        miedo: 'row-start-3 col-start-2',
                        neutral: 'row-start-2 col-start-2',
                      }[emocion] || 'row-start-2 col-start-2';

                      return (
                        <div key={emocion} className={`${cellPosition} flex items-center justify-center`}>
                          <div className={`relative ${sizeClass} rounded-full shadow-[0_0_20px_rgba(0,0,0,0.4)]`} style={getEmotionPieStyle(val, emocionesColors[emocion])}>
                            <div className="absolute inset-0 rounded-full bg-[#141b2d] m-4 flex flex-col items-center justify-center text-center shadow-inner">
                              <span className="text-gray-400 text-[10px] uppercase tracking-[0.2em]">{emocion}</span>
                              <span className="text-white text-2xl font-bold">{val.toFixed(1)}%</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Beneficios List */}
                <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10 shadow-xl">
                  <h3 className="text-xl font-bold text-white mb-5">Beneficio Total por Emoción</h3>
                  <div className="space-y-3">
                    {Object.entries(stats.beneficio_total_emociones || {}).map(([emocion, beneficio]) => (
                      <div key={emocion} className="flex items-center justify-between p-3 bg-black/20 rounded-2xl border border-white/5 hover:bg-white/5 transition-colors">
                        <div className="flex items-center gap-3">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: emocionesColors[emocion] }}></div>
                          <span className="text-gray-200 capitalize font-medium text-sm">{emocion}</span>
                        </div>
                        <div className={`text-base font-bold tracking-wider ${beneficio > 0 ? 'text-green-400' : beneficio < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                          {beneficio > 0 ? '+' : ''}{formatCurrency(beneficio, selectedDivisa)}
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
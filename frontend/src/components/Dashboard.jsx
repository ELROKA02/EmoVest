import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import OperacionesTrading from './OperacionesTrading';
import CustomSelect from './CustomSelect';
import Sidebar from './Sidebar';
import { fetchAndStoreUserName } from '../utils/userSession';
import { formatCurrency } from '../utils/currency';

const Dashboard = () => {
  // Obtener estado del sidebar desde localStorage o usar true por defecto
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const navigate = useNavigate();
  const location = useLocation();

  const [userName, setUserName] = useState(localStorage.getItem('userName') || 'Usuario');

  useEffect(() => {
    let isMounted = true;

    const loadCurrentUser = async () => {
      try {
        const name = await fetchAndStoreUserName();
        if (name && isMounted) {
          setUserName(name);
        }
      } catch (error) {
        console.error('Error al cargar usuario actual:', error);
      }
    };

    loadCurrentUser();

    return () => {
      isMounted = false;
    };
  }, []);

  // Estado para el formulario de crear cuenta
  const [accountData, setAccountData] = useState({
    nombre_cuenta: '',
    divisa: 'EUR',
    saldo_inicial: ''
  });
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [tradingAccounts, setTradingAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');

  // Estados para el selector de fecha y ganancias
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [gananciasNetas, setGananciasNetas] = useState(null);
  const [loadingGanancias, setLoadingGanancias] = useState(false);
  const [estadisticasCompletas, setEstadisticasCompletas] = useState(null);
  const [loadingEstadisticas, setLoadingEstadisticas] = useState(false);

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };
  const selectedAccountObj = tradingAccounts.find(account => account.id === selectedAccount);
  const selectedDivisa = selectedAccountObj?.divisa || 'EUR';
  const accountOptionText = account => `${account.nombre_cuenta} (${account.divisa}) - ${formatCurrency(account.saldo_inicial, account.divisa)}`;
  const saldoPlaceholder = formatCurrency(0, accountData.divisa);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('rememberedEmail');
    localStorage.removeItem('userName');
    navigate('/login');
  };

  const handleCreateAccount = async (e) => {
    e.preventDefault();

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/cuentas/crearcuenta', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ...accountData,
          saldo_inicial: accountData.saldo_inicial === '' ? 0 : parseFloat(accountData.saldo_inicial)
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Cuenta creada exitosamente:', result);
        alert('Cuenta de trading creada exitosamente');
        
        // Cerrar el modal y resetear el formulario
        setShowAccountForm(false);
        setAccountData({
          nombre_cuenta: '',
          divisa: 'EUR',
          saldo_inicial: ''
        });
        
        // Refrescar la lista de cuentas
        fetchTradingAccounts();
      } else {
        const errorData = await response.json();
        console.error('Error al crear cuenta:', errorData);
        alert('Error al crear la cuenta: ' + (errorData.detail || 'Error desconocido'));
      }
    } catch (error) {
      console.error('Error de conexión:', error);
      alert('Error de conexión al servidor');
    }
  };

  const handleCreateAccountClick = () => {
    setAccountData({
      nombre_cuenta: '',
      divisa: 'EUR',
      saldo_inicial: ''
    });
    setShowAccountForm(true);
  };

  const handleAccountSubmit = (e) => {
    e.preventDefault();
    handleCreateAccount(e);
  };

  // Fetch trading accounts on component mount
  const fetchTradingAccounts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/cuentas/vercuentas', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const accounts = await response.json();
        console.log('Cuentas recibidas del backend:', accounts);
        console.log('Número de cuentas:', accounts.length);
        setTradingAccounts(accounts);
        if (accounts.length > 0) {
          console.log('ID de la primera cuenta:', accounts[0].id);
          setSelectedAccount(accounts[0].id);
        }
      } else {
        // Si es 404, significa que no hay cuentas (es normal)
        if (response.status === 404) {
          console.log('No hay cuentas (404 - es normal)');
          setTradingAccounts([]);
          setSelectedAccount('');
        } else {
          console.error('Error fetching accounts:', response.status);
        }
      }
    } catch (error) {
      console.error('Error de conexión al obtener cuentas:', error);
    }
  };

  // Función para obtener todas las estadísticas completas
  const fetchEstadisticasCompletas = async () => {
    if (!selectedAccount) {
      setGananciasNetas(null);
      setEstadisticasCompletas(null);
      return;
    }

    setLoadingGanancias(true);
    setLoadingEstadisticas(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `http://localhost:8000/cuentas/${selectedAccount}/estadisticas/mensual?year=${selectedYear}&month=${selectedMonth}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setGananciasNetas(data.ganancias_netas);
        setEstadisticasCompletas(data);
      } else {
        console.error('Error al obtener estadísticas:', response.status);
        setGananciasNetas(null);
        setEstadisticasCompletas(null);
      }
    } catch (error) {
      console.error('Error de conexión:', error);
      setGananciasNetas(null);
      setEstadisticasCompletas(null);
    } finally {
      setLoadingGanancias(false);
      setLoadingEstadisticas(false);
    }
  };

  // Efecto para cargar estadísticas cuando cambia la cuenta, mes o año
  useEffect(() => {
    fetchEstadisticasCompletas();
  }, [selectedAccount, selectedMonth, selectedYear]);

  // Efecto para cargar cuentas al montar el componente
  useEffect(() => {
    fetchTradingAccounts();
  }, []);

  // Opciones para meses y años
  const meses = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  const años = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);

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
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>
      ),
      path: '/estadisticas'
    }
  ];

  const renderContent = () => {
    if (location.pathname === '/dashboard/operaciones') {
      return <OperacionesTrading />;
    }

    return (
      <div className="p-14 pl-30 h-full">
        {/* Selectores de Fecha - Principales */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <button
              onClick={handleCreateAccountClick}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-full transition-all duration-300"
            >
              Crear Cuenta Trading
            </button>
            
            <div className="flex items-center gap-2">
              <label className="text-white font-medium">Cuentas:</label>
              <CustomSelect
                value={
                  selectedAccountObj
                    ? accountOptionText(selectedAccountObj)
                    : 'No hay cuentas disponibles'
                }
                onChange={(selectedText) => {
                  const selectedAccountObj = tradingAccounts.find(account => accountOptionText(account) === selectedText);
                  if (selectedAccountObj) {
                    setSelectedAccount(selectedAccountObj.id);
                  }
                }}
                options={
                  tradingAccounts.length === 0
                    ? ['No hay cuentas disponibles']
                    : tradingAccounts.map(account => accountOptionText(account))
                }
              />
            </div>
          </div>

          <div className="flex items-center gap-6 bg-black/20 backdrop-blur-sm rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-3">
              <label className="text-white font-medium">Mes:</label>
              <CustomSelect
                value={meses[selectedMonth - 1]}
                onChange={(selectedText) => {
                  const monthIndex = meses.indexOf(selectedText);
                  if (monthIndex !== -1) {
                    setSelectedMonth(monthIndex + 1);
                  }
                }}
                options={meses}
              />
            </div>

            <div className="flex items-center gap-3">
              <label className="text-white font-medium">Año:</label>
              <CustomSelect
                value={selectedYear.toString()}
                onChange={(selectedText) => {
                  setSelectedYear(parseInt(selectedText));
                }}
                options={años.map(año => año.toString())}
              />
            </div>
          </div>
        </div>

        {/* Grid de Estadísticas Moderno */}
        {loadingEstadisticas ? (
          <div className="flex justify-center items-center py-20">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-8 h-8 bg-blue-500 rounded-full animate-pulse"></div>
              </div>
            </div>
            <div className="ml-4 text-white text-lg font-medium">Analizando estadísticas...</div>
          </div>
        ) : estadisticasCompletas ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
            {/* Ganancias Netas - Tarjeta Hero */}
            <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${estadisticasCompletas.ganancias_netas >= 0 ? 'from-green-600/20 to-emerald-600/10 border-green-500/30' : 'from-red-600/20 to-rose-600/10 border-red-500/30'} backdrop-blur-xl border p-6 transform transition-all duration-300 hover:scale-105 hover:shadow-2xl`}>
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-white/5 to-transparent rounded-full -mr-16 -mt-16"></div>
              <div className="relative">
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-4 h-4 rounded-full ${estadisticasCompletas.ganancias_netas >= 0 ? 'bg-green-500 shadow-lg shadow-green-500/50' : 'bg-red-500 shadow-lg shadow-red-500/50'} animate-pulse`}></div>
                  <h3 className="text-white font-bold text-lg">Ganancias Netas</h3>
                </div>
                <div className={`text-4xl font-black ${estadisticasCompletas.ganancias_netas >= 0 ? 'text-green-400' : 'text-red-400'} mb-2`}>
                  {formatCurrency(estadisticasCompletas.ganancias_netas, selectedDivisa)}
                </div>
                <div className={`text-sm ${estadisticasCompletas.ganancias_netas >= 0 ? 'text-green-300' : 'text-red-300'} font-medium`}>
                  {estadisticasCompletas.ganancias_netas >= 0 ? 'Beneficio Neto' : 'Pérdida Neta'}
                </div>
              </div>
            </div>

            {/* Win Rate - Tarjeta con Gráfica Circular */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-600/20 to-indigo-600/10 backdrop-blur-xl border border-blue-500/30 p-6 transform transition-all duration-300 hover:scale-105 hover:shadow-2xl">
              <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-blue-500/10 to-transparent rounded-full -mr-12 -mt-12"></div>
              <div className="relative">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-4 h-4 rounded-full bg-blue-500 shadow-lg shadow-blue-500/50"></div>
                  <h3 className="text-white font-bold text-lg">Win Rate</h3>
                </div>
                <div className="flex items-center justify-center mb-4">
                  <div className="relative w-24 h-24">
                    <svg className="w-24 h-24 transform -rotate-90">
                      <circle cx="48" cy="48" r="36" stroke="rgba(55, 65, 81, 0.5)" strokeWidth="12" fill="none"/>
                      <circle 
                        cx="48" 
                        cy="48" 
                        r="36" 
                        stroke="url(#gradient)" 
                        strokeWidth="12" 
                        fill="none"
                        strokeDasharray={`${2 * Math.PI * 36}`}
                        strokeDashoffset={`${2 * Math.PI * 36 * (1 - estadisticasCompletas.win_rate / 100)}`}
                        className="transition-all duration-1000 ease-out"
                      />
                      <defs>
                        <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#10b981"/>
                          <stop offset="100%" stopColor="#3b82f6"/>
                        </linearGradient>
                      </defs>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-2xl font-black text-blue-400">{estadisticasCompletas.win_rate.toFixed(0)}%</div>
                    </div>
                  </div>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-green-400 font-medium">✓ Ganadoras</span>
                  <span className="text-red-400 font-medium">✗ Perdedoras</span>
                </div>
              </div>
            </div>

            {/* Promedios Operación - Tarjeta Dual */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-600/20 to-pink-600/10 backdrop-blur-xl border border-purple-500/30 p-6 transform transition-all duration-300 hover:scale-105 hover:shadow-2xl">
              <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-purple-500/10 to-transparent rounded-full -mr-10 -mt-10"></div>
              <div className="relative">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-4 h-4 rounded-full bg-purple-500 shadow-lg shadow-purple-500/50"></div>
                  <h3 className="text-white font-bold text-lg">Promedios</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-green-500/10 rounded-xl p-3 border border-green-500/20">
                    <div className="text-green-400 text-xs mb-1 font-medium">Ganancia</div>
                    <div className="text-green-300 font-bold text-lg">{formatCurrency(estadisticasCompletas.ganancias_promedio, selectedDivisa)}</div>
                  </div>
                  <div className="bg-red-500/10 rounded-xl p-3 border border-red-500/20">
                    <div className="text-red-400 text-xs mb-1 font-medium">Pérdida</div>
                    <div className="text-red-300 font-bold text-lg">{formatCurrency(Math.abs(estadisticasCompletas.perdidas_promedio), selectedDivisa)}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Max Drawdown - Tarjeta de Alerta */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-orange-600/20 to-amber-600/10 backdrop-blur-xl border border-orange-500/30 p-6 transform transition-all duration-300 hover:scale-105 hover:shadow-2xl">
              <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-orange-500/10 to-transparent rounded-full -mr-10 -mt-10"></div>
              <div className="relative">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-4 h-4 rounded-full bg-orange-500 shadow-lg shadow-orange-500/50 animate-pulse"></div>
                  <h3 className="text-white font-bold text-lg">Max Drawdown</h3>
                </div>
                <div className="text-3xl font-black text-orange-400 mb-2">
                  {formatCurrency(estadisticasCompletas.max_drawdown.drawdown_euros, selectedDivisa)}
                </div>
                <div className="bg-orange-500/20 rounded-lg px-3 py-1 inline-block">
                  <div className="text-orange-300 text-sm font-medium">
                    {estadisticasCompletas.max_drawdown.drawdown_porcentaje.toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>

            {/* Estadísticas de Operaciones - Tarjeta Compacta */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-cyan-600/20 to-teal-600/10 backdrop-blur-xl border border-cyan-500/30 p-6 transform transition-all duration-300 hover:scale-105 hover:shadow-2xl">
              <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-cyan-500/10 to-transparent rounded-full -mr-10 -mt-10"></div>
              <div className="relative">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-4 h-4 rounded-full bg-cyan-500 shadow-lg shadow-cyan-500/50"></div>
                  <h3 className="text-white font-bold text-lg">Estadísticas</h3>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-cyan-300 text-sm">Media hasta ganar</span>
                    <span className="text-cyan-400 font-bold">{estadisticasCompletas.media_operaciones_hasta_ganadora.toFixed(1)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-yellow-300 text-sm">Media hasta error</span>
                    <span className="text-yellow-400 font-bold">{estadisticasCompletas.media_operaciones_hasta_error.toFixed(1)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-green-300 text-sm">Racha actual</span>
                    <span className="text-green-400 font-bold">{estadisticasCompletas.operaciones_ganadoras_consecutivas_actuales}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Rachas - Tarjeta con Indicadores */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-600/20 to-green-600/10 backdrop-blur-xl border border-emerald-500/30 p-6 transform transition-all duration-300 hover:scale-105 hover:shadow-2xl">
              <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-emerald-500/10 to-transparent rounded-full -mr-10 -mt-10"></div>
              <div className="relative">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-4 h-4 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50"></div>
                  <h3 className="text-white font-bold text-lg">Rachas</h3>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                        <span className="text-emerald-400 text-xs">🔥</span>
                      </div>
                      <span className="text-emerald-300 text-sm">Mejor racha</span>
                    </div>
                    <div className="text-emerald-400 font-bold text-lg">{estadisticasCompletas.racha_ganadora_mas_larga}</div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 bg-red-500/20 rounded-lg flex items-center justify-center">
                        <span className="text-red-400 text-xs">❄️</span>
                      </div>
                      <span className="text-red-300 text-sm">Peor racha</span>
                    </div>
                    <div className="text-red-400 font-bold text-lg">{estadisticasCompletas.racha_perdedora_mas_larga}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Días Rentables - Tarjeta Semanal */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600/20 to-blue-600/10 backdrop-blur-xl border border-indigo-500/30 p-6 transform transition-all duration-300 hover:scale-105 hover:shadow-2xl">
              <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-indigo-500/10 to-transparent rounded-full -mr-10 -mt-10"></div>
              <div className="relative">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-4 h-4 rounded-full bg-indigo-500 shadow-lg shadow-indigo-500/50"></div>
                  <h3 className="text-white font-bold text-lg">Días Rentables</h3>
                </div>
                <div className="space-y-3">
                  <div className="bg-green-500/10 rounded-xl p-3 border border-green-500/20">
                    <div className="flex justify-between items-center">
                      <span className="text-green-400 text-sm font-medium">Mejor día</span>
                      <span className="text-green-300 font-bold">{estadisticasCompletas.dia_semanal_mas_rentable.dia || 'N/A'}</span>
                    </div>
                    {estadisticasCompletas.dia_semanal_mas_rentable.dia && (
                      <div className="text-green-300 text-xs mt-1">+{formatCurrency(estadisticasCompletas.dia_semanal_mas_rentable.ganancia, selectedDivisa)}</div>
                    )}
                  </div>
                  <div className="bg-red-500/10 rounded-xl p-3 border border-red-500/20">
                    <div className="flex justify-between items-center">
                      <span className="text-red-400 text-sm font-medium">Peor día</span>
                      <span className="text-red-300 font-bold">{estadisticasCompletas.dia_semanal_menos_rentable.dia || 'N/A'}</span>
                    </div>
                    {estadisticasCompletas.dia_semanal_menos_rentable.dia && (
                      <div className="text-red-300 text-xs mt-1">{formatCurrency(estadisticasCompletas.dia_semanal_menos_rentable.ganancia, selectedDivisa)}</div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Expectativa - Tarjeta Destacada */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-600/30 via-purple-600/20 to-pink-600/10 backdrop-blur-xl border border-violet-500/40 p-6 transform transition-all duration-300 hover:scale-105 hover:shadow-2xl md:col-span-2">
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-violet-500/20 to-transparent rounded-full -mr-16 -mt-16"></div>
              <div className="absolute bottom-0 left-0 w-24 h-24 bg-gradient-to-tr from-pink-500/10 to-transparent rounded-full -ml-12 -mb-12"></div>
              <div className="relative">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-4 h-4 rounded-full bg-violet-500 shadow-lg shadow-violet-500/50 animate-pulse"></div>
                  <h3 className="text-white font-bold text-lg">Expectativa Matemática</h3>
                </div>
                <div className="flex items-baseline gap-4 mb-3">
                  <div className="text-5xl font-black text-violet-400">
                    {formatCurrency(estadisticasCompletas.expectativa, selectedDivisa)}
                  </div>
                  <div className="text-violet-300 text-sm">
                    por operación
                  </div>
                </div>
                <div className="bg-violet-500/20 rounded-lg px-4 py-2 inline-block">
                  <div className="text-violet-300 text-sm font-medium">
                    {estadisticasCompletas.expectativa >= 0 ? 'Estrategia rentable' : 'Estrategia no rentable'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : selectedAccount ? (
          <div className="flex justify-center items-center py-12">
            <div className="text-gray-400 text-lg">No hay datos para el período seleccionado</div>
          </div>
        ) : null}

        {/* Formulario modal para crear cuenta */}
        {showAccountForm && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-[#1a2235] rounded-2xl p-6 border border-white/20 w-full max-w-md shadow-2xl">
              <h2 className="text-xl font-bold mb-4 text-white">Crear Cuenta Trading</h2>
              <form onSubmit={handleAccountSubmit} className="space-y-3">
                <div>
                  <label className="block text-xs text-white mb-1">Nombre de Cuenta</label>
                  <input
                    type="text"
                    value={accountData.nombre_cuenta}
                    onChange={(e) => setAccountData({...accountData, nombre_cuenta: e.target.value})}
                    className="w-full p-2 text-sm text-white bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-blue-500"
                    placeholder="Ej: Cuenta Principal"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-xs text-white mb-1">Divisa</label>
                  <CustomSelect
                    value={accountData.divisa}
                    onChange={(value) => setAccountData({...accountData, divisa: value})}
                    options={['EUR', 'USD']}
                  />
                </div>
                
                <div>
                  <label className="block text-xs text-white mb-1">Saldo Inicial</label>
                  <input
                    type="number"
                    step="100"
                    min="0"
                    value={accountData.saldo_inicial}
                    onChange={(e) => setAccountData({...accountData, saldo_inicial: e.target.value})}
                    className="w-full p-2 text-sm text-white bg-white/5 border border-white/10 rounded-lg focus:outline-none"
                    placeholder={saldoPlaceholder}
                    required
                  />
                </div>
                
                <div className="flex justify-end gap-2 pt-3">
                  <button
                    type="button"
                    onClick={() => setShowAccountForm(false)}
                    className="px-4 py-2 text-sm text-white bg-gray-700 hover:bg-gray-600 rounded-full transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-full transition-colors font-semibold"
                  >
                    Crear Cuenta
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen flex" style={bgGradient}>
      <Sidebar sidebarOpen={sidebarOpen} onToggle={() => setSidebarOpen(prev => !prev)} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <header className="bg-black/30 backdrop-blur-xl border-b border-white/10 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-300 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h2 className="text-xl font-semibold text-white">Tablero</h2>
          </div>

          <div className="flex items-center gap-8">
            {/* User Icon */}
            <div onClick={() => navigate('/perfil')} className="flex items-center gap-2 text-gray-300 hover:text-white cursor-pointer transition-colors" title="Ver perfil">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span className="font-medium">{userName}</span>
            </div>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-full transition-all duration-300 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              Cerrar Sesión
            </button>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-auto">
          {renderContent()}
        </main>
      </div>
    </div>
  );
};

export default Dashboard;

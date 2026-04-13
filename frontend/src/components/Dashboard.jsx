import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import OperacionesTrading from './OperacionesTrading';
import CustomSelect from './CustomSelect';
import logo from '../assets/logoEmoVest.png';

const Dashboard = () => {
  // Obtener estado del sidebar desde localStorage o usar true por defecto
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    localStorage.setItem('sidebarOpen', JSON.stringify(sidebarOpen));
  }, [sidebarOpen]);

  // Obtener el nombre del usuario del localStorage
  const userName = localStorage.getItem('userName') || 'Usuario';

  // Estado para el formulario de crear cuenta
  const [accountData, setAccountData] = useState({
    nombre_cuenta: '',
    divisa: 'EUR',
    saldo_inicial: 0
  });
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [tradingAccounts, setTradingAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('rememberedEmail');
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
        body: JSON.stringify(accountData)
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
          saldo_inicial: 0
        });
        
        // Refrescar la lista de cuentas
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
              setTradingAccounts(accounts);
              if (accounts.length > 0) {
                setSelectedAccount(accounts[accounts.length - 1].id); // Seleccionar la nueva cuenta
              }
            } else if (response.status === 404) {
              setTradingAccounts([]);
              setSelectedAccount('');
            }
          } catch (error) {
            console.error('Error al refrescar cuentas:', error);
          }
        };
        
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
      saldo_inicial: 0
    });
    setShowAccountForm(true);
  };

  const handleAccountSubmit = (e) => {
    e.preventDefault();
    handleCreateAccount(e);
  };

  // Fetch trading accounts on component mount
  useEffect(() => {
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

    fetchTradingAccounts();
  }, []);

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
    }
  ];

  const renderContent = () => {
    if (location.pathname === '/dashboard/operaciones') {
      return <OperacionesTrading />;
    }

    // Dashboard content sin grid
    console.log('Estado actual de tradingAccounts en render:', tradingAccounts);
    console.log('Longitud de tradingAccounts:', tradingAccounts.length);
    return (
      <div className="p-14 pl-30 h-full">
        <div className="mb-6 flex items-center gap-8">
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
                tradingAccounts.find(account => account.id === selectedAccount)
                  ? `${tradingAccounts.find(account => account.id === selectedAccount).nombre_cuenta} (${tradingAccounts.find(account => account.id === selectedAccount).divisa}) - $${tradingAccounts.find(account => account.id === selectedAccount).saldo_inicial.toFixed(2)}`
                  : 'No hay cuentas disponibles'
              }
              onChange={(selectedText) => {
                const selectedAccountObj = tradingAccounts.find(account => `${account.nombre_cuenta} (${account.divisa}) - $${account.saldo_inicial.toFixed(2)}` === selectedText);
                if (selectedAccountObj) {
                  setSelectedAccount(selectedAccountObj.id);
                }
              }}
              options={
                tradingAccounts.length === 0
                  ? ['No hay cuentas disponibles']
                  : tradingAccounts.map(account => `${account.nombre_cuenta} (${account.divisa}) - $${account.saldo_inicial.toFixed(2)}`)
              }
            />
          </div>
        </div>

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
                    step="0.01"
                    min="0"
                    value={accountData.saldo_inicial}
                    onChange={(e) => setAccountData({...accountData, saldo_inicial: parseFloat(e.target.value) || 0})}
                    className="w-full p-2 text-sm text-white bg-white/5 border border-white/10 rounded-lg focus:outline-none"
                    placeholder="0.00"
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
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-black/30 backdrop-blur-xl border-r border-white/10 transition-all duration-300 flex flex-col`}>
        {/* Logo */}
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <img
              src={logo}
              alt="Logo"
              className="h-10 w-auto object-contain"
            />
            {sidebarOpen && (
              <h1 className="font-cinzel text-xl font-bold tracking-widest text-white">
                EmoVest
              </h1>
            )}
          </div>
        </div>

        {/* Menu Items */}
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {menuItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => navigate(item.path)}
                  className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-all duration-300 ${location.pathname === item.path
                      ? 'bg-blue-600/30 text-blue-400 border border-blue-500/30'
                      : 'text-gray-300 hover:bg-white/10 hover:text-white'
                    }`}
                >
                  <span className="flex-shrink-0 flex items-center justify-center">{item.icon}</span>
                  {sidebarOpen && (
                    <span className="font-medium">{item.name}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* Toggle Sidebar Button */}
        <div className="p-4 border-t border-white/10">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center justify-center gap-3 px-4 py-2 rounded-lg text-gray-300 hover:bg-white/10 transition-all duration-300"
          >
            <span className="text-xl">{sidebarOpen ? '›' : '‹'}</span>
            {sidebarOpen && <span className="font-medium">Contraer</span>}
          </button>
        </div>
      </div>

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

          <div className="flex items-center gap-4">
            {/* User Icon */}
            <div className="flex items-center gap-2 text-gray-300">
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
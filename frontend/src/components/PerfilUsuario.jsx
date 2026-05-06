import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import CustomSelect from './CustomSelect';
import { formatCurrency } from '../utils/currency';

const PerfilUsuario = () => {
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const navigate = useNavigate();

  const [userData, setUserData] = useState({ name: 'Cargando...', email: 'Cargando...' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Estados para Información de Cuentas
  const [currentView, setCurrentView] = useState('Información Personal');
  const [cuentas, setCuentas] = useState([]);
  const [loadingCuentas, setLoadingCuentas] = useState(false);
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [accountData, setAccountData] = useState({
    nombre_cuenta: '',
    divisa: 'EUR',
    saldo: ''
  });

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          navigate('/login');
          return;
        }
        const response = await fetch('http://localhost:8000/me', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setUserData(data);
          localStorage.setItem('userName', data.name);
        } else {
          setError('No se pudo cargar la información del perfil');
        }
      } catch (error) {
        setError('Error de conexión al servidor', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [navigate]);

  // Obtener cuentas de trading
  const fetchCuentas = async () => {
    setLoadingCuentas(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/cuentas/vercuentas', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setCuentas(data);
      } else if (response.status === 404) {
        setCuentas([]);
      } else {
        console.error('Error al obtener cuentas');
      }
    } catch (err) {
      console.error('Error de conexión:', err);
    } finally {
      setLoadingCuentas(false);
    }
  };

  useEffect(() => {
    if (currentView === 'Información de Cuentas') {
      fetchCuentas();
    }
  }, [currentView]);

  const handleAccountSubmit = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem('token');
    const isEditing = !!editingAccount;
    const url = isEditing
      ? `http://localhost:8000/cuentas/actualizarcuenta/${editingAccount.id}`
      : 'http://localhost:8000/cuentas/crearcuenta';
    const method = isEditing ? 'PUT' : 'POST';

    const payload = isEditing ? {
      nombre_cuenta: accountData.nombre_cuenta,
      saldo_actual: parseFloat(accountData.saldo)
    } : {
      nombre_cuenta: accountData.nombre_cuenta,
      divisa: accountData.divisa,
      saldo_inicial: parseFloat(accountData.saldo)
    };

    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        fetchCuentas();
        setShowAccountForm(false);
        setEditingAccount(null);
      } else {
        const errData = await response.json();
        alert(errData.detail || 'Error al guardar la cuenta');
      }
    } catch (error) {
      alert('Error de conexión al servidor',error);
    }
  };

  const handleDeleteCuenta = async (id) => {
    if (!window.confirm('¿Estás seguro de eliminar esta cuenta de trading? Esta acción no se puede deshacer.')) return;
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8000/cuentas/eliminarcuenta/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        fetchCuentas();
      } else {
        const errData = await response.json();
        alert(errData.detail || 'Error al eliminar la cuenta');
      }
    } catch (error) {
      alert('Error de conexión al servidor', error);
    }
  };

  const openCreateForm = () => {
    setEditingAccount(null);
    setAccountData({ nombre_cuenta: '', divisa: 'EUR', saldo: '' });
    setShowAccountForm(true);
  };

  const openEditForm = (cuenta) => {
    setEditingAccount(cuenta);
    setAccountData({
      nombre_cuenta: cuenta.nombre_cuenta,
      divisa: cuenta.divisa,
      saldo: cuenta.saldo_actual
    });
    setShowAccountForm(true);
  };

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('rememberedEmail');
    localStorage.removeItem('userName');
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex" style={bgGradient}>
      <Sidebar sidebarOpen={sidebarOpen} onToggle={() => setSidebarOpen(prev => !prev)} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <header className="sticky top-0 z-40 bg-black/30 backdrop-blur-xl border-b border-white/10 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-gray-300 hover:text-white transition-colors">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
            </button>
            <h2 className="text-xl font-semibold text-white">Perfil de Usuario</h2>
          </div>
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2 text-white transition-colors">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span className="font-medium">{userData.name}</span>
            </div>
            <button onClick={handleLogout} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-full transition-all duration-300 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
              Cerrar Sesión
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-8">
          <div className="max-w-3xl mx-auto">
            <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/10 shadow-2xl">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8 pb-8 border-b border-white/10">
                <div className="flex items-center gap-6">
                  <div className="w-24 h-24 bg-blue-600/20 border border-blue-500/50 rounded-full flex items-center justify-center text-blue-400">
                    <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold text-white">{userData.name}</h3>
                    <p className="text-gray-400">{userData.email}</p>
                  </div>
                </div>
                
                {/* Selector de Vistas */}
                <div className="w-full md:w-64">
                  <CustomSelect
                    value={currentView}
                    onChange={setCurrentView}
                    options={['Información Personal', 'Información de Cuentas']}
                  />
                </div>
              </div>

              {error && (
                <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300">
                  {error}
                </div>
              )}

              {currentView === 'Información Personal' ? (
                <div className="space-y-6 animate-in fade-in duration-300">
                  <h4 className="text-lg font-semibold text-white mb-4">Información Personal</h4>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <label className="text-sm text-gray-400 block">Nombre Completo</label>
                      <input type="text" value={loading ? 'Cargando...' : userData.name} disabled className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:outline-none" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm text-gray-400 block">Correo Electrónico</label>
                      <input type="email" value={loading ? 'Cargando...' : userData.email} disabled className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:outline-none" />
                    </div>
                  </div>

                  <div className="pt-6 mt-6 border-t border-white/10">
                    <h4 className="text-lg font-semibold text-white mb-4">Ajustes</h4>
                    <p className="text-gray-400 text-sm mb-4">
                      Esta sección permite configurar preferencias adicionales de la cuenta en el futuro (cambio de contraseña, notificaciones, plan de suscripción).
                    </p>
                    <button className="px-6 py-2.5 bg-blue-600/50 text-white font-semibold rounded-xl cursor-not-allowed border border-blue-500/30">
                      Editar Perfil (Próximamente)
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-6 animate-in fade-in duration-300">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold text-white">Tus Cuentas de Trading</h4>
                    <button
                      onClick={openCreateForm}
                      className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-full transition-all duration-300 text-sm"
                    >
                      + Añadir Cuenta
                    </button>
                  </div>

                  {loadingCuentas ? (
                    <div className="text-center py-8 text-gray-400">Cargando cuentas...</div>
                  ) : cuentas.length === 0 ? (
                    <div className="text-center py-8 text-gray-400 border border-dashed border-white/10 rounded-xl">
                      No tienes cuentas de trading registradas.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {cuentas.map(cuenta => (
                        <div key={cuenta.id} className="bg-white/5 border border-white/10 p-5 rounded-xl flex flex-col sm:flex-row justify-between sm:items-center gap-4 hover:bg-white/10 transition-colors">
                          <div>
                            <h5 className="text-white font-bold text-lg">{cuenta.nombre_cuenta}</h5>
                            <div className="flex items-center gap-4 mt-1">
                              <span className="text-gray-400 text-sm">Divisa: <strong className="text-white">{cuenta.divisa}</strong></span>
                              <span className="text-gray-400 text-sm">Saldo Actual: <strong className={cuenta.saldo_actual >= cuenta.saldo_inicial ? "text-green-400" : "text-red-400"}>{formatCurrency(cuenta.saldo_actual, cuenta.divisa)}</strong></span>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={() => openEditForm(cuenta)}
                              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold rounded-full transition-colors"
                            >
                              Editar
                            </button>
                            <button
                              onClick={() => handleDeleteCuenta(cuenta.id)}
                              className="px-4 py-2 bg-red-600/80 hover:bg-red-700 text-white text-sm font-semibold rounded-full transition-colors"
                            >
                              Eliminar
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Modal Formulario de Cuenta */}
          {showAccountForm && (
            <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
              <div className="bg-[#1a2235] rounded-2xl p-6 border border-white/20 w-full max-w-md shadow-2xl animate-in zoom-in duration-200">
                <h2 className="text-xl font-bold mb-4 text-white">
                  {editingAccount ? 'Editar Cuenta' : 'Crear Cuenta Trading'}
                </h2>
                <form onSubmit={handleAccountSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs text-white mb-1">Nombre de Cuenta</label>
                    <input
                      type="text"
                      value={accountData.nombre_cuenta}
                      onChange={(e) => setAccountData({...accountData, nombre_cuenta: e.target.value})}
                      className="w-full p-2.5 text-sm text-white bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-blue-500"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-xs text-white mb-1">Divisa</label>
                    <div className={editingAccount ? "opacity-50 pointer-events-none" : ""}>
                      <CustomSelect
                        value={accountData.divisa}
                        onChange={(value) => setAccountData({...accountData, divisa: value})}
                        options={['EUR', 'USD']}
                      />
                    </div>
                    {editingAccount && <span className="text-[10px] text-gray-400 mt-1 block">La divisa no se puede modificar.</span>}
                  </div>
                  
                  <div>
                    <label className="block text-xs text-white mb-1">{editingAccount ? 'Saldo Actual' : 'Saldo Inicial'}</label>
                    <input
                      type="number"
                      step="any"
                      value={accountData.saldo}
                      onChange={(e) => setAccountData({...accountData, saldo: e.target.value})}
                      className="w-full p-2.5 text-sm text-white bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-blue-500"
                      required
                    />
                  </div>
                  
                  <div className="flex justify-end gap-3 pt-4">
                    <button type="button" onClick={() => setShowAccountForm(false)} className="px-5 py-2 text-sm text-white bg-gray-700 hover:bg-gray-600 rounded-full transition-colors">Cancelar</button>
                    <button type="submit" className="px-5 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-full transition-colors font-semibold">Guardar</button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default PerfilUsuario;
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import CustomSelect from './CustomSelect';
import AiSettings from './AiSettings';
import { formatCurrency } from '../utils/currency';
import { apiFetch } from '../config';
import { Spinner, LoadingState, ErrorState, EmptyState } from './ui';

const PerfilUsuario = () => {
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const navigate = useNavigate();

  const [userData, setUserData] = useState({ name: 'Cargando...', email: 'Cargando...' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tradingProfile, setTradingProfile] = useState({ strategy: '', plan: '' });
  const [savingTradingProfile, setSavingTradingProfile] = useState(false);
  const [tradingProfileSaved, setTradingProfileSaved] = useState(false);
  const [tradingProfileError, setTradingProfileError] = useState('');

  // Estados para Información de Cuentas
  const [currentView, setCurrentView] = useState('Información Personal');
  const [cuentas, setCuentas] = useState([]);
  const [loadingCuentas, setLoadingCuentas] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [defaultCurrency, setDefaultCurrency] = useState(() => localStorage.getItem('defaultCurrency') || 'EUR');
  const [prefsSaved, setPrefsSaved] = useState(false);
  const [avatar, setAvatar] = useState(() => localStorage.getItem('userAvatar') || '');
  const [avatarError, setAvatarError] = useState(null);
  const fileInputRef = useRef(null);
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [showFundsModal, setShowFundsModal] = useState(false);
  const [fundsType, setFundsType] = useState('add'); // 'add' or 'withdraw'
  const [fundsAmount, setFundsAmount] = useState('');
  const [selectedAccountForFunds, setSelectedAccountForFunds] = useState(null);
  const [accountData, setAccountData] = useState({
    nombre_cuenta: '',
    divisa: 'EUR',
    saldo: ''
  });

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = sessionStorage.getItem('token');
        if (!token) {
          navigate('/login');
          return;
        }
        const response = await apiFetch('/me', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setUserData(data);
          setTradingProfile({
            strategy: data.trading_strategy || '',
            plan: data.trading_plan || '',
          });
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
      const token = sessionStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }
      const response = await apiFetch('/cuentas/vercuentas', {
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

  const handleViewChange = (view) => {
    setCurrentView(view);
    if (view === 'Información de Cuentas') {
      fetchCuentas();
    }
  };

  const saveTradingProfile = async () => {
    const token = sessionStorage.getItem('token');
    if (!token || savingTradingProfile) return;

    setSavingTradingProfile(true);
    setTradingProfileSaved(false);
    setTradingProfileError('');
    try {
      const response = await apiFetch('/me/trading-profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          estrategia: tradingProfile.strategy,
          plan: tradingProfile.plan,
        }),
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'No se pudo guardar el contexto para EVA.');
      }
      const data = await response.json();
      setTradingProfile({
        strategy: data.trading_strategy || '',
        plan: data.trading_plan || '',
      });
      setTradingProfileSaved(true);
    } catch (requestError) {
      setTradingProfileError(requestError.message || 'No se pudo guardar el contexto para EVA.');
    } finally {
      setSavingTradingProfile(false);
    }
  };

  const handleAccountSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    const token = sessionStorage.getItem('token');
    const isEditing = !!editingAccount;
    const url = isEditing
      ? `/cuentas/actualizarcuenta/${editingAccount.id}`
      : '/cuentas/crearcuenta';
    const method = isEditing ? 'PUT' : 'POST';

    const payload = isEditing ? {
      nombre_cuenta: accountData.nombre_cuenta,
      saldo_actual: parseFloat(accountData.saldo)
    } : {
      nombre_cuenta: accountData.nombre_cuenta,
      divisa: accountData.divisa,
      saldo_inicial: parseFloat(accountData.saldo)
    };

    setSubmitting(true);
    setActionError(null);
    try {
      const response = await apiFetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        await fetchCuentas();
        setShowAccountForm(false);
        setEditingAccount(null);
      } else {
        const errData = await response.json();
        setActionError(errData.detail || 'Error al guardar la cuenta');
      }
    } catch (error) {
      setActionError('Error de conexión al servidor');
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteCuenta = async (id) => {
    if (deletingId) return;
    if (!window.confirm('¿Estás seguro de eliminar esta cuenta de trading? Esta acción no se puede deshacer.')) return;
    setDeletingId(id);
    setActionError(null);
    try {
      const token = sessionStorage.getItem('token');
      const response = await apiFetch(`/cuentas/eliminarcuenta/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        await fetchCuentas();
      } else {
        const errData = await response.json();
        setActionError(errData.detail || 'Error al eliminar la cuenta');
      }
    } catch (error) {
      setActionError('Error de conexión al servidor');
      console.error(error);
    } finally {
      setDeletingId(null);
    }
  };

  const openCreateForm = () => {
    setEditingAccount(null);
    setActionError(null);
    setAccountData({ nombre_cuenta: '', divisa: defaultCurrency, saldo: '' });
    setShowAccountForm(true);
  };

  const openEditForm = (cuenta) => {
    setEditingAccount(cuenta);
    setActionError(null);
    setAccountData({
      nombre_cuenta: cuenta.nombre_cuenta,
      divisa: cuenta.divisa,
      saldo: cuenta.saldo_actual
    });
    setShowAccountForm(true);
  };

  const openFundsModal = (cuenta, type) => {
    setSelectedAccountForFunds(cuenta);
    setFundsType(type);
    setFundsAmount('');
    setActionError(null);
    setShowFundsModal(true);
  };

  const handleFundsSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    const amount = parseFloat(fundsAmount);
    if (isNaN(amount) || amount <= 0) {
      setActionError('Por favor ingresa un monto válido mayor a 0');
      return;
    }

    const newSaldo = fundsType === 'add' 
      ? selectedAccountForFunds.saldo_actual + amount 
      : selectedAccountForFunds.saldo_actual - amount;

    if (newSaldo < 0) {
      setActionError('No puedes retirar más fondos de los que tienes en la cuenta');
      return;
    }

    setSubmitting(true);
    setActionError(null);
    try {
      const token = sessionStorage.getItem('token');
      const response = await apiFetch(`/cuentas/actualizarcuenta/${selectedAccountForFunds.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          saldo_actual: newSaldo
        })
      });

      if (response.ok) {
        await fetchCuentas();
        setShowFundsModal(false);
        setFundsAmount('');
        setSelectedAccountForFunds(null);
      } else {
        const errData = await response.json();
        setActionError(errData.detail || 'Error al actualizar el saldo');
      }
    } catch (error) {
      setActionError('Error de conexión al servidor');
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDefaultCurrencyChange = (value) => {
    setDefaultCurrency(value);
    localStorage.setItem('defaultCurrency', value);
    setPrefsSaved(true);
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarError(null);
    if (!file.type.startsWith('image/')) {
      setAvatarError('El archivo debe ser una imagen.');
      e.target.value = '';
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setAvatarError('La imagen no puede superar 2 MB.');
      e.target.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      setAvatar(dataUrl);
      localStorage.setItem('userAvatar', dataUrl);
    };
    reader.onerror = () => setAvatarError('No se pudo leer la imagen.');
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const handleRemoveAvatar = () => {
    setAvatar('');
    setAvatarError(null);
    localStorage.removeItem('userAvatar');
  };

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  const handleLogout = () => {
    sessionStorage.removeItem('token');
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
              {avatar ? (
                <img src={avatar} alt="Avatar del usuario" className="w-8 h-8 rounded-full object-cover border border-white/20" />
              ) : (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              )}
              <span className="font-medium">{userData.name}</span>
            </div>
            <button onClick={handleLogout} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-full transition-all duration-300 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
              Cerrar Sesión
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-8">
          <div className="max-w-6xl mx-auto">
            <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-8 md:p-10 border border-white/10 shadow-2xl min-h-[70vh]">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8 pb-8 border-b border-white/10">
                <div className="flex items-center gap-6">
                  <div className="relative group">
                    <button
                      type="button"
                      onClick={handleAvatarClick}
                      title="Cambiar imagen"
                      className="w-24 h-24 rounded-full overflow-hidden bg-blue-600/20 border border-blue-500/50 flex items-center justify-center text-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
                    >
                      {avatar ? (
                        <img src={avatar} alt="Avatar del usuario" className="w-full h-full object-cover" />
                      ) : (
                        <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      )}
                      <span className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50 text-white text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                        Cambiar
                      </span>
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleAvatarChange}
                      className="hidden"
                    />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold text-white">{userData.name}</h3>
                    <p className="text-gray-400">{userData.email}</p>
                    <div className="mt-2 flex items-center gap-3">
                      <button type="button" onClick={handleAvatarClick} className="text-xs font-medium text-blue-400 hover:text-blue-300 transition-colors">
                        Cambiar imagen
                      </button>
                      {avatar && (
                        <button type="button" onClick={handleRemoveAvatar} className="text-xs font-medium text-red-400 hover:text-red-300 transition-colors">
                          Quitar
                        </button>
                      )}
                    </div>
                    {avatarError && (
                      <p className="mt-1 text-xs text-red-400">{avatarError}</p>
                    )}
                  </div>
                </div>
                
              </div>

              <div className="flex flex-col md:flex-row gap-8">
                <nav className="md:w-56 flex-shrink-0">
                  <ul className="flex flex-wrap md:flex-col gap-2">
                    {['Información Personal', 'Información de Cuentas', 'Ajustes'].map((opt) => (
                      <li key={opt} className="flex-1 md:flex-none">
                        <button
                          type="button"
                          onClick={() => handleViewChange(opt)}
                          className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-all duration-300 ${
                            currentView === opt
                              ? 'bg-blue-600/30 text-blue-400 border border-blue-500/30'
                              : 'text-gray-300 hover:bg-white/10 hover:text-white border border-transparent'
                          }`}
                        >
                          {opt}
                        </button>
                      </li>
                    ))}
                  </ul>
                </nav>

                <div className="flex-1 min-w-0">
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

                  <section className="rounded-xl border border-blue-400/20 bg-blue-400/[0.05] p-5">
                    <h5 className="text-base font-semibold text-white">Contexto para EVA</h5>
                    <p className="mt-1 text-sm text-gray-300">
                      EVA tendrá en cuenta estas reglas al analizar tus operaciones. Es opcional, pero será más precisa si son concretas y verificables.
                    </p>
                    <p className="mt-2 text-xs text-blue-100/70">
                      Describe activos, temporalidad, condiciones de entrada, invalidación, salida y riesgo máximo. No incluyas contraseñas, claves API ni datos sensibles.
                    </p>

                    <div className="mt-5 space-y-5">
                      <label className="block text-sm text-gray-200">
                        Estrategia de trading
                        <textarea
                          value={tradingProfile.strategy}
                          onChange={(event) => {
                            setTradingProfile((current) => ({ ...current, strategy: event.target.value }));
                            setTradingProfileSaved(false);
                          }}
                          maxLength={4000}
                          rows={6}
                          placeholder="Ejemplo: Opero pullbacks a favor de tendencia en EUR/USD y NASDAQ en 15 min. Entro tras rechazo de zona y confirmación de estructura."
                          className="mt-2 w-full resize-y rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white outline-none transition placeholder:text-gray-600 focus:border-blue-400"
                        />
                      </label>

                      <label className="block text-sm text-gray-200">
                        Plan de trading y gestión de riesgo
                        <textarea
                          value={tradingProfile.plan}
                          onChange={(event) => {
                            setTradingProfile((current) => ({ ...current, plan: event.target.value }));
                            setTradingProfileSaved(false);
                          }}
                          maxLength={4000}
                          rows={6}
                          placeholder="Ejemplo: Arriesgo un 0,5 % por operación, máximo dos pérdidas al día. Cierro parcial en 1R y muevo el stop a break-even según mi regla."
                          className="mt-2 w-full resize-y rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white outline-none transition placeholder:text-gray-600 focus:border-blue-400"
                        />
                      </label>
                    </div>

                    {tradingProfileError && (
                      <p role="alert" className="mt-4 text-sm text-red-300">{tradingProfileError}</p>
                    )}
                    {tradingProfileSaved && (
                      <p className="mt-4 text-sm text-emerald-300">Contexto guardado. EVA lo tendrá en cuenta en el siguiente mensaje.</p>
                    )}
                    <button
                      type="button"
                      onClick={() => void saveTradingProfile()}
                      disabled={savingTradingProfile}
                      className="mt-5 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {savingTradingProfile && <Spinner size="sm" />}
                      {savingTradingProfile ? 'Guardando…' : 'Guardar contexto para EVA'}
                    </button>
                  </section>

                </div>
              ) : currentView === 'Información de Cuentas' ? (
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

                  {actionError && (
                    <ErrorState variant="inline" message={actionError} onDismiss={() => setActionError(null)} className="mb-4" />
                  )}

                  {loadingCuentas ? (
                    <LoadingState message="Cargando cuentas..." />
                  ) : cuentas.length === 0 ? (
                    <EmptyState message="No tienes cuentas de trading registradas." />
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
                              onClick={() => openFundsModal(cuenta, 'add')}
                              disabled={deletingId === cuenta.id}
                              className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              + Fondos
                            </button>
                            <button
                              onClick={() => openFundsModal(cuenta, 'withdraw')}
                              disabled={deletingId === cuenta.id}
                              className="px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white text-sm font-semibold rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              - Fondos
                            </button>
                            <button
                              onClick={() => openEditForm(cuenta)}
                              disabled={deletingId === cuenta.id}
                              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              Editar
                            </button>
                            <button
                              onClick={() => handleDeleteCuenta(cuenta.id)}
                              disabled={deletingId === cuenta.id}
                              className="px-4 py-2 bg-red-600/80 hover:bg-red-700 text-white text-sm font-semibold rounded-full transition-colors inline-flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {deletingId === cuenta.id && <Spinner size="sm" />}
                              {deletingId === cuenta.id ? 'Eliminando...' : 'Eliminar'}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-8 animate-in fade-in duration-300">
                  {/* Preferencias */}
                  <div>
                    <h4 className="text-lg font-semibold text-white mb-4">Preferencias</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <label className="text-sm text-gray-400 block">Divisa por defecto</label>
                        <CustomSelect
                          value={defaultCurrency}
                          onChange={handleDefaultCurrencyChange}
                          options={['EUR', 'USD']}
                        />
                        <p className="text-xs text-gray-500">Se usará como divisa predeterminada al crear nuevas cuentas.</p>
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm text-gray-400 block">Menú lateral</label>
                        <button
                          type="button"
                          onClick={() => setSidebarOpen(prev => !prev)}
                          className="w-full flex items-center justify-between bg-white/5 border border-white/10 rounded-xl p-3 text-white hover:bg-white/10 transition-colors"
                        >
                          <span>{sidebarOpen ? 'Expandido' : 'Contraído'}</span>
                          <span className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${sidebarOpen ? 'bg-blue-600' : 'bg-gray-600'}`}>
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${sidebarOpen ? 'translate-x-6' : 'translate-x-1'}`} />
                          </span>
                        </button>
                        <p className="text-xs text-gray-500">Preferencia guardada en este dispositivo.</p>
                      </div>
                    </div>
                    {prefsSaved && (
                      <p className="mt-3 text-sm text-green-400">Preferencias guardadas.</p>
                    )}
                  </div>

                  <AiSettings />

                  {/* Cuenta (requiere backend, no disponible) */}
                  <div className="pt-6 border-t border-white/10">
                    <h4 className="text-lg font-semibold text-white mb-2">Cuenta</h4>
                    <p className="text-gray-400 text-sm mb-4">Estas opciones aún no están disponibles.</p>
                    <div className="flex flex-wrap gap-3">
                      <button disabled title="No disponible" className="px-6 py-2.5 bg-blue-600/40 text-white/70 font-semibold rounded-xl cursor-not-allowed border border-blue-500/30">
                        Editar nombre y correo
                      </button>
                      <button disabled title="No disponible" className="px-6 py-2.5 bg-white/5 text-white/70 font-semibold rounded-xl cursor-not-allowed border border-white/10">
                        Cambiar contraseña
                      </button>
                    </div>
                  </div>

                  {/* Suscripción (requiere backend, no disponible) */}
                  <div className="pt-6 border-t border-white/10">
                    <h4 className="text-lg font-semibold text-white mb-2">Suscripción</h4>
                    <div className="flex items-center justify-between bg-white/5 border border-white/10 rounded-xl p-4">
                      <div>
                        <p className="text-white font-medium">Plan actual</p>
                        <p className="text-xs text-gray-500">Gestión de plan no disponible.</p>
                      </div>
                      <span className="px-3 py-1 rounded-full bg-gray-600/40 text-gray-300 text-xs font-semibold border border-white/10">No disponible</span>
                    </div>
                  </div>

                  {/* Sesión y zona de peligro */}
                  <div className="pt-6 border-t border-white/10">
                    <h4 className="text-lg font-semibold text-white mb-4">Sesión</h4>
                    <div className="flex flex-wrap gap-3">
                      <button
                        onClick={handleLogout}
                        className="px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl transition-colors inline-flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
                        Cerrar Sesión
                      </button>
                      <button disabled title="No disponible" className="px-6 py-2.5 bg-red-900/30 text-red-300/60 font-semibold rounded-xl cursor-not-allowed border border-red-500/20">
                        Eliminar cuenta
                      </button>
                    </div>
                  </div>
                </div>
              )}
                </div>
              </div>
            </div>
          </div>

          {/* Modal Formulario de Cuenta */}
          {showAccountForm && (
            <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
              <div className="bg-[#1a2235] rounded-2xl p-6 border border-white/20 w-full max-w-md shadow-2xl animate-in zoom-in duration-200">
                <h2 className="text-xl font-bold mb-4 text-white">
                  {editingAccount ? 'Editar Cuenta' : 'Crear Cuenta Trading'}
                </h2>
                {actionError && (
                  <ErrorState variant="inline" message={actionError} onDismiss={() => setActionError(null)} className="mb-4" />
                )}
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
                    <button type="button" onClick={() => setShowAccountForm(false)} disabled={submitting} className="px-5 py-2 text-sm text-white bg-gray-700 hover:bg-gray-600 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed">Cancelar</button>
                    <button type="submit" disabled={submitting} className="px-5 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-full transition-colors font-semibold inline-flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed">
                      {submitting && <Spinner size="sm" />}
                      {submitting ? 'Guardando...' : 'Guardar'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Modal Añadir/Retirar Fondos */}
          {showFundsModal && selectedAccountForFunds && (
            <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
              <div className="bg-[#1a2235] rounded-2xl p-6 border border-white/20 w-full max-w-md shadow-2xl animate-in zoom-in duration-200">
                <h2 className="text-xl font-bold mb-4 text-white">
                  {fundsType === 'add' ? 'Añadir Fondos' : 'Retirar Fondos'}
                </h2>
                <p className="text-sm text-gray-300 mb-4">
                  Cuenta: <strong>{selectedAccountForFunds.nombre_cuenta}</strong> ({selectedAccountForFunds.divisa})<br />
                  Saldo Actual: <strong>{formatCurrency(selectedAccountForFunds.saldo_actual, selectedAccountForFunds.divisa)}</strong>
                </p>
                {actionError && (
                  <ErrorState variant="inline" message={actionError} onDismiss={() => setActionError(null)} className="mb-4" />
                )}
                <form onSubmit={handleFundsSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs text-white mb-1">
                      Monto a {fundsType === 'add' ? 'Añadir' : 'Retirar'} ({selectedAccountForFunds.divisa})
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={fundsAmount}
                      onChange={(e) => setFundsAmount(e.target.value)}
                      className="w-full p-2.5 text-sm text-white bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-blue-500"
                      placeholder="0.00"
                      min="0"
                      required
                    />
                  </div>
                  
                  <div className="flex justify-end gap-3 pt-4">
                    <button type="button" onClick={() => setShowFundsModal(false)} disabled={submitting} className="px-5 py-2 text-sm text-white bg-gray-700 hover:bg-gray-600 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed">Cancelar</button>
                    <button type="submit" disabled={submitting} className="px-5 py-2 text-sm text-white bg-green-600 hover:bg-green-700 rounded-full transition-colors font-semibold inline-flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed">
                      {submitting && <Spinner size="sm" />}
                      {submitting ? 'Procesando...' : (fundsType === 'add' ? 'Añadir' : 'Retirar')}
                    </button>
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

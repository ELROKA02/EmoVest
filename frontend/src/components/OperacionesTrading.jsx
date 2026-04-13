import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import logo from '../assets/logoEmoVest.png';
import CustomSelect from './CustomSelect';

const API_BASE_URL = 'http://localhost:8000';

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` })
  };
};

const OperacionesTrading = () => {
  console.log('OperacionesTrading renderizado');

  // Obtener estado del sidebar desde localStorage o usar true por defecto
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const navigate = useNavigate();
  const location = useLocation();

  // Estados para backend
  const [cuentas, setCuentas] = useState([]);
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    localStorage.setItem('sidebarOpen', JSON.stringify(sidebarOpen));
  }, [sidebarOpen]);

  // Obtener el nombre del usuario del localStorage
  const userName = localStorage.getItem('userName') || 'Usuario';

  // Cargar cuentas al montar
  useEffect(() => {
    cargarCuentas();
  }, []);

  // Cargar operaciones cuando cambia la cuenta
  useEffect(() => {
    if (cuentaSeleccionada) {
      cargarOperacionesDeCuenta();
    }
  }, [cuentaSeleccionada]);

  const cargarCuentas = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/cuentas/vercuentas`, {
        method: 'GET',
        headers: getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error('Error al cargar cuentas');
      }
      const data = await response.json();
      setCuentas(data);
      if (data.length > 0) {
        setCuentaSeleccionada(data[0].id);
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const cargarOperacionesDeCuenta = async () => {
    if (!cuentaSeleccionada) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/cuentas/${cuentaSeleccionada}/operaciones/`, {
        method: 'GET',
        headers: getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error('Error al cargar operaciones');
      }
      const data = await response.json();
      setOperaciones(data);
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('rememberedEmail');
    navigate('/login');
  };

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

  const [operaciones, setOperaciones] = useState([]);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState({
    fecha_hora: '',
    tipo_operacion: 'LONG',
    cantidad: '',
    activo: '',
    precio_entrada: '',
    precio_salida: '',
    notas: '',
    stop_loss: '',
    take_profit: '',
    resultado: '',
    ratio_rr: '',
    nivel_confianza: '',
    screenshot: null
  });

  const handleCreate = () => {
    setEditing(null);
    setFormData({
      fecha_hora: new Date().toISOString().slice(0, 16),
      tipo_operacion: 'LONG',
      cantidad: '',
      activo: '',
      precio_entrada: '',
      precio_salida: '',
      notas: '',
      stop_loss: '',
      take_profit: '',
      resultado: '',
      ratio_rr: '',
      nivel_confianza: '',
      screenshot: null
    });
    setShowForm(true);
  };

  const handleEdit = (op) => {
    setEditing(op.id);
    setFormData({
      fecha_hora: new Date(op.fecha_hora).toISOString().slice(0, 16),
      tipo_operacion: op.tipo_operacion,
      cantidad: op.cantidad,
      activo: op.activo,
      precio_entrada: op.precio_entrada,
      precio_salida: op.precio_salida || '',
      notas: op.notas || '',
      stop_loss: op.stop_loss || '',
      take_profit: op.take_profit || '',
      resultado: op.resultado || '',
      ratio_rr: op.ratio_rr || '',
      nivel_confianza: op.nivel_confianza || '',
      screenshot: op.screenshot || null
    });
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Estás seguro de eliminar esta operación?')) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/cuentas/${cuentaSeleccionada}/operaciones/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error('Error al eliminar operación');
      }
      setOperaciones(operaciones.filter(op => op.id !== id));
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!cuentaSeleccionada) {
      setError('Debes seleccionar una cuenta');
      return;
    }

    const data = {
      fecha_hora: new Date(formData.fecha_hora).toISOString(),
      tipo_operacion: formData.tipo_operacion,
      cantidad: parseFloat(formData.cantidad),
      activo: formData.activo,
      precio_entrada: parseFloat(formData.precio_entrada),
      precio_salida: formData.precio_salida ? parseFloat(formData.precio_salida) : null,
      notas: formData.notas || null,
      stop_loss: formData.stop_loss ? parseFloat(formData.stop_loss) : null,
      take_profit: formData.take_profit ? parseFloat(formData.take_profit) : null,
      resultado: formData.resultado ? parseFloat(formData.resultado) : null,
      ratio_rr: formData.ratio_rr ? parseFloat(formData.ratio_rr) : null,
      nivel_confianza: formData.nivel_confianza ? parseInt(formData.nivel_confianza) : null,
      screenshot: formData.screenshot
    };

    setLoading(true);
    setError(null);
    try {
      if (editing) {
        const response = await fetch(`${API_BASE_URL}/cuentas/${cuentaSeleccionada}/operaciones/${editing}`, {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify(data)
        });
        if (!response.ok) {
          throw new Error('Error al actualizar operación');
        }
        setOperaciones(operaciones.map(op => op.id === editing ? { ...op, ...data, id: editing } : op));
      } else {
        const response = await fetch(`${API_BASE_URL}/cuentas/${cuentaSeleccionada}/operaciones/`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify(data)
        });
        if (!response.ok) {
          throw new Error('Error al crear operación');
        }
        await cargarOperacionesDeCuenta();
      }
      setShowForm(false);
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
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
                  className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-all duration-300 ${
                    location.pathname === item.path
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
            <h2 className="text-xl font-semibold text-white">Operaciones de Trading</h2>
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
        <main className="flex-1 overflow-auto p-8">
          <div className="container mx-auto">
            {error && (
              <div className="mb-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300">
                {error}
                <button onClick={() => setError(null)} className="ml-4 underline">Cerrar</button>
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between mb-6">
              <div className="flex flex-col gap-2">
                <label className="text-sm text-gray-300">Seleccionar Cuenta:</label>
                <CustomSelect
                  value={cuentaSeleccionada ? cuentas.find(c => c.id === cuentaSeleccionada)?.nombre_cuenta + ' (' + cuentas.find(c => c.id === cuentaSeleccionada)?.divisa + ')' : 'Cargando cuentas...'}
                  onChange={(selectedText) => {
                    const cuenta = cuentas.find(c => selectedText.includes(c.nombre_cuenta));
                    if (cuenta) setCuentaSeleccionada(cuenta.id);
                  }}
                  options={cuentas.length === 0 ? ['Cargando cuentas...'] : cuentas.map(cuenta => `${cuenta.nombre_cuenta} (${cuenta.divisa})`)}
                />
              </div>

              <button
                onClick={handleCreate}
                disabled={!cuentaSeleccionada || loading}
                className="mt-6 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white font-semibold rounded-full transition-all duration-300"
              >
                {loading ? 'Cargando...' : 'Crear Operación'}
              </button>
            </div>

            <div className="mt-12 bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10 overflow-x-auto">
              {loading && (
                <div className="py-8 text-center text-gray-300">
                  <p>Cargando operaciones...</p>
                </div>
              )}
              
              {!loading && operaciones.length === 0 ? (
                <div className="py-8 text-center text-gray-300">
                  <p>No hay operaciones registradas para esta cuenta.</p>
                </div>
              ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="text-gray-400 border-b border-white/10">
                    <th className="p-4">Fecha</th>
                    <th className="p-4">Tipo</th>
                    <th className="p-4">Activo</th>
                    <th className="p-4">Cantidad</th>
                    <th className="p-4">Precio Entrada</th>
                    <th className="p-4">Precio Salida</th>
                    <th className="p-4">Notas</th>
                    <th className="p-4">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {operaciones.map(op => (
                    <tr key={op.id} className="border-t text-white border-white/10 hover:bg-white/5 transition-colors">
                      <td className="p-4">{new Date(op.fecha_hora).toLocaleString()}</td>
                      <td className={`p-4  font-bold ${op.tipo_operacion === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                        {op.tipo_operacion}
                      </td>
                      <td className="p-4 text-white">{op.activo}</td>
                      <td className="p-4 text-white">{op.cantidad}</td>
                      <td className="p-4 font-mono text-white">${op.precio_entrada}</td>
                      <td className="p-4 font-mono text-white">{op.precio_salida ? `$${op.precio_salida}` : '-'}</td>
                      <td className="p-4 text-sm text-gray-300">{op.notas || '-'}</td>
                      <td className="p-4 flex gap-2">
                        <button
                          onClick={() => handleEdit(op)}
                          disabled={loading}
                          className="px-4 py-2 text-white bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 rounded-full text-sm transition-colors disabled:cursor-not-allowed"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => handleDelete(op.id)}
                          disabled={loading}
                          className="px-4 py-2 text-white bg-red-600 hover:bg-red-700 disabled:bg-red-600/50 rounded-full text-sm transition-colors disabled:cursor-not-allowed"
                        >
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              )}
            </div>

            {showForm && (
              <div className="fixed inset-0 bg-black/50 backdrop-blur-md flex items-center justify-center z-50 p-4">
                <div className="bg-[#1a2235]/80 backdrop-blur-lg rounded-2xl p-6 border border-white/30 w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
                  <h2 className="text-2xl font-bold mb-4 text-white">{editing ? 'Editar Operación' : 'Crear Operación'}</h2>
                  <form onSubmit={handleSubmit} className="space-y-3">
                    <div>
                      <label className="block text-xs text-white mb-1">Fecha y Hora</label>
                      <input
                        type="datetime-local"
                        value={formData.fecha_hora}
                        onChange={(e) => setFormData({...formData, fecha_hora: e.target.value})}
                        className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                        disabled={loading}
                        required
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-xs text-white mb-1">Tipo</label>
                        <CustomSelect
                          value={formData.tipo_operacion}
                          onChange={(value) => setFormData({...formData, tipo_operacion: value})}
                          options={['LONG', 'SHORT']}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-white mb-1">Activo</label>
                        <input
                          type="text"
                          placeholder="BTC"
                          value={formData.activo}
                          onChange={(e) => setFormData({...formData, activo: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-white mb-1">Cantidad</label>
                        <input
                          type="number"
                          step="any"
                          value={formData.cantidad}
                          onChange={(e) => setFormData({...formData, cantidad: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          required
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-xs text-white mb-1">Precio Entrada</label>
                        <input
                          type="number"
                          step="any"
                          value={formData.precio_entrada}
                          onChange={(e) => setFormData({...formData, precio_entrada: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-white mb-1">Precio Salida</label>
                        <input
                          type="number"
                          step="any"
                          value={formData.precio_salida}
                          onChange={(e) => setFormData({...formData, precio_salida: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          placeholder="Opt"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-white mb-1">Stop Loss</label>
                        <input
                          type="number"
                          step="any"
                          value={formData.stop_loss}
                          onChange={(e) => setFormData({...formData, stop_loss: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          placeholder="Opt"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-xs text-white mb-1">Take Profit</label>
                        <input
                          type="number"
                          step="any"
                          value={formData.take_profit}
                          onChange={(e) => setFormData({...formData, take_profit: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          placeholder="Opt"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-white mb-1">Resultado</label>
                        <input
                          type="number"
                          step="any"
                          value={formData.resultado}
                          onChange={(e) => setFormData({...formData, resultado: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          placeholder="G/P"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-white mb-1">Ratio RR</label>
                        <input
                          type="number"
                          step="any"
                          value={formData.ratio_rr}
                          onChange={(e) => setFormData({...formData, ratio_rr: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          placeholder="R/R"
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="block text-xs text-white">Confianza: <span className="text-blue-400 font-bold">{formData.nivel_confianza || 0}%</span></label>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={formData.nivel_confianza}
                        onChange={(e) => setFormData({...formData, nivel_confianza: e.target.value})}
                        className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        disabled={loading}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-white mb-1">Notas</label>
                      <textarea
                        value={formData.notas}
                        onChange={(e) => setFormData({...formData, notas: e.target.value})}
                        className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500 h-12"
                        disabled={loading}
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <button
                        type="button"
                        onClick={() => setShowForm(false)}
                        disabled={loading}
                        className="px-4 py-1.5 text-xs text-white bg-gray-700 hover:bg-gray-600 disabled:bg-gray-700/50 rounded-full transition-colors disabled:cursor-not-allowed"
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        disabled={loading}
                        className="px-4 py-1.5 text-xs text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 rounded-full transition-colors font-bold disabled:cursor-not-allowed"
                      >
                        {loading ? 'Guardando...' : 'Guardar'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default OperacionesTrading;
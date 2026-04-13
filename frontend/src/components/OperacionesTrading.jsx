import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import logo from '../assets/logoEmoVest.png';

const OperacionesTrading = () => {
  console.log('OperacionesTrading renderizado');

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

  const [operaciones, setOperaciones] = useState([
    {
      id: 1,
      fecha_hora: '2023-10-01T10:00:00',
      tipo_operacion: 'LONG',
      cantidad: 100,
      activo: 'AAPL',
      precio_entrada: 150.00,
      precio_salida: 155.00,
      notas: 'Operación exitosa'
    },
    {
      id: 2,
      fecha_hora: '2023-10-02T11:00:00',
      tipo_operacion: 'SHORT',
      cantidad: 50,
      activo: 'GOOGL',
      precio_entrada: 2800.00,
      precio_salida: null,
      notas: 'En progreso'
    }
  ]);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState({
    fecha_hora: '',
    tipo_operacion: 'LONG',
    cantidad: '',
    activo: '',
    precio_entrada: '',
    precio_salida: '',
    notas: ''
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
      notas: ''
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
      notas: op.notas || ''
    });
    setShowForm(true);
  };

  const handleDelete = (id) => {
    if (window.confirm('¿Estás seguro de eliminar esta operación?')) {
      setOperaciones(operaciones.filter(op => op.id !== id));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const data = {
      ...formData,
      fecha_hora: new Date(formData.fecha_hora).toISOString(),
      cantidad: parseFloat(formData.cantidad),
      precio_entrada: parseFloat(formData.precio_entrada),
      precio_salida: formData.precio_salida ? parseFloat(formData.precio_salida) : null
    };

    if (editing) {
      setOperaciones(operaciones.map(op => op.id === editing ? { ...op, ...data, id: editing } : op));
    } else {
      const newOp = { ...data, id: Date.now() };
      setOperaciones([...operaciones, newOp]);
    }
    setShowForm(false);
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
            <div className="mb-4">
              <button
                onClick={handleCreate}
                className="mt-6 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-full transition-all duration-300"
              >
                Crear Operación
              </button>
            </div>

            <div className="mt-12 bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10 overflow-x-auto">
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
                          className="px-4 py-2 text-white bg-purple-600 hover:bg-purple-700 rounded-full text-sm transition-colors"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => handleDelete(op.id)}
                          className="px-4 py-2 text-white bg-red-600 hover:bg-red-700 rounded-full text-sm transition-colors"
                        >
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {showForm && (
              <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                <div className="bg-[#1a2235] rounded-2xl p-8 border border-white/20 w-full max-w-md shadow-2xl">
                  <h2 className="text-2xl font-bold mb-6 text-white">{editing ? 'Editar Operación' : 'Crear Operación'}</h2>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <label className="block text-sm text-white mb-1">Fecha y Hora</label>
                      <input
                        type="datetime-local"
                        value={formData.fecha_hora}
                        onChange={(e) => setFormData({...formData, fecha_hora: e.target.value})}
                        className="w-full p-2 text-white bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-blue-500"
                        required
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-white mb-1">Tipo</label>
                        <select
                          value={formData.tipo_operacion}
                          onChange={(e) => setFormData({...formData, tipo_operacion: e.target.value})}
                          className="w-full p-2 text-white bg-white/5 border border-white/10 rounded-lg focus:outline-none"
                        >
                          <option value="LONG">LONG</option>
                          <option value="SHORT">SHORT</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm text-white mb-1">Activo</label>
                        <input
                          type="text"
                          placeholder="Ej: BTC"
                          value={formData.activo}
                          onChange={(e) => setFormData({...formData, activo: e.target.value})}
                          className="w-full p-2 text-white bg-white/5 border border-white/10 rounded-lg"
                          required
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-white mb-1">Cantidad</label>
                        <input
                          type="number"
                          step="any"
                          value={formData.cantidad}
                          onChange={(e) => setFormData({...formData, cantidad: e.target.value})}
                          className="w-full p-2 bg-white/5 border border-white/10 rounded-lg"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-white mb-1">Precio Entrada</label>
                        <input
                          type="number"
                          step="any"
                          value={formData.precio_entrada}
                          onChange={(e) => setFormData({...formData, precio_entrada: e.target.value})}
                          className="w-full p-2 text-white bg-white/5 border border-white/10 rounded-lg"
                          required
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm text-white mb-1">Precio Salida (Opcional)</label>
                      <input
                        type="number"
                        step="any"
                        value={formData.precio_salida}
                        onChange={(e) => setFormData({...formData, precio_salida: e.target.value})}
                        className="w-full p-2 bg-white/5 border border-white/10 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-white mb-1">Notas</label>
                      <textarea
                        value={formData.notas}
                        onChange={(e) => setFormData({...formData, notas: e.target.value})}
                        className="w-full p-2 text-white bg-white/5 border border-white/10 rounded-lg h-20"
                      />
                    </div>
                    <div className="flex justify-end gap-3 pt-4">
                      <button
                        type="button"
                        onClick={() => setShowForm(false)}
                        className="px-6 py-2 text-white bg-gray-700 hover:bg-gray-600 rounded-full transition-colors"
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        className="px-6 py-2 text-white bg-blue-600 hover:bg-blue-700 rounded-full transition-colors font-bold"
                      >
                        Guardar
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
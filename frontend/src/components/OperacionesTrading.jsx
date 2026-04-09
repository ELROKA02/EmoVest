import React, { useState } from 'react';

const OperacionesTrading = () => {
  console.log('🎯 Componente OperacionesTrading renderizado');

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
    <div className="min-h-screen bg-gradient-to-br from-[#050a10] via-[#1a364d] to-[#101422] text-white p-8 pt-20">
      <div className="container mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">Operaciones Trading</h1>
        
        <div className="mb-4">
          <button
            onClick={handleCreate}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-full transition-all duration-300"
          >
            Crear Operación
          </button>
        </div>

        <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10 overflow-x-auto">
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
                <tr key={op.id} className="border-t border-white/10 hover:bg-white/5 transition-colors">
                  <td className="p-4">{new Date(op.fecha_hora).toLocaleString()}</td>
                  <td className={`p-4 font-bold ${op.tipo_operacion === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                    {op.tipo_operacion}
                  </td>
                  <td className="p-4">{op.activo}</td>
                  <td className="p-4">{op.cantidad}</td>
                  <td className="p-4 font-mono">${op.precio_entrada}</td>
                  <td className="p-4 font-mono">{op.precio_salida ? `$${op.precio_salida}` : '-'}</td>
                  <td className="p-4 text-sm text-gray-300">{op.notas || '-'}</td>
                  <td className="p-4 flex gap-2">
                    <button
                      onClick={() => handleEdit(op)}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-full text-sm transition-colors"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => handleDelete(op.id)}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-full text-sm transition-colors"
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
              <h2 className="text-2xl font-bold mb-6">{editing ? 'Editar Operación' : 'Crear Operación'}</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Fecha y Hora</label>
                  <input
                    type="datetime-local"
                    value={formData.fecha_hora}
                    onChange={(e) => setFormData({...formData, fecha_hora: e.target.value})}
                    className="w-full p-2 bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Tipo</label>
                    <select
                      value={formData.tipo_operacion}
                      onChange={(e) => setFormData({...formData, tipo_operacion: e.target.value})}
                      className="w-full p-2 bg-[#1a2235] border border-white/10 rounded-lg focus:outline-none"
                    >
                      <option value="LONG">LONG</option>
                      <option value="SHORT">SHORT</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Activo</label>
                    <input
                      type="text"
                      placeholder="Ej: BTC"
                      value={formData.activo}
                      onChange={(e) => setFormData({...formData, activo: e.target.value})}
                      className="w-full p-2 bg-white/5 border border-white/10 rounded-lg"
                      required
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Cantidad</label>
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
                    <label className="block text-sm text-gray-400 mb-1">Precio Entrada</label>
                    <input
                      type="number"
                      step="any"
                      value={formData.precio_entrada}
                      onChange={(e) => setFormData({...formData, precio_entrada: e.target.value})}
                      className="w-full p-2 bg-white/5 border border-white/10 rounded-lg"
                      required
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Precio Salida (Opcional)</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.precio_salida}
                    onChange={(e) => setFormData({...formData, precio_salida: e.target.value})}
                    className="w-full p-2 bg-white/5 border border-white/10 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Notas</label>
                  <textarea
                    value={formData.notas}
                    onChange={(e) => setFormData({...formData, notas: e.target.value})}
                    className="w-full p-2 bg-white/5 border border-white/10 rounded-lg h-20"
                  />
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-full transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-full transition-colors font-bold"
                  >
                    Guardar
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OperacionesTrading;
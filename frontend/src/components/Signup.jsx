import React, { useState } from 'react'; 
import logo from '../assets/logoEmoVest.png'; 
import { Link, useNavigate } from 'react-router-dom';
import { apiFetch } from '../config';

const Signup = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [formData, setFormData] = useState({
        nombre: '',
        correo_electronico: '',
        contrasena: '',
        confirmar_contrasena: '',
        terminos: false
    });

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
        setError('');
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        // Validaciones
        if (!formData.nombre.trim()) {
            setError('Por favor ingresa tu nombre completo');
            return;
        }

        if (!formData.correo_electronico.trim()) {
            setError('Por favor ingresa un correo electrónico válido');
            return;
        }

        if (formData.contrasena.length < 6) {
            setError('La contraseña debe tener al menos 6 caracteres');
            return;
        }

        if (formData.contrasena !== formData.confirmar_contrasena) {
            setError('Las contraseñas no coinciden');
            return;
        }

        if (!formData.terminos) {
            setError('Debes aceptar los términos y condiciones');
            return;
        }

        setLoading(true);

        try {
            const response = await apiFetch('/signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    nombre: formData.nombre,
                    correo_electronico: formData.correo_electronico,
                    contrasena: formData.contrasena
                })
            });

            const data = await response.json();

            if (!response.ok) {
                setError(data.detail || 'Error al registrarse. Intenta de nuevo.');
                return;
            }

            setSuccess('¡Cuenta creada exitosamente! Redireccionando...');
            setTimeout(() => {
                navigate('/login');
            }, 2000);
        } catch (err) {
            setError('Error de conexión. Verifica que el servidor esté corriendo.');
            console.error('Error:', err);
        } finally {
            setLoading(false);
        }
    };

    return (

        <div className="fixed inset-0 w-full h-full flex flex-col justify-center items-center bg-[#050a10] p-3 sm:p-4 overflow-y-auto">
            
            {/* Logo */}
            <div className="mb-4 flex justify-center pt-60">
                <img
                    src={logo}
                    alt="EmoVest Logo"
                    className="w-40 h-auto object-contain"
                />
            </div>

            <div className="w-full max-w-[350px] sm:max-w-[400px] bg-white/5 backdrop-blur-xl rounded-[32px] p-4 sm:p-6 shadow-2xl border border-white/10 animate-in fade-in zoom-in duration-500">
                <h1 className="text-xl sm:text-2xl font-bold text-white mb-4 text-center tracking-tight">
                    Crear Cuenta
                </h1>

                <p className="text-gray-400 text-xs sm:text-sm mb-6 text-center px-4">
                    Regístrate en EmoVest para comenzar a invertir con inteligencia emocional.
                </p>

                {error && (
                    <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-red-400 text-xs sm:text-sm mb-4">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="bg-green-500/10 border border-green-500/50 rounded-lg p-3 text-green-400 text-xs sm:text-sm mb-4">
                        {success}
                    </div>
                )}

                <form className="space-y-4" onSubmit={handleSubmit}>
                    <input
                        type="text"
                        name="nombre"
                        placeholder="Nombre completo"
                        value={formData.nombre}
                        onChange={handleChange}
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white placeholder-gray-500"
                        required
                    />
                    <input
                        type="email"
                        name="correo_electronico"
                        placeholder="Correo electrónico"
                        value={formData.correo_electronico}
                        onChange={handleChange}
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white placeholder-gray-500"
                        required
                    />
                    <input
                        type="password"
                        name="contrasena"
                        placeholder="Contraseña"
                        value={formData.contrasena}
                        onChange={handleChange}
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white placeholder-gray-500"
                        required
                    />
                    <input
                        type="password"
                        name="confirmar_contrasena"
                        placeholder="Confirmar contraseña"
                        value={formData.confirmar_contrasena}
                        onChange={handleChange}
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white placeholder-gray-500"
                        required
                    />

                    <label className="flex items-start space-x-3 cursor-pointer group">
                        <input 
                            type="checkbox" 
                            name="terminos"
                            checked={formData.terminos}
                            onChange={handleChange}
                            className="w-4 h-4 bg-[#0d1117]/90 border border-white/5 rounded text-blue-600 focus:ring-blue-500 focus:ring-2 focus:ring-offset-0 mt-0.5 flex-shrink-0"
                            required
                        />
                        <span className="text-xs text-gray-400 group-hover:text-white transition-colors">
                            Acepto los <a href="/docs/Terminos_y_Condiciones_EmoVest_Logo.pdf" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 underline">términos y condiciones</a> y la <a href="/docs/Politica_de_Privacidad_EmoVest.pdf" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 underline">política de privacidad</a>
                        </span>
                    </label>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-[#2563eb] hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-3 mt-4 rounded-xl active:scale-[0.98] transition-all text-[10px] sm:text-[11px] md:text-[12px] uppercase tracking-wider shadow-lg shadow-blue-900/20"
                    >
                        {loading ? 'Registrando...' : 'Registrarse'}
                    </button>
                </form>

                <div className="mt-6 text-center">
                    <p className="text-xs sm:text-sm md:text-base text-gray-400">
                        ¿Ya tienes cuenta? <Link to="/login" className="text-white font-bold hover:underline">Inicia Sesión</Link>
                    </p>
                </div>

                <div className="mt-6 pt-4 border-t border-white/5 text-center">
                    <p className="text-[10px] sm:text-[12px] text-gray-500 uppercase mb-1">EmoVest Ecosystem</p>
                    <p className="text-[10px] sm:text-[12px] text-gray-600">Al registrarte, aceptas nuestras Condiciones y Privacidad.</p>
                </div>
            </div>
            
            <Link to="/" className="mt-4 text-gray-500 text-[12px] sm:text-[14px] hover:text-white transition-colors pb-10">
                — VOLVER AL INICIO —
            </Link>
        </div>
    );
};

export default Signup;

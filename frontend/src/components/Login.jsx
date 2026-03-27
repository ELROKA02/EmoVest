import React, { useState } from 'react'; 
import logo from '../assets/logoEmoVest.png'; 
import { Link, useNavigate } from 'react-router-dom';

const Login = () => {
    const [email, setEmail] = useState(() => localStorage.getItem('rememberedEmail') || '');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [rememberMe, setRememberMe] = useState(() => !!localStorage.getItem('rememberedEmail'));
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            const response = await fetch('http://localhost:8000/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    correo_electronico: email,
                    contrasena: password,
                }),
            });
            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('token', data.access_token);
                if (rememberMe) {
                    localStorage.setItem('rememberedEmail', email);
                } else {
                    localStorage.removeItem('rememberedEmail');
                }
                navigate('/dashboard');
            } else {
                const errorData = await response.json();
                setError(errorData.detail || 'Error en el login');
            }
        } catch {
            setError('Error de conexión al servidor');
        }
    };

    return (
       
        <div className="fixed inset-0 w-full h-full flex flex-col justify-center items-center bg-[#050a10] overflow-hidden p-3 sm:p-4">
            
            {}
            <div className="mb-4 flex justify-center">
                <img
                    src={logo}
                    alt="EmoVest Logo"
                    className="w-40 h-auto object-contain"
                />
            </div>

            <div className="w-full max-w-[350px] sm:max-w-[400px] bg-white/5 backdrop-blur-xl rounded-[32px] p-4 sm:p-6 shadow-2xl border border-white/10 animate-in fade-in zoom-in duration-500">
                <h1 className="text-xl sm:text-2xl font-bold text-white mb-1 text-center tracking-tight pb-2">
                    Bienvenido
                </h1>

                <p className="text-gray-400 text-xs sm:text-sm mb-5 text-center px-4">
                    Ingresa tus credenciales para acceder a EmoVest
                </p>

                <form className="space-y-3" onSubmit={handleSubmit}>
                    <input
                        type="email"
                        placeholder="Correo electrónico"
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                    <div className="space-y-3">
                        <input
                            type="password"
                            placeholder="Contraseña"
                            className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                        <div className="flex items-center justify-between">
                            <label className="flex items-center space-x-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="w-4 h-4 bg-[#0d1117]/90 border border-white/5 rounded text-blue-600 focus:ring-blue-500 focus:ring-2 focus:ring-offset-0"
                                    checked={rememberMe}
                                    onChange={(e) => setRememberMe(e.target.checked)}
                                />
                                <span className="text-xs text-gray-400 hover:text-white transition-colors">
                                    Recordar usuario
                                </span>
                            </label>
                            <a href="#" className="text-[10px] sm:text-[12px] text-blue-400/80 hover:text-blue-300 transition-colors">
                                ¿Olvidaste tu contraseña?
                            </a>
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="w-full bg-[#2563eb] hover:bg-green-600 text-white font-bold py-3 mt-2 rounded-xl active:scale-[0.98] transition-all text-[10px] sm:text-[11px] md:text-[12px] uppercase tracking-wider shadow-lg shadow-blue-900/20"
                    >
                        Iniciar Sesión
                    </button>
                </form>

                {error && <p className="text-red-500 text-sm mt-2 text-center">{error}</p>}

                <div className="mt-4 text-center">
                    <p className="text-xs sm:text-sm md:text-base text-gray-400">
                        ¿No tienes cuenta? <Link to="/signin" className="text-white font-bold hover:underline">Regístrate</Link>
                    </p>
                </div>

                <div className="mt-5 pt-4 border-t border-white/5 text-center">
                    <p className="text-[10px] sm:text-[12px] text-gray-500 uppercase mb-1">EmoVest Ecosystem</p>
                    <p className="text-[10px] sm:text-[12px] text-gray-600">Al continuar, aceptas nuestras Condiciones y Privacidad.</p>
                </div>
            </div>
            
            <Link to="/" className="mt-4 text-gray-500 text-[12px] sm:text-[14px] hover:text-white transition-colors">
                — VOLVER AL INICIO —
            </Link>
        </div>
    );
};

export default Login;
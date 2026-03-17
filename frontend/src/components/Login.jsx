import React from 'react'; 
import logo from '../assets/logoEmoVest.png'; 
import { Link } from 'react-router-dom';

const Login = () => {
    return (
        /* fixed inset-0 fuerza al componente a ocupar toda la pantalla sin desbordar */
        <div className="fixed inset-0 w-full h-full flex flex-col justify-center items-center bg-[#050a10] overflow-hidden p-3 sm:p-4">
            
            {/* Logo - Reducido un poco para ganar espacio */}
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
                    Ingresa tus credenciales para acceder a **EmoVest**.
                </p>

                <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
                    <input
                        type="email"
                        placeholder="Correo electrónico / Nickname"
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                        required
                    />
                    <div className="space-y-3">
                        <input
                            type="password"
                            placeholder="Contraseña"
                            className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                            required
                        />
                        <div className="text-right">
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
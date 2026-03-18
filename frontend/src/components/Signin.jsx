import React from 'react'; 
import logo from '../assets/logoEmoVest.png'; 
import { Link } from 'react-router-dom';

const Signin = () => {
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

                <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
                    <input
                        type="text"
                        placeholder="Nombre completo"
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                        required
                    />
                    <input
                        type="text"
                        placeholder="Username"
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                        required
                    />
                    <input
                        type="email"
                        placeholder="Correo electrónico"
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                        required
                    />
                    <input
                        type="password"
                        placeholder="Contraseña"
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                        required
                    />
                    <input
                        type="password"
                        placeholder="Confirmar contraseña"
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                        required
                    />

                    <label className="flex items-start space-x-3 cursor-pointer group">
                        <input 
                            type="checkbox" 
                            className="w-4 h-4 bg-[#0d1117]/90 border border-white/5 rounded text-blue-600 focus:ring-blue-500 focus:ring-2 focus:ring-offset-0 mt-0.5 flex-shrink-0"
                            required
                        />
                        <span className="text-xs text-gray-400 group-hover:text-white transition-colors">
                            Acepto los <span className="text-blue-400 hover:text-blue-300 underline">términos y condiciones</span> y la <span className="text-blue-400 hover:text-blue-300 underline">política de privacidad</span>
                        </span>
                    </label>

                    <button
                        type="submit"
                        className="w-full bg-[#2563eb] hover:bg-green-600 text-white font-bold py-3 mt-4 rounded-xl active:scale-[0.98] transition-all text-[10px] sm:text-[11px] md:text-[12px] uppercase tracking-wider shadow-lg shadow-blue-900/20"
                    >
                        Registrarse
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

export default Signin;
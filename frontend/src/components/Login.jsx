import React from 'react'; 
import logo from '../assets/logoEmoVest.png'; 
import { Link } from 'react-router-dom';

const Login = () => {
    const handleSubmit = (e) => {
        e.preventDefault();
        console.log("Formulario enviado");
    };

    return (
        /* Contenedor principal sin fondo propio, usando el espacio de App.js */
        <div className="w-full max-w-[440px] animate-in fade-in zoom-in duration-500">
            
            {/* Logo - Centrado sobre la tarjeta */}
            <div className="mb-8 w-full flex justify-center">
                <img
                    src={logo}
                    alt="EmoVest Logo"
                    className="w-48 h-auto object-contain drop-shadow-2xl"
                />
            </div>

        
            <div
                className="bg-white/5 backdrop-blur-xl rounded-[40px] p-10 md:p-12 shadow-[0_20px_50px_rgba(0,0,0,0.3)] border border-white/10"
            >
                <h1 className="text-3xl font-bold text-white mb-2 text-center tracking-tight">
                    Bienvenido
                </h1>

                <p className="text-gray-400 text-sm mb-10 text-center px-4">
                    Ingresa tus credenciales para acceder a **EmoVest**.
                </p>

                <form className="space-y-5" onSubmit={handleSubmit}>
                    <div className="space-y-1">
                        <input
                            type="email"
                            placeholder="Correo electrónico"
                            className="w-full bg-[#0d1117]/80 border border-white/5 focus:border-blue-500/50 p-4 rounded-2xl outline-none transition-all placeholder:text-gray-600 text-white shadow-inner"
                            required
                        />
                    </div>

                    <div className="space-y-1">
                        <input
                            type="password"
                            placeholder="Contraseña"
                            className="w-full bg-[#0d1117]/80 border border-white/5 focus:border-blue-500/50 p-4 rounded-2xl outline-none transition-all placeholder:text-gray-600 text-white shadow-inner"
                            required
                        />
                        <div className="text-right pr-2">
                            <a href="#" className="text-[11px] text-blue-400/80 hover:text-blue-300 transition-colors">
                                ¿Olvidaste tu contraseña?
                            </a>
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="w-full bg-blue-600 hover:bg-green-600 text-white font-bold py-4 mt-4 rounded-2xl active:scale-[0.98] transition-all tracking-widest text-xs uppercase shadow-lg shadow-blue-600/20"
                    >
                        Iniciar Sesión
                    </button>
                </form>

                <div className="mt-8 text-center">
                    <p className="text-sm text-gray-400">
                        ¿No tienes cuenta? <Link to="/register" className="text-white font-bold hover:text-blue-400 transition-colors underline-offset-4 hover:underline">Regístrate</Link>
                    </p>
                </div>

                <hr className="my-8 border-white/5" />

                <div className="text-[10px] text-gray-500 space-y-2 text-center leading-relaxed">
                    <p className="uppercase tracking-tighter opacity-70">EmoVest Ecosystem</p>
                    <p>Al continuar, aceptas nuestras Condiciones y Privacidad.</p>
                </div>
            </div>
            
            {/* Botón opcional para volver atrás si el header no existe */}
            <div className="mt-8 text-center">
                <Link to="/" className="text-gray-500 text-xs hover:text-white transition-colors">
                   ← Volver al inicio
                </Link>
            </div>
        </div>
    );
};

export default Login;
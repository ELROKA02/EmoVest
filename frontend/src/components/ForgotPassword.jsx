import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import logo from '../assets/logoEmoVest.png';
import { API_BASE_URL } from '../config';

const ForgotPassword = () => {
    const [email, setEmail] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');

        if (!email.trim()) {
            setError('Ingresa tu correo electrónico.');
            return;
        }

        setLoading(true);

        try {
            const response = await fetch(`${API_BASE_URL}/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ correo_electronico: email }),
            });

            const data = await response.json();

            if (!response.ok) {
                setError(data.detail || 'No se pudo procesar la solicitud.');
                return;
            }

            setMessage(data.msg || 'Si existe una cuenta asociada, recibirás un email con instrucciones.');
        } catch (err) {
            console.error('Error:', err);
            setError('Error de conexión con el servidor.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 w-full h-full flex flex-col justify-center items-center bg-[#050a10] overflow-hidden p-3 sm:p-4">
            <div className="mb-4 flex justify-center">
                <img src={logo} alt="EmoVest Logo" className="w-40 h-auto object-contain" />
            </div>

            <div className="w-full max-w-[350px] sm:max-w-[400px] bg-white/5 backdrop-blur-xl rounded-[32px] p-4 sm:p-6 shadow-2xl border border-white/10 animate-in fade-in zoom-in duration-500">
                <h1 className="text-xl sm:text-2xl font-bold text-white mb-2 text-center tracking-tight">
                    Recuperar contraseña
                </h1>
                <p className="text-gray-400 text-xs sm:text-sm mb-6 text-center px-4">
                    Te enviaremos un enlace para restablecer tu contraseña al correo registrado.
                </p>

                {error && <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm mb-4">{error}</div>}
                {message && <div className="bg-green-500/10 border border-green-500/50 rounded-lg p-3 text-green-400 text-sm mb-4">{message}</div>}

                <form className="space-y-4" onSubmit={handleSubmit}>
                    <input
                        type="email"
                        placeholder="Correo electrónico"
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-[#2563eb] hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl active:scale-[0.98] transition-all text-[10px] sm:text-[11px] md:text-[12px] uppercase tracking-wider shadow-lg shadow-blue-900/20"
                    >
                        {loading ? 'Enviando...' : 'Enviar enlace'}
                    </button>
                </form>

                <div className="mt-5 text-center">
                    <p className="text-xs sm:text-sm md:text-base text-gray-400">
                        ¿Recordaste tu contraseña? <Link to="/login" className="text-white font-bold hover:underline">Inicia Sesión</Link>
                    </p>
                </div>
            </div>

            <Link to="/" className="mt-4 text-gray-500 text-[12px] sm:text-[14px] hover:text-white transition-colors">
                — VOLVER AL INICIO —
            </Link>
        </div>
    );
};

export default ForgotPassword;

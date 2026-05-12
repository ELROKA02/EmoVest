import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import logo from '../assets/logoEmoVest.png';

const ResetPassword = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const token = searchParams.get('token') || '';
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!token) {
            setError('El enlace de restablecimiento es inválido.');
        }
    }, [token]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');

        if (!token) {
            setError('Falta el token de recuperación.');
            return;
        }

        if (password.length < 6) {
            setError('La contraseña debe tener al menos 6 caracteres.');
            return;
        }

        if (password !== confirmPassword) {
            setError('Las contraseñas no coinciden.');
            return;
        }

        setLoading(true);

        try {
            const response = await fetch('http://localhost:8000/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, contrasena: password }),
            });

            const data = await response.json();

            if (!response.ok) {
                setError(data.detail || 'No se pudo cambiar la contraseña.');
                return;
            }

            setMessage('Contraseña restablecida con éxito. Redireccionando a login...');
            setTimeout(() => {
                navigate('/login');
            }, 2500);
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
                    Restablecer contraseña
                </h1>
                <p className="text-gray-400 text-xs sm:text-sm mb-6 text-center px-4">
                    Escribe una nueva contraseña para tu cuenta.
                </p>

                {error && <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm mb-4">{error}</div>}
                {message && <div className="bg-green-500/10 border border-green-500/50 rounded-lg p-3 text-green-400 text-sm mb-4">{message}</div>}

                <form className="space-y-4" onSubmit={handleSubmit}>
                    <input
                        type="password"
                        placeholder="Nueva contraseña"
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                    <input
                        type="password"
                        placeholder="Confirmar contraseña"
                        className="w-full bg-[#0d1117]/90 border border-white/5 focus:border-blue-500/50 p-2.5 sm:p-3 rounded-xl outline-none text-sm text-white"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                    />

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-[#2563eb] hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl active:scale-[0.98] transition-all text-[10px] sm:text-[11px] md:text-[12px] uppercase tracking-wider shadow-lg shadow-blue-900/20"
                    >
                        {loading ? 'Restableciendo...' : 'Guardar contraseña'}
                    </button>
                </form>

                <div className="mt-5 text-center">
                    <p className="text-xs sm:text-sm md:text-base text-gray-400">
                        ¿Ya tienes cuenta? <Link to="/login" className="text-white font-bold hover:underline">Inicia Sesión</Link>
                    </p>
                </div>
            </div>

            <Link to="/" className="mt-4 text-gray-500 text-[12px] sm:text-[14px] hover:text-white transition-colors">
                — VOLVER AL INICIO —
            </Link>
        </div>
    );
};

export default ResetPassword;

import { Link, useLocation } from 'react-router-dom';
import Navbar from './Navbar';
import logo from '../assets/logoEmoVest.png';


function Header() {
    const location = useLocation();

    // Si la ruta actual es del área privada, no renderizamos el header regular
    if (location.pathname === '/login' || location.pathname === '/signup' || location.pathname.startsWith('/dashboard') || location.pathname === '/trading' || location.pathname === '/perfil' || location.pathname === '/estadisticas' || location.pathname === '/calendar' || location.pathname === '/forgot-password' || location.pathname === '/reset-password') {
        return null;
    }


    return (
        <header className="fixed left-0 right-0 top-0 z-50 flex items-center justify-between border-b border-violet-400/10 bg-[#050a10]/55 px-6 py-2 text-white shadow-lg shadow-black/10 backdrop-blur-2xl">
            <Link to="/" className="flex items-center gap-3">
                <img
                    src={logo}
                    alt="Logo"
                    className="h-[50px] w-auto object-contain transition-transform group-hover:scale-105"
                />
                <h1 className="font-cinzel text-[24px] font-bold tracking-widest">
                    EmoVest
                </h1>
            </Link>

            <Navbar />
        </header>
    );
}

export default Header;

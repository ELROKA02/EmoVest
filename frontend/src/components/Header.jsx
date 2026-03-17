import { Link, useLocation } from 'react-router-dom';
import Navbar from './Navbar';
import logo from '../assets/logoEmoVest.png';

function Header() {

    const bgGradient = {
        background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
    };

    const location = useLocation();

    // Si la ruta actual es /login, no renderizamos el header
    if (location.pathname === '/login') {
        return null;
    }else if(location.pathname === '/signin'){
        return null;
    }


    return (
        <header style={bgGradient} className="flex justify-between items-center px-6 py-4 backdrop-blur-md text-white fixed top-0 left-0 right-0 z-50 border-b border-white/10">
            <Link to="/" className="flex items-center gap-4">
                <img
                    src={logo}
                    alt="Logo"
                    className="h-[100px] w-auto object-contain transition-transform group-hover:scale-105"
                />
                <h1 className="font-cinzel text-[40px] font-bold tracking-widest">
                    EmoVest
                </h1>
            </Link>

            <Navbar />
        </header>
    );
}

export default Header;
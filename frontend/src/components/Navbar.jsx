import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { fetchAndStoreUserName } from '../utils/userSession';

function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredButton, setHoveredButton] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const isLoggedIn = !!localStorage.getItem('token');
  const showLogout = isLoggedIn && location.pathname === '/dashboard';

  const [userName, setUserName] = useState(localStorage.getItem('userName') || 'Usuario');

  useEffect(() => {
    let isMounted = true;

    const loadCurrentUser = async () => {
      try {
        const name = await fetchAndStoreUserName();
        if (name && isMounted) {
          setUserName(name);
        }
      } catch (error) {
        console.error('Error al cargar usuario actual:', error);
      }
    };

    if (isLoggedIn) {
      loadCurrentUser();
    }

    return () => {
      isMounted = false;
    };
  }, [isLoggedIn]);

  const handleButtonClick = () => {
    setIsOpen(false); 
    navigate('/login'); 
  };

  const handleRegisterClick = () => {
    setIsOpen(false); 
    navigate('/signup'); 
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('rememberedEmail');
    localStorage.removeItem('userName');
    setIsOpen(false);
    navigate('/login');
  };

  const handleTradingClick = () => {
    setIsOpen(false);
    navigate('/dashboard');
  };

  const links = isLoggedIn ? [] : [
    { name: 'Quiénes somos', href: '#que-somos' },
    { name: 'Suscripciones', href: '#suscripciones' },
    { name: 'Sobre nosotros', href: '#sobre-nosotros' },
  ];

  return (
    <nav className="relative">
      {/* Desktop Menu */}
      <ul className="hidden md:flex items-center space-x-6 lg:space-x-8">
        {links.map(link => (
          <li key={link.name}>
            <a 
              href={link.href} 
              className="bg-gradient-to-r from-transparent to-transparent text-white px-4 lg:px-6 py-2.5 lg:py-3 rounded-full font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg text-xs lg:text-sm uppercase tracking-wider hover:from-purple-600 hover:to-purple-700 border border-purple-600/30 hover:border-purple-500"
            >
              {link.name}
            </a>
          </li>
        ))}
        {isLoggedIn && location.pathname !== '/trading' && location.pathname !== '/perfil' && (
          <li>
            <button
              onClick={handleTradingClick}
              className="bg-gradient-to-r from-transparent to-transparent text-white px-4 lg:px-6 py-2.5 lg:py-3 rounded-full font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg text-xs lg:text-sm uppercase tracking-wider hover:from-purple-600 hover:to-purple-700 border border-purple-600/30 hover:border-purple-500"
            >
              Trading
            </button>
          </li>
        )}
        {isLoggedIn && (
          <>
            <li className="flex items-center gap-3 ml-4 lg:ml-6">
              {/* User Icon */}
              <div onClick={() => navigate('/perfil')} className="flex items-center gap-2 text-gray-300 hover:text-white cursor-pointer transition-colors" title="Ver perfil">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span className="font-medium">{userName}</span>
              </div>

              {/* Logout Button */}
              <button 
                onClick={handleLogout}
                onMouseEnter={() => setHoveredButton('logout')}
                onMouseLeave={() => setHoveredButton(null)}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-full transition-all duration-300 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Cerrar Sesión
              </button>
            </li>
          </>
        )}
        {!isLoggedIn && (
          <>
            <li className="ml-4 lg:ml-6">
              <button 
                onClick={handleButtonClick}
                onMouseEnter={() => setHoveredButton('login')}
                onMouseLeave={() => setHoveredButton(null)}
                className={`bg-gradient-to-r text-white px-4 lg:px-6 py-2.5 lg:py-3 rounded-full font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg text-xs lg:text-sm uppercase tracking-wider ${
                  hoveredButton === 'login' 
                    ? 'from-green-600 to-green-700 hover:from-green-700 hover:to-green-800' 
                    : hoveredButton === 'register'
                    ? 'from-green-600 to-green-700 hover:from-green-700 hover:to-green-800'
                    : 'from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800'
                }`}
              >
                Iniciar Sesión
              </button>
            </li>
            <li>
              <button 
                onClick={handleRegisterClick}
                onMouseEnter={() => setHoveredButton('register')}
                onMouseLeave={() => setHoveredButton(null)}
                className={`bg-gradient-to-r text-white px-4 lg:px-6 py-2.5 lg:py-3 rounded-full font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg text-xs lg:text-sm uppercase tracking-wider ${
                  hoveredButton === 'register' 
                    ? 'from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800' 
                    : hoveredButton === 'login'
                    ? 'from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800'
                    : 'from-green-600 to-green-700 hover:from-green-700 hover:to-green-800'
                }`}
              >
                Registrarse
              </button>
            </li>
          </>
        )}
      </ul>

      {/* Mobile Menu Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="md:hidden flex flex-col justify-center items-center w-8 h-8 space-y-1.5"
      >
        <span className={`block w-6 h-0.5 bg-white transition-all duration-300 ${isOpen ? 'rotate-45 translate-y-2' : ''}`}></span>
        <span className={`block w-6 h-0.5 bg-white transition-all duration-300 ${isOpen ? 'opacity-0' : ''}`}></span>
        <span className={`block w-6 h-0.5 bg-white transition-all duration-300 ${isOpen ? '-rotate-45 -translate-y-2' : ''}`}></span>
      </button>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden absolute top-full right-0 mt-2 w-64 bg-white/10 backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl overflow-hidden">
          <ul className="flex flex-col p-4 space-y-3">
            {links.map(link => (
              <li key={link.name}>
                <a 
                  href={link.href}
                  onClick={() => setIsOpen(false)}
                  className="block text-sm font-medium text-gray-300 hover:text-white transition-all duration-300 px-3 py-2 rounded-lg hover:bg-white/10"
                >
                  {link.name}
                </a>
              </li>
            ))}
            <li className="pt-3 border-t border-white/20 space-y-3">
              {showLogout ? (
                <button 
                  onClick={handleLogout} 
                  className="w-full bg-gradient-to-r from-red-600 to-red-700 text-white px-4 py-3 rounded-full font-semibold hover:from-red-700 hover:to-red-800 transition-all duration-300 text-xs uppercase tracking-wider"
                >
                  Cerrar Sesión
                </button>
              ) : (
                <>
                  <button 
                    onClick={handleButtonClick} 
                    className="w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-3 rounded-full font-semibold hover:from-blue-700 hover:to-blue-800 transition-all duration-300 text-xs uppercase tracking-wider"
                  >
                    Iniciar Sesión
                  </button>
                  <button 
                    onClick={handleRegisterClick} 
                    className="w-full bg-gradient-to-r from-green-600 to-green-700 text-white px-4 py-3 rounded-full font-semibold hover:from-green-700 hover:to-green-800 transition-all duration-300 text-xs uppercase tracking-wider"
                  >
                    Registrarse
                  </button>
                </>
              )}
            </li>
          </ul>
        </div>
      )}
    </nav>
  );
}

export default Navbar;
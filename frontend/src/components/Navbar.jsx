import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredButton, setHoveredButton] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const isLoggedIn = !!localStorage.getItem('token');
  const showLogout = isLoggedIn && location.pathname === '/dashboard';

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
    setIsOpen(false);
    navigate('/login');
  };

  const links = [
    { name: 'Quiénes somos', href: '#que-somos' },
    { name: 'Suscripciones', href: '#suscripciones' },
    { name: 'Sobre nosotros', href: '#sobre-nosotros' },
  ];

  const handleTradingClick = () => {
    setIsOpen(false);
    navigate('/trading');
  };

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
        {isLoggedIn && (
          <li>
            <button
              onClick={handleTradingClick}
              className="bg-gradient-to-r from-transparent to-transparent text-white px-4 lg:px-6 py-2.5 lg:py-3 rounded-full font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg text-xs lg:text-sm uppercase tracking-wider hover:from-purple-600 hover:to-purple-700 border border-purple-600/30 hover:border-purple-500"
            >
              Trading
            </button>
          </li>
        )}
        {showLogout ? (
          <li className="ml-4 lg:ml-6">
            <button 
              onClick={handleLogout}
              onMouseEnter={() => setHoveredButton('logout')}
              onMouseLeave={() => setHoveredButton(null)}
              className={`bg-gradient-to-r text-white px-4 lg:px-6 py-2.5 lg:py-3 rounded-full font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg text-xs lg:text-sm uppercase tracking-wider from-red-600 to-red-700 hover:from-red-700 hover:to-red-800`}
            >
              Cerrar Sesión
            </button>
          </li>
        ) : (
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
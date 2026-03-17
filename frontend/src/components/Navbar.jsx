import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();

  const handleButtonClick = () => {
    setIsOpen(false); 
    navigate('/login'); 
  };

  const handleRegisterClick = () => {
    setIsOpen(false); 
    navigate('/signin'); 
  };

  const links = [
    { name: 'Sobre Nosotros', href: '#sobre-nosotros' },
    { name: 'Servicios', href: '#servicios' },
    { name: 'Ubicación', href: '#ubicacion' },
  ];

  return (
    <nav className="relative">
      {/* Desktop Menu */}
      <ul className="hidden md:flex items-center space-x-6 lg:space-x-8">
        {links.map(link => (
          <li key={link.name}>
            <a 
              href={link.href} 
              className="text-sm font-medium text-gray-300 hover:text-white transition-all duration-300 hover:scale-105 px-3 py-2 rounded-lg"
            >
              {link.name}
            </a>
          </li>
        ))}
        <li className="ml-4 lg:ml-6">
          <button 
            onClick={handleButtonClick} 
            className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 lg:px-6 py-2.5 lg:py-3 rounded-full font-semibold hover:from-blue-700 hover:to-blue-800 transition-all duration-300 hover:scale-105 hover:shadow-lg text-xs lg:text-sm uppercase tracking-wider"
          >
            Iniciar Sesión
          </button>
        </li>
        <li>
          <button 
            onClick={handleRegisterClick} 
            className="bg-gradient-to-r from-green-600 to-green-700 text-white px-4 lg:px-6 py-2.5 lg:py-3 rounded-full font-semibold hover:from-green-700 hover:to-green-800 transition-all duration-300 hover:scale-105 hover:shadow-lg text-xs lg:text-sm uppercase tracking-wider"
          >
            Registrarse
          </button>
        </li>
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
            </li>
          </ul>
        </div>
      )}
    </nav>
  );
}

export default Navbar;
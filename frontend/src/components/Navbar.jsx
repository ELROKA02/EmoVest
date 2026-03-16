import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();

  const handleButtonClick = () => {
    setIsOpen(false); 
    navigate('/login'); 
  };

  const links = [
    { name: 'Sobre Nosotros', href: '#sobre-nosotros' },
    { name: 'Servicios', href: '#servicios' },
    { name: 'Ubicación', href: '#ubicacion' },
  ];

  return (
    <nav className="relative">
      <ul className="hidden md:flex space-x-12 items-center">
        {links.map(link => (
          <li key={link.name}>
            <a href={link.href} className="text-sm uppercase tracking-widest hover:text-green-500 transition-colors">
              {link.name}
            </a>
          </li>
        ))}
        <li>
          <button 
            onClick={handleButtonClick} 
            className="bg-white text-black px-8 py-4 rounded-full font-bold hover:bg-green-600 hover:text-white transition-all uppercase text-xs"
          >
            Iniciar Sesión
          </button>
        </li>
      </ul>
    </nav>
  );
}

export default Navbar;
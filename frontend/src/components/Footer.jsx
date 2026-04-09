import React from 'react';

const Footer = () => {
  // Ocultar footer si el usuario ha iniciado sesión
  const isLoggedIn = !!localStorage.getItem('token');
  
  if (isLoggedIn) {
    return null;
  }
  
  return (
    <footer className="w-full py-6 text-center border-t border-white/10 bg-[#050a10]">
      <p className="text-gray-400 text-sm">
        2026 EmoVest. Todos los derechos reservados.
      </p>
      <p className="text-gray-500 text-xs mt-2">
        Invierte con inteligencia emocional
      </p>
    </footer>
  );
};

export default Footer;
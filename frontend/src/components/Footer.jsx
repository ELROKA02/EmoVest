import React from 'react';

const Footer = () => {
  // Ocultar footer si el usuario ha iniciado sesión
  const isLoggedIn = !!sessionStorage.getItem('token');
  const contactEmail = 'contactoemovest@gmail.com';
  
  if (isLoggedIn) {
    return null;
  }
  
  return (
    <footer className="w-full py-6 text-center border-t border-white/10 bg-[#050a10]">
      <p className="text-gray-400 text-sm">
        2026 EmoVest. Open source bajo licencia MIT.
      </p>
      <p className="text-gray-500 text-xs mt-2">
        Invierte con inteligencia emocional
      </p>
      <a className="mt-3 inline-block text-sm font-semibold text-violet-300 hover:text-violet-200" href={`mailto:${contactEmail}`}>
        {contactEmail}
      </a>
    </footer>
  );
};

export default Footer;

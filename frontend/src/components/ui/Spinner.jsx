import React from 'react';

const sizeMap = {
  sm: 'h-4 w-4 border-2',
  md: 'h-8 w-8 border-2',
  lg: 'h-12 w-12 border-[3px]',
};

const Spinner = ({ size = 'md', className = '' }) => {
  const dimensions = sizeMap[size] || sizeMap.md;
  return (
    <span
      role="status"
      aria-label="Cargando"
      className={`inline-block animate-spin rounded-full border-white/20 border-t-blue-500 ${dimensions} ${className}`}
    />
  );
};

export default Spinner;

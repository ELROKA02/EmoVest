import React from 'react';
import Spinner from './Spinner';

const LoadingState = ({ message = 'Cargando...', size = 'lg', className = '' }) => {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center gap-4 py-12 text-gray-300 ${className}`}
    >
      <Spinner size={size} />
      {message && <p className="text-sm text-gray-400">{message}</p>}
    </div>
  );
};

export default LoadingState;

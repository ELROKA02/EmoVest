import React from 'react';

const ErrorState = ({
  message = 'Ha ocurrido un error.',
  onRetry,
  onDismiss,
  variant = 'block',
  className = '',
}) => {
  if (variant === 'inline') {
    return (
      <div
        role="alert"
        className={`flex flex-wrap items-center gap-3 rounded-lg border border-red-500/50 bg-red-500/20 p-4 text-red-300 ${className}`}
      >
        <span className="flex-1 min-w-0 text-sm">{message}</span>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-full border border-red-400/40 px-3 py-1 text-xs font-semibold text-red-200 transition hover:bg-red-500/30"
          >
            Reintentar
          </button>
        )}
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="text-xs underline text-red-200/80 transition hover:text-red-100"
          >
            Cerrar
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      role="alert"
      className={`flex flex-col items-center justify-center gap-4 rounded-2xl border border-red-500/30 bg-red-500/10 py-12 px-6 text-center ${className}`}
    >
      <svg className="h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
      <p className="max-w-md text-sm text-red-200">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-full bg-red-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
        >
          Reintentar
        </button>
      )}
    </div>
  );
};

export default ErrorState;

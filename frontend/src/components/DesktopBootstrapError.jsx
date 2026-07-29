const DesktopBootstrapError = ({ error, onRetry }) => (
  <main className="min-h-screen bg-[#050a10] px-6 py-12 text-white">
    <section className="mx-auto flex min-h-[70vh] max-w-xl flex-col items-center justify-center text-center">
      <div className="mb-5 rounded-full border border-red-400/30 bg-red-400/10 p-4 text-red-300">
        <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M12 9v4m0 4h.01M10.3 3.8 2.7 17a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.8a2 2 0 0 0-3.4 0Z" />
        </svg>
      </div>
      <h1 className="text-2xl font-semibold">EmoVest no pudo iniciar el servicio local</h1>
      <p className="mt-3 text-sm leading-6 text-slate-300">
        Tus datos no se han eliminado. Puedes reintentar el arranque o copiar este mensaje
        para soporte.
      </p>
      <pre className="mt-6 max-h-40 w-full overflow-auto rounded-xl border border-white/10 bg-black/30 p-4 text-left text-xs text-slate-300">
        {error?.message || 'Error de inicio desconocido.'}
      </pre>
      <button
        type="button"
        onClick={onRetry}
        className="mt-6 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold transition hover:bg-blue-500"
      >
        Reintentar
      </button>
    </section>
  </main>
);

export default DesktopBootstrapError;

import { useState } from 'react';
import ImportOperationsButton from './ImportOperationsButton';
import MetaTraderImportWizard from '../MetaTraderImportWizard';

const ImportOperationsMenu = ({ cuentaId, disabled = false, onImported }) => {
  const [showMetaTrader, setShowMetaTrader] = useState(false);

  return (
    <>
      <details className="group relative">
        <summary className="inline-flex min-h-11 cursor-pointer list-none items-center gap-2 rounded-full border border-slate-500/70 bg-slate-800/80 px-5 py-2.5 text-sm font-semibold text-slate-100 hover:bg-slate-700/90 [&::-webkit-details-marker]:hidden">
          Importar
          <svg className="h-4 w-4 transition group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="m6 9 6 6 6-6" /></svg>
        </summary>
        <div className="absolute right-0 z-50 mt-2 flex min-w-60 flex-col gap-2 rounded-2xl border border-white/10 bg-slate-950/95 p-3 shadow-2xl backdrop-blur-xl">
          <ImportOperationsButton cuentaId={cuentaId} disabled={disabled} onImported={onImported} />
          <button type="button" disabled={disabled || !cuentaId} onClick={() => setShowMetaTrader(true)} className="inline-flex min-h-11 items-center justify-center rounded-full border border-blue-400/40 bg-blue-500/10 px-5 text-sm font-semibold text-blue-100 hover:bg-blue-500/20 disabled:opacity-40">MetaTrader 5 (HTML)</button>
        </div>
      </details>
      {showMetaTrader && <MetaTraderImportWizard accountId={cuentaId} onClose={() => setShowMetaTrader(false)} onImported={onImported} />}
    </>
  );
};

export default ImportOperationsMenu;

import { useMemo, useState } from 'react';
import { apiFetch } from '../config';

const readError = async (response) => {
  try {
    const payload = await response.json();
    return typeof payload?.detail === 'string'
      ? payload.detail
      : payload?.detail?.message || 'El informe no ha superado la validación.';
  } catch {
    return `No se pudo procesar el informe (${response.status}).`;
  }
};

const MetaTraderImportWizard = ({ accountId, onClose, onImported }) => {
  const defaultZone = useMemo(() => Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC', []);
  const [file, setFile] = useState(null);
  const [timezone, setTimezone] = useState(defaultZone);
  const [preview, setPreview] = useState(null);
  const [resolutionJson, setResolutionJson] = useState('[]');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const token = sessionStorage.getItem('token');

  const request = async (action) => {
    if (!file || !accountId) return;
    try {
      new Intl.DateTimeFormat(undefined, { timeZone: timezone }).format();
    } catch {
      setError('La zona horaria debe ser un identificador IANA válido, por ejemplo Europe/Madrid.');
      return;
    }
    try {
      const resolution = JSON.parse(resolutionJson || '[]');
      if (!Array.isArray(resolution)) throw new Error();
    } catch {
      setError('La resolución manual debe ser una lista JSON válida.');
      return;
    }
    const body = new FormData();
    body.append('file', file);
    body.append('zona_horaria', timezone);
    body.append('resolution_json', resolutionJson || '[]');
    if (action === 'commit') body.append('expected_preview_token', preview.preview_token);
    setBusy(true);
    setError('');
    try {
      const response = await apiFetch(`/cuentas/${accountId}/importaciones/metatrader/${action}`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body,
      });
      if (!response.ok) throw new Error(await readError(response));
      const payload = await response.json();
      if (action === 'preview') setPreview(payload);
      else {
        await onImported?.(payload);
        onClose();
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[10020] flex items-start justify-center overflow-y-auto bg-black/75 p-4 pt-10 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Importar informe MetaTrader 5">
      <div className="w-full max-w-5xl rounded-3xl border border-white/10 bg-[#101827] p-5 text-slate-100 shadow-2xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div><h2 className="text-xl font-bold">Importar desde MetaTrader 5</h2><p className="text-sm text-slate-400">Informe HTML · Deals · solo posiciones cerradas en esta primera versión</p></div>
          <button type="button" onClick={onClose} className="rounded-full p-2 text-slate-400 hover:bg-white/10 hover:text-white" aria-label="Cerrar">✕</button>
        </div>

        <div className="grid gap-3 sm:grid-cols-[1fr_18rem_auto]">
          <label className="text-xs text-slate-400">Informe HTML
            <input type="file" accept=".html,.htm,text/html" onChange={(event) => { setFile(event.target.files?.[0] || null); setPreview(null); }} className="mt-1 block w-full rounded-xl border border-white/10 bg-white/5 p-2 text-sm" />
          </label>
          <label className="text-xs text-slate-400">Zona horaria del servidor (IANA)
            <input value={timezone} onChange={(event) => { setTimezone(event.target.value); setPreview(null); }} placeholder="Europe/Madrid" className="mt-1 block w-full rounded-xl border border-white/10 bg-white/5 p-2 text-sm text-white" />
          </label>
          <button type="button" disabled={!file || !timezone || busy} onClick={() => request('preview')} className="mt-5 min-h-10 rounded-xl bg-blue-600 px-4 text-sm font-semibold hover:bg-blue-500 disabled:opacity-40">{busy ? 'Analizando…' : 'Previsualizar'}</button>
        </div>

        {error && <p className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200" role="alert">{error}</p>}
        {preview && (
          <div className="mt-5 space-y-5">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-6">
              {Object.entries(preview.summary).map(([name, value]) => <div key={name} className="rounded-xl bg-white/5 p-3"><div className="text-xl font-bold">{value}</div><div className="text-[10px] uppercase text-slate-400">{name.replace('_', ' ')}</div></div>)}
            </div>
            <p className="text-xs text-slate-400">Cuenta origen: {preview.account} · Broker: {preview.broker || 'No indicado'} · Codificación: {preview.encoding}</p>

            <section><h3 className="mb-2 font-semibold">Operaciones propuestas</h3>
              <div className="max-h-64 overflow-auto rounded-xl border border-white/10">
                <table className="w-full text-xs"><thead className="sticky top-0 bg-slate-900"><tr><th className="p-2">Position</th><th>Activo</th><th>Lado</th><th>Cantidad</th><th>Entradas</th><th>Salidas</th></tr></thead>
                  <tbody>{preview.proposed_operations.map((item) => <tr key={item.position} className="border-t border-white/10 text-center"><td className="p-2">{item.position}</td><td>{item.activo}</td><td>{item.tipo_operacion}</td><td>{item.cantidad}</td><td>{item.entries.length}</td><td>{item.exits.length}</td></tr>)}</tbody>
                </table>
              </div>
            </section>
            <div className="grid gap-4 md:grid-cols-3">
              <section><h3 className="font-semibold">Movimientos ({preview.movements.length})</h3>{preview.movements.map((item) => <p key={item.deal} className="text-xs text-slate-400">{item.tipo}: {item.importe}</p>)}</section>
              <section><h3 className="font-semibold">Abiertas omitidas ({preview.skipped_open.length})</h3>{preview.skipped_open.map((item) => <p key={item.position} className="text-xs text-slate-400">{item.position} · {item.symbol} · restante {item.cantidad_abierta}</p>)}</section>
              <section><h3 className="font-semibold text-amber-200">Conflictos ({preview.conflicts.length + preview.errors.length})</h3>{[...preview.conflicts, ...preview.errors].map((item, index) => <p key={index} className="text-xs text-amber-200">{item.reason || item.error}</p>)}</section>
            </div>
            {(preview.conflicts.length > 0 || preview.errors.length > 0) && (
              <section className="rounded-xl border border-amber-400/20 bg-amber-500/5 p-3">
                <h3 className="font-semibold text-amber-100">Agrupación manual avanzada</h3>
                <p className="mb-2 text-xs text-slate-400">Usa los <code>source_key</code> de las filas normalizadas. Cada grupo acepta: position, tipo_operacion (LONG/SHORT), entries[] y exits[]. Después vuelve a previsualizar.</p>
                <textarea value={resolutionJson} onChange={(event) => setResolutionJson(event.target.value)} rows="5" className="w-full rounded-xl border border-white/10 bg-slate-950 p-2 font-mono text-xs text-white" aria-label="Resolución manual JSON" />
                <details className="mt-2"><summary className="cursor-pointer text-xs text-blue-300">Ver filas normalizadas</summary><pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-[10px] text-slate-400">{JSON.stringify(preview.normalized_rows, null, 2)}</pre></details>
              </section>
            )}
            {preview.already_imported && <p className="rounded-xl bg-emerald-500/10 p-3 text-sm text-emerald-200">Este mismo archivo ya fue importado. No se duplicará nada.</p>}
            <div className="flex justify-end gap-2"><button type="button" onClick={onClose} className="rounded-full border border-white/10 px-4 py-2 text-sm">Cancelar</button><button type="button" disabled={!preview.ready_to_commit || busy} onClick={() => request('commit')} className="rounded-full bg-emerald-600 px-5 py-2 text-sm font-bold hover:bg-emerald-500 disabled:opacity-40">{busy ? 'Importando…' : 'Confirmar importación'}</button></div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MetaTraderImportWizard;

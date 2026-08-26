const emptyExit = () => ({
  fecha_hora: '',
  cantidad: '',
  precio: '',
  resultado_bruto: '',
  comision: '0',
  swap: '0',
  tasa: '0',
});

const number = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const PartialExitsEditor = ({ value = [], onChange, entryQuantity, entryPrice, side, disabled = false }) => {
  const exits = Array.isArray(value) ? value : [];
  const exited = exits.reduce((total, item) => total + number(item.cantidad), 0);
  const remaining = number(entryQuantity) - exited;
  const net = exits.reduce((total, item) => (
    total + number(item.resultado_bruto) - number(item.comision) + number(item.swap) - number(item.tasa)
  ), 0);

  const update = (index, field, fieldValue) => {
    onChange(exits.map((item, itemIndex) => (
      itemIndex === index ? (() => {
        const updated = { ...item, [field]: fieldValue };
        if (field === 'resultado_bruto') {
          updated._resultado_auto = false;
        } else if (['cantidad', 'precio'].includes(field) && item._resultado_auto !== false) {
          const quantity = number(updated.cantidad);
          const entry = number(entryPrice);
          const exit = number(updated.precio);
          if (quantity > 0 && entry > 0 && exit > 0) {
            updated.resultado_bruto = String((side === 'SHORT' ? entry - exit : exit - entry) * quantity);
            updated._resultado_auto = true;
          }
        }
        return updated;
      })() : item
    )));
  };

  return (
    <section className="space-y-3 rounded-2xl border border-blue-400/20 bg-blue-500/5 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-white">Salidas parciales</h3>
          <p className="text-[11px] text-slate-400">Añade cada cierre por separado. Los costes se expresan como importes positivos; swap conserva su signo.</p>
        </div>
        <button
          type="button"
          onClick={() => onChange([...exits, emptyExit()])}
          disabled={disabled || remaining <= 0}
          className="rounded-full border border-blue-400/40 px-3 py-1.5 text-xs font-semibold text-blue-200 hover:bg-blue-500/15 disabled:opacity-40"
        >
          + Añadir salida
        </button>
      </div>

      {exits.map((item, index) => (
        <div key={item.id || index} className="rounded-xl border border-white/10 bg-slate-950/35 p-2">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-200">Salida {index + 1}</span>
            <button type="button" disabled={disabled} onClick={() => onChange(exits.filter((_, itemIndex) => itemIndex !== index))} className="text-xs text-red-300 hover:text-red-200">Eliminar</button>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              ["fecha_hora", "Fecha y hora", "datetime-local"],
              ["cantidad", "Cantidad", "number"],
              ["precio", "Precio", "number"],
              ["resultado_bruto", "Resultado bruto", "number"],
              ["comision", "Comisión", "number"],
              ["swap", "Swap", "number"],
              ["tasa", "Tasa", "number"],
            ].map(([field, label, type]) => (
              <label key={field} className="text-[10px] text-slate-400">
                {label}
                <input
                  type={type}
                  step={type === 'number' ? 'any' : undefined}
                  value={item[field] ?? ''}
                  onChange={(event) => update(index, field, event.target.value)}
                  disabled={disabled}
                  required={['fecha_hora', 'cantidad'].includes(field)}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/10 p-1.5 text-xs text-white focus:border-blue-500 focus:outline-none"
                />
              </label>
            ))}
          </div>
        </div>
      ))}

      {exits.length === 0 && <p className="rounded-xl border border-dashed border-white/10 p-3 text-center text-xs text-slate-500">La operación permanecerá abierta hasta que añadas una salida.</p>}
      <div className={`flex flex-wrap justify-between gap-2 text-xs ${remaining < 0 ? 'text-red-300' : 'text-slate-300'}`}>
        <span>Cantidad cerrada: {exited}</span>
        <span>Restante: {remaining}</span>
        <span>Neto realizado: {net.toFixed(2)}</span>
      </div>
    </section>
  );
};

export default PartialExitsEditor;

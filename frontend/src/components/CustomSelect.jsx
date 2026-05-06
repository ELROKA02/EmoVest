import { useState, useEffect, useRef } from "react";

export default function CustomSelect({ value, onChange, options }) {
  const [open, setOpen] = useState(false);
  const ref = useRef();

  // Cerrar al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative w-full z-[100]">
      {/* Botón */}
      <div
        onClick={() => setOpen(!open)}
        className="w-full bg-[#1a2235]/80 text-white text-sm px-4 py-2 rounded-xl border border-white/10 cursor-pointer transition-all duration-200 hover:bg-[#1a2235]/90 flex items-center justify-between min-w-[120px]"
      >
        <span className="truncate">{value}</span>
        <span className="ml-2 text-white/70">▼</span>
      </div>

      {/* Opciones */}
      {open && (
        <div className="absolute mt-1 w-full bg-[#1a2235]/95 border border-white/10 rounded-xl overflow-hidden shadow-2xl backdrop-blur-xl z-[9999]">
          {options.map((opt) => (
            <div
              key={opt}
              onClick={() => {
                onChange(opt);
                setOpen(false);
              }}
              className="px-4 py-2 text-sm text-white hover:bg-white/10 cursor-pointer transition-colors whitespace-nowrap"
            >
              {opt}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
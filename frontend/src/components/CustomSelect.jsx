import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

export default function CustomSelect({ value, onChange, options, className = "" }) {
  const [open, setOpen] = useState(false);
  const [dropdownStyle, setDropdownStyle] = useState({});
  const triggerRef = useRef();
  const dropdownRef = useRef();

  const updatePosition = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setDropdownStyle({
        position: "fixed",
        top: rect.bottom + 4,
        left: rect.left,
        minWidth: rect.width,
        zIndex: 10010,
      });
    }
  };

  const handleOpen = () => {
    if (!open) updatePosition();
    setOpen((prev) => !prev);
  };

  // Cerrar al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        triggerRef.current && !triggerRef.current.contains(e.target) &&
        dropdownRef.current && !dropdownRef.current.contains(e.target)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Cerrar y recalcular posición al hacer scroll o resize
  useEffect(() => {
    if (!open) return;
    const handleScroll = () => setOpen(false);
    const handleResize = () => setOpen(false);
    window.addEventListener("scroll", handleScroll, true);
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("scroll", handleScroll, true);
      window.removeEventListener("resize", handleResize);
    };
  }, [open]);

  return (
    <div ref={triggerRef} className={`relative ${className}`}>
      {/* Botón */}
      <div
        onClick={handleOpen}
        className={`w-full bg-[#1a2235]/80 text-white text-sm px-4 py-2 rounded-xl border border-white/10 cursor-pointer transition-all duration-200 hover:bg-[#1a2235]/90 flex items-center justify-between ${className}`}
      >
        <span className="whitespace-nowrap">{value}</span>
        <span className="ml-2 text-white/70">▼</span>
      </div>

      {/* Opciones — renderizadas en document.body para evitar que el header las tape */}
      {open && createPortal(
        <div
          ref={dropdownRef}
          style={dropdownStyle}
          className="w-max bg-[#1a2235]/95 border border-white/10 rounded-xl overflow-hidden shadow-2xl backdrop-blur-xl"
        >
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
        </div>,
        document.body
      )}
    </div>
  );
}
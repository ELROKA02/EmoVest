const SiriOrb = ({ compact = false, className = '', label = 'EVA, analista de inteligencia artificial' }) => (
  <div
    className={`siri-orb ${compact ? 'siri-orb--compact' : ''} ${className}`.trim()}
    role={compact ? undefined : 'img'}
    aria-label={compact ? undefined : label}
    aria-hidden={compact || undefined}
  >
    <span className="siri-orb__glow siri-orb__glow--violet" />
    <span className="siri-orb__glow siri-orb__glow--indigo" />
    <span className="siri-orb__glow siri-orb__glow--cyan" />
    <span className="siri-orb__glow siri-orb__glow--blue" />
    <span className="siri-orb__sheen" />
  </div>
);

export default SiriOrb;

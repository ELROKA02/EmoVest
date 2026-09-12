import { useCallback, useEffect, useRef } from 'react';

const OrbFallback = () => (
  <>
    <span className="siri-orb__glow siri-orb__glow--violet" />
    <span className="siri-orb__glow siri-orb__glow--indigo" />
    <span className="siri-orb__glow siri-orb__glow--cyan" />
    <span className="siri-orb__glow siri-orb__glow--blue" />
    <span className="siri-orb__sheen" />
  </>
);

const SiriOrb = ({
  compact = false,
  className = '',
  label = 'EVA, analista de inteligencia artificial',
  state = 'thinking',
}) => {
  const frameRef = useRef(null);

  const syncState = useCallback(() => {
    const liquidOrb = frameRef.current?.contentWindow?.liquidOrb;
    if (liquidOrb?.getState() !== state) liquidOrb?.setState(state);
  }, [state]);

  useEffect(() => {
    if (!compact) syncState();
  }, [compact, syncState]);

  if (compact) {
    return (
      <div className={`siri-orb siri-orb--compact ${className}`.trim()} aria-hidden="true">
        <OrbFallback />
      </div>
    );
  }

  return (
    <div
      className={`siri-orb siri-orb--liquid ${className}`.trim()}
      role="img"
      aria-label={label}
    >
      <iframe
        ref={frameRef}
        src="/liquid-orb.html?embedded=1"
        title={label}
        className="siri-orb__frame"
        aria-hidden="true"
        tabIndex={-1}
        allow="webgpu"
        onLoad={syncState}
      />
    </div>
  );
};

export default SiriOrb;

import React from 'react';

// Assuming a Checkbox component exists and accepts these props.
// This is a placeholder for the actual Checkbox component.
const Checkbox = ({ id, tooltip }: { id: string, tooltip: string }) => (
  <div>
    <label htmlFor={id}>{id}</label>
    <input type="checkbox" id={id} title={tooltip} />
    <span style={{ marginLeft: '8px' }}>{tooltip}</span>
  </div>
);


const OverrideDrawer = () => {
  return (
    <div>
      <Checkbox
        id="temp-allow-edid"
        tooltip="Bypass display trust for 24h. Required for untrusted monitors. Profile remains constrained."
      />
    </div>
  );
};

export default OverrideDrawer;

import React from 'react';

interface DataRingProps {
  value: number | string;
  label: string;
  color?: string;
  size?: number;
  showValue?: boolean;
  unit?: string;
}

const DataRing: React.FC<DataRingProps> = ({
  value,
  label,
  color = 'rgba(0, 255, 255, 0.3)',
  size = 80,
  unit = ''
}) => {
  console.log('DataRing rendering with:', { value, label, color, size });
  // Simple test: just a colored square with the value and label
  return (
    <div className="relative w-[{size}px] h-[{size}px] bg-gray-800/50 rounded-lg border border-white/20 flex flex-col items-center justify-center">
      <div className="text-2xl font-bold text-white">{value}{unit}</div>
      <div className="text-xs text-gray-400">{label}</div>
    </div>
  );
};

export default DataRing;
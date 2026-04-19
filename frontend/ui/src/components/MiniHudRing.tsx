import { motion } from 'framer-motion';
import React from 'react';

const MiniHudRing: React.FC = () => {
  const R = 35;
  const CX = 50;
  const CY = 50;

  const ticks = Array.from({ length: 24 }, (_, i) => {
    const angle = (i * 360) / 24 - 90;
    const isMajor = i % 6 === 0;
    const len = isMajor ? 8 : 4;
    const x1 = CX + R * Math.cos((angle * Math.PI) / 180);
    const y1 = CY + R * Math.sin((angle * Math.PI) / 180);
    const x2 = CX + (R + len) * Math.cos((angle * Math.PI) / 180);
    const y2 = CY + (R + len) * Math.sin((angle * Math.PI) / 180);
    return { x1, y1, x2, y2, isMajor };
  });

  return (
    <div className="absolute top-4 right-4 w-[8vmin] h-[8vmin] max-w-[80px] max-h-[80px]">
      <motion.div
        className="absolute inset-0"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 30, ease: 'linear' }}
      >
        <svg width="100%" height="100%" viewBox="0 0 100 100">
          <circle cx={CX} cy={CY} r={R} fill="none" stroke="rgba(0,255,255,0.15)" strokeWidth="1.5" />
          {ticks.map((t, i) => (
            <line
              key={i}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke={t.isMajor ? "rgba(0,255,255,0.5)" : "rgba(0,255,255,0.2)"}
              strokeWidth={t.isMajor ? 1 : 0.5}
              strokeLinecap="round"
            />
          ))}
        </svg>
      </motion.div>

      <motion.div
        className="absolute inset-0"
        animate={{ rotate: -360 }}
        transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}
      >
        <svg width="100%" height="100%" viewBox="0 0 100 100">
          <path
            d={`M ${CX} ${CY} L ${CX + R} ${CY} A ${R} ${R} 0 0 1 ${CX + R * Math.cos(Math.PI/6)} ${CY + R * Math.sin(Math.PI/6)} Z`}
            fill="rgba(0,255,255,0.1)"
          />
        </svg>
      </motion.div>

      <div className="absolute inset-0 flex items-center justify-center">
        <motion.div
          className="w-[5%] h-[5%] rounded-full"
          animate={{
            boxShadow: [
              '0 0 3px rgba(0,255,255,0.6)',
              '0 0 6px rgba(0,255,255,1)',
              '0 0 3px rgba(0,255,255,0.6)',
            ],
          }}
          transition={{ repeat: Infinity, duration: 2 }}
          style={{
            background: 'radial-gradient(circle, rgba(0,255,255,0.9) 0%, rgba(0,255,255,0.3) 100%)',
          }}
        />
      </div>
    </div>
  );
};

export default MiniHudRing;
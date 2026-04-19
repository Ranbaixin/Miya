import { motion } from 'framer-motion';
import React from 'react';

const HudRing: React.FC = () => {
  const R = 40;
  const CX = 50;
  const CY = 50;

  const ticks = Array.from({ length: 72 }, (_, i) => {
    const angle = (i * 360) / 72 - 90;
    const isMajor = i % 6 === 0;
    const len = isMajor ? 4 : 2.5;
    const x1 = CX + R * Math.cos((angle * Math.PI) / 180);
    const y1 = CY + R * Math.sin((angle * Math.PI) / 180);
    const x2 = CX + (R + len) * Math.cos((angle * Math.PI) / 180);
    const y2 = CY + (R + len) * Math.sin((angle * Math.PI) / 180);
    return { x1, y1, x2, y2, isMajor };
  });

  const labels = [
    { text: 'N', angle: -90 },
    { text: 'E', angle: 0 },
    { text: 'S', angle: 90 },
    { text: 'W', angle: 180 },
  ].map(({ text, angle }) => ({
    x: CX + (R + 7) * Math.cos((angle * Math.PI) / 180),
    y: CY + (R + 7) * Math.sin((angle * Math.PI) / 180),
    text,
  }));

  const emotionColors: Record<string, string> = {
    '心动': 'rgba(255, 100, 150, 0.4)',
    '甜蜜': 'rgba(255, 182, 193, 0.4)',
    '依恋': 'rgba(147, 112, 219, 0.4)',
    '温暖': 'rgba(255, 200, 100, 0.4)',
    '平静': 'rgba(0, 255, 255, 0.3)',
    '焦虑': 'rgba(255, 165, 0, 0.4)',
    '悲伤': 'rgba(100, 149, 237, 0.4)',
    '愉悦': 'rgba(255, 255, 100, 0.4)',
  };

  const currentColor = emotionColors['心动'] || 'rgba(0, 255, 255, 0.3)';

  return (
    <div className="relative w-full h-full">
      <motion.div
        className="absolute inset-0"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 60, ease: 'linear' }}
      >
        <svg width="100%" height="100%" viewBox="0 0 100 100" className="absolute inset-0">
          <defs>
            <linearGradient id="outerRingGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgba(0,255,255,0.1)" />
              <stop offset="50%" stopColor="rgba(168,85,247,0.1)" />
              <stop offset="100%" stopColor="rgba(0,255,255,0.1)" />
            </linearGradient>
          </defs>
          <circle cx={CX} cy={CY} r={R + 8} fill="none" stroke="url(#outerRingGrad)" strokeWidth="0.8" strokeDasharray="2,4" />
        </svg>
      </motion.div>

      <motion.div
        className="absolute inset-0"
        animate={{ rotate: -360 }}
        transition={{ repeat: Infinity, duration: 30, ease: 'linear' }}
      >
        <svg width="100%" height="100%" viewBox="0 0 100 100" className="absolute inset-0">
          <circle cx={CX} cy={CY} r={R} fill="none" stroke="rgba(0,255,255,0.25)" strokeWidth="1" />
          {ticks.map((t, i) => (
            <line
              key={i}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke={t.isMajor ? "rgba(0,255,255,0.7)" : "rgba(0,255,255,0.3)"}
              strokeWidth={t.isMajor ? 1 : 0.5}
              strokeLinecap="round"
            />
          ))}
          {labels.map((l, i) => (
            <text
              key={i}
              x={l.x}
              y={l.y}
              fill="rgba(0,255,255,0.6)"
              fontSize="3"
              fontWeight="bold"
              textAnchor="middle"
              dominantBaseline="middle"
              className="font-mono"
            >
              {l.text}
            </text>
          ))}
        </svg>
      </motion.div>

      <motion.div
        className="absolute inset-0"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}
      >
        <svg width="100%" height="100%" viewBox="0 0 100 100" className="absolute inset-0">
          <defs>
            <linearGradient id="scanGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={currentColor} />
              <stop offset="100%" stopColor="rgba(0,255,255,0)" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          <path
            d={`M ${CX} ${CY} L ${CX + R} ${CY} A ${R} ${R} 0 0 1 ${CX + R * Math.cos(Math.PI/8)} ${CY + R * Math.sin(Math.PI/8)} Z`}
            fill="url(#scanGradient)"
            stroke={currentColor.replace('0.4', '0.6')}
            strokeWidth="0.5"
            filter="url(#glow)"
          />
        </svg>
      </motion.div>

      <motion.div
        className="absolute inset-0"
        animate={{ rotate: -360 }}
        transition={{ repeat: Infinity, duration: 8, ease: 'linear' }}
      >
        <svg width="100%" height="100%" viewBox="0 0 100 100" className="absolute inset-0">
          <circle cx={CX} cy={CY} r={R - 9} fill="none" stroke="rgba(168,85,247,0.2)" strokeWidth="0.5" strokeDasharray="1,3" />
        </svg>
      </motion.div>

      <motion.div
        className="absolute inset-0"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 12, ease: 'linear' }}
      >
        <svg width="100%" height="100%" viewBox="0 0 100 100" className="absolute inset-0">
          <circle cx={CX} cy={CY} r={R - 18} fill="none" stroke="rgba(0,255,255,0.1)" strokeWidth="0.3" />
        </svg>
      </motion.div>

      <motion.div
        className="absolute inset-0"
        animate={{ rotate: -360 }}
        transition={{ repeat: Infinity, duration: 20, ease: 'linear' }}
      >
        <svg width="100%" height="100%" viewBox="0 0 100 100" className="absolute inset-0">
          <circle cx={CX} cy={CY} r={R - 25} fill="none" stroke={currentColor} strokeWidth="0.3" strokeDasharray="4,8" opacity="0.5" />
        </svg>
      </motion.div>

      <div className="absolute inset-0 flex items-center justify-center">
        <motion.div
          className="w-[2.5%] h-[2.5%] rounded-full"
          animate={{
            boxShadow: [
              '0 0 4px rgba(0,255,255,0.8), 0 0 8px rgba(0,255,255,0.4)',
              '0 0 8px rgba(255,100,150,1), 0 0 16px rgba(255,100,150,0.6)',
              '0 0 4px rgba(0,255,255,0.8), 0 0 8px rgba(0,255,255,0.4)',
            ],
          }}
          transition={{ repeat: Infinity, duration: 3 }}
          style={{
            background: 'radial-gradient(circle, rgba(255,255,255,0.95) 0%, rgba(0,255,255,0.6) 50%, rgba(0,255,255,0.2) 100%)',
          }}
        />
        <motion.div
          className="absolute rounded-full"
          animate={{ scale: [1, 1.6, 1], opacity: [0.6, 0, 0.6] }}
          transition={{ repeat: Infinity, duration: 2 }}
          style={{
            width: '6%', height: '6%',
            background: `radial-gradient(circle, transparent 40%, ${currentColor} 100%)`,
          }}
        />
        <motion.div
          className="absolute rounded-full"
          animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0, 0.3] }}
          transition={{ repeat: Infinity, duration: 2 }}
          style={{
            width: '10%', height: '10%',
            background: `radial-gradient(circle, transparent 50%, ${currentColor.replace('0.4', '0.15')} 100%)`,
          }}
        />
      </div>

      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `radial-gradient(circle at 50% 50%, ${currentColor}, transparent 60%)`,
          mixBlendMode: 'overlay',
          opacity: 0.15,
        }}
        animate={{
          opacity: [0.1, 0.25, 0.1],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </div>
  );
};

export default HudRing;
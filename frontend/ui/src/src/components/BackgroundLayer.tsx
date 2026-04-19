import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface BackgroundLayerProps {
  imageUrl: string;
  blur: number;
  dim: number;
}

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  duration: number;
  delay: number;
  opacity: number;
}

const BackgroundLayer: React.FC<BackgroundLayerProps> = ({ imageUrl, blur, dim }) => {
  const [bgUrl, setBgUrl] = useState(imageUrl);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [lightOrbs, setLightOrbs] = useState<Particle[]>([]);

  useEffect(() => {
    const timer = setTimeout(() => setBgUrl(imageUrl), 200);
    return () => clearTimeout(timer);
  }, [imageUrl]);

  useEffect(() => {
    const newParticles: Particle[] = [];
    for (let i = 0; i < 25; i++) {
      newParticles.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 3 + 1,
        duration: Math.random() * 10 + 8,
        delay: Math.random() * 5,
        opacity: Math.random() * 0.5 + 0.2,
      });
    }
    setParticles(newParticles);

    const newOrbs: Particle[] = [];
    for (let i = 0; i < 6; i++) {
      newOrbs.push({
        id: i + 100,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 80 + 40,
        duration: Math.random() * 15 + 12,
        delay: Math.random() * 8,
        opacity: Math.random() * 0.15 + 0.05,
      });
    }
    setLightOrbs(newOrbs);
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden">
      <div
        className="absolute inset-0 bg-cover bg-center transition-all duration-500"
        style={{
          backgroundImage: `url(${bgUrl})`,
          filter: `blur(${blur}px) brightness(${1 - dim})`,
        }}
      />

      <div 
        className="absolute inset-0 opacity-30"
        style={{
          background: `linear-gradient(rgba(0,255,255,0.1) 2px, transparent 2px),
                      linear-gradient(90deg, rgba(0,255,255,0.1) 2px, transparent 2px)`,
          backgroundSize: '100% 20px, 20px 100%',
          animation: 'scan 4s linear infinite',
        }}
      />
      
      <div 
        className="absolute inset-0 opacity-10"
        style={{
          background: `
            linear-gradient(rgba(0,255,255,0.2) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,255,255,0.2) 1px, transparent 1px)
          `,
          backgroundSize: '20px 20px',
        }}
      />

      <div 
        className="absolute inset-0 transition-colors duration-500"
        style={{ backgroundColor: `rgba(0, 0, 0, ${dim})` }}
      />

      <AnimatePresence>
        {lightOrbs.map((orb) => (
          <motion.div
            key={orb.id}
            className="absolute rounded-full"
            style={{
              left: `${orb.x}%`,
              top: `${orb.y}%`,
              width: orb.size,
              height: orb.size,
              background: 'radial-gradient(circle, rgba(0,255,255,0.15) 0%, transparent 70%)',
              filter: 'blur(20px)',
            }}
            animate={{
              x: [0, 30, -20, 10, 0],
              y: [0, -40, 20, -10, 0],
              scale: [1, 1.2, 0.9, 1.1, 1],
              opacity: [orb.opacity, orb.opacity * 1.5, orb.opacity * 0.8, orb.opacity * 1.2, orb.opacity],
            }}
            transition={{
              duration: orb.duration,
              delay: orb.delay,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        ))}
      </AnimatePresence>

      <AnimatePresence>
        {particles.map((p) => (
          <motion.div
            key={p.id}
            className="absolute rounded-full"
            style={{
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: p.size,
              height: p.size,
              background: `rgba(0, 255, 255, ${p.opacity})`,
              boxShadow: `0 0 ${p.size * 2}px rgba(0, 255, 255, ${p.opacity})`,
            }}
            animate={{
              y: [0, -100, -200],
              x: [0, 20, -10, 20, 0],
              opacity: [p.opacity, p.opacity * 0.8, 0],
              scale: [1, 1.5, 0.5],
            }}
            transition={{
              duration: p.duration,
              delay: p.delay,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        ))}
      </AnimatePresence>

      <motion.div
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(180deg, transparent 0%, rgba(0,255,255,0.02) 50%, transparent 100%)',
        }}
        animate={{
          y: [0, 100],
          opacity: [0.3, 0.6, 0.3],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: 'linear',
        }}
      />
    </div>
  );
};

export default BackgroundLayer;

const style = document.createElement('style');
style.textContent = `
  @keyframes scan {
    0% { background-position: 0 0; }
    100% { background-position: 0 20px; }
  }
`;
document.head.appendChild(style);
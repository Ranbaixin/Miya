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

interface Aurora {
  id: number;
  x: number;
  width: number;
  opacity: number;
  hue: number;
}

const BackgroundLayer: React.FC<BackgroundLayerProps> = ({ imageUrl, blur, dim }) => {
  const [bgUrl, setBgUrl] = useState(imageUrl);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [lightOrbs, setLightOrbs] = useState<Particle[]>([]);
  const [auroras, setAuroras] = useState<Aurora[]>([]);
  const [stars, setStars] = useState<Particle[]>([]);

  useEffect(() => {
    const timer = setTimeout(() => setBgUrl(imageUrl), 200);
    return () => clearTimeout(timer);
  }, [imageUrl]);

  useEffect(() => {
    const newParticles: Particle[] = [];
    for (let i = 0; i < 30; i++) {
      newParticles.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 2 + 1,
        duration: Math.random() * 12 + 10,
        delay: Math.random() * 8,
        opacity: Math.random() * 0.4 + 0.2,
      });
    }
    setParticles(newParticles);

    const newOrbs: Particle[] = [];
    for (let i = 0; i < 8; i++) {
      newOrbs.push({
        id: i + 100,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 100 + 50,
        duration: Math.random() * 18 + 14,
        delay: Math.random() * 10,
        opacity: Math.random() * 0.12 + 0.04,
      });
    }
    setLightOrbs(newOrbs);

    const newAuroras: Aurora[] = [];
    for (let i = 0; i < 4; i++) {
      newAuroras.push({
        id: i + 200,
        x: Math.random() * 100,
        width: Math.random() * 60 + 40,
        opacity: Math.random() * 0.08 + 0.02,
        hue: i % 3 === 0 ? 180 : i % 3 === 1 ? 270 : 220,
      });
    }
    setAuroras(newAuroras);

    const newStars: Particle[] = [];
    for (let i = 0; i < 60; i++) {
      newStars.push({
        id: i + 300,
        x: Math.random() * 100,
        y: Math.random() * 80,
        size: Math.random() * 1.5 + 0.5,
        duration: Math.random() * 3 + 2,
        delay: Math.random() * 5,
        opacity: Math.random() * 0.8 + 0.2,
      });
    }
    setStars(newStars);
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
        className="absolute inset-0 opacity-20"
        style={{
          background: `linear-gradient(rgba(0,255,255,0.08) 2px, transparent 2px),
                      linear-gradient(90deg, rgba(0,255,255,0.08) 2px, transparent 2px)`,
          backgroundSize: '100% 20px, 20px 100%',
          animation: 'scan 5s linear infinite',
        }}
      />
      
      <div 
        className="absolute inset-0 opacity-06"
        style={{
          background: `
            linear-gradient(rgba(0,255,255,0.12) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,255,255,0.12) 1px, transparent 1px)
          `,
          backgroundSize: '30px 30px',
        }}
      />

      <AnimatePresence>
        {auroras.map((aurora) => (
          <motion.div
            key={aurora.id}
            className="absolute h-[40%] w-[40%]"
            style={{
              left: `${aurora.x}%`,
              top: '10%',
              background: `radial-gradient(ellipse ${aurora.width}% 50% at 50% 100%, 
                hsla(${aurora.hue}, 100%, 70%, ${aurora.opacity}) 0%, 
                hsla(${aurora.hue + 30}, 80%, 50%, ${aurora.opacity * 0.5}) 40%,
                transparent 70%)`,
              filter: 'blur(30px)',
            }}
            animate={{
              x: [0, 30, -20, 10, 0],
              scaleX: [1, 1.2, 0.9, 1.1, 1],
              opacity: [aurora.opacity, aurora.opacity * 1.5, aurora.opacity * 0.6, aurora.opacity * 1.2, aurora.opacity],
            }}
            transition={{
              duration: aurora.id % 3 === 0 ? 20 : aurora.id % 3 === 1 ? 25 : 18,
              delay: aurora.id * 2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        ))}
      </AnimatePresence>

      <AnimatePresence>
        {stars.map((star) => (
          <motion.div
            key={star.id}
            className="absolute rounded-full"
            style={{
              left: `${star.x}%`,
              top: `${star.y}%`,
              width: star.size,
              height: star.size,
              background: `rgba(255, 255, 255, ${star.opacity})`,
              boxShadow: `0 0 ${star.size * 2}px rgba(255, 255, 255, ${star.opacity * 0.8})`,
            }}
            animate={{
              opacity: [star.opacity * 0.3, star.opacity, star.opacity * 0.3],
              scale: [0.8, 1.2, 0.8],
            }}
            transition={{
              duration: star.duration,
              delay: star.delay,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        ))}
      </AnimatePresence>

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
              background: `radial-gradient(circle, 
                rgba(0, 212, 255, ${orb.opacity * 1.5}) 0%, 
                rgba(168, 85, 247, ${orb.opacity}) 30%,
                rgba(244, 114, 182, ${orb.opacity * 0.5}) 60%,
                transparent 70%)`,
              filter: 'blur(25px)',
            }}
            animate={{
              x: [0, 40, -25, 15, 0],
              y: [0, -50, 30, -15, 0],
              scale: [1, 1.3, 0.85, 1.15, 1],
              opacity: [orb.opacity * 0.8, orb.opacity * 1.4, orb.opacity * 0.6, orb.opacity * 1.1, orb.opacity * 0.8],
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
        {particles.map((p) => {
          const hue = p.id % 3 === 0 ? '0, 212, 255' : p.id % 3 === 1 ? '168, 85, 247' : '244, 114, 182';
          return (
            <motion.div
              key={p.id}
              className="absolute rounded-full"
              style={{
                left: `${p.x}%`,
                top: `${p.y}%`,
                width: p.size,
                height: p.size,
                background: `rgba(${hue}, ${p.opacity})`,
                boxShadow: `0 0 ${p.size * 2}px rgba(${hue}, ${p.opacity})`,
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
          );
        })}
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
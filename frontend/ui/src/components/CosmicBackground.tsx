// ============================================================
// 深蓝星渊 · CosmicBackground — 星海能量粒子
// ============================================================
import { useRef, useEffect, useCallback } from 'react';

interface Particle {
  x: number; y: number;
  r: number;
  opacity: number;
  phase: number;
  speed: number;
  driftX: number;
  driftY: number;
  color: string;
}

interface EnergyMote {
  x: number; y: number;
  vx: number; vy: number;
  life: number; maxLife: number;
  opacity: number;
  size: number;
  color: string;
}

const STAR_COLORS = [
  'rgba(255, 255, 255, 0.7)',
  'rgba(200, 220, 255, 0.5)',
  'rgba(0, 229, 255, 0.4)',
  'rgba(140, 200, 255, 0.45)',
  'rgba(180, 200, 255, 0.35)',
];

const ENERGY_COLORS = [
  'rgba(0, 229, 255, 0.5)',
  'rgba(64, 240, 255, 0.45)',
  'rgba(124, 77, 255, 0.4)',
  'rgba(179, 136, 255, 0.35)',
];

const CosmicBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const motesRef = useRef<EnergyMote[]>([]);
  const animRef = useRef<number>(0);
  const frameRef = useRef(0);

  const init = useCallback((w: number, h: number) => {
    const ps: Particle[] = [];
    for (let i = 0; i < 120; i++) {
      ps.push({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 2.5 + 0.5,
        opacity: Math.random() * 0.5 + 0.2,
        phase: Math.random() * Math.PI * 2,
        speed: Math.random() * 0.01 + 0.003,
        driftX: (Math.random() - 0.5) * 0.3,
        driftY: (Math.random() - 0.5) * 0.3,
        color: STAR_COLORS[Math.floor(Math.random() * STAR_COLORS.length)],
      });
    }
    particlesRef.current = ps;
  }, []);

  const spawnMote = useCallback((w: number, h: number): EnergyMote => ({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.5,
    vy: (Math.random() - 0.5) * 0.5 - 0.2,
    life: 0,
    maxLife: Math.random() * 200 + 100,
    opacity: Math.random() * 0.5 + 0.2,
    size: Math.random() * 3 + 1,
    color: ENERGY_COLORS[Math.floor(Math.random() * ENERGY_COLORS.length)],
  }), []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      init(canvas.width, canvas.height);
    };
    resize();
    window.addEventListener('resize', resize);

    const animate = () => {
      const w = canvas.width, h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const stars = particlesRef.current;
      for (const p of stars) {
        p.phase += p.speed;
        const alpha = p.opacity * (0.5 + 0.5 * Math.sin(p.phase));
        if (alpha < 0.05) continue;
        ctx.beginPath();
        ctx.arc(p.x + p.driftX * Math.sin(p.phase * 0.5), p.y + p.driftY * Math.cos(p.phase * 0.4), p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.color.replace(/[\d.]+\)$/, `${alpha.toFixed(2)})`);
        if (p.r > 1.8) {
          ctx.shadowColor = 'rgba(0, 229, 255, 0.3)';
          ctx.shadowBlur = 4;
        }
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      const motes = motesRef.current;
      for (let i = motes.length - 1; i >= 0; i--) {
        const m = motes[i];
        m.x += m.vx;
        m.y += m.vy;
        m.life++;
        const lifeRatio = m.life < 30 ? m.life / 30 : m.life > m.maxLife - 30 ? (m.maxLife - m.life) / 30 : 1;
        const alpha = m.opacity * lifeRatio;
        if (alpha < 0.02 || m.y > h + 10 || m.y < -10 || m.x > w + 10 || m.x < -10) {
          motes.splice(i, 1);
          continue;
        }
        ctx.beginPath();
        ctx.arc(m.x, m.y, m.size, 0, Math.PI * 2);
        ctx.fillStyle = m.color.replace(/[\d.]+\)$/, `${alpha.toFixed(2)})`);
        ctx.shadowColor = 'rgba(0, 229, 255, 0.4)';
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      frameRef.current++;
      if (frameRef.current % 8 === 0 && motes.length < 30) {
        motes.push(spawnMote(w, h));
      }

      animRef.current = requestAnimationFrame(animate);
    };

    animate();
    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [init, spawnMote]);

  return (
    <>
      <div className="void-bg" />
      <canvas ref={canvasRef} className="cosmic-canvas" />
    </>
  );
};

export default CosmicBackground;

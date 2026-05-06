// ============================================================
// 樱梦背景 · SakuraDreamBackground
// 光点粒子 + 樱花飘落
// ============================================================
import { useRef, useEffect, useCallback } from 'react';

interface Particle {
  x: number; y: number;
  r: number;
  opacity: number;
  phase: number;
  speed: number;
  color: string;
}

interface Petal {
  x: number; y: number;
  vx: number; vy: number;
  rotation: number; rotSpeed: number;
  size: number;
  opacity: number;
  color: string;
  life: number; maxLife: number;
}

const PARTICLE_COLORS = [
  'rgba(240,168,192,0.5)',
  'rgba(196,181,253,0.4)',
  'rgba(147,197,253,0.4)',
  'rgba(253,230,138,0.35)',
  'rgba(167,243,208,0.35)',
];

const PETAL_COLORS = [
  'rgba(252,180,200,0.45)',
  'rgba(248,190,210,0.4)',
  'rgba(245,170,195,0.45)',
  'rgba(255,200,220,0.35)',
  'rgba(196,181,253,0.3)',
];

const SakuraBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const petalsRef = useRef<Petal[]>([]);
  const animRef = useRef<number>(0);

  const init = useCallback((w: number, h: number) => {
    const ps: Particle[] = [];
    for (let i = 0; i < 80; i++) {
      ps.push({
        x: Math.random() * w, y: Math.random() * h,
        r: Math.random() * 3 + 1,
        opacity: Math.random() * 0.4 + 0.15,
        phase: Math.random() * Math.PI * 2,
        speed: Math.random() * 0.008 + 0.003,
        color: PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)],
      });
    }
    particlesRef.current = ps;
  }, []);

  const spawnPetal = useCallback((w: number) => ({
    x: Math.random() * w, y: -10,
    vx: (Math.random() - 0.5) * 0.6,
    vy: Math.random() * 0.5 + 0.3,
    rotation: Math.random() * 360,
    rotSpeed: (Math.random() - 0.5) * 0.8,
    size: Math.random() * 8 + 4,
    opacity: Math.random() * 0.4 + 0.2,
    color: PETAL_COLORS[Math.floor(Math.random() * PETAL_COLORS.length)],
    life: 0, maxLife: Math.random() * 500 + 400,
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

    let frame = 0;
    const animate = () => {
      const w = canvas.width, h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      // 光点粒子
      for (const p of particlesRef.current) {
        p.phase += p.speed;
        const alpha = p.opacity * (0.4 + 0.6 * Math.sin(p.phase));
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.color.replace(/[\d.]+\)$/, `${alpha})`);
        if (p.r > 2) {
          ctx.shadowColor = p.color.replace(/[\d.]+\)$/, '0.3)');
          ctx.shadowBlur = 6;
        }
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // 樱花花瓣
      const petals = petalsRef.current;
      for (let i = petals.length - 1; i >= 0; i--) {
        const pt = petals[i];
        pt.x += pt.vx;
        pt.y += pt.vy;
        pt.rotation += pt.rotSpeed;
        pt.life++;
        const alpha = pt.life < 50 ? pt.opacity * (pt.life / 50) :
                      pt.life > pt.maxLife - 50 ? pt.opacity * ((pt.maxLife - pt.life) / 50) :
                      pt.opacity;

        ctx.save();
        ctx.translate(pt.x, pt.y);
        ctx.rotate((pt.rotation * Math.PI) / 180);

        // 画花瓣形状
        ctx.beginPath();
        ctx.ellipse(0, 0, pt.size * 0.6, pt.size * 0.3, 0, 0, Math.PI * 2);
        ctx.fillStyle = pt.color.replace(/[\d.]+\)$/, `${alpha})`);
        ctx.shadowColor = pt.color.replace(/[\d.]+\)$/, '0.2)');
        ctx.shadowBlur = 4;
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.restore();

        if (pt.life >= pt.maxLife || pt.y > h + 20) {
          petals.splice(i, 1);
        }
      }

      // 新花瓣
      frame++;
      if (frame % 40 === 0 && petals.length < 15) {
        petals.push(spawnPetal(w));
      }

      animRef.current = requestAnimationFrame(animate);
    };

    animate();
    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [init, spawnPetal]);

  return (
    <>
      <div className="dream-bg" />
      <canvas ref={canvasRef} className="particle-canvas" />
    </>
  );
};

export default SakuraBackground;

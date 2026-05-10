// ============================================================
// 深蓝星渊 · ResonatorCard — 共鸣者卡片组件
//   MIYA 的每个子系统都是一位"共鸣者"
// ============================================================
import { motion } from 'framer-motion';
import { cn } from '../utils';

export type AttributeType = 'aether' | 'resonance' | 'starlight' | 'active' | 'idle' | 'error';

export interface ResonatorCardProps {
  name: string;
  title: string;
  attribute: AttributeType;
  attributeLabel: string;
  children?: React.ReactNode;
  className?: string;
  delay?: number;
  onClick?: () => void;
  size?: 'sm' | 'md' | 'lg';
  active?: boolean;
  footer?: React.ReactNode;
}

const attrColors: Record<AttributeType, { bg: string; border: string; text: string; glow: string }> = {
  aether:     { bg: 'bg-aether-glow', border: 'border-aether/20', text: 'text-aether-bright', glow: 'shadow-glow-aether' },
  resonance:  { bg: 'bg-resonance-glow', border: 'border-resonance/20', text: 'text-resonance-bright', glow: 'shadow-glow-resonance' },
  starlight:  { bg: 'bg-starlight/10', border: 'border-starlight/20', text: 'text-starlight', glow: 'shadow-glow-starlight' },
  active:     { bg: 'bg-status-active/5', border: 'border-status-active/20', text: 'text-status-active', glow: '' },
  idle:       { bg: 'bg-status-idle/10', border: 'border-status-idle/15', text: 'text-text-secondary', glow: '' },
  error:      { bg: 'bg-status-error/5', border: 'border-status-error/20', text: 'text-status-error', glow: '' },
};

const ResonatorCard: React.FC<ResonatorCardProps> = ({
  name, title, attribute, attributeLabel, children, className, delay = 0, onClick, size = 'md', active = false, footer,
}) => {
  const ac = attrColors[attribute];
  const padding = size === 'sm' ? 'p-3' : size === 'lg' ? 'p-5' : 'p-4';

  return (
    <motion.div
      className={cn(
        'resonator-card cursor-pointer group',
        active && 'active',
        ac.glow,
        className,
      )}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay * 0.06, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      onClick={onClick}
      whileHover={{ y: -3, transition: { duration: 0.25 } }}
    >
      {/* 角标装饰 */}
      <div className="corner-decor corner-tl" />
      <div className="corner-decor corner-tr" />
      <div className="corner-decor corner-bl" />
      <div className="corner-decor corner-br" />

      <div className={padding}>
        {/* 属性标签 */}
        <div className={cn('attr-badge mb-2.5', `attr-${attribute}`)}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: attribute === 'aether' ? '#40f0ff' : attribute === 'resonance' ? '#b388ff' : attribute === 'starlight' ? '#ffab40' : attribute === 'active' ? '#4cff8d' : attribute === 'error' ? '#ff5252' : '#8892b0' }} />
          {attributeLabel}
        </div>

        {/* 名称 */}
        <div className={cn(
          'font-display font-bold tracking-wide mb-1 group-hover:text-shadow transition-all duration-300',
          size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-xl' : 'text-base',
          active ? 'text-aether' : 'text-text-primary',
        )}>
          {name}
        </div>

        {/* 副标题 */}
        <div className={cn(
          'text-text-secondary mb-3',
          size === 'sm' ? 'text-[10px]' : 'text-xs',
        )}>
          {title}
        </div>

        {/* 内容区 */}
        {children && <div className="mb-3">{children}</div>}

        {/* 共鸣能量条 */}
        <div className="resonance-bar">
          <div className="resonance-bar-fill" style={{ width: active ? '100%' : '40%' }} />
        </div>

        {/* 底部信息 */}
        {footer && (
          <div className="mt-2.5 flex items-center justify-between text-[10px] text-text-dim">
            {footer}
          </div>
        )}

        {/* 扫描线 */}
        <div className="scan-line" style={{ top: '50%', opacity: 0.15, display: active ? 'block' : 'none' }} />
      </div>
    </motion.div>
  );
};

export default ResonatorCard;

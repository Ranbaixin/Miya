import { cn } from '../utils';

interface PanelProps {
  title?: string;
  children?: React.ReactNode;
  className?: string;
}

const Panel: React.FC<PanelProps> = ({ title, children, className }) => {
  return (
    <div className={cn(
      "glass-panel p-3 relative overflow-hidden",
      className
    )}>
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />
      <h3 className="text-cyan-300 text-xs font-bold mb-2 flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
        {title}
      </h3>
      {children}
    </div>
  );
};

export default Panel;
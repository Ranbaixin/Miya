interface Background {
  id: string;
  name: string;
  url: string;
}

interface SettingsPageProps {
  backgrounds?: Background[];
  currentBg?: string;
  onBgChange?: (id: string) => void;
}

const SettingsPage: React.FC<SettingsPageProps> = ({ 
  backgrounds = [], 
  currentBg = 'default',
  onBgChange = () => {} 
}) => (
  <div className="p-4">
    <div className="space-y-4">
      {/* 背景设置 */}
      {backgrounds.length > 0 && (
        <div className="glass-panel p-4">
          <div className="text-white font-medium mb-3">背景图片</div>
          <div className="grid grid-cols-3 gap-2">
            {backgrounds.map(bg => (
              <button
                key={bg.id}
                onClick={() => onBgChange(bg.id)}
                className={`p-2 rounded text-sm ${
                  currentBg === bg.id 
                    ? 'bg-cyan-500/30 border border-cyan-500 text-cyan-400' 
                    : 'bg-cyan-900/20 border border-cyan-500/20 text-gray-400 hover:bg-cyan-900/30'
                }`}
              >
                {bg.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="glass-panel p-4">
        <div className="text-white font-medium mb-3">自动回复</div>
        <label className="flex items-center gap-2">
          <input type="checkbox" defaultChecked className="w-4 h-4 accent-cyan-500" />
          <span className="text-gray-300">启用自动回复</span>
        </label>
      </div>
      <div className="glass-panel p-4">
        <div className="text-white font-medium mb-3">敏感词过滤</div>
        <label className="flex items-center gap-2">
          <input type="checkbox" defaultChecked className="w-4 h-4 accent-cyan-500" />
          <span className="text-gray-300">启用敏感词过滤</span>
        </label>
      </div>
    </div>
  </div>
);
export default SettingsPage;
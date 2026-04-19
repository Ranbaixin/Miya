import { motion } from 'framer-motion';
import useMiyaQQData from '../hooks/useMiyaQQData';

const formNames: Record<string, string> = {
  'default': '默认',
  'bianka': '比安卡',
  'yongning': '永宁',
  'ruanmei': '阮梅',
  'huangquan': '黄泉',
  'liuying': '刘英',
  'feixiao': '绯星',
  'kafka': '卡芙卡',
  'xiazhi': '夏芷',
  'raiden': '雷电',
};

interface PersonalityFormPanelProps {
  onFormChange?: (form: string) => void;
}

const PersonalityFormPanel: React.FC<PersonalityFormPanelProps> = ({ onFormChange }) => {
  const miyaData = useMiyaQQData();
  const currentForm = miyaData.personality.form;
  const forms = Object.keys(formNames);

  return (
    <div className="glass-panel p-3">
      <div className="text-cyan-400 text-xs mb-2">人格形态</div>
      <div className="space-y-1 max-h-32 overflow-y-auto">
        {forms.map((formId) => {
          const isActive = currentForm === formId;
          return (
            <motion.div
              key={formId}
              className={`p-1.5 rounded border cursor-pointer transition-all ${
                isActive 
                  ? 'border-cyan-500 bg-cyan-500/10' 
                  : 'border-cyan-500/20 hover:border-cyan-500/40'
              }`}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onFormChange?.(formId)}
            >
              <div className="flex items-center justify-between">
                <span className={`text-xs ${isActive ? 'text-cyan-400' : 'text-gray-300'}`}>
                  {formNames[formId] || formId}
                </span>
                {isActive && (
                  <span className="text-[10px] text-cyan-500">●</span>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default PersonalityFormPanel;
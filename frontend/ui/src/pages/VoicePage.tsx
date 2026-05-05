import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { miyaAPI } from '../services/miyaApi';

interface VoiceConfig {
  tts_enabled: boolean;
  tts_provider: string;
  tts_voice: string;
  tts_speed: number;
  tts_pitch: number;
  stts_enabled: boolean;
  stts_provider: string;
  stts_language: string;
}

const defaultConfig: VoiceConfig = {
  tts_enabled: true,
  tts_provider: 'edge',
  tts_voice: 'zh-CN-XiaoxiaoNeural',
  tts_speed: 1.0,
  tts_pitch: 0,
  stts_enabled: false,
  stts_provider: 'edge',
  stts_language: 'zh-CN',
};

const voiceProviders = [
  { id: 'edge', name: 'Edge TTS', voices: ['zh-CN-XiaoxiaoNeural', 'zh-CN-YunxiNeural', 'zh-CN-YunyangNeural'] },
  { id: 'openai', name: 'OpenAI TTS', voices: ['tts-1', 'tts-1-hd'] },
  { id: 'coqui', name: 'Coqui TTS', voices: ['custom'] },
  { id: 'elevenlabs', name: 'ElevenLabs', voices: ['custom'] },
];

const languages = [
  { id: 'zh-CN', name: '中文(简体)' },
  { id: 'zh-TW', name: '中文(繁体)' },
  { id: 'en-US', name: 'English' },
  { id: 'ja-JP', name: '日本語' },
];

const VoicePage: React.FC = () => {
  const [config, setConfig] = useState<VoiceConfig>(defaultConfig);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    const loadConfig = async () => {
      const data = await miyaAPI.getVoiceConfig();
      if (data) setConfig({ ...defaultConfig, ...data });
    };
    loadConfig();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);
    const result = await miyaAPI.saveVoiceConfig(config);
    setSaveMessage(result?.success ? '配置已保存' : '保存失败，请检查后端服务');
    setSaving(false);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    const result = await miyaAPI.testVoice();
    if (result?.success) {
      setTestResult(result.audio_url ? '语音测试成功，可播放音频' : '语音测试成功');
    } else {
      setTestResult('语音测试功能需要后端服务运行');
    }
    setTesting(false);
  };

  const currentProvider = voiceProviders.find(p => p.id === config.tts_provider);
  const voices = currentProvider?.voices || [];

  return (
    <div className="p-4 space-y-4">
      <div className="glass-panel p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🎤</span>
            <div>
              <div className="text-white font-medium">语音合成 (TTS)</div>
              <div className="text-gray-400 text-sm">将文本转换为语音</div>
            </div>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1 text-xs rounded bg-cyan-500/20 text-cyan-400 disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
        </div>

        {saveMessage && (
          <div className="mb-3 p-2 rounded text-sm text-center bg-green-500/20 text-green-400">
            {saveMessage}
          </div>
        )}

        <div className="space-y-4">
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={config.tts_enabled}
              onChange={(e) => setConfig({ ...config, tts_enabled: e.target.checked })}
              className="w-5 h-5 accent-cyan-500"
            />
            <span className="text-gray-300">启用语音合成</span>
          </label>

          {config.tts_enabled && (
            <div className="space-y-3 ml-8">
              <div>
                <label className="text-gray-400 text-sm block mb-1">TTS 提供商</label>
                <select
                  value={config.tts_provider}
                  onChange={(e) => setConfig({ ...config, tts_provider: e.target.value, tts_voice: '' })}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white"
                >
                  {voiceProviders.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-gray-400 text-sm block mb-1">语音选择</label>
                <select
                  value={config.tts_voice}
                  onChange={(e) => setConfig({ ...config, tts_voice: e.target.value })}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white"
                >
                  {voices.map(v => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-gray-400 text-sm block mb-1">
                  语速: {config.tts_speed.toFixed(1)}x
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={config.tts_speed}
                  onChange={(e) => setConfig({ ...config, tts_speed: parseFloat(e.target.value) })}
                  className="w-full accent-cyan-500"
                />
              </div>

              <div>
                <label className="text-gray-400 text-sm block mb-1">
                  音调: {config.tts_pitch > 0 ? '+' : ''}{config.tts_pitch}
                </label>
                <input
                  type="range"
                  min="-12"
                  max="12"
                  step="1"
                  value={config.tts_pitch}
                  onChange={(e) => setConfig({ ...config, tts_pitch: parseInt(e.target.value) })}
                  className="w-full accent-cyan-500"
                />
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleTest}
                disabled={testing}
                className="w-full py-2 bg-cyan-500/20 border border-cyan-500/50 rounded-lg text-cyan-400 hover:bg-cyan-500/30"
              >
                {testing ? '测试中...' : '测试语音'}
              </motion.button>

              {testResult && (
                <div className="text-gray-400 text-sm text-center">{testResult}</div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="glass-panel p-4">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🗣️</span>
          <div>
            <div className="text-white font-medium">语音识别 (STTS)</div>
            <div className="text-gray-400 text-sm">将语音转换为文本</div>
          </div>
        </div>

        <div className="space-y-4">
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={config.stts_enabled}
              onChange={(e) => setConfig({ ...config, stts_enabled: e.target.checked })}
              className="w-5 h-5 accent-cyan-500"
            />
            <span className="text-gray-300">启用语音识别</span>
          </label>

          {config.stts_enabled && (
            <div className="space-y-3 ml-8">
              <div>
                <label className="text-gray-400 text-sm block mb-1">STTS 提供商</label>
                <select
                  value={config.stts_provider}
                  onChange={(e) => setConfig({ ...config, stts_provider: e.target.value })}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white"
                >
                  {voiceProviders.slice(0, 2).map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-gray-400 text-sm block mb-1">识别语言</label>
                <select
                  value={config.stts_language}
                  onChange={(e) => setConfig({ ...config, stts_language: e.target.value })}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white"
                >
                  {languages.map(l => (
                    <option key={l.id} value={l.id}>{l.name}</option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="glass-panel p-4">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">⚡</span>
          <div>
            <div className="text-white font-medium">快捷键设置</div>
            <div className="text-gray-400 text-sm">语音控制快捷键</div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between py-2 border-b border-gray-800">
            <span className="text-gray-300">按住说话</span>
            <kbd className="bg-gray-800 px-2 py-1 rounded text-gray-400 text-sm">Ctrl + 空格</kbd>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-800">
            <span className="text-gray-300">停止语音</span>
            <kbd className="bg-gray-800 px-2 py-1 rounded text-gray-400 text-sm">Escape</kbd>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-gray-300">语音合成</span>
            <kbd className="bg-gray-800 px-2 py-1 rounded text-gray-400 text-sm">T</kbd>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VoicePage;
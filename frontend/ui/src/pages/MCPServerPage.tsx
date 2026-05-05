import { motion } from 'framer-motion';
import { useMCPServers } from '../services/miyaApi';
import type { MCPServerInfo } from '../services/miyaApi';

const MCPServerPage: React.FC = () => {
  const { servers, loading, refresh } = useMCPServers();

  const getStatusColor = (status: MCPServerInfo['status']) => {
    switch (status) {
      case 'running': return 'text-green-400';
      case 'stopped': return 'text-gray-400';
      case 'error': return 'text-red-400';
      default: return 'text-yellow-400';
    }
  };

  const getStatusDot = (status: MCPServerInfo['status']) => {
    switch (status) {
      case 'running': return 'bg-green-400';
      case 'stopped': return 'bg-gray-500';
      case 'error': return 'bg-red-400';
      default: return 'bg-yellow-400';
    }
  };

  return (
    <div className="p-4 overflow-auto h-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-cyan-400 text-sm font-medium">MCP 服务</div>
        <motion.button
          className="px-3 py-1 text-xs rounded bg-cyan-500/20 text-cyan-400"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => refresh()}
        >
          刷新
        </motion.button>
      </div>

      <div className="flex items-center gap-3 text-xs">
        <span className="text-gray-400">总计 <span className="text-white">{servers.length}</span></span>
        <span className="text-green-400">运行中 <span className="text-white">{servers.filter(s => s.status === 'running').length}</span></span>
        <span className="text-gray-500">已停止 <span className="text-white">{servers.filter(s => s.status === 'stopped').length}</span></span>
        <span className="text-red-400">错误 <span className="text-white">{servers.filter(s => s.status === 'error').length}</span></span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {servers.map((server) => (
          <motion.div
            key={server.name}
            className="glass- panel p-4"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded bg-gray-700/50 flex items-center justify-center text-lg">
                🤖
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-white font-medium truncate">{server.name}</span>
                  <span className={`w-2 h-2 rounded-full ${getStatusDot(server.status)}`} />
                </div>
                <div className={`text-xs ${getStatusColor(server.status)}`}>
                  {server.status === 'running' ? '运行中' : server.status === 'stopped' ? '已停止' : server.status === 'error' ? '错误' : '未知'}
                </div>
                <div className="text-gray-500 text-xs truncate mt-1">
                  {server.enabled ? '已启用' : '已禁用'}
                </div>
              </div>
            </div>

            {server.command && (
              <div className="mt-3 text-xs text-gray-500 truncate">
                {server.command}
                {server.args && server.args.length > 0 && ` ${server.args.join(' ')}`}
              </div>
            )}

            {server.tools && server.tools.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {server.tools.slice(0, 5).map((tool) => (
                  <span key={tool} className="px-2 py-0.5 text-xs rounded bg-cyan-500/20 text-cyan-400">
                    {tool}
                  </span>
                ))}
                {server.tools.length > 5 && (
                  <span className="px-2 py-0.5 text-xs text-gray-500">
                    +{server.tools.length - 5} more
                  </span>
                )}
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {servers.length === 0 && !loading && (
        <div className="text-center text-gray-500 py-8">
          <div className="text-2xl mb-2">🤖</div>
          <div>暂无 MCP 服务</div>
          <div className="text-sm mt-1">请在 config/mcp.json 中配置 MCP 服务器</div>
        </div>
      )}

      {loading && (
        <div className="fixed bottom-4 right-4 text-cyan-400 text-sm">加载中...</div>
      )}
    </div>
  );
};

export default MCPServerPage;
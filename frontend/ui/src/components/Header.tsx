import { useState } from 'react';

interface HeaderProps {
  title: string;
}

const Header: React.FC<HeaderProps> = ({ title }) => {
  const [search, setSearch] = useState('');

  return (
    <div className="h-12 bg-gray-900/80 backdrop-blur-sm flex items-center justify-between px-4 border-b border-gray-800/50">
      <div className="flex items-center gap-4">
        <h1 className="text-primary font-medium text-sm text-glow">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative">
          <input
            type="text"
            placeholder="搜索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-48 bg-gray-800/60 backdrop-blur-sm text-white text-xs rounded-xl px-3 py-1.5 outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent placeholder-gray-400"
          />
        </div>

        <button className="w-8 h-8 rounded-xl bg-gray-800/60 backdrop-blur-sm hover:bg-gray-700/60 flex items-center justify-center text-gray-300 hover:text-white transition-all duration-200">
          👤
        </button>
      </div>
    </div>
  );
};

export default Header;
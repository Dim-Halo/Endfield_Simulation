import React, { useState, useRef, useEffect } from 'react';
import { useSimulationStore, FALLBACK_SCRIPTS } from '../store/useSimulationStore';
import { User, Search, ChevronDown, Check } from 'lucide-react';
import { clsx } from 'clsx';

interface Props {
  index: number;
}

const CharacterSelector: React.FC<{
  selected: string;
  options: string[];
  onChange: (val: string) => void;
}> = ({ selected, options, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Focus input when opening
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
    if (!isOpen) {
        setSearch(""); // Reset search on close
    }
  }, [isOpen]);

  const filteredOptions = options.filter(opt => 
    opt.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="relative w-full" ref={containerRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded px-3 py-2 text-sm font-medium text-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500/50"
      >
        <span className={clsx(!selected || selected === "无" ? "text-gray-400" : "text-gray-900")}>
           {selected}
        </span>
        <ChevronDown className="w-4 h-4 text-gray-400" />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-xl z-50 overflow-hidden flex flex-col max-h-[300px]">
          <div className="p-2 border-b border-gray-100 bg-gray-50">
             <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                <input
                  ref={inputRef}
                  type="text"
                  className="w-full pl-8 pr-2 py-1.5 text-xs border border-gray-200 rounded focus:outline-none focus:border-blue-500"
                  placeholder="搜索干员..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
             </div>
          </div>
          
          <div className="overflow-y-auto flex-1 p-1">
             {filteredOptions.length === 0 ? (
                <div className="p-3 text-center text-xs text-gray-400">未找到相关干员</div>
             ) : (
                filteredOptions.map(opt => (
                  <button
                    key={opt}
                    onClick={() => {
                      onChange(opt);
                      setIsOpen(false);
                    }}
                    className={clsx(
                      "w-full text-left px-3 py-2 text-sm rounded flex items-center justify-between group transition-colors",
                      opt === selected ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700 hover:bg-gray-50"
                    )}
                  >
                    <span>{opt}</span>
                    {opt === selected && <Check className="w-3.5 h-3.5" />}
                  </button>
                ))
             )}
          </div>
        </div>
      )}
    </div>
  );
};

export const CharacterCard: React.FC<Props> = ({ index }) => {
  const { characters, setCharacter, availableCharacters, defaultScripts, weapons } = useSimulationStore();
  const char = characters[index];

  const handleNameChange = (newName: string) => {
    // Look up default script from store (loaded from backend), fallback to empty
    const defaultScript = defaultScripts[newName] || FALLBACK_SCRIPTS[newName] || "";
    setCharacter(index, { name: newName, script: defaultScript, weapon_id: undefined });
  };

  const handleWeaponChange = (weaponId: string) => {
    setCharacter(index, { weapon_id: weaponId === 'none' ? undefined : weaponId });
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 flex flex-col gap-3 min-h-[160px]">
      <div className="flex items-center gap-3">
        <span className="bg-blue-100 text-blue-700 text-xs font-bold px-2 py-1 rounded">P{index + 1}</span>
        <div className="flex-1">
            <CharacterSelector 
               selected={char.name} 
               options={availableCharacters || ["无"]} 
               onChange={handleNameChange}
            />
        </div>
      </div>

      <div className="flex-1 flex flex-col justify-center">
        {char.name !== "无" ? (
          <div className="flex flex-col gap-4 px-1">
            {/* 武器选择 */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">武器</label>
              <select
                className="w-full p-2 text-xs border border-gray-200 rounded bg-gray-50 hover:bg-gray-100"
                value={char.weapon_id || 'none'}
                onChange={(e) => handleWeaponChange(e.target.value)}
              >
                <option value="none">无武器</option>
                {weapons.map(weapon => (
                  <option key={weapon.id} value={weapon.id}>
                    {weapon.name} (ATK+{weapon.weapon_atk})
                  </option>
                ))}
              </select>
            </div>

            {/* Status / Stacks Config */}
            {char.name === "莱瓦汀" && (
              <div className="flex items-center justify-between bg-orange-50 px-3 py-2 rounded border border-orange-100">
                <span className="text-xs font-medium text-orange-800">熔火层数</span>
                <div className="flex items-center gap-2">
                   <input
                    type="range"
                    min="0" max="4"
                    value={char.molten_stacks || 0}
                    onChange={(e) => setCharacter(index, { molten_stacks: Number(e.target.value) })}
                    className="w-16 h-1.5 bg-orange-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
                  />
                  <span className="text-xs font-bold text-orange-700 w-4 text-center">{char.molten_stacks || 0}</span>
                </div>
              </div>
            )}

            {/* Info Snippet */}
            <div className="text-[10px] text-gray-400 text-center mt-auto">
               可在"排轴编辑"页面调整时间轴
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center text-gray-300 h-full">
            <div className="flex flex-col items-center gap-2">
               <div className="w-12 h-12 rounded-full bg-gray-50 border border-gray-100 flex items-center justify-center">
                  <User className="w-6 h-6 opacity-30" />
               </div>
               <span className="text-xs">未配置干员</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

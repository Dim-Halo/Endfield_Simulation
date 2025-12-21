import React from 'react';
import { CharacterCard } from './CharacterCard';
import { useSimulationStore } from '../store/useSimulationStore';
import { Settings, Shield, Zap, Flame, Leaf, Clock, Snowflake, Swords } from 'lucide-react';

export const ConfigView: React.FC = () => {
  const { characters, duration, enemy, setDuration, setEnemy } = useSimulationStore();
  
  return (
    <div className="p-6 h-full overflow-y-auto flex flex-col gap-6">
       
       {/* Section 1: Global Settings */}
       <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
             <Settings className="w-4 h-4" /> 模拟设置
          </h2>
          
          <div className="grid grid-cols-1 gap-6">
             {/* Duration */}
             <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-gray-400" /> 时长: {duration}s
                </label>
                <input
                  type="range"
                  min="5"
                  max="60"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
             </div>

             {/* Defense */}
             <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-gray-400" /> 防御力
                </label>
                <input
                  type="number"
                  value={enemy.defense}
                  onChange={(e) => setEnemy({ defense: Number(e.target.value) })}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
             </div>

             {/* Damage Taken Multipliers */}
             <div>
                <label className="block text-sm font-medium mb-3 text-gray-700">
                  属性承伤系数
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
               {/* Physical */}
               <div>
                  <label className="block text-xs mb-1 text-gray-500 flex items-center gap-1">
                    <Swords className="w-3 h-3 text-gray-400" /> 物理承伤
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range" min="0" max="2" step="0.1"
                      value={enemy.dmg_taken_mult_physical}
                      onChange={(e) => setEnemy({ dmg_taken_mult_physical: Number(e.target.value) })}
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="text-xs w-10 text-right font-mono">{enemy.dmg_taken_mult_physical.toFixed(1)}</span>
                  </div>
               </div>

               {/* Heat */}
               <div>
                  <label className="block text-xs mb-1 text-gray-500 flex items-center gap-1">
                    <Flame className="w-3 h-3 text-red-400" /> 灼热承伤
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range" min="0" max="2" step="0.1"
                      value={enemy.dmg_taken_mult_heat}
                      onChange={(e) => setEnemy({ dmg_taken_mult_heat: Number(e.target.value) })}
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="text-xs w-10 text-right font-mono">{enemy.dmg_taken_mult_heat.toFixed(1)}</span>
                  </div>
               </div>

               {/* Electric */}
               <div>
                  <label className="block text-xs mb-1 text-gray-500 flex items-center gap-1">
                    <Zap className="w-3 h-3 text-yellow-400" /> 电磁承伤
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range" min="0" max="2" step="0.1"
                      value={enemy.dmg_taken_mult_electric}
                      onChange={(e) => setEnemy({ dmg_taken_mult_electric: Number(e.target.value) })}
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="text-xs w-10 text-right font-mono">{enemy.dmg_taken_mult_electric.toFixed(1)}</span>
                  </div>
               </div>

               {/* Nature */}
               <div>
                  <label className="block text-xs mb-1 text-gray-500 flex items-center gap-1">
                    <Leaf className="w-3 h-3 text-green-400" /> 自然承伤
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range" min="0" max="2" step="0.1"
                      value={enemy.dmg_taken_mult_nature}
                      onChange={(e) => setEnemy({ dmg_taken_mult_nature: Number(e.target.value) })}
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="text-xs w-10 text-right font-mono">{enemy.dmg_taken_mult_nature.toFixed(1)}</span>
                  </div>
               </div>

               {/* Frost */}
               <div>
                  <label className="block text-xs mb-1 text-gray-500 flex items-center gap-1">
                    <Snowflake className="w-3 h-3 text-blue-400" /> 寒冷承伤
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range" min="0" max="2" step="0.1"
                      value={enemy.dmg_taken_mult_frost}
                      onChange={(e) => setEnemy({ dmg_taken_mult_frost: Number(e.target.value) })}
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="text-xs w-10 text-right font-mono">{enemy.dmg_taken_mult_frost.toFixed(1)}</span>
                  </div>
               </div>
             </div>
             </div>
          </div>
       </div>

       {/* Section 2: Team */}
       <div>
          <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4">编队配置</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {characters.map((_, idx) => (
              <CharacterCard key={idx} index={idx} />
            ))}
          </div>
       </div>
    </div>
  );
};

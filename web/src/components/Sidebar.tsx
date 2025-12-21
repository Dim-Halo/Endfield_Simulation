import React from 'react';
import { useSimulationStore } from '../store/useSimulationStore';
import { Settings, Shield, Zap, Flame, Leaf, Snowflake, Swords } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { duration, enemy, setDuration, setEnemy } = useSimulationStore();

  return (
    <div className="w-64 bg-gray-900 text-white p-4 flex flex-col h-full border-r border-gray-700">
      <div className="flex items-center gap-2 mb-6">
        <Settings className="w-6 h-6 text-blue-400" />
        <h1 className="text-xl font-bold">模拟设置</h1>
      </div>

      <div className="space-y-6">
        {/* Duration */}
        <div>
          <label className="block text-sm font-medium mb-2 text-gray-300">时长 (秒)</label>
          <input
            type="range"
            min="5"
            max="60"
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            className="w-full"
          />
          <div className="text-right text-xs text-gray-400">{duration}s</div>
        </div>

        <div className="border-t border-gray-700 pt-4">
          <h2 className="text-sm font-bold mb-4 text-gray-400 uppercase tracking-wider flex items-center gap-2">
            <Shield className="w-4 h-4" /> 靶子属性
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-xs mb-1 text-gray-400">防御力</label>
              <input
                type="number"
                value={enemy.defense}
                onChange={(e) => setEnemy({ defense: Number(e.target.value) })}
                className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs mb-1 text-gray-400 flex items-center gap-1">
                <Swords className="w-3 h-3 text-gray-400" /> 物理承伤
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={enemy.dmg_taken_mult_physical}
                onChange={(e) => setEnemy({ dmg_taken_mult_physical: Number(e.target.value) })}
                className="w-full"
              />
              <div className="text-right text-xs text-gray-500">{enemy.dmg_taken_mult_physical.toFixed(1)}</div>
            </div>

            <div>
              <label className="block text-xs mb-1 text-gray-400 flex items-center gap-1">
                <Flame className="w-3 h-3 text-red-400" /> 灼热承伤
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={enemy.dmg_taken_mult_heat}
                onChange={(e) => setEnemy({ dmg_taken_mult_heat: Number(e.target.value) })}
                className="w-full"
              />
              <div className="text-right text-xs text-gray-500">{enemy.dmg_taken_mult_heat.toFixed(1)}</div>
            </div>

            <div>
              <label className="block text-xs mb-1 text-gray-400 flex items-center gap-1">
                <Zap className="w-3 h-3 text-yellow-400" /> 电磁承伤
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={enemy.dmg_taken_mult_electric}
                onChange={(e) => setEnemy({ dmg_taken_mult_electric: Number(e.target.value) })}
                className="w-full"
              />
              <div className="text-right text-xs text-gray-500">{enemy.dmg_taken_mult_electric.toFixed(1)}</div>
            </div>

            <div>
              <label className="block text-xs mb-1 text-gray-400 flex items-center gap-1">
                <Leaf className="w-3 h-3 text-green-400" /> 自然承伤
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={enemy.dmg_taken_mult_nature}
                onChange={(e) => setEnemy({ dmg_taken_mult_nature: Number(e.target.value) })}
                className="w-full"
              />
              <div className="text-right text-xs text-gray-500">{enemy.dmg_taken_mult_nature.toFixed(1)}</div>
            </div>

            <div>
              <label className="block text-xs mb-1 text-gray-400 flex items-center gap-1">
                <Snowflake className="w-3 h-3 text-blue-400" /> 寒冷承伤
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={enemy.dmg_taken_mult_frost}
                onChange={(e) => setEnemy({ dmg_taken_mult_frost: Number(e.target.value) })}
                className="w-full"
              />
              <div className="text-right text-xs text-gray-500">{enemy.dmg_taken_mult_frost.toFixed(1)}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

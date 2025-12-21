import React, { useState } from 'react';
import { useSimulationStore } from '../store/useSimulationStore';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';
import { Activity, FileText } from 'lucide-react';
import clsx from 'clsx';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export const SimulationResults: React.FC = () => {
  const { result } = useSimulationStore();
  const [activeTab, setActiveTab] = useState<'logs' | 'stats'>('stats');

  if (!result) return null;

  const pieData = result.statistics 
    ? Object.values(result.statistics).map(s => ({
        name: s.name,
        value: s.total_damage
      }))
    : [];

  return (
    <div className="flex-1 p-6 overflow-y-auto bg-gray-50 h-full">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">模拟结果</h2>
        <div className="bg-white px-4 py-2 rounded-lg shadow-sm border border-gray-200">
          <span className="text-gray-500 text-sm mr-2">总伤害</span>
          <span className="text-2xl font-bold text-blue-600">{Math.floor(result.total_dmg).toLocaleString()}</span>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mb-6 flex-1 flex flex-col">
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setActiveTab('stats')}
            className={clsx(
              "px-6 py-3 text-sm font-medium flex items-center gap-2 transition-colors",
              activeTab === 'stats' ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50/50" : "text-gray-600 hover:bg-gray-50"
            )}
          >
            <Activity className="w-4 h-4" /> 数据统计
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={clsx(
              "px-6 py-3 text-sm font-medium flex items-center gap-2 transition-colors",
              activeTab === 'logs' ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50/50" : "text-gray-600 hover:bg-gray-50"
            )}
          >
            <FileText className="w-4 h-4" /> 日志
          </button>
        </div>

        <div className="p-6 flex-1 overflow-hidden flex flex-col">
          {activeTab === 'stats' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 h-full">
              <div className="min-h-[300px] flex flex-col">
                <h3 className="text-sm font-bold text-gray-700 mb-4 text-center">伤害占比</h3>
                <div className="flex-1 min-h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        fill="#8884d8"
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <RechartsTooltip formatter={(value: number) => value.toLocaleString()} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-bold text-gray-700 mb-4">详细数据</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">角色</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">总伤害</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">占比</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {pieData.map((d, idx) => (
                        <tr key={d.name}>
                          <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900 flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></span>
                            {d.name}
                          </td>
                          <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 text-right">{d.value.toLocaleString()}</td>
                          <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 text-right">
                            {result.total_dmg > 0 ? ((d.value / result.total_dmg) * 100).toFixed(1) : 0}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="bg-gray-900 rounded-lg p-4 h-full overflow-y-auto font-mono text-xs text-gray-300 space-y-1">
              {result.logs.map((log, idx) => {
                let colorClass = "text-gray-300";
                if (log.type === "damage") colorClass = "text-yellow-400";
                if (log.type === "reaction") colorClass = "text-purple-400";
                if (log.type === "buff") colorClass = "text-blue-400";
                if (log.type === "status") colorClass = "text-green-400";

                return (
                  <div key={idx} className="hover:bg-gray-800 px-1 rounded">
                    <span className="text-gray-500 mr-2">{log.time}</span>
                    <span className={colorClass}>{log.message}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

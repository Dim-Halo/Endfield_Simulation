import React, { useMemo } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

interface GanttProps {
  history: any[];
  charNames: string[];
  totalDuration: number;
}

interface Interval {
  task: string;
  start: number;
  duration: number; // needed for BarChart range
  end: number;
  resource: string;
  type: string;
}

const ACTION_COLORS: Record<string, string> = {
  "普攻": "#b2bec3", 
  "战技": "#0984e3", 
  "终结技": "#d63031", 
  "连携技": "#fdcb6e", 
  "等待": "transparent", 
  "其他": "#636e72"
};

const getActionType = (res: string | null): string => {
  if (!res) return "其他";
  const r = res.toLowerCase();
  if (r.includes("wait") || r.includes("等待")) return "等待";
  if (r.includes("a") || r.includes("普攻")) return "普攻";
  if (r.includes("skill") || r.includes("战技") || r.includes("弹痕") || r.includes("研究") || r.includes("多利") || r.includes("荆棘")) return "战技";
  if (r.includes("ult") || r.includes("魔剑") || r.includes("超频") || r.includes("派对") || r.includes("怒")) return "终结技";
  if (r.includes("qte") || r.includes("手雷") || r.includes("蘑菇") || r.includes("磁暴")) return "连携技";
  return "其他";
};

export const GanttChart: React.FC<GanttProps> = ({ history, charNames, totalDuration }) => {
  const intervals = useMemo(() => {
    const dataList: Interval[] = [];
    const activeActions: Record<string, { action: string, start: number } | null> = {};
    
    charNames.forEach(name => activeActions[name] = null);

    history.forEach(frame => {
      const timeSec = frame.tick / 10.0;
      
      Object.entries(frame.entities).forEach(([name, data]: [string, any]) => {
        if (!charNames.includes(name)) return;
        
        const currentActName = data.action ? data.action.name : null;
        const lastRecord = activeActions[name];

        if (currentActName) {
          if (!lastRecord || lastRecord.action !== currentActName) {
            if (lastRecord) {
              dataList.push({
                task: name,
                start: lastRecord.start,
                end: timeSec,
                duration: timeSec - lastRecord.start,
                resource: lastRecord.action,
                type: getActionType(lastRecord.action)
              });
            }
            activeActions[name] = { action: currentActName, start: timeSec };
          }
        } else {
          if (lastRecord) {
            dataList.push({
              task: name,
              start: lastRecord.start,
              end: timeSec,
              duration: timeSec - lastRecord.start,
              resource: lastRecord.action,
              type: getActionType(lastRecord.action)
            });
            activeActions[name] = null;
          }
        }
      });
    });

    const finalTime = history[history.length - 1].tick / 10.0;
    Object.entries(activeActions).forEach(([name, record]) => {
      if (record) {
        dataList.push({
          task: name,
          start: record.start,
          end: finalTime,
          duration: finalTime - record.start,
          resource: record.action,
          type: getActionType(record.action)
        });
      }
    });

    return dataList;
  }, [history, charNames]);

  // Using a custom HTML rendering for Gantt because Recharts doesn't natively support "Range Bar" well without hacks.
  // A simple absolute positioning approach is cleaner for this specific visual.
  
  return (
    <div className="w-full bg-white p-4 rounded-lg shadow-sm border border-gray-200 overflow-x-auto">
      <h3 className="text-sm font-bold text-gray-700 mb-4">行动时间轴</h3>
      <div className="relative min-w-[600px]" style={{ height: `${charNames.length * 40 + 30}px` }}>
        {/* Time Grid */}
        <div className="absolute top-0 bottom-6 left-20 right-0 flex border-b border-gray-300">
          {Array.from({ length: Math.ceil(totalDuration) + 1 }).map((_, i) => (
            <div key={i} className="flex-1 border-l border-gray-100 text-xs text-gray-400 relative">
              <span className="absolute -bottom-5 -left-2">{i}s</span>
            </div>
          ))}
        </div>

        {/* Rows */}
        {charNames.map((charName, idx) => (
          <div 
            key={charName} 
            className="absolute left-0 w-full flex items-center"
            style={{ top: `${idx * 40}px`, height: '40px' }}
          >
            {/* Label */}
            <div className="w-20 text-sm font-medium text-gray-600 truncate pr-2 text-right">
              {charName}
            </div>
            
            {/* Track */}
            <div className="flex-1 relative h-full border-t border-gray-50 bg-gray-50/50">
              {intervals.filter(i => i.task === charName).map((interval, iIdx) => {
                const leftPct = (interval.start / totalDuration) * 100;
                const widthPct = (interval.duration / totalDuration) * 100;
                const color = ACTION_COLORS[interval.type] || ACTION_COLORS["其他"];
                
                if (interval.type === "等待") return null;

                return (
                  <div
                    key={iIdx}
                    className="absolute h-6 top-2 rounded text-[10px] text-white flex items-center justify-center overflow-hidden whitespace-nowrap px-1 cursor-help transition-all hover:brightness-110 hover:z-10 hover:shadow-md"
                    style={{ 
                      left: `${leftPct}%`, 
                      width: `${widthPct}%`, 
                      backgroundColor: color,
                      minWidth: '2px'
                    }}
                    title={`${interval.resource} (${interval.start.toFixed(1)}s - ${interval.end.toFixed(1)}s)`}
                  >
                    {widthPct > 2 && interval.resource}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

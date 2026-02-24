import React, { useState, useEffect } from 'react';
import { TimelineAction, ActionType } from '../store/useSimulationStore';
import { X, Trash2 } from 'lucide-react';

interface EditActionModalProps {
  action: TimelineAction;
  onSave: (updates: Partial<TimelineAction>) => void;
  onDelete: () => void;
  onClose: () => void;
}

export const EditActionModal: React.FC<EditActionModalProps> = ({ action, onSave, onDelete, onClose }) => {
  const [name, setName] = useState(action.name);
  const [type, setType] = useState<ActionType>(action.type);
  const [startTime, setStartTime] = useState(action.startTime);
  const [duration, setDuration] = useState(action.duration);

  const handleSave = () => {
    onSave({
      name,
      type,
      startTime: Number(startTime),
      duration: Number(duration)
    });
    onClose();
  };

  const handleStartTimeChange = (value: string) => {
    const numValue = Number(value);
    setStartTime(numValue);
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-80 p-6 border border-gray-200 transform transition-all scale-100">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold text-gray-800">编辑动作</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">动作名称</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">类型</label>
            <select
              value={type}
              onChange={e => setType(e.target.value as ActionType)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white"
            >
              <option value="Skill">Skill (战技)</option>
              <option value="Ult">Ult (终结技)</option>
              <option value="QTE">QTE (连携)</option>
              <option value="Attack">Attack (普攻)</option>
              <option value="Wait">Wait (等待)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
             <div>
                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">
                  开始时间 (s)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={startTime}
                  onChange={e => handleStartTimeChange(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                />
                <p className="text-[10px] text-gray-400 mt-1">
                  可自由设置间隔
                </p>
             </div>
             <div>
                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">持续时间 (s)</label>
                <input
                  type="number"
                  step="0.1"
                  value={duration}
                  onChange={e => setDuration(Number(e.target.value))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                />
             </div>
          </div>
        </div>

        <div className="flex gap-3 mt-8">
           <button
             onClick={onDelete}
             className="flex-1 bg-red-50 text-red-600 hover:bg-red-100 py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
           >
             <Trash2 className="w-4 h-4" /> 删除
           </button>
           <button
             onClick={handleSave}
             className="flex-1 bg-blue-600 text-white hover:bg-blue-700 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm"
           >
             保存修改
           </button>
        </div>
      </div>
    </div>
  );
};

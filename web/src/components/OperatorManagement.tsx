import React, { useState, useEffect } from 'react';
import { useSimulationStore } from '../store/useSimulationStore';
import { characterApi } from '../api/client';
import { Save } from 'lucide-react';

export const OperatorManagement: React.FC = () => {
  const { characters, setCharacter } = useSimulationStore();
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  // 获取当前编队的干员（排除"无"）
  const activeCharacters = characters
    .map((char, index) => ({ ...char, index }))
    .filter(char => char.name !== '无');

  const handleSave = (index: number, updates: any) => {
    setCharacter(index, { custom_attrs: updates });
    setEditingIndex(null);
  };

  if (activeCharacters.length === 0) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <div className="text-center text-gray-400">
          <p className="text-lg mb-2">当前编队为空</p>
          <p className="text-sm">请先在"编队与设置"页面选择干员</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 overflow-y-auto">
      <h2 className="text-2xl font-bold mb-6">干员属性管理</h2>
      <p className="text-sm text-gray-600 mb-6">
        在此页面修改的属性将在模拟时生效。修改会实时保存。
      </p>

      <div className="space-y-6">
        {activeCharacters.map(({ name, index, custom_attrs }) => (
          <CharacterAttributeEditor
            key={index}
            characterName={name}
            characterIndex={index}
            customAttrs={custom_attrs}
            isEditing={editingIndex === index}
            onEdit={() => setEditingIndex(index)}
            onSave={(updates) => handleSave(index, updates)}
            onCancel={() => setEditingIndex(null)}
          />
        ))}
      </div>
    </div>
  );
};

interface CharacterAttributeEditorProps {
  characterName: string;
  characterIndex: number;
  customAttrs?: any;
  isEditing: boolean;
  onEdit: () => void;
  onSave: (updates: any) => void;
  onCancel: () => void;
}

const CharacterAttributeEditor: React.FC<CharacterAttributeEditorProps> = ({
  characterName,
  characterIndex,
  customAttrs,
  isEditing,
  onEdit,
  onSave,
  onCancel,
}) => {
  const [formData, setFormData] = useState({
    level: customAttrs?.level || 90,
    attrs: {
      strength: customAttrs?.attrs?.strength || 0,
      agility: customAttrs?.attrs?.agility || 0,
      intelligence: customAttrs?.attrs?.intelligence || 0,
      willpower: customAttrs?.attrs?.willpower || 0,
    },
    base_stats: {
      base_hp: customAttrs?.base_stats?.base_hp || 0,
      base_atk: customAttrs?.base_stats?.base_atk || 0,
      base_def: customAttrs?.base_stats?.base_def || 0,
      technique_power: customAttrs?.base_stats?.technique_power || 0,
    },
  });

  // 获取角色默认属性
  useEffect(() => {
    const fetchDefaultAttrs = async () => {
      try {
        const defaultAttrs = await characterApi.getDefaultAttrs(characterName);

        // 如果没有自定义属性，使用默认属性
        if (!customAttrs) {
          setFormData({
            level: defaultAttrs.base_stats.level,
            attrs: {
              strength: defaultAttrs.attrs.strength,
              agility: defaultAttrs.attrs.agility,
              intelligence: defaultAttrs.attrs.intelligence,
              willpower: defaultAttrs.attrs.willpower,
            },
            base_stats: {
              base_hp: defaultAttrs.base_stats.base_hp,
              base_atk: defaultAttrs.base_stats.base_atk,
              base_def: defaultAttrs.base_stats.base_def,
              technique_power: defaultAttrs.base_stats.technique_power,
            },
          });
        }
      } catch (error) {
        console.error('Failed to fetch default attributes:', error);
      }
    };

    fetchDefaultAttrs();
  }, [characterName, customAttrs]);

  const handleSave = () => {
    onSave(formData);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold">{characterName}</h3>
          <p className="text-sm text-gray-500">位置 P{characterIndex + 1}</p>
        </div>
        {!isEditing && (
          <button
            onClick={onEdit}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
          >
            编辑属性
          </button>
        )}
      </div>

      {isEditing ? (
        <div className="space-y-4">
          {/* 等级 */}
          <div>
            <label className="block text-sm font-medium mb-1">等级</label>
            <input
              type="number"
              className="w-full p-2 border rounded"
              value={formData.level}
              onChange={(e) => setFormData({ ...formData, level: parseInt(e.target.value) })}
            />
          </div>

          {/* 四维属性 */}
          <div>
            <h4 className="font-medium mb-2">四维属性</h4>
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: 'strength', label: '力量' },
                { key: 'agility', label: '敏捷' },
                { key: 'intelligence', label: '智识' },
                { key: 'willpower', label: '意志' },
              ].map(({ key, label }) => (
                <div key={key}>
                  <label className="block text-xs mb-1">{label}</label>
                  <input
                    type="number"
                    className="w-full p-2 border rounded text-sm"
                    value={formData.attrs[key as keyof typeof formData.attrs]}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        attrs: { ...formData.attrs, [key]: parseInt(e.target.value) },
                      })
                    }
                  />
                </div>
              ))}
            </div>
          </div>

          {/* 基础面板 */}
          <div>
            <h4 className="font-medium mb-2">基础面板</h4>
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: 'base_hp', label: '生命值' },
                { key: 'base_atk', label: '攻击力' },
                { key: 'base_def', label: '防御力' },
                { key: 'technique_power', label: '源石技艺强度' },
              ].map(({ key, label }) => (
                <div key={key}>
                  <label className="block text-xs mb-1">{label}</label>
                  <input
                    type="number"
                    className="w-full p-2 border rounded text-sm"
                    value={formData.base_stats[key as keyof typeof formData.base_stats]}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        base_stats: {
                          ...formData.base_stats,
                          [key]: parseFloat(e.target.value),
                        },
                      })
                    }
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              onClick={handleSave}
              className="flex items-center gap-1 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              <Save size={16} />
              保存
            </button>
            <button
              onClick={onCancel}
              className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400"
            >
              取消
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3 text-sm">
          <div>
            <span className="font-medium">等级:</span> {formData.level}
          </div>
          <div>
            <span className="font-medium">四维属性:</span>
            <div className="ml-4 mt-1 grid grid-cols-2 gap-2">
              <div>力量: {formData.attrs.strength}</div>
              <div>敏捷: {formData.attrs.agility}</div>
              <div>智识: {formData.attrs.intelligence}</div>
              <div>意志: {formData.attrs.willpower}</div>
            </div>
          </div>
          <div>
            <span className="font-medium">基础面板:</span>
            <div className="ml-4 mt-1 grid grid-cols-2 gap-2">
              <div>生命: {formData.base_stats.base_hp}</div>
              <div>攻击: {formData.base_stats.base_atk}</div>
              <div>防御: {formData.base_stats.base_def}</div>
              <div>技艺: {formData.base_stats.technique_power}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { X, Sword, Shield, Activity } from 'lucide-react';
import { useSimulationStore } from '../store/useSimulationStore';
import { characterApi } from '../api/client';

interface CharacterAttrs {
  strength: number;
  agility: number;
  intelligence: number;
  willpower: number;
}

interface CharacterBaseStats {
  level: number;
  base_hp: number;
  base_atk: number;
  base_def: number;
  technique_power: number;
}

interface CharacterData {
  attrs: CharacterAttrs;
  base_stats: CharacterBaseStats;
  main_attr?: string;
  sub_attr?: string;
}

interface FinalPanel {
  hp: number;
  atk: number;
  def: number;
  tech_power: number;
  phys_res: number;
  magic_res: number;
  strength: number;
  agility: number;
  intelligence: number;
  willpower: number;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  characterIndex: number;
}

export const CharacterConfigModal: React.FC<Props> = ({ isOpen, onClose, characterIndex }) => {
  const { characters, setCharacter, weapons, equipments } = useSimulationStore();
  const char = characters[characterIndex];

  const [weaponId, setWeaponId] = useState<string | undefined>(char.weapon_id);
  const [equipmentIds, setEquipmentIds] = useState<Record<string, string>>({
    gloves: char.equipment_ids?.gloves || '',
    armor: char.equipment_ids?.armor || '',
    accessory_1: char.equipment_ids?.accessory_1 || '',
    accessory_2: char.equipment_ids?.accessory_2 || ''
  });

  const [charAttrs, setCharAttrs] = useState<CharacterAttrs | null>(null);
  const [charBaseStats, setCharBaseStats] = useState<CharacterBaseStats | null>(null);
  const [charData, setCharData] = useState<CharacterData | null>(null);
  const [finalPanel, setFinalPanel] = useState<FinalPanel | null>(null);

  // 获取干员基础属性
  useEffect(() => {
    if (isOpen && char.name !== "无") {
      characterApi.getDefaultAttrs(char.name).then(data => {
        setCharAttrs(data.attrs);
        setCharBaseStats(data.base_stats);
        setCharData(data);
      }).catch(err => {
        console.error("Failed to fetch character attrs:", err);
      });
    }
  }, [isOpen, char.name]);

  // 计算最终面板 - 调用后端API确保一致性
  useEffect(() => {
    if (!char.name || char.name === '无') {
      setFinalPanel(null);
      return;
    }

    // 准备装备ID（过滤掉空值）
    const filteredEquipmentIds: Record<string, string> = {};
    Object.entries(equipmentIds).forEach(([slot, id]) => {
      if (id && id !== 'none') {
        filteredEquipmentIds[slot] = id;
      }
    });

    // 调用后端API计算面板
    characterApi.calculatePanel({
      character_name: char.name,
      weapon_id: weaponId || null,
      equipment_ids: Object.keys(filteredEquipmentIds).length > 0 ? filteredEquipmentIds : null,
      custom_attrs: null
    })
      .then(data => {
        const panel = data.panel;
        setFinalPanel({
          hp: Math.round(panel.base_hp || 0),
          atk: Math.round(panel.final_atk || 0),
          def: Math.round(panel.base_def || 0),
          tech_power: Math.round(panel.technique_power || 0),
          phys_res: Math.round((panel.phys_res || 0) * 100),
          magic_res: Math.round((panel.magic_res || 0) * 100),
          strength: Math.round(panel.strength || 0),
          agility: Math.round(panel.agility || 0),
          intelligence: Math.round(panel.intelligence || 0),
          willpower: Math.round(panel.willpower || 0)
        });
      })
      .catch(err => {
        console.error("Failed to calculate panel:", err);
        setFinalPanel(null);
      });
  }, [char.name, weaponId, equipmentIds]);

  useEffect(() => {
    if (isOpen) {
      setWeaponId(char.weapon_id);
      setEquipmentIds({
        gloves: char.equipment_ids?.gloves || '',
        armor: char.equipment_ids?.armor || '',
        accessory_1: char.equipment_ids?.accessory_1 || '',
        accessory_2: char.equipment_ids?.accessory_2 || ''
      });
    }
  }, [isOpen, char]);

  const handleSave = () => {
    const cleanedEquipmentIds: Record<string, string> = {};
    Object.entries(equipmentIds).forEach(([slot, id]) => {
      if (id && id !== 'none') {
        cleanedEquipmentIds[slot] = id;
      }
    });

    setCharacter(characterIndex, {
      weapon_id: weaponId === 'none' ? undefined : weaponId,
      equipment_ids: Object.keys(cleanedEquipmentIds).length > 0 ? cleanedEquipmentIds : undefined
    });
    onClose();
  };

  const getEquipmentsBySlot = (slot: string) => {
    if (!Array.isArray(equipments)) {
      return [];
    }
    // 配件1和配件2共用装备池
    if (slot === 'accessory_1' || slot === 'accessory_2') {
      return equipments.filter(eq => eq.slot === 'accessory_1' || eq.slot === 'accessory_2');
    }
    return equipments.filter(eq => eq.slot === slot);
  };

  const slotNames = {
    gloves: '护手',
    armor: '护甲',
    accessory_1: '配件1',
    accessory_2: '配件2'
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">
            配置干员：{char.name}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* 最终面板显示 */}
          {finalPanel && (
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="w-5 h-5 text-blue-600" />
                <h3 className="text-sm font-bold text-gray-900">最终面板</h3>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white rounded p-3 shadow-sm">
                  <div className="text-xs text-gray-500 mb-1">生命值</div>
                  <div className="text-lg font-bold text-gray-900">{finalPanel.hp}</div>
                </div>
                <div className="bg-white rounded p-3 shadow-sm">
                  <div className="text-xs text-gray-500 mb-1">攻击力</div>
                  <div className="text-lg font-bold text-gray-900">{finalPanel.atk}</div>
                </div>
                <div className="bg-white rounded p-3 shadow-sm">
                  <div className="text-xs text-gray-500 mb-1">防御力</div>
                  <div className="text-lg font-bold text-gray-900">{finalPanel.def}</div>
                </div>
                <div className="bg-white rounded p-3 shadow-sm">
                  <div className="text-xs text-gray-500 mb-1">源石技艺强度</div>
                  <div className="text-lg font-bold text-gray-900">{finalPanel.tech_power}</div>
                </div>
                <div className="bg-white rounded p-3 shadow-sm">
                  <div className="text-xs text-gray-500 mb-1">物理抗性</div>
                  <div className="text-lg font-bold text-gray-900">{finalPanel.phys_res}%</div>
                </div>
                <div className="bg-white rounded p-3 shadow-sm">
                  <div className="text-xs text-gray-500 mb-1">法术抗性</div>
                  <div className="text-lg font-bold text-gray-900">{finalPanel.magic_res}%</div>
                </div>
                <div className="bg-white rounded p-3 shadow-sm">
                  <div className="text-xs text-gray-500 mb-1">力量</div>
                  <div className="text-lg font-bold text-gray-900">{finalPanel.strength}</div>
                </div>
                <div className="bg-white rounded p-3 shadow-sm">
                  <div className="text-xs text-gray-500 mb-1">敏捷</div>
                  <div className="text-lg font-bold text-gray-900">{finalPanel.agility}</div>
                </div>
                <div className="bg-white rounded p-3 shadow-sm">
                  <div className="text-xs text-gray-500 mb-1">智识</div>
                  <div className="text-lg font-bold text-gray-900">{finalPanel.intelligence}</div>
                </div>
                <div className="bg-white rounded p-3 shadow-sm">
                  <div className="text-xs text-gray-500 mb-1">意志</div>
                  <div className="text-lg font-bold text-gray-900">{finalPanel.willpower}</div>
                </div>
              </div>
            </div>
          )}

          {/* 武器选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <Sword className="w-4 h-4" /> 武器
            </label>
            <select
              className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={weaponId || 'none'}
              onChange={(e) => setWeaponId(e.target.value === 'none' ? undefined : e.target.value)}
            >
              <option value="none">无武器</option>
              {weapons.map(weapon => (
                <option key={weapon.id} value={weapon.id}>
                  {weapon.name} (ATK+{weapon.weapon_atk})
                </option>
              ))}
            </select>
          </div>

          {/* 装备选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
              <Shield className="w-4 h-4" /> 装备 {Array.isArray(equipments) && `(共${equipments.length}件)`}
            </label>
            <div className="space-y-4">
              {Object.entries(slotNames).map(([slot, name]) => {
                const slotEquipments = getEquipmentsBySlot(slot);
                return (
                  <div key={slot}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      {name} ({slotEquipments.length}件可选)
                    </label>
                    <select
                      className="w-full p-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                      value={equipmentIds[slot] || 'none'}
                      onChange={(e) => setEquipmentIds({
                        ...equipmentIds,
                        [slot]: e.target.value === 'none' ? '' : e.target.value
                      })}
                    >
                      <option value="none">无装备</option>
                      {slotEquipments.map(equipment => (
                        <option key={equipment.id} value={equipment.id}>
                          {equipment.name}
                          {equipment.set_name && ` [${equipment.set_name}]`}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  );
};

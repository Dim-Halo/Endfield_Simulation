import axios from 'axios';

// Use environment variable for API URL
// In development, use proxy path /api
// In production (ngrok), use relative path to work with same domain
const API_URL = import.meta.env.VITE_API_URL ||
  (import.meta.env.MODE === 'production' ? '' : '/api');

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Operator Config Types
export interface OperatorConfig {
  id: string;
  character_name: string;
  config_name: string;
  level: number;
  attrs: {
    strength: number;
    agility: number;
    intelligence: number;
    willpower: number;
  };
  base_stats: Record<string, number>;
}

export interface OperatorConfigCreate {
  character_name: string;
  config_name: string;
  level: number;
  attrs: {
    strength: number;
    agility: number;
    intelligence: number;
    willpower: number;
  };
  base_stats: Record<string, number>;
}

export interface OperatorConfigUpdate {
  config_name?: string;
  level?: number;
  attrs?: {
    strength: number;
    agility: number;
    intelligence: number;
    willpower: number;
  };
  base_stats?: Record<string, number>;
}

// Operator Config API
export const operatorConfigApi = {
  getAll: async (characterName?: string) => {
    const params = characterName ? { character_name: characterName } : {};
    const response = await apiClient.get<OperatorConfig[]>('/operator-configs', { params });
    return response.data;
  },

  getById: async (id: string) => {
    const response = await apiClient.get<OperatorConfig>(`/operator-configs/${id}`);
    return response.data;
  },

  create: async (data: OperatorConfigCreate) => {
    const response = await apiClient.post<OperatorConfig>('/operator-configs', data);
    return response.data;
  },

  update: async (id: string, data: OperatorConfigUpdate) => {
    const response = await apiClient.put<OperatorConfig>(`/operator-configs/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    const response = await apiClient.delete(`/operator-configs/${id}`);
    return response.data;
  },
};

// Weapon Types
export interface WeaponEffect {
  effect_type: string;
  trigger_condition: Record<string, any>;
  buff_stats: Record<string, number>;
  duration: number;
  description: string;
}

export interface Weapon {
  id: string;
  name: string;
  description: string;
  weapon_atk: number;
  stat_bonuses: Record<string, number>;
  effects: WeaponEffect[];
}

export interface WeaponCreate {
  name: string;
  description: string;
  weapon_atk: number;
  stat_bonuses: Record<string, number>;
  effects?: WeaponEffect[];
}

export interface WeaponUpdate {
  name?: string;
  description?: string;
  weapon_atk?: number;
  stat_bonuses?: Record<string, number>;
  effects?: WeaponEffect[];
}

// Weapon API
export const weaponApi = {
  getAll: async () => {
    const response = await apiClient.get<Weapon[]>('/weapons');
    return response.data;
  },

  getById: async (id: string) => {
    const response = await apiClient.get<Weapon>(`/weapons/${id}`);
    return response.data;
  },

  create: async (data: WeaponCreate) => {
    const response = await apiClient.post<Weapon>('/weapons', data);
    return response.data;
  },

  update: async (id: string, data: WeaponUpdate) => {
    const response = await apiClient.put<Weapon>(`/weapons/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    const response = await apiClient.delete(`/weapons/${id}`);
    return response.data;
  },
};

// Equipment Types
export interface EquipmentEffect {
  effect_type: string;
  trigger_condition: Record<string, any>;
  buff_stats: Record<string, number>;
  duration: number;
  description: string;
}

export interface Equipment {
  id: string;
  name: string;
  description: string;
  slot: string;
  stat_bonuses: Record<string, number>;
  effects: EquipmentEffect[];
  set_id?: string | null;
  set_name?: string | null;
}

// Equipment API
export const equipmentApi = {
  getAll: async () => {
    const response = await apiClient.get<Equipment[]>('/equipments');
    return response.data;
  },

  getById: async (id: string) => {
    const response = await apiClient.get<Equipment>(`/equipments/${id}`);
    return response.data;
  },

  getBySlot: async (slot: string) => {
    const response = await apiClient.get<Equipment[]>(`/equipments/slot/${slot}`);
    return response.data;
  },
};

// Character Default Attributes
export interface CharacterDefaultAttrs {
  character_name: string;
  attrs: {
    strength: number;
    agility: number;
    intelligence: number;
    willpower: number;
  };
  base_stats: {
    level: number;
    base_hp: number;
    base_atk: number;
    base_def: number;
    technique_power: number;
  };
  main_attr?: string;
  sub_attr?: string;
}

// Panel Calculation Types
export interface PanelCalculationRequest {
  character_name: string;
  weapon_id?: string | null;
  equipment_ids?: Record<string, string> | null;
  custom_attrs?: any | null;
}

export interface PanelCalculationResponse {
  character_name: string;
  panel: Record<string, number>;
}

export const characterApi = {
  getDefaultAttrs: async (characterName: string) => {
    const response = await apiClient.get<CharacterDefaultAttrs>(`/characters/${characterName}/default-attrs`);
    return response.data;
  },

  calculatePanel: async (data: PanelCalculationRequest) => {
    const response = await apiClient.post<PanelCalculationResponse>('/calculate-panel', data);
    return response.data;
  },
};

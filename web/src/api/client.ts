import axios from 'axios';

// Use environment variable for API URL
// In production (ngrok), use relative path to work with same domain
// In development, use localhost
const API_URL = import.meta.env.VITE_API_URL ||
  (import.meta.env.MODE === 'production' ? '' : 'http://127.0.0.1:8000');

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
}

export const characterApi = {
  getDefaultAttrs: async (characterName: string) => {
    const response = await apiClient.get<CharacterDefaultAttrs>(`/characters/${characterName}/default-attrs`);
    return response.data;
  },
};

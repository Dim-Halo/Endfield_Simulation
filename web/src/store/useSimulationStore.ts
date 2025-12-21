import { create } from 'zustand';
import { getActionDuration, preloadCharacterConstants } from '../utils/constants';
import { apiClient } from '../api/client';

export type CharacterName = "无" | "莱瓦汀" | "狼卫" | "艾尔黛拉" | "安塔尔" | "管理员" | "陈千语" | "大潘" | "骏卫";
export type ActionType = "Skill" | "Ult" | "QTE" | "Attack" | "Wait";

export interface TimelineAction {
  id: string;
  type: ActionType;
  startTime: number;
  duration: number;
  name: string; // "Skill", "Ult", "QTE", "A1", etc.
}

export interface CharacterConfig {
  name: string; // Relaxed type
  script: string;
  molten_stacks?: number;
  timeline?: TimelineAction[];
}

export interface EnemyConfig {
  defense: number;
  dmg_taken_mult_physical: number;
  dmg_taken_mult_heat: number;
  dmg_taken_mult_electric: number;
  dmg_taken_mult_nature: number;
  dmg_taken_mult_frost: number;
}

export interface SimulationResult {
  history: any[];
  logs: any[];
  total_dmg: number;
  char_names: string[];
  statistics: Record<string, any> | null;
  // Snapshot data for real-time visualization
  snapshots?: {
      time: number;
      sp: number;
      // other real-time data
  }[];
}

interface SimulationState {
  duration: number;
  enemy: EnemyConfig;
  characters: CharacterConfig[];
  availableCharacters: string[]; // List of character names from backend
  defaultScripts: Record<string, string>; // Store scripts from backend
  result: SimulationResult | null;
  isSimulating: boolean;
  
  fetchAvailableCharacters: () => Promise<void>;
  setDuration: (d: number) => void;
  setEnemy: (e: Partial<EnemyConfig>) => void;
  setCharacter: (index: number, c: Partial<CharacterConfig>) => void;
  setResult: (r: SimulationResult | null) => void;
  setIsSimulating: (s: boolean) => void;
  
  // Timeline Actions
  addTimelineAction: (charIndex: number, action: Omit<TimelineAction, 'id'>) => void;
  updateTimelineAction: (charIndex: number, actionId: string, updates: Partial<TimelineAction>) => void;
  removeTimelineAction: (charIndex: number, actionId: string) => void;
  generateScriptFromTimeline: (charIndex: number) => string;
}

// Fallback scripts only if backend fails
export const FALLBACK_SCRIPTS: Record<string, string> = {
  "无": ""
};

// Helper to parse existing scripts into timeline actions (basic implementation)
const parseScriptToTimeline = (script: string): TimelineAction[] => {
  const actions: TimelineAction[] = [];
  let currentTime = 0;
  
  const lines = script.split('\n').map(l => l.trim()).filter(Boolean);
  
  lines.forEach((line, idx) => {
    const parts = line.split(' ');
    const cmd = parts[0].toLowerCase();
    
    if (cmd === 'wait') {
      const dur = parseFloat(parts[1] || '0');
      currentTime += dur;
    } else {
      let type: ActionType = "Attack";
      let dur = 1.0; // Default duration assumption
      let name = "";
      
      if (['skill', '战技'].some(k => cmd.includes(k))) { type = "Skill"; dur = 1.5; name="skill"; }
      else if (['ult', '终结技'].some(k => cmd.includes(k))) { type = "Ult"; dur = 2.0; name="ult"; }
      else if (['qte', '连携技'].some(k => cmd.includes(k))) { type = "QTE"; dur = 1.0; name="qte"; }
      else if (['a', '普攻'].some(k => cmd.includes(k))) { type = "Attack"; name="a1"; } // Normalize 'a' to 'a1' if not specific? Or keep original cmd?
      
      // If cmd is specific like "a3", keep it.
      if (cmd.startsWith("a") && /\d/.test(cmd)) {
          name = cmd;
      }
      
      actions.push({
        id: `action-${idx}-${Date.now()}`,
        type,
        startTime: currentTime,
        duration: dur,
        name: name || cmd // Fallback to cmd if name not set
      });
      
      currentTime += 0.5; // Minimal gap or cast time
    }
  });
  
  return actions;
};

// Updated Helper: Uses wait_until for absolute synchronization
const generateScriptFromActions = (actions: TimelineAction[], charName: string): string => {
  if (!actions.length) return "";

  let script = "";

  actions.sort((a, b) => a.startTime - b.startTime);

  actions.forEach(action => {
    // Use wait_until for absolute time positioning
    // This ensures backend execution time matches frontend visual time exactly
    script += `wait_until ${action.startTime.toFixed(2)}\n`;
    script += `${action.name}\n`;
  });

  return script;
};

// Collision detection helper
const checkCollision = (action: TimelineAction, otherActions: TimelineAction[], excludeId?: string): boolean => {
  const actionEnd = action.startTime + action.duration;

  return otherActions.some(other => {
    if (excludeId && other.id === excludeId) return false; // Skip self when updating

    const otherEnd = other.startTime + other.duration;
    // Two actions collide if: action.start < other.end AND other.start < action.end
    return action.startTime < otherEnd && other.startTime < actionEnd;
  });
};

// Find next available time slot (no collision)
const findNextAvailableSlot = (
  startTime: number,
  duration: number,
  existingActions: TimelineAction[],
  maxDuration: number
): number => {
  let candidateTime = startTime;
  const step = 0.1; // Check every 0.1 second

  while (candidateTime + duration <= maxDuration) {
    const testAction: TimelineAction = {
      id: 'temp',
      type: 'Attack',
      startTime: candidateTime,
      duration: duration,
      name: 'temp'
    };

    if (!checkCollision(testAction, existingActions)) {
      return candidateTime;
    }

    candidateTime += step;
  }

  // If no slot found, return original time (will be rejected)
  return startTime;
};

// Find nearest non-colliding position when dragging
const findNearestValidPosition = (
  targetTime: number,
  duration: number,
  existingActions: TimelineAction[],
  excludeId: string,
  maxDuration: number
): number => {
  // Clamp to timeline boundaries first
  const clampedTime = Math.max(0, Math.min(targetTime, maxDuration - duration));

  // Check if clamped position is at boundary (snapped to edge)
  const isAtStartBoundary = clampedTime === 0;
  const isAtEndBoundary = clampedTime === maxDuration - duration;

  // If at boundary and no collision, use boundary position
  if (isAtStartBoundary || isAtEndBoundary) {
    const testAction: TimelineAction = {
      id: 'temp',
      type: 'Attack',
      startTime: clampedTime,
      duration: duration,
      name: 'temp'
    };

    if (!checkCollision(testAction, existingActions, excludeId)) {
      return clampedTime;
    }
  }

  // First check if target position is valid
  const testAction: TimelineAction = {
    id: 'temp',
    type: 'Attack',
    startTime: clampedTime,
    duration: duration,
    name: 'temp'
  };

  if (!checkCollision(testAction, existingActions, excludeId)) {
    return clampedTime;
  }

  // Find all gaps between actions
  const sortedActions = existingActions
    .filter(a => a.id !== excludeId)
    .sort((a, b) => a.startTime - b.startTime);

  // Check if we can fit before the first action
  if (sortedActions.length > 0 && clampedTime < sortedActions[0].startTime) {
    const spaceAvailable = sortedActions[0].startTime;
    if (duration <= spaceAvailable) {
      return Math.max(0, Math.min(clampedTime, sortedActions[0].startTime - duration));
    }
  }

  // Check gaps between actions
  for (let i = 0; i < sortedActions.length - 1; i++) {
    const current = sortedActions[i];
    const next = sortedActions[i + 1];
    const gapStart = current.startTime + current.duration;
    const gapEnd = next.startTime;
    const gapSize = gapEnd - gapStart;

    // If target is in this gap
    if (clampedTime >= gapStart && clampedTime <= gapEnd) {
      if (gapSize >= duration) {
        // Fit in the gap, snap to nearest edge
        const distToStart = Math.abs(clampedTime - gapStart);
        const distToEnd = Math.abs(clampedTime - (gapEnd - duration));
        return distToStart < distToEnd ? gapStart : gapEnd - duration;
      } else {
        // Gap too small, snap to left edge
        return Math.max(0, gapStart - duration);
      }
    }
  }

  // Check if we can fit after the last action
  if (sortedActions.length > 0) {
    const lastAction = sortedActions[sortedActions.length - 1];
    const afterLast = lastAction.startTime + lastAction.duration;
    if (clampedTime >= afterLast && afterLast + duration <= maxDuration) {
      return Math.max(afterLast, Math.min(clampedTime, maxDuration - duration));
    }
  }

  // Fallback: snap to nearest edge
  const colliding = sortedActions.find(a => {
    const aEnd = a.startTime + a.duration;
    return clampedTime < aEnd && clampedTime + duration > a.startTime;
  });

  if (colliding) {
    const collidingEnd = colliding.startTime + colliding.duration;
    const distToLeft = Math.abs(clampedTime - (colliding.startTime - duration));
    const distToRight = Math.abs(clampedTime - collidingEnd);

    if (distToLeft < distToRight && colliding.startTime - duration >= 0) {
      return colliding.startTime - duration;
    } else if (collidingEnd + duration <= maxDuration) {
      return collidingEnd;
    }
  }

  return clampedTime;
};

export const useSimulationStore = create<SimulationState>((set, get) => ({
  duration: 20,
  enemy: {
    defense: 100,
    dmg_taken_mult_physical: 1.0,
    dmg_taken_mult_heat: 1.0,
    dmg_taken_mult_electric: 1.0,
    dmg_taken_mult_nature: 1.0,
    dmg_taken_mult_frost: 1.0,
  },
  characters: Array(4).fill(null).map(() => ({ name: "无", script: "", timeline: [] })),
  availableCharacters: ["无"], // Initial default
  defaultScripts: {},
  result: null,
  isSimulating: false,

  fetchAvailableCharacters: async () => {
      try {
          const res = await apiClient.get('/characters');
          if (res.data) {
              const characters = res.data.characters || [];
              set({
                  availableCharacters: ["无", ...characters],
                  defaultScripts: res.data.default_scripts || {}
              });

              // Preload character constants for all available characters
              if (characters.length > 0) {
                  preloadCharacterConstants(characters).catch(err => {
                      console.warn('Failed to preload character constants:', err);
                  });
              }
          }
      } catch (err) {
          console.error("Failed to fetch characters", err);
          // Fallback if backend fails
          set({
              availableCharacters: ["无"],
              defaultScripts: {}
           });
      }
  },

  setDuration: (d) => set({ duration: d }),
  setEnemy: (e) => set((state) => ({ enemy: { ...state.enemy, ...e } })),
  
  setCharacter: (index, c) => {
    set((state) => {
      const newChars = [...state.characters];

      // If name changed, reset timeline based on default script
      if (c.name && c.name !== state.characters[index].name) {
         // Look up script in dynamic backend list, or fallback
         const script = c.script !== undefined ? c.script : (state.defaultScripts[c.name] || FALLBACK_SCRIPTS[c.name] || "");
         c.timeline = parseScriptToTimeline(script);
         c.script = script;

         // Async: Update durations from character constants
         if (c.timeline && c.timeline.length > 0 && c.name !== "无") {
           (async () => {
             const updatedTimeline = await Promise.all(
               c.timeline!.map(async (action) => {
                 const duration = await getActionDuration(c.name!, action.type);
                 return { ...action, duration };
               })
             );

             // Update state with corrected durations
             set((state) => {
               const newChars = [...state.characters];
               newChars[index] = {
                 ...newChars[index],
                 timeline: updatedTimeline,
                 script: generateScriptFromActions(updatedTimeline, c.name!)
               };
               return { characters: newChars };
             });
           })();
         }
      } else if (c.script !== undefined && !c.timeline) {
         // If script updated manually but no timeline provided, try to parse
         // c.timeline = parseScriptToTimeline(c.script);
         // NOTE: We avoid auto-parsing user manual edits to avoid overwriting timeline state unexpectedly
         // But for initial load it's fine.
      }

      newChars[index] = { ...newChars[index], ...c };
      return { characters: newChars };
    });
  },
  
  setResult: (r) => set({ result: r }),
  setIsSimulating: (s) => set({ isSimulating: s }),

  addTimelineAction: (charIndex, action) => set((state) => {
    const newChars = [...state.characters];
    const char = newChars[charIndex];
    if (!char.timeline) char.timeline = [];

    // Check for collision and find available slot if needed
    let adjustedStartTime = action.startTime;
    const tempAction: TimelineAction = {
      ...action,
      id: 'temp',
      startTime: adjustedStartTime
    };

    if (checkCollision(tempAction, char.timeline)) {
      // Find next available slot
      adjustedStartTime = findNextAvailableSlot(
        action.startTime,
        action.duration,
        char.timeline,
        state.duration
      );

      // If still collides (no slot found), don't add
      tempAction.startTime = adjustedStartTime;
      if (checkCollision(tempAction, char.timeline)) {
        console.warn('No available slot found for action');
        return {}; // Don't add the action
      }
    }

    const newAction = { ...action, startTime: adjustedStartTime, id: `act-${Date.now()}` };
    char.timeline = [...char.timeline, newAction].sort((a, b) => a.startTime - b.startTime);

    // Auto-update script
    char.script = generateScriptFromActions(char.timeline, char.name);

    return { characters: newChars };
  }),

  updateTimelineAction: (charIndex, actionId, updates) => set((state) => {
    const newChars = [...state.characters];
    const char = newChars[charIndex];
    if (!char.timeline) return {};

    // Find the action being updated
    const actionIndex = char.timeline.findIndex(a => a.id === actionId);
    if (actionIndex === -1) return {};

    const originalAction = char.timeline[actionIndex];
    const updatedAction = { ...originalAction, ...updates };

    // Always clamp to timeline boundaries first
    updatedAction.startTime = Math.max(0, Math.min(updatedAction.startTime, state.duration - updatedAction.duration));

    // Check for collision (excluding self)
    if (checkCollision(updatedAction, char.timeline, actionId)) {
      // Instead of rejecting, find nearest valid position
      const adjustedStartTime = findNearestValidPosition(
        updatedAction.startTime,
        updatedAction.duration,
        char.timeline,
        actionId,
        state.duration
      );

      updatedAction.startTime = adjustedStartTime;
    }

    char.timeline = char.timeline.map(a =>
      a.id === actionId ? updatedAction : a
    ).sort((a, b) => a.startTime - b.startTime);

    char.script = generateScriptFromActions(char.timeline, char.name);
    return { characters: newChars };
  }),

  removeTimelineAction: (charIndex, actionId) => set((state) => {
    const newChars = [...state.characters];
    const char = newChars[charIndex];
    if (!char.timeline) return {};

    char.timeline = char.timeline.filter(a => a.id !== actionId);
    char.script = generateScriptFromActions(char.timeline, char.name);
    return { characters: newChars };
  }),

  generateScriptFromTimeline: (charIndex) => {
    const state = get();
    const char = state.characters[charIndex];
    if (!char.timeline) return "";
    return generateScriptFromActions(char.timeline, char.name);
  }
}));

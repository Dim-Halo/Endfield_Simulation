// Frontend constant mirror of backend logic
// Fetches character constants from API instead of hardcoding

import { apiClient } from '../api/client';

export interface FrameData {
    total: number;
    hit?: number;
    interval?: number;
    [key: string]: any;
}

export interface CharacterConstants {
    character_name: string;
    frame_data: Record<string, any>;
    skill_multipliers: Record<string, any>;
    mechanics: Record<string, any>;
}

// Cache for character constants
const constantsCache = new Map<string, CharacterConstants>();

// Fetch character constants from API
export async function fetchCharacterConstants(charName: string): Promise<CharacterConstants | null> {
    if (constantsCache.has(charName)) {
        return constantsCache.get(charName)!;
    }

    try {
        const response = await apiClient.get(`/characters/${encodeURIComponent(charName)}/constants`);
        const data = response.data;
        constantsCache.set(charName, data);
        return data;
    } catch (error) {
        console.error(`Error fetching constants for ${charName}:`, error);
        return null;
    }
}

// Get action duration from character constants
export async function getActionDuration(charName: string, type: string): Promise<number> {
    const constants = await fetchCharacterConstants(charName);

    if (!constants || !constants.frame_data) {
        // Fallback to default duration
        return 1.0;
    }

    const frameData = constants.frame_data;
    let frames = 0;

    // Map action type to frame data key
    switch (type) {
        case "Skill":
            frames = frameData.skill?.total || 0;
            break;
        case "Ult":
            frames = frameData.ult?.total || 0;
            break;
        case "QTE":
            frames = frameData.qte?.total || 0;
            break;
        case "Attack":
            // Use first normal attack frame
            frames = frameData.normal?.[0]?.total || 0;
            break;
        default:
            frames = 0;
    }

    // Convert frames to seconds (1 frame = 0.1 seconds)
    return frames > 0 ? frames * 0.1 : 1.0;
}

// Preload constants for multiple characters
export async function preloadCharacterConstants(charNames: string[]): Promise<void> {
    await Promise.all(charNames.map(name => fetchCharacterConstants(name)));
}

// Clear cache (useful for testing or refresh)
export function clearConstantsCache(): void {
    constantsCache.clear();
}

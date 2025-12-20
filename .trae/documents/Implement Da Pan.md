## Implement New Character: Da Pan (大潘)

I will implement the new character "Da Pan" with the specified mechanics, focusing on his interaction with the Break (PhysAnomalyType.BREAK) system and his unique QTE/Talent mechanics.

### 1. Data Definitions (`entities/characters/dapan_constants.py`)
- Define skill multipliers:
  - Normal Attack: 63%, 75%, 113%, 136% (Total 4 hits).
  - Skill (颠勺！): 300%.
  - Ultimate (切丝入锅！): Air Slash 50% * 6, Final Hit 400%.
  - QTE (加料！): 650% + Impact (M猛击) with 20% boost.
- Define Frame Data (using standard placeholders ~0.5s-1.0s per action).

### 2. Simulation Logic (`entities/characters/dapan_sim.py`)
- **Class**: `DaPanSim` inheriting from `BaseActor`.
- **Attributes**: Str 175, Agi 96, Int 94, Wil 102.
- **Mechanics**:
  - **QTE Trigger**: Listen to `PHYS_ANOMALY` events. When enemy Break stacks reach 4, activate QTE.
  - **QTE Execution**: Custom logic to trigger Impact (consumes stacks) and apply a 20% boost to the *reaction damage* specifically, then deal the main skill damage.
  - **Talent 1 (尝尝咸淡)**: 
    - Ult final hit applies "BeiLiao" (备料) buff to self.
    - QTE execution checks for "BeiLiao". If present, consumes 1 stack and resets QTE cooldown/readiness (allowing rapid chaining if conditions permit).
  - **Talent 2 (勾芡)**: 
    - Dynamic damage bonus based on target's Break stacks (10% per stack).
    - Implemented by overriding `get_current_panel` or injecting logic into damage calculation context.

### 3. System Integration (`app.py`)
- Register "大潘" in `CHAR_MAP`.
- Add a default script for easy testing (e.g., `skill` -> `wait` -> `ult` -> `qte`).

### 4. Verification
- I will verify the implementation by running the simulation and checking:
  - QTE triggers correctly at 4 stacks.
  - Impact damage is boosted.
  - Talent 1 refreshes QTE (if applicable in script).
  - Talent 2 increases damage as stacks rise.
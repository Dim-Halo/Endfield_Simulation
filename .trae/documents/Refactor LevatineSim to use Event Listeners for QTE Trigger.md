I have analyzed the codebase and identified that **LevatineSim** is currently using a polling mechanism (checking target status in `parse_command`) instead of an event-driven mechanism (listening for "moment of application"). This contradicts your requirement to "detect the moment the enemy is inflicted with an anomaly".

Other characters like **WolfguardSim**, **ChenSim**, **DaPanSim**, etc., are already correctly using event listeners (`BUFF_APPLIED`, `REACTION_TRIGGERED`, `POST_DAMAGE`) to detect specific moments.

**Plan to Fix LevatineSim:**

1.  **Switch to Event Listener**:
    *   Modify `LevatineSim` to listen for `BUFF_APPLIED` (and `BUFF_STACKED` for refreshes) events.
    *   In the event handler, check if the applied buff has the `BURNING` or `CORROSION` tag.
    *   When detected, set `self.qte_ready_timer = 30` (activating the QTE window), similar to how WolfguardSim works.

2.  **Update Command Parsing**:
    *   Modify `LevatineSim.parse_command` to check `self.qte_ready_timer > 0` instead of polling `self.target.buffs.has_tag(...)`.

3.  **Consistency Check**:
    *   Ensure **WolfguardSim** also listens for both `BUFF_APPLIED` (new application) and possibly `BUFF_STACKED` (refresh) to ensure consistent behavior when anomalies are refreshed. (Currently, it only listens to `APPLIED`, which I will keep as is unless requested, but for Levatine, I will ensure it catches the "moment").

**Note on AntalSim**:
*   I noticed **AntalSim** currently has **no QTE trigger logic** implemented (its `on_reaction_triggered` is empty). Since you asked to check "all characters", I flag this as a missing feature, but I will focus on fixing LevatineSim's *incorrect* logic first. If you want AntalSim's QTE implemented (likely triggered by Electric/Overload), please let me know.

I will proceed with refactoring **LevatineSim** to use the event-driven approach.
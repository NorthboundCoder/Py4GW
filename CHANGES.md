# HeroAI Build System - Changes

Re-implementation of custom HeroAI builds and supporting skills layer.

---

## Skills Layer — Modified Files

### Monk
| File | Changes |
|---|---|
| `Py4GWCoreLib/Builds/Skills/Monk/HealingPrayers.py` | Added `Orison_of_Healing(health_threshold)`, `Healing_Breeze(health_threshold)` |
| `Py4GWCoreLib/Builds/Skills/Monk/SmitingPrayers.py` | Added `Banish`, `Symbol_of_Wrath` |
| `Py4GWCoreLib/Builds/Skills/Monk/ProtectionPrayers.py` | Added `Shielding_Hands` |

### Any
| File | Changes |
|---|---|
| `Py4GWCoreLib/Builds/Skills/any/NoAttribute.py` | Added `Resurrection_Signet` (targets dead players via `Agent.IsPlayer`) |

### Ranger
| File | Changes |
|---|---|
| `Py4GWCoreLib/Builds/Skills/ranger/BeastMastery.py` | Added `Comfort_Animal` (heals own pet below 80% HP) |

### Mesmer
| File | Changes |
|---|---|
| `Py4GWCoreLib/Builds/Skills/mesmer/IllusionMagic.py` | Added `Empathy`, `Conjure_Phantasm`, `Shatter_Delusions`, `Imagined_Burden` |
| `Py4GWCoreLib/Builds/Skills/mesmer/DominationMagic.py` | Added `Backfire` (targets casters, lazy-import pattern) |
| `Py4GWCoreLib/Builds/Skills/mesmer/InspirationMagic.py` | Added `Ether_Feast` (self-heal via energy drain, health < 75%) |

### Elementalist
| File | Changes |
|---|---|
| `Py4GWCoreLib/Builds/Skills/elementalist/FireMagic.py` | Added `Flare` (spam), `Fire_Storm(min_enemies=2)` |
| `Py4GWCoreLib/Builds/Skills/elementalist/AirMagic.py` | Added `Blinding_Flash`, `Lightning_Javelin` — both restricted to `Range.Nearby` (close melee attackers only) |

### Necromancer
| File | Changes |
|---|---|
| `Py4GWCoreLib/Builds/Skills/necromancer/BloodMagic.py` | Added `Vampiric_Gaze(0.80)`, `Vampiric_Touch(0.75)` (adjacent), `Life_Siphon` |
| `Py4GWCoreLib/Builds/Skills/necromancer/DeathMagic.py` | Added `Animate_Bone_Horror` (corpse-gated), `Deathly_Swarm` (clustered) |
| `Py4GWCoreLib/Builds/Skills/necromancer/Curses.py` | Added `Faintheartedness` (prefers attackers, skip already-hexed) |

---

## Build Files — Created

| File | Description |
|---|---|
| `Py4GWCoreLib/Builds/Monk/Mo_R/Smiter_Healer.py` | Primary healer + smiter. Mo/Any. Healing priority: RoF → Shielding Hands → Orison (75%) → Healing Breeze (75%) |
| `Py4GWCoreLib/Builds/Monk/Mo_Any/Smiting_Monk.py` | Last-resort healer + smiter. Mo/Any. Orison/Breeze at 50% threshold |
| `Py4GWCoreLib/Builds/Mesmer/Me_E/Illusion_Hexer.py` | Illusion/Domination hexer with Ele secondary. Me/E. Damage priority: Flare → Fire Storm (2+) |
| `Py4GWCoreLib/Builds/Elementalist/E_Mo/Fire_Monk.py` | Fire damage + secondary healer. E/Mo. Orison/Breeze at 60% threshold. Damage priority: Flare → LJ → BF → Fire Storm (2+) |
| `Py4GWCoreLib/Builds/Necromancer/N_Any/Blood_Death_Necro.py` | Blood life-steal + Death minion summoner. N/Any. Animate fires before InAggro gate |

---

## Cross-Build Healing Priority

Threshold-based design prevents duplicate heals across three healers:

| Build | Orison threshold | Healing Breeze threshold |
|---|---|---|
| Smiter Healer | 75% | 75% or degen |
| Fire Monk | 60% | 60% or degen |
| Smiting Monk | 50% | 50% or degen |

---

## Bug Fixes

### 2026-04-09 — Loot pickup broken after build files added

**Problem:** Heroes stopped picking up loot after the 5 custom build files were created.

**Root cause:** All 5 build files had `Skill.GetID()` calls at **module level** (outside any class). `BuildRegistry._scan_build_types()` uses `importlib.import_module()` with no error handling — if module-level code raises during the scan, `EnsureBuildContract` throws every frame, `HeroAI_BT.tick()` never runs, and `LootingNode` never fires.

**Fix:** Moved all `Skill.GetID()` calls inside `__init__` as instance attributes (`self.X_ID = Skill.GetID("X")`), set before `super().__init__()` so they're available for `required_skills`/`optional_skills`. Updated all `self.IsSkillEquipped(X_ID)` references in `_run_local_skill_logic` to `self.X_ID`.

**Files changed:** All 5 build files (`Smiter_Healer.py`, `Smiting_Monk.py`, `Illusion_Hexer.py`, `Fire_Monk.py`, `Blood_Death_Necro.py`)

### 2026-04-09 — Healing Breeze no-duplicate-cast guards

**Changes:**
1. **Someone else is casting it:** Added a party scan before target selection. If any other ally is currently casting `Healing_Breeze` (checked via `Agent.IsCasting` + `Agent.GetCastingSkillID`), the skill is skipped entirely for this frame. Prevents two healers from casting it simultaneously.
2. **Already been cast (pre-existing):** The existing `Routines.Checks.Effects.HasBuff` filter already excluded targets that have the enchantment active. Added a comment to make this explicit.

**File changed:** `Py4GWCoreLib/Builds/Skills/Monk/HealingPrayers.py` — applies to all three builds that use `Healing_Breeze` (Smiter Healer, Fire Monk, Smiting Monk).

### 2026-04-09 — Backfire targets highest level caster; no melee fallback

**Changes:**
- `Backfire` now selects the highest level enemy caster (`Agent.GetLevel` max) instead of cluster-score targeting.
- Removed the non-caster fallback. Backfire on a melee enemy is wasted energy — if there are no casters in range, the skill simply doesn't fire.

**File changed:** `Py4GWCoreLib/Builds/Skills/mesmer/DominationMagic.py`

### 2026-04-09 — Fire Storm cluster detection and priority rewrite

**Problem:** Fire Storm was rarely casting because `Flare` (placed first in both builds) always succeeded, and the old cluster check only counted enemies in spellcast range — not whether they were actually adjacent to each other.

**Fix:**
1. **`FireMagic.py` — `Fire_Storm`**: Rewrote cluster detection to use `Range.Adjacent.value`. Iterates alive enemies in spellcast range, finds the enemy-centered position with the most adjacent enemies. Also checks party member positions as cluster centers (for when enemies swarm an ally). Returns False immediately if no position has `≥ min_enemies` adjacent — so Flare can fire normally in non-clustered fights.
2. **`Fire_Monk.py`**: Moved Fire Storm call before Flare. Now takes priority when a cluster exists; falls through to Flare otherwise.
3. **`Illusion_Hexer.py`**: Same reordering — Fire Storm before Flare.

### 2026-04-09 — Healer kill priority across all custom builds

**Change:** All custom builds now prioritise killing Monk-primary enemies (healers) first when selecting targets for damage and debuff skills.

| File | Skill(s) affected |
|---|---|
| `FireMagic.py` | `Flare` — checks for healer target before normal injured-enemy fallback |
| `BloodMagic.py` | `Life_Siphon`, `Vampiric_Gaze`, `Vampiric_Touch` — sort healer targets to front |
| `IllusionMagic.py` | `Conjure_Phantasm` — tries healer pool first, falls back to full pool |
| `DominationMagic.py` | `Backfire` — sorts `(Monk-primary first, then highest level)` |

AoE skills (`Fire_Storm`, `Deathly_Swarm`) are unchanged — cluster-center targeting by enemy density is more appropriate for ground-targeted AoE.

**Detection:** `Agent.GetProfessions(agent_id)` returns `(primary_id, secondary_id)`; compare `primary == Profession.Monk.value`.

### 2026-04-09 — Healing Breeze now triggers on hex degen

**Change:** `Healing_Breeze` in `HealingPrayers.py` now also casts on targets with a health-degen hex (`Agent.IsDegenHexed`), in addition to health threshold, bleeding, and poisoned. Degen-hexed targets are sorted to the front of the priority list alongside bleeding/poisoned targets.

**File changed:** `Py4GWCoreLib/Builds/Skills/Monk/HealingPrayers.py`

### 2026-04-09 — Looting permanently broken after Messaging.py reload mid-loot

**Problem:** After reloading the Messaging.py widget (or launcher reload) while a `PickUpLoot` coroutine was mid-flight, looting would stop working permanently until GW clients were restarted.

**Root cause:** When Messaging.py reloads, the module-level `hero_ai_snapshots` dict is cleared. But the in-flight `PickUpLoot` coroutine had already called `MarkMessageAsRunning` (message stays `Active=True, Running=True`) and `DisableHeroAIOptions` (`Looting=False` in SharedMemory). With the snapshot gone, two `HealStaleHeroAISnapshot` early-exits fire: first at "no snapshot → return", then at "active suspending message → return". Neither path restores options. `LootingNode` reads `Looting=False` → FAILURE every frame.

**Fix:** Added ghost-message recovery to `HealStaleHeroAISnapshot`: when an active suspending message exists BUT there's no snapshot AND all options are disabled, Messaging.py must have reloaded mid-operation. The stuck message is marked finished via `MarkMessageAsFinished` and options are restored via `RestoreHeroAISnapshot` (which calls `EnableHeroAIOptions` as fallback when there's no snapshot to pop).

**File changed:** `Widgets/System/Messaging.py` (`HealStaleHeroAISnapshot`)

### 2026-04-09 — Headless tree loot cancellation fix

**Problem:** `HeroAIHeadlessTree._finish_active_pick_up_loot_message()` would cancel a `PickUpLoot` message that `Messaging.py` was actively processing (Running state), aborting loot mid-execution and causing a cancel loop.

**Fix:** Added a `Running` check — if the message has `Running=True`, skip cancellation and let `Messaging.py` complete it.

**File changed:** `HeroAI/headless_tree.py`

---

## 2026-06-15 — TOTF quest dispatch rewrite

**Problem:** Characters in other parties (other bot accounts on the same machine) were picking up "The Dreamer and the Zealot" quest (ID 1461) during the TOTF run.

**Root cause:** `_follower_npc_dialog_node` used `GLOBAL_CACHE.ShMem.GetAllAccountData()` to find followers, but that function returns **all active accounts on the machine**, not just accounts in the current party. Any other bot instances running concurrently received `SendManualDialog` for the TOTF quest NPC.

**Architecture confirmed:** Only the leader runs the full planner. Followers rely on dispatch commands (HeroAI handles movement, ShMem commands handle specific interactions). Cross-dispatch is still needed — the fix is to dispatch to the right accounts.

**Fix:**
1. Rewrote `_follower_npc_dialog_node` to use `SendDialogToTarget` (agent-ID based) instead of `SendManualDialog` (coordinate-search based). The NPC agent ID comes from `Player.GetTargetID()` captured in `_dispatch`, which runs in the same `SequenceNode._tick_impl` while-loop iteration as the preceding `BT.MoveAndInteract` — guaranteed to be the NPC with no interleaving ticks. Eliminates the `TargetNearestNPCXY` search on the follower that was the previous failure mode.
2. Added same-party filter: cross-references `account.AgentData.AgentID` (from ShMem) against `Party.Players.GetAgentIDByLoginNumber(login)` for every party member. Only same-party accounts receive the dispatch.
3. Removed `npc_pos` and `search_range` params from `_follower_npc_dialog_node` (not needed with `SendDialogToTarget`).
4. Fixed `_open_chest_sequential_node` with the same same-party filter and fixed `_party_pos` — was using `getattr(account, "PlayerID", 0)` which always returned 0 (field doesn't exist on `AccountStruct`). Now uses `account.AgentData.AgentID`.

| File | Change |
|---|---|
| `Widgets/Automation/Bots/Missions/Dungeons/Tunnels of the Forsaken.py` | Rewrote `_follower_npc_dialog_node` with `SendDialogToTarget` + party filter; fixed `_open_chest_sequential_node` party filter and `_party_pos` |

---

## Known API Gotchas

- `Agent.IsHuman` does not exist — use `Agent.IsPlayer`
- `Agent.IsBlinded` does not exist — use `Routines.Checks.Agents.HasEffect(agent_id, skill_id)`
- `DominationMagic` methods use lazy imports — always include `Routines` in the lazy import block
- `Animate_Bone_Horror` must be placed **before** the `InAggro()` gate in build logic
- Unhandled exceptions in any skill coroutine crash the entire HeroAI behaviour tree — reload launcher after fixing skill errors
- **Never call `Skill.GetID()` at module level in build files** — `BuildRegistry._scan_build_types()` imports all build modules with no error handling; any exception at import time prevents `HeroAI_BT.tick()` from running. Always call `Skill.GetID()` inside `__init__` as `self.X_ID = Skill.GetID("X")`
- **HeroAI build matching only reads skill slots 1–5** — skills placed in slots 6–8 are invisible to the matcher. All `required_skills` must be in the first 5 slots on the skill bar or the build will not match and will fall back to HeroAI default.

---

## Session 2026-04-29 — Re-implementation on Fork

Re-implemented all changes from prior session (CHANGES.md above) onto this repo fork.

### Skill Layer — Added Methods

| File | Methods Added |
|---|---|
| `Py4GWCoreLib/Builds/Skills/Monk/HealingPrayers.py` | `Orison_of_Healing(health_threshold)`, `Healing_Breeze(health_threshold)` (with degen/bleed/poison priority, no-duplicate guard, HasBuff filter) |
| `Py4GWCoreLib/Builds/Skills/Monk/SmitingPrayers.py` | `Banish`, `Symbol_of_Wrath` |
| `Py4GWCoreLib/Builds/Skills/Monk/ProtectionPrayers.py` | `Shielding_Hands` |
| `Py4GWCoreLib/Builds/Skills/any/NoAttribute.py` | `Resurrection_Signet` (targets dead players via `Agent.IsPlayer`) |
| `Py4GWCoreLib/Builds/Skills/ranger/BeastMastery.py` | `Comfort_Animal` (heals own pet below 80% HP via `Party.Pets.GetPetID`) |
| `Py4GWCoreLib/Builds/Skills/mesmer/IllusionMagic.py` | `Empathy`, `Conjure_Phantasm` (healer-first targeting), `Shatter_Delusions`, `Imagined_Burden` |
| `Py4GWCoreLib/Builds/Skills/mesmer/DominationMagic.py` | `Backfire` (Monk-primary first, then highest level, no melee fallback) |
| `Py4GWCoreLib/Builds/Skills/mesmer/InspirationMagic.py` | `Ether_Feast` (self-heal < 75% HP) |
| `Py4GWCoreLib/Builds/Skills/elementalist/FireMagic.py` | `Fire_Storm(min_enemies)` (Adjacent cluster detection, party-center check), `Flare` (healer-kill priority) |
| `Py4GWCoreLib/Builds/Skills/elementalist/AirMagic.py` | `Blinding_Flash`, `Lightning_Javelin` (both Nearby-restricted, melee attackers only) |
| `Py4GWCoreLib/Builds/Skills/necromancer/BloodMagic.py` | `Vampiric_Gaze(0.80)`, `Vampiric_Touch(0.75)` (adjacent), `Life_Siphon` (all with healer-kill priority) |
| `Py4GWCoreLib/Builds/Skills/necromancer/DeathMagic.py` | `Animate_Bone_Horror` (corpse-gated via `Agent.IsExploitableCorpse`), `Deathly_Swarm` (clustered) |
| `Py4GWCoreLib/Builds/Skills/necromancer/Curses.py` | `Faintheartedness` (attacker-preferred, skip already-hexed) |

### Build Files — Created

| File | Description |
|---|---|
| `Py4GWCoreLib/Builds/Monk/Mo_R/Smiter_Healer.py` | Mo/R primary healer + smiter. RoF → Shielding Hands → Orison (75%) → Healing Breeze (75%) → smite |
| `Py4GWCoreLib/Builds/Monk/Mo_Any/Smiting_Monk.py` | Mo/Any last-resort healer + smiter. Orison/Breeze at 50% threshold |
| `Py4GWCoreLib/Builds/Mesmer/Me_E/Illusion_Hexer.py` | Me/E illusion hexer + fire damage. Backfire → Empathy → Conjure Phantasm → Shatter Delusions → Imagined Burden → Fire Storm (2+) → Flare |
| `Py4GWCoreLib/Builds/Elementalist/E_Mo/Fire_Monk.py` | E/Mo fire damage + secondary healer. Orison/Breeze at 60%. Fire Storm (2+) → LJ → BF → Flare |
| `Py4GWCoreLib/Builds/Necromancer/N_Any/Blood_Death_Necro.py` | N/Any blood life-steal + death minions. Animate fires before InAggro gate |

### Bug Fixes Applied

- **`Widgets/System/Messaging.py` — `HealStaleHeroAISnapshot`**: Added ghost-message recovery path — when `hero_ai_snapshots` is empty but an active suspending message exists with all options disabled (sign of a reload mid-operation), the stuck message is cleared via `MarkMessageAsFinished` and options restored via `RestoreHeroAISnapshot`.
- **`HeroAI/headless_tree.py` — `_finish_active_pick_up_loot_message`**: Added `Running` check — skips cancellation if `message.Running == True`, allowing Messaging.py to complete the in-flight operation.

### Infrastructure

- Created `CLAUDE.md` with session rule: append `CHANGES.md` at end of each session.

---

## Session 2026-04-29 (continued) — Dedicated Healer build support

### Skill Layer — Signature Fixes

| File | Change |
|---|---|
| `Py4GWCoreLib/Builds/Skills/Monk/ProtectionPrayers.py` | Added missing `Range`, `AgentArray` imports (bug from prior session) |
| `Py4GWCoreLib/Builds/Skills/Monk/ProtectionPrayers.py` | `Shielding_Hands` — added optional `health_threshold` parameter (defaults to `0.85`) |
| `Py4GWCoreLib/Builds/Skills/Monk/ProtectionPrayers.py` | `Reversal_of_Fortune` — added optional `health_threshold` parameter (overrides `Conditions.LessLife` when supplied) |

### Build Files

`Py4GWCoreLib/Builds/Monk/Mo_Any/Dedicated_Healer.py` was authored by the user and is ready to run — no changes needed to the build file itself.

**Design note:** `Dedicated_Healer` does not call `UpdatePartyHealthMonitor`, so `GetPartyHealthDelta` will return 0 for all targets. RoF priority ordering (melee → caster → other) still applies correctly; only spike-detection ranking is bypassed.

---

## Session 2026-04-29 (continued) — Bug fixes: Symbol of Wrath and Fire Storm

### Bug Fixes

**`SmitingPrayers.py` — `Symbol_of_Wrath`**

- **Root cause:** Was using `_pick_clustered_target` which finds enemies clustered anywhere in spellcast range, regardless of where the player is. Symbol of Wrath is a PBAoE centred on the caster — it should only fire when enemies are adjacent to the player's own position.
- **Fix:** Replaced with a direct player-position check. Gets enemies within spellcast range, filters to those within `Range.Adjacent` of the player, fires only if at least **2** are adjacent. Added `Player`, `Utils` imports to `SmitingPrayers.py`.

**`FireMagic.py` — `Fire_Storm`**

- **Root cause 1:** No early-out when `len(alive_enemies) < min_enemies`. The count loop could set `best_count = 1` (an enemy counting itself as adjacent), pass the `< min_enemies` check with `min_enemies = 1` edge cases, and cast.
- **Root cause 2:** When an ally position was the best cluster centre, `best_target` was set to `alive_enemies[0]` (first enemy in list) instead of the nearest enemy to that centre — wrong cast target.
- **Fix:** Added `if len(alive_enemies) < min_enemies: return False` as the first guard. Rewrote cluster logic to return the list of enemies within adjacent range (`_enemies_within_adjacent`) and check `len(nearby)` directly. Ally-centre branch now correctly picks the nearest enemy within that cluster.

---

## Session 2026-04-29 (continued) — Igneous Summoning Stone auto-use on explorable entry

### Feature

When the party enters a new explorable area, the highest-level sub-20 party member automatically uses their Igneous Summoning Stone (if they have one).

### Implementation

**File changed:** `Widgets/Automation/Multiboxing/HeroAI.py`

**Changes:**
1. Added `from Py4GWCoreLib.Party import Party` import.
2. Added module-level `_summoning_stone_map_signature: tuple[int, int, int, int] | None = None` to track which explorable area the stone was last dispatched for.
3. Added `_send_summoning_stone_on_entry()`:
   - Guards on `Party.IsPartyLeader()` — only the party leader coordinates dispatch, preventing every account from independently sending duplicate messages.
   - Queries `GLOBAL_CACHE.ShMem.GetAllAccountData()` for all active player accounts.
   - Filters to accounts with `0 < AgentData.Level < 20`.
   - Picks the account with the highest level (`max(..., key=lambda a: a.AgentData.Level)`).
   - Sends `SharedCommandType.UseSummoningStone` to only that account's email.
4. In `main()`:
   - Added `_summoning_stone_map_signature` to the `global` statement.
   - When `initialize(cached_data)` succeeds (explorable, party loaded), computes the current map signature `(MapID, Region, District, Language)` and fires `_send_summoning_stone_on_entry()` once whenever it differs from the stored signature. Stores the new signature to prevent repeated fires in the same area.
   - In the `else` branch (not explorable / loading), resets `_summoning_stone_map_signature = None` so re-entering the same area fires again.

### Behaviour

- Fires exactly once per distinct explorable area entry per session.
- The `UseSummoningStone` handler in `Messaging.py` already guards against summoning sickness and an alive summon, so double-use of a stone is prevented even in edge cases.
- Level-20 accounts are excluded from stone selection (`Level < 20`). The Igneous Stone `player_level < 20` guard in the handler provides a second layer of safety.
- If no sub-20 account is in the party, nothing is sent.

---

## Session 2026-04-29 (continued) — Fire Storm sequential priority across accounts

### Feature

When multiple party members have Fire Storm equipped, they now cast in sequence (Elementalist → Mesmer → others) with a 15-second gap between casts, rather than all firing simultaneously.

### Implementation

**File changed:** `Py4GWCoreLib/Builds/Skills/elementalist/FireMagic.py`

**Changes:**
1. Added module-level priority table `_FIRE_STORM_PROFESSION_PRIORITY = {6: 0, 5: 1}` (Elementalist = 6 highest priority, Mesmer = 5 second, all others default 99).
2. Added `_FIRE_STORM_DELAY_S = 15.0` — the gap between sequential casts.
3. Added `_fire_storm_priority_blocked(self, fire_storm_id)` method:
   - Gets the account's own primary profession and maps it to a priority number.
   - Elementalists (priority 0) always return `False` immediately — never blocked.
   - All other accounts scan `GLOBAL_CACHE.ShMem.GetAllAccountData()` for accounts with a strictly lower priority number (i.e., higher cast priority).
   - For each higher-priority account, scans their `AgentData.Skillbar.Skills` for a skill with `Id == fire_storm_id`. If found with `Recharge > 15.0` (cast within the last 15s), returns `True` (blocked).
4. `Fire_Storm()` calls `_fire_storm_priority_blocked()` immediately after the `IsSkillEquipped` check, returning `False` if blocked.

### Behaviour

- **Ele** casts Fire Storm whenever the cluster condition is met (2+ adjacent enemies), unrestricted.
- **Mes** can cast 15 seconds after the Ele's cast (when Ele's Recharge drops to 15). If the Ele doesn't have Fire Storm equipped, the Mes is unrestricted.
- **Others** can cast 15 seconds after the Mes's cast. If Mes doesn't have it, they defer to Ele timing only.
- If a higher-priority account cannot cast (out of energy, wrong range, no cluster), the lower-priority account is unblocked when that account's recharge reaches 0 (never cast recently) and takes over naturally.
- Fire Storm has a 20s recharge. The block threshold is `Recharge > (20 - 15) = 5.0` — i.e., blocked while the higher-priority cast happened less than 15 seconds ago. Constants: `_FIRE_STORM_TOTAL_RECHARGE_S = 20.0`, `_FIRE_STORM_DESIRED_GAP_S = 15.0`, `_FIRE_STORM_RECHARGE_THRESHOLD_S = 5.0`.

---

## Session 2026-04-29 (continued) — Fire Storm minimum cluster fix (HeroAI fallback path)

### Bug

Characters using the HeroAI default skill system (not a custom build) were casting Fire Storm on solo enemies. The custom build path (`FireMagic.Fire_Storm(2)`) correctly requires 2+ adjacent enemies, but the HeroAI fallback path through `TargetClusteredEnemy` had no minimum cluster count — it scored candidates by density but always returned the best candidate even if that was a lone enemy.

### Fix

Four files changed:

| File | Change |
|---|---|
| `HeroAI/custom_skill_src/skill_types.py` | Added `MinClusterSize: int = 1` to `CastConditions`. Default 1 (no restriction). |
| `HeroAI/targeting.py` | Added `min_cluster_size: int = 1` parameter to `TargetClusteredEnemy`. Guard: `if len(blob) < min_cluster_size: continue`. When all candidates are below the threshold, `scored` is empty and the function returns 0. |
| `HeroAI/combat.py` | Passes `min_cluster_size=conditions.MinClusterSize` to `TargetClusteredEnemy` in the `EnemyClustered` branch. |
| `HeroAI/custom_skill_src/elementalist.py` | Added `skill.Conditions.MinClusterSize = 2` to the Fire Storm custom skill definition. |

### Behaviour

- Characters on custom builds (Fire_Monk, Illusion_Hexer): cluster check already enforced by `FireMagic.Fire_Storm(2)`.
- Characters on HeroAI default: `TargetClusteredEnemy` now returns 0 when no candidate has ≥ 2 enemies in the blob. Since `TargetingStrict = True` (the default), the nearest-enemy fallback is suppressed and the skill does not fire.
- All other `EnemyClustered` skills are unaffected (default `MinClusterSize = 1`).
- The shared memory skillbar updates every ~37ms, giving a negligible transition window at the exact 15s boundary. The existing whiteboard intent system provides additional protection against simultaneous same-target casts within that window.

---

## Session 2026-04-29 (continued) — Healing Breeze triple-cast fix

### Bug

When Healing Breeze was needed on a single target, all three accounts that have it equipped (Smiter Monk, Fire Ele, Dedicated Healer) would cast it simultaneously. The existing guard checked `Agent.IsCasting` on party members, but all three accounts evaluate on the same tick before any cast animation has propagated — a classic TOCTOU race. Additionally, Healing Breeze was not registered with the whiteboard, so BuildMgr's cross-account intent system never engaged.

### Fix

**File changed:** `Py4GWCoreLib/Builds/Skills/Monk/HealingPrayers.py` — `Healing_Breeze()`

Three-layer defence:

1. **Whiteboard registration:** Calls `_wb_register(healing_breeze_id)` so `CastSkillID` will check and block if another account has already claimed the same `(skill_id, target)` pair in shared intent memory.
2. **Active-cast check:** Scans `GLOBAL_CACHE.ShMem.GetAllAccountData()` for any other account with `AgentData.Skillbar.CastingSkillID == healing_breeze_id`. If found, returns `False` without selecting a target.
3. **Recent-cast check:** For each other account's skillbar skills, if `skill.Id == healing_breeze_id and skill.Recharge > 0` (cast within the last ~2 seconds, still on recharge), returns `False`. This closes the window between commitment and animation visibility.

The existing `HasBuff` check (condition 3: "Healing Breeze already active on target — don't cast") was preserved and unchanged.

---

## Session 2026-05-01 — New Dervish Build: D/Any Pious Renewal

### Feature

New build added for Dervish/Any characters that spam Pious Renewal as a teardown buffer to continuously proc Aura of Holy Might (AoE armour-ignoring damage).

### Implementation

**File created:** `Py4GWCoreLib/Builds/Dervish/D_Any/Pious_Renewal.py`

**Required skills:** Pious Renewal (1499), Pious Fury (2146)

**Optional skills:** Aura of Holy Might kurzick (1955) / luxon (2098), Pious Assault (1490), Twin Moon Sweep (1487), Wearying Strike (1537), Aura Slicer (2070), Reap Impurities (1486), Irresistible Sweep (1489), Eremite's Attack (1485), Rending Sweep (1753), Asuran Scan (2415)

**Skill priority in `_run_local_skill_logic`:**

1. **Maintain AoHM** — cast if the buff is missing (checked via `Routines.Checks.Effects.HasBuff`). `_get_aohm_id()` returns whichever AoHM variant (kurzick/luxon) is equipped.
2. **Asuran Scan** — cast on nearest enemy to make attacks unblockable/unevadable.
3. **Pious Fury setup** — if Pious Fury is missing, cast PR first (so PF teardowns PR and procs AoHM), then cast Pious Fury.
4. **Buffer Pious Renewal** — cast PR if missing; PR must be the topmost enchantment so teardown attacks always consume it and not Pious Fury or AoHM.
5. **Teardown attacks** — Pious Assault → Twin Moon Sweep → Wearying Strike → Eremite's Attack. Each strips PR from the top, procing AoHM.
6. **Aura Slicer** — self-targeted enchantment that tears the topmost enchantment on cast; used after teardown attacks.
7. **Non-teardown support** — Irresistible Sweep (only when enchanted), Reap Impurities, Rending Sweep (only when target is enchanted).

### Key Design Decisions

- **Two AoHM variants:** `_get_aohm_id()` checks kurzick first, then luxon. Both are in `optional_skills` so either version is recognised.
- **Enchantment stack order (GW mechanic):** GW tears the most-recently-cast enchantment first. PR must always be cast last (topmost), which is why step 4 re-buffers PR before attacks and step 3 casts PR before Pious Fury.
- **Aura Slicer uses `CastSkillID`** (self-targeted), not `CastSkillIDAndRestoreTarget`.
- **Irresistible Sweep gate:** Irresistible Sweep requires the caster to be enchanted; the gate checks `has_pious_fury or has_pious_renewal or aohm_active`.

---

## Session 2026-05-03 — Pre-Searing inline builds: Mesmer + Healer

### Feature

Two new pre-searing builds following the creator's inline pattern (same as `Pre_Searing_Necro`, `Pre_Searing_ele`) — no `SkillsTemplate` dependency, all logic inline in `_run_local_skill_logic`.

### Build Files — Created

| File | Description |
|---|---|
| `Py4GWCoreLib/Builds/Mesmer/Me_E/Pre_Searing_Mesmer.py` | Me/E pre-searing hexer. Required: Empathy, Conjure Phantasm. Optional: Backfire, Shatter Delusions, Imagined Burden, Fire Storm, Flare, Ether Feast, Resurrection Signet. |
| `Py4GWCoreLib/Builds/Monk/Mo_Any/Pre_Searing_Healer.py` | Mo/Any pre-searing healer. Required: Healing Breeze, Orison of Healing. Optional: Reversal of Fortune, Shielding Hands, Bane Signet, Banish, Symbol of Wrath, Resurrection Signet. |

### Pre_Searing_Mesmer skill priority

1. Resurrection Signet — dead ally in spellcast range
2. Ether Feast — self-heal when own HP < 65% and an enemy is targeted
3. InAggro gate
4. Backfire — casters only, Monk primary first then highest level
5. Empathy — melee/martial enemies only
6. Conjure Phantasm — Monk-primary first, then any
7. Shatter Delusions — hexed enemies only
8. Imagined Burden — moving enemies first, then any
9. Fire Storm — 2+ enemies in spellcast range
10. Flare — nearest enemy fallback

### Pre_Searing_Healer skill priority

1. Resurrection Signet — dead ally in spellcast range
2. Shielding Hands — lowest-HP ally < 90%, no existing buff, InAggro only
3. Reversal of Fortune — lowest-HP ally < 90%, no existing buff, InAggro only
4. Orison of Healing — lowest-HP ally < 90%
5. Healing Breeze — ally < 90% OR bleeding/poisoned/degen-hexed, no existing buff; degen cases prioritised first
6. InAggro gate (smiting only below)
7. Bane Signet — attacking enemies
8. Banish — lowest-HP enemy
9. Symbol of Wrath — 2+ adjacent enemies (PBAoE, player position check)

### Bug Fixes Applied This Session

- **`Pre_Searing_Necro.py` — Animate Bone Horror spam:** Added minion cap (< 2 alive owned minions) before the corpse check. Requires `AgentArray` + `Agent` imports (added). Previously the skill fired on every corpse unconditionally.
- **`DeathMagic.Animate_Bone_Horror` — minion cap:** Added `max_minions=3` parameter. Checks `AgentArray.GetMinionArray()` filtered by `Agent.IsAlive` and `Agent.GetOwnerID == player_agent_id`. Fires only when live minion count is below cap.
- **Merge conflict re-apply (upstream pull):** After accepting upstream on 5 files (`NoAttribute.py`, `DominationMagic.py`, `IllusionMagic.py`, `Curses.py`, `DeathMagic.py`), re-applied all session changes. Upstream had added `Ineptitude`/`Wandering_Eye` to `IllusionMagic.py` and `Putrid_Bile`/`Putrid_Explosion`/`Rising_Bile` to `DeathMagic.py` — accommodated all new methods.

### Infrastructure

- Created `C:\Users\iancc\.claude\projects\D--GWBOTS-PyMine-Py4GW\memory\reference_project_docs.md` pointing to `AGENTS.md`, `docs/Py4GW_Conceptual_Model.md`, `FOLLOW_REFACTOR_HANDOVER.md`.
- Updated `CLAUDE.md` with session-start documentation reading rule.

---

## Session 2026-05-04 — Build cleanup, module-level ID fix, Fire Storm cluster fixes

### Build Files — Deleted

| File | Reason |
|---|---|
| `Py4GWCoreLib/Builds/Mesmer/Me_E/Illusion_Hexer.py` | Replaced by `Pre_Searing_Mesmer.py` |
| `Py4GWCoreLib/Builds/Monk/Mo_Any/Dedicated_Healer.py` | Replaced by `Pre_Searing_Healer.py` |

### Bug Fixes

**Module-level `Skill.GetID()` in `Pre_Searing_Mesmer.py` and `Pre_Searing_Healer.py`**

Both new builds were initially written with `Skill.GetID()` calls at module level (following the creator's pattern). After restart the Pre-Searing Ele stopped matching — `BuildRegistry._scan_build_types()` imports all builds with no error handling, so an exception in our new files' module-level code caused `EnsureBuildContract` to throw every frame, breaking all build matching across every character.

Fix: moved all `Skill.GetID()` calls inside `__init__` as `self.X_ID = Skill.GetID("X")`, with `super().__init__()` called after. All `_run_local_skill_logic` references updated to `self.X_ID`.

**`Pre_Searing_ele.py` — Fire Storm unconditioned**

Fire Storm was casting the instant any enemy was in aggro range — no enemy count or cluster check at all. Also had no `player_x, player_y` and no `alive_enemies` list.

Fix:
- Added `player_x, player_y = Player.GetXY()`
- Added `alive_enemies` list filtered by `Agent.IsAlive`
- Fire Storm now requires `len(alive_enemies) >= 2` and `TargetClusteredEnemy(area=Range.Nearby.value)` returns a target
- Flare now explicitly targets `GetNearestEnemy` instead of relying on current target

**`Pre_Searing_Necro.py` — Fire Storm cluster area too loose**

`TargetClusteredEnemy(area=Range.Spellcast.value)` counts all enemies within 1248 units as "clustered" — essentially always returns a target if 3 enemies exist anywhere in range. With `enemy_count >= 3` this fired too readily in pre-searing.

Fix: changed area to `Range.Nearby.value` (~700 units, enemies must actually be near each other). Lowered threshold from `>= 3` to `>= 2` since most pre-searing groups are pairs.

**`Pre_Searing_Mesmer.py` — same Fire Storm cluster area fix**

Same loose `area=Range.Spellcast.value` applied for consistency. Changed to `Range.Nearby.value`.

---

## Session 2026-06-08 — Reconnect follow/combat regression fix (v1, incomplete)

### Bug

When a multibox account disconnects mid-run and reconnects, it no longer follows or acts in combat. Clicking the leader's global Following/Combat toggle in the HeroAI UI does not fix it.

### Root Cause

`Py4GWSharedMemoryManager.update_callback` runs every draw frame and calls `SetPlayerData` to keep the shared memory slot fresh. `SetPlayerData` refreshes `AccountData` (including `LastUpdated`, `AgentID`, `PartyID`, etc.) but **does not touch `HeroAIOptions` or `Inbox`**.

When the account disconnects mid-run during an active suspending command (e.g. `BruteForceUnstuck`, `PixelStack`, `InteractWithTarget`):
1. `DisableHeroAIOptions` had already set `Following=False, Combat=False` in the slot
2. The account disconnects before `RestoreHeroAISnapshot` runs
3. The stale Active suspending message remains in `Inbox`
4. On reconnect, `SetPlayerData` (or `SubmitAccountData` if the slot expired) refreshes `AccountData` but leaves `HeroAIOptions` with `Following=False, Combat=False`
5. `HealStaleHeroAISnapshot` cannot fix it because `_has_active_hero_ai_suspending_message` returns True
6. The leader's UI toggle cannot fix it if the account is not yet visible in the leader's party cache (timing issue on reconnect)

### Fix (v1 — GW restart only, confirmed not to work for in-session reconnect)

**File changed:** `Py4GWCoreLib/GlobalCache/SharedMemory.py`

Added `_session_slot_reset_done = False` flag in `__init__`. In `update_callback`, on the first frame where the account has a valid email, reset `HeroAIOptions` and `Inbox` for the account's own slot.

**This fix only helped when GW fully crashed and restarted (new Python process).** For network disconnects where the GW client stays running (Python keeps running), `_session_slot_reset_done` was already `True` from initial startup, so the reset never fired again on reconnect.

### Known API Gotchas — Added

- **HeroAI build matching only reads skill slots 1–5** — required skills placed in slots 6–8 are invisible to the matcher; build falls back to HeroAI default. All required skills must be in the first 5 bar slots.

---

## Session 2026-06-09 — Reconnect follow/combat regression fix (v2)

### Root Cause (extended)

The v1 fix used a one-shot `_session_slot_reset_done` flag that only fires once per Python process lifetime. For in-session reconnects (GW network disconnect + reconnect without restarting GW), Python stays running, the flag stays `True`, and the reset never fires. Additionally, `HealStaleHeroAISnapshot` in `Messaging.py` was missing two recovery paths that were lost in an upstream merge.

### Fixes

**`Py4GWCoreLib/GlobalCache/SharedMemory.py`**

Replaced `_session_slot_reset_done` (one-shot) with `_had_email` (email-transition tracker). The slot reset now fires whenever `Player.GetAccountEmail()` transitions from empty/unavailable to non-empty. This covers:
- GW crash + restart (Python restarts, `_had_email = False`)  
- In-session reconnect where GW goes to login/character-select screen (email goes empty → comes back)

When email is non-empty and `_had_email` was False, the same reset runs: `HeroAIOptions[index].reset()` + `Inbox[index].reset()`. When email goes empty, `_had_email` is cleared so the next reconnect triggers the reset again.

**`Widgets/System/Messaging.py` — `HealStaleHeroAISnapshot`**

Two recovery paths added (previously lost in upstream merge `e30a07bb`):

1. **Ghost-message recovery (Messaging.py reload mid-operation):** When `hero_ai_snapshots` is empty but a suspending message is Active AND options are all disabled — Messaging.py reloaded while a command was running. Clears the stuck message via `MarkMessageAsFinished`, calls `RestoreHeroAISnapshot` (which calls `EnableHeroAIOptions` as fallback), logs a warning.

2. **Stale-message recovery (reconnect without Python restart):** When `hero_ai_snapshots` is non-empty, there IS an active suspending message, but ALL options are disabled AND the message has been `Running=True` for more than 120 seconds — the coroutine is abandoned. Clears the stuck message; the existing restore loop then re-enables options from the snapshot stack. A non-stale active message (< 120s old) is left alone.

| File | Change |
|---|---|
| `Py4GWCoreLib/GlobalCache/SharedMemory.py` | Replaced one-shot `_session_slot_reset_done` with `_had_email` email-transition trigger |
| `Widgets/System/Messaging.py` | Added ghost-message recovery and stale-message (120s timeout) recovery to `HealStaleHeroAISnapshot` |

---

## Session 2026-06-09 — Reconnect follow/combat regression fix (v3)

### Two additional bugs in the v2 fix

**Bug 1 — Wrong Inbox slot cleared**

The v2 fix called `all_accounts.Inbox[account_slot_index].reset()` where `account_slot_index` is the player's slot in `AccountData[]`. But the `Inbox[]` array is a shared pool — `SendMessage` picks the first free slot, completely independent of the receiver's `AccountData` index. The stale message for the reconnecting account could sit in any Inbox slot. Clearing `Inbox[account_slot_index]` almost always clears an unrelated (or already-empty) slot and leaves the actual stale message intact.

**Bug 2 — HWND-fallback email consumes the transition**

`Player.GetAccountEmail()` returns the real email if `Map.IsMapReady()` and `Player.IsPlayerLoaded()` and `GWContext.Char.GetContext()` are all ready. If those checks pass but `player_email_str` is empty or non-ASCII, `_sanitize_account_email_or_fallback` returns `"{hwnd}@Py4GW"` as a fallback.

During the reconnect window there can be a brief frame where `IsMapReady()/IsPlayerLoaded()` flip to True before the account email is populated. In that frame `GetAccountEmail()` returns the HWND fallback — a non-empty string. The v2 code used a boolean `_had_email`, so that first non-empty transition consumed the reset (with `_find_account_slot_by_email("{hwnd}@Py4GW")` returning -1, so nothing was reset). When the real email arrived next frame, `_had_email` was already `True` and the reset never fired.

### Fix

**`Py4GWCoreLib/GlobalCache/SharedMemory.py`**

- Replaced `_had_email: bool` with `_prev_email: str = ""`. The reset now fires whenever the email **changes** to a new non-empty value — tracking the previous raw email string means HWND-fallback → real-email transitions also fire the reset.
- Added a condition: the reset only runs when at least one of `Following` or `Combat` is currently False. This prevents unnecessary inbox clearing on normal map transitions where options are already enabled.
- Fixed the Inbox sweep: instead of clearing `Inbox[account_slot_index]` (wrong slot), the fix now scans all `SHMEM_MAX_PLAYERS` inbox slots and clears any with `Active=True` and `ReceiverEmail == email`.
- Added a `ConsoleLog(Warning)` that fires when the reconnect reset triggers, so the fix is visible in the console.

| File | Change |
|---|---|
| `Py4GWCoreLib/GlobalCache/SharedMemory.py` | `_had_email` → `_prev_email` (string); condition-guarded reset; full inbox scan for correct slot clearing; console log |

---

## Session 2026-05-04 (continued) — Pre_Searing_Healer behaviour updates

### Changes

**`Py4GWCoreLib/Builds/Monk/Mo_Any/Pre_Searing_Healer.py`**

Three separate updates applied this session:

**1. Critical-HP emergency pass (< 50%)**

Added a pre-prot healing pass that fires before Shielding Hands and Reversal of Fortune. When any ally is below 50% HP, Orison of Healing fires immediately (followed by Healing Breeze if Orison is on cooldown). This prevents the prot spells consuming the cast slot while a character is actively dying.

Added `_CRITICAL_THRESHOLD = 0.50` module-level constant.

**2. Out-of-combat healing suppression**

The healer was spending energy healing missing HP out of combat, which delayed the group (waiting on energy regen before re-engaging). HP regenerates naturally out of combat, so active healing is wasteful unless degen is preventing that regen.

New behaviour: outside of combat (`IsInAggro() == False`), the only spell the healer may cast is Healing Breeze — and only on allies with an active bleed, poison, or degen hex who don't already have the buff. All other heals are skipped.

**3. Attack skill reduction — Banish and Symbol of Wrath removed**

Banish and Symbol of Wrath cost significant energy. In pre-searing the healer's energy pool is small, and spending it on offence meant healing spells were delayed or skipped mid-fight.

Removed: Banish, Symbol of Wrath (skill logic, `__init__` ID lookups, `optional_skills` entries, `Utils` import).

Kept: Bane Signet (signet — zero energy cost, fires only after all healing is resolved, dazes an attacking enemy to reduce incoming damage).

### Updated skill priority (Post-session)

**Out of combat:**
1. Resurrection Signet — dead ally in spellcast range
2. Healing Breeze — active degen (bleed/poison/degen hex) only; no other heals

**In combat:**
1. Resurrection Signet — dead ally in spellcast range
2. Critical pass (< 50%) — Orison → Healing Breeze on the most critically injured ally
3. Shielding Hands — lowest-HP ally < 90%, no existing buff
4. Reversal of Fortune — lowest-HP ally < 90%, no existing buff
5. Orison of Healing — lowest-HP ally < 90%
6. Healing Breeze — ally < 90% OR degen active, no existing buff; degen cases sorted first
7. Bane Signet — attacking enemy (signet, zero energy cost)

---

## Session 2026-05-04 (continued) — AoE party spread exploration (no code changes)

### Context

All four party members were hit by the same AoE attack simultaneously. Explored whether the HeroAI can be made to keep characters spread beyond Adjacent range during combat.

### Findings

**Ally repulsion already exists** — `HeroAI/follow/vector_fields.py` implements a vector field system with ally repulsion and enemy repulsion. When `Avoidance` is enabled and `party_in_aggro == True`, `follower_runtime.py` calls `compute_mixed_follow_target()` which pushes each character away from nearby allies and enemies.

**Why it isn't working well enough — two root causes:**

1. **Combat follow threshold vs. repulsion radius mismatch:** The combat follow threshold defaults to `Range.Touch = 144 units` (`follow_move_threshold_combat` in `ui_base.py`). The ally repulsion radius defaults to `Range.Adjacent = 166 units` (`vector_fields.py`). The 22-unit gap means two characters sharing the same slot position don't repel hard enough to push apart cleanly — the tolerance window nearly swallows the repulsion range.

2. **Melee characters are fully exempt from combat movement:** `follower_runtime.py:154` returns `FAILURE` immediately for any melee weapon type (`Axe`, `Hammer`, `Daggers`, `Scythe`, `Sword`) during combat. They park on their follow slot and never spread, regardless of ally proximity.

### Tuning options (no code changes required for non-melee)

All of these are INI-tunable via the Follow settings window or `FollowRuntime.ini`:

| Setting | Current default | Suggested direction | Effect |
|---|---|---|---|
| `ally_repulsion_radius` | 166 (Adjacent) | Raise to 252 (Nearby) or higher | Widens the bubble within which ally repulsion activates |
| `ally_repulsion_weight` | 0.65 | Raise toward 1.0 | Stronger push when allies are within the repulsion radius |
| `follow_move_threshold_combat` | 144 (Touch) | Lower to 0–50 | Characters re-position more aggressively to hit their slot |

### What would require a code change

- **Melee characters spreading in combat** — the `if party_in_aggro and is_melee: return FAILURE` early exit in `follower_runtime.py:154` would need to be relaxed or conditioned differently (e.g., only exempt if not overlapping an ally).

### Status

Exploration only — no changes made. To be revisited when ready to implement.

---

## Session 2026-05-06 — Ele/Mo Healer build

### Feature

New Elementalist/Monk dedicated healer build using Aura of Restoration for energy sustain plus a prot/heal mix from the Monk secondary.

### Build File — Created

| File | Description |
|---|---|
| `Py4GWCoreLib/Builds/Elementalist/E_Mo/Ele_Healer.py` | E/Mo healer. All 6 required. Priority: Aura of Restoration (always) → RoF (85%) → Shielding Hands (85%) → Orison (75%) → Healing Breeze (75%) → Flare. |

### Skill priority in `_run_local_skill_logic`

1. **Aura of Restoration** — self-buff from EnergyStorage, applied before aggro check so it's always active
2. InAggro gate + `UpdatePartyHealthMonitor`
3. **Reversal of Fortune** — 0.25s activation, cast on any ally below 85% HP who doesn't already have it
4. **Shielding Hands** — cast on lowest-HP ally below 85% HP without existing buff
5. **Orison of Healing** — heals lowest-HP ally below 75%
6. **Healing Breeze** — regen enchantment with bleed/poison/degen-hex priority; includes shared-memory duplicate-cast guard
7. **Flare** — damage filler when party is stable

**Out-of-combat behaviour:** only Healing Breeze is allowed, and only on allies with an active bleed, poison, or degen hex (`Healing_Breeze(0.0)` — health-threshold path suppressed). All other heals are skipped; HP recovers naturally between fights.

---

## Session 2026-05-07 — Upstream merge conflict resolution, engagement range, Healing Breeze fixes

### Merge Conflict Resolution

Synced 44 upstream commits from origin/main. Two files had real conflicts that required manual resolution:

| File | Resolution |
|---|---|
| `HeroAI/headless_tree.py` | Kept our additive `_finish_active_pick_up_loot_message` method; upstream had only removed whitespace |
| `Py4GWCoreLib/Builds/Skills/Monk/SmitingPrayers.py` | Kept our `Symbol_of_Wrath` insertion AND upstream's updated `Smite_Hex(min_priority: int = HexRemovalPriority.LOW)` signature |

### Feature — `danger_range` parameter for `auto_path` steps

Added a `danger_range` parameter that temporarily overrides the `pause_on_danger_fn` used during path movement, controlling at what range the bot pauses to engage enemies.

**Why it works:** `pause_on_danger_fn` is captured fresh per waypoint inside `_coro_xy`. Overriding it once before the path starts applies the new range to every group encountered along the entire route — no per-group coordinates needed.

| File | Change |
|---|---|
| `Py4GWCoreLib/routines_src/behaviourtrees_src/botting_pathing.py` | Added `danger_range: float \| None` param to `add_auto_path_state`. Wraps path execution with Set/Restore Danger Range states that call `cfg._set_pause_on_danger_fn` / `cfg._reset_pause_on_danger_fn` |
| `Py4GWCoreLib/routines_src/behaviourtrees_src/modular_core/actions_movement_pathing.py` | Parses `danger_range` from step JSON and passes it through to `add_auto_path_state` |
| `Py4GWCoreLib/routines_src/behaviourtrees_src/modular_core/actions_movement.py` | Added `"danger_range"` to `allowed_params` for `auto_path` step type |
| `Sources/modular_data/dungeons/scourge_beneath.json` | Added `"danger_range": 1248` to 5 enemy-encounter paths (Spellcast = 1248 units) |

### Bug Fix — Ele/Mo Healer: Healing Breeze threshold and ordering

Two problems in `Ele_Healer.py`:

1. **Out-of-combat:** `Healing_Breeze(0.0)` suppressed the health threshold, so HB only fired for degen (bleed/poison/hex), never for low health. Fixed to `Healing_Breeze(0.60)`.
2. **In-combat ordering:** `Orison_of_Healing(0.75)` was evaluated before `Healing_Breeze(0.60)`, so Orison would fire first and return `True`, blocking HB from ever being evaluated. Fixed by moving HB before Orison in the priority list.

**File changed:** `Py4GWCoreLib/Builds/Elementalist/E_Mo/Ele_Healer.py`

### Bug Fix — Healing Breeze re-cast while buff already active

**Problem:** After applying Healing Breeze, the build would keep re-casting it every few seconds for the full duration of poison/bleed, even though the buff was already active.

**Root cause:** `_needs_breeze` used `Routines.Checks.Effects.HasBuff(agent_id, healing_breeze_id)` to gate re-casts. `Checks.Effects.HasBuff` calls `PyEffects.PyEffects(agent_id).GetBuffs()` — reading local game memory. In a multibox party, the local game client cannot see buffs on agents controlled by other game instances. The check always returned `False` for non-local party members.

**Fix:** Changed to `Routines.Checks.Agents.HasEffect(agent_id, healing_breeze_id)`, which first checks `shared_agent_data.Buffs.Buffs` from cross-account SharedMemory (data each client broadcasts about itself), then falls back to the local `PyEffects` path. The SharedMemory path correctly sees the buff on non-local party members.

**File changed:** `Py4GWCoreLib/Builds/Skills/Monk/HealingPrayers.py` (`_needs_breeze` inner function)

---

## Session 2026-05-15 — Smiting_Monk build removed

### Build Files — Deleted

| File | Reason |
|---|---|
| `Py4GWCoreLib/Builds/Monk/Mo_Any/Smiting_Monk.py` | Crashed every frame: called `self.skills.Any.NoAttribute.Resurrection_Signet()` but `Resurrection_Signet` was never implemented in `any/NoAttribute.py`. 496 identical `AttributeError` stack traces per log session. |

### Loot Manager — Trophies enabled

**File changed:** `Widgets/Config/loot_config.json`

Set `enabled: true` on all 244 Trophy-group items (was 2/244 enabled).

---

## 2026-05-18 — Voltaic Spear Farm Bot

### New Files — Created

| File | Description |
|---|---|
|  | New dungeon farm bot targeting Justicar Thommis' room in Slaver's Exile for the Voltaic Spear drop |

### Summary

Translated the existing AutoIt  farm into the Py4GW / widget pattern, following the same structure as the existing  and  dungeon bots in the same folder.

**Route:**
1. Travel to Umbral Grotto (map 639), form party
2. Exit into Verdant Cascades (map 566), fight through two combat sections to the Troll Bridge
3. Enter Slaver's Exile (map 620), navigate through the entrance area into the Justicar wing
4. Get Dwarven Blessing (dialog 0x84) from the shrine NPC
5. Fight through six group zones to the boss area
6. Interact with the Justicar Thommis chest (gadget ID 9284), rely on auto-loot upkeeper for item pickup
7. Return to Umbral Grotto and loop

**Features:**
- Normal/Hard Mode toggle (INI-persisted)
- Random EU district rotation
- Run timing (current, average, best, worst)
- Secure-return anchors per fight zone for wipe recovery
- Multibox party summon/invite on startup
- Statistics tab in the bot UI window

---

## Session 2026-05-29 — Defensive Refrain paragon: full refrain chain

### Feature

Added `Mending_Refrain`, `Bladeturn_Refrain`, and `Burning_Refrain` support to the Defensive Refrain build, and changed `Hasty_Refrain` from combat-only to always-on. All four refrains now follow the same sequential chain behaviour as `Heroic_Refrain`: applied to the paragon and every party member in and out of combat, with each refrain only starting after the previous one is fully applied to everyone.

### Priority order (all run before the `IsInAggro()` gate)

1. `Heroic_Refrain` — existing; cycles through self + all allies
2. `Mending_Refrain` — starts only when all party members have HR
3. `Bladeturn_Refrain` — starts only when all party members have MR (or MR not equipped)
4. `Burning_Refrain` — starts only when all party members have BT (or BT not equipped)
5. `Hasty_Refrain` — starts only when all party members have BR (or BR not equipped); moved out of the aggro-only section

### Files changed

| File | Change |
|---|---|
| `Py4GWCoreLib/Builds/Skills/paragon/Leadership.py` | Added `Burning_Refrain()` — self-check then `ResolveAllyTarget` |
| `Py4GWCoreLib/Builds/Skills/paragon/Command.py` | Added `Bladeturn_Refrain()` — same pattern |
| `Py4GWCoreLib/Builds/Skills/paragon/Motivation.py` | Added `Mending_Refrain()`; updated `Hasty_Refrain()` to cast on self first before targeting allies. Added `Player`, `Routines` imports. |
| `Py4GWCoreLib/Builds/Paragon/P_W/Defensive Refrain.py` | Added `Mending_Refrain_ID`, `Bladeturn_Refrain_ID`, `Burning_Refrain_ID` constants + optional_skills entries. Added `_all_party_have_effect()` and `_refrain_chain_done()` helper methods. Moved all four refrains before `IsInAggro()` gate with chain gating via `_refrain_chain_done`. Removed Hasty_Refrain from the combat-only section. |

### Design notes

- `_all_party_have_effect(skill_id)`: checks player has effect via `Routines.Checks.Agents.HasEffect`, then checks no ally without it via `TargetLowestAlly(filter_skill_id=skill_id)`.
- `_refrain_chain_done(*prereq_ids)`: iterates `prereq_ids` in reverse, returns `_all_party_have_effect` of the last equipped prereq; returns `True` if none equipped.
- If any skill in the chain is not equipped (e.g. no Mending Refrain on bar), the chain skips it and gates on the previous equipped refrain instead.

---

## Session 2026-05-29 (continued) — R/W Flail Turret build

### Feature

New Ranger/Warrior Flail Turret build (`Py4GWCoreLib/Builds/Ranger/R_W/Flail_Turret.py`). Pet-based adrenaline turret: the pet's auto-attacks charge adrenaline, which is spent on Together as One (party heal/energy), Save Yourselves (party +100 armour), and Flail (IAS stance).

### Build File — Created

| File | Description |
|---|---|
| `Py4GWCoreLib/Builds/Ranger/R_W/Flail_Turret.py` | R/W pet adrenaline turret. Template: `OgESc5MTwgMG7WqG8VwGj1xgA` |

### Skill priority

**Out of combat:**
1. Comfort Animal — pet revive/heal (< 30% HP)
2. Troll Unguent — self-heal when < 90% HP and not already active

**In combat (after `IsInAggro` gate):**
3. Together as One — fires when adrenaline charged (party heal + energy)
4. Save Yourselves luxon / kurzick — fires when adrenaline charged (party +100 armour)
5. Enraging Charge — +4 adrenaline + speed; keeps the adrenaline cycle running
6. Flail — IAS stance; only fires when TaO and SY **both** lack enough adrenaline (checked via `CanCastSkillID`), preventing Flail from draining the adrenaline those skills need
7. Healing Signet — emergency self-heal when < 60% HP and not moving

### Required / Optional skills

| Bucket | Skills |
|---|---|
| Required | Together as One, Flail |
| Optional | Save Yourselves (luxon), Save Yourselves (kurzick), Enraging Charge, Comfort Animal, Charm Animal, Troll Unguent, Healing Signet |

Save Yourselves in both faction variants is optional (not required) so the build matches regardless of which faction allegiance the character has.

### Design notes

- All skill IDs set in `__init__` as `self.X_ID` (not module-level) — per CHANGES.md gotcha about `BuildRegistry._scan_build_types()`.
- `CanCastSkillID` check before Flail: prevents the stance from dumping all adrenaline when TaO or SY are one hit away from firing.

### Revision — correct skill list applied

Updated `Flail_Turret.py` with the correct skill set after user provided the full wiki skill list. Removed guessed optional skills (Enraging Charge, Comfort Animal, Charm Animal, Troll Unguent, Healing Signet). Promoted Save Yourselves to `required_skills` (both faction variants); set `minimum_required_match = len(required_skills) - 1` so the build matches with either the Luxon or Kurzick variant. Replaced all optional skills with the correct wiki set.

| Bucket | Skills |
|---|---|
| Required | Together as One, Flail, Save Yourselves (luxon), Save Yourselves (kurzick) — 3-of-4 match |
| Optional | Triple Shot (kurzick), Triple Shot (luxon), Dual Shot, Arcing Shot, Saving Shot, Read the Wind, Expert Focus, Penetrating Attack |

**Skill priority in `_run_local_skill_logic`:**

Out of combat:
1. Read the Wind / Expert Focus — maintain whichever prep is equipped (prefer Read the Wind; mutually exclusive)

In combat:
2. Together as One — party heal + energy (adrenaline shout)
3. Save Yourselves — party +100 armour (adrenaline shout)
4. Triple Shot kurzick / luxon — 3 arrows, maximum adrenaline generation
5. Dual Shot — 2 arrows
6. Penetrating Attack — armor-penetrating shot
7. Arcing Shot — conditional knockdown shot
8. Saving Shot — 2 arrows + adjacent party armor boost (ends current preparation)
9. Flail — IAS stance; only when neither TaO nor SY has enough adrenaline

---

## Session 2026-05-30 — R/Rt Splinter Turret build

### Feature

New Ranger/Ritualist Splinter Turret build (`Py4GWCoreLib/Builds/Ranger/R_Rt/Splinter_Turret.py`). Archer adrenaline turret with Splinter Weapon (Channeling Magic) maintained on self: each auto-attack burst triggers AoE lightning damage on up to 3 hits.

### Build File — Created

| File | Description |
|---|---|
| `Py4GWCoreLib/Builds/Ranger/R_Rt/Splinter_Turret.py` | R/Rt Splinter Weapon turret. Template code not yet assigned. |

### Required / Optional skills

| Bucket | Skills |
|---|---|
| Required | Together as One, Splinter Weapon, Save Yourselves (luxon), Save Yourselves (kurzick) — 3-of-4 match |
| Optional | Triple Shot (kurzick), Triple Shot (luxon), Dual Shot, Arcing Shot, Saving Shot, Read the Wind, Expert Focus, Penetrating Attack |

### Skill priority in `_run_local_skill_logic`

**Out of combat:**
1. Read the Wind / Expert Focus — maintain whichever prep is equipped (prefer Read the Wind)

**In combat (after `IsInAggro` gate):**
2. Together as One — party heal + energy (adrenaline shout)
3. Save Yourselves luxon / kurzick — party +100 armour (adrenaline shout)
4. Splinter Weapon — cast on self (`target_agent_id=player_agent_id`) whenever the weapon-spell buff is not active; recasts immediately each time the 3-hit charge is consumed
5. Triple Shot kurzick / luxon — 3 arrows, maximum adrenaline generation
6. Dual Shot — 2 arrows
7. Penetrating Attack — armor-penetrating shot
8. Arcing Shot — conditional knockdown shot
9. Saving Shot — 2 arrows + adjacent party armor boost (ends current preparation)

### Design notes

- `Splinter_Weapon_ID` stored as `self.Splinter_Weapon_ID` in `__init__` (not module-level) — per CHANGES.md gotcha about `BuildRegistry._scan_build_types()`.
- Splinter Weapon is cast with explicit `target_agent_id=player_agent_id` to guarantee it always lands on self, never on the current enemy target.
- No Flail-style adrenaline gate needed: Splinter Weapon has no adrenaline interaction and should be spammed unconditionally whenever its buff is absent.

### Revision — SY removed, Volley added, TaO comment fixed

- **Removed** Save Yourselves (luxon + kurzick) from required and optional skills — SY requires Warrior as primary or secondary; R/Rt cannot run it.
- **Added** Volley as the third required skill. Volley fires 5 arrows in a cone; each arrow independently triggers Splinter Weapon's chain lightning, multiplying damage output. Volley is the primary spam attack in the rotation.
- **Removed** `minimum_required_match` override — no longer needed without the SY faction split.
- **Fixed** wrong comment on TaO: TaO has a straight recharge (not adrenaline); `CastSkillID`/`CanCastSkillID` already handles the cooldown gate correctly.

---

## Session 2026-05-31 — Sunspear title bot: skip account isolation in multibox mode

### Bug Fix

**File changed:** `Widgets/Automation/Bots/Farmers/Titles/Sunspear title farm.py`

**Problem:** When multibox mode was enabled (`_party_mode == 1`), `ConfigureAggressiveEnv` called `bot.Templates.Aggressive()` with the default `account_isolation=True`, which added a `SetAccountIsolation(True)` FSM step. This broke multibox operation by isolating shared-memory state between accounts.

**Root cause:** `Templates.Aggressive()` defaults to `account_isolation=True` for single-account hero use. The Sunspear bot's `ConfigureAggressiveEnv` always called it with no arguments, so the setting was applied unconditionally regardless of party mode.

**Fix (revised):** Changed `ConfigureAggressiveEnv` to branch on `_party_mode`: calls `bot.Templates.Multibox_Aggressive()` when multibox is active (which sets `SetAccountIsolation(False)`) and `bot.Templates.Aggressive()` otherwise (which sets `SetAccountIsolation(True)`). This matches the pattern used by the Vanguard title bot. An earlier attempt passed `account_isolation=(_party_mode == 0)` to `Aggressive()`, but `_party_mode` is evaluated at `bot_routine` setup time before the INI is loaded via `_draw_settings`, so it always resolved to `True`.

### Bug Fix 3 — Bounty blessing not broadcast to other accounts in multibox mode

**File changed:** `Widgets/Automation/Bots/Farmers/Titles/Sunspear title farm.py`

**Problem:** In multibox mode the bounty NPC dialog was only taken by the leader; other accounts did not receive the broadcast.

**Root cause:** `_do_bounty_interaction` is a custom state that reads `_party_mode` at FSM execution time. `_party_mode` defaults to `0` and is only loaded from INI inside `_draw_settings`, which is called when the Config tab is rendered. If the user never opened the Config tab before the bounty step executed (e.g. the Statistics or Heroes tab was open instead), `_party_mode` remained `0` and the single-account path ran instead of the multibox broadcast path.

**Fix:** Added `_ensure_mode_loaded(bot)` helper (same pattern as the Norn title bot) that loads `_party_mode` from INI exactly once. Called at the top of `bot_routine` so the mode is guaranteed correct before any states are configured or executed, regardless of whether the Config tab has been rendered. Updated `_draw_settings` to use `_ensure_mode_loaded` instead of the previous inline guard.

### Bug Fix 2 — Multibox party not re-invited after resign loop

**Problem:** After each resign the bot jumped to `LOOP_STEP_NAME`, which pointed at the second header (`BotSettings.BOT_NAME_loop`). The "Setup Heroes" custom state (summon + invite all accounts) lives before that header, so it was skipped on every subsequent loop iteration. Other accounts were never re-invited after the first run.

**Root cause:** `LOOP_STEP_NAME` was computed immediately before the second header (`_next_header_step_name(bot, f"{BotSettings.BOT_NAME}_loop")`), placing the loop entry point after the party setup step. The Vanguard title bot avoids this by jumping all the way back to its first header, which re-runs `_maybe_setup_heroes` every loop.

**Fix (revised):** Restored `LOOP_STEP_NAME` to capture the second header (the combat loop). Added a new `_maybe_invite_for_loop` custom state at the top of the combat loop that waits 3 s then calls `_invite_all_accounts` in multibox mode (no-op in single-account mode). The one-time startup sequence (travel, summon+invite, hard mode, resign-setup exit/enter) remains under the first header and only runs on initial startup. Subsequent loop iterations jump straight to the combat header, re-invite alts, restock, and fight.

---

## Session 2026-06-05 — Comfort Animal bug fix + ESurge Air of Superiority optional

### Bug Fix — Tao Bow Spam: Comfort Animal casting on cooldown

**File changed:** `Py4GWCoreLib/Builds/Ranger/R_W/Tao_Bow_Spam.py`

**Problem:** Comfort Animal was gated only on `self.CanCastSkillID`, meaning it fired every time the cooldown expired regardless of pet health. This produced constant spurious casts interrupting the attack rotation.

**Root cause:** Incorrect condition — `CanCastSkillID` checks cooldown only, not whether the pet actually needs healing or resurrection.

**Fix:** Added a pet health check matching the `Tao_Dagger_Spam` pattern. Now casts only when `Party.Pets.GetPetID` returns a valid ID and the pet is either dead (`not Agent.IsAlive`) or below 30% health (`Agent.GetHealth < 0.30`). Added `Party` to the import line.

### Bug Fix — Paragon Refrains: casting on pets

**Files changed:** `Py4GWCoreLib/Builds/Skills/paragon/Leadership.py`, `Py4GWCoreLib/Builds/Skills/paragon/Motivation.py`

**Problem:** `Heroic_Refrain`, `Blazing_Finale`, and `Hasty_Refrain` were casting on animal companion pets. The pet appeared as the lowest-HP "ally" and won target selection.

**Root cause:** `ResolveAllyTarget` → `TargetLowestAlly` manually merges `AgentArray.GetSpiritPetArray()` (filtered to pets only, non-spirits) into the ally array, then sorts by HP. If a pet is the lowest-HP agent, it wins before any real party member is considered. `TargetAllyByPredicate` (a different targeting path) already excludes spirit/pet agents by default via an explicit filter, but `TargetLowestAlly` does not use it.

**Fix:** After `ResolveAllyTarget` returns a target, check `Agent.IsPet(target_agent_id)`. If true, retry with `TargetAllyByPredicate(filter_skill_id=...)` which excludes pets by default. Same inline guard applied to all three affected methods.

### Change — ESurge Mesmer: Air of Superiority moved to optional

**File changed:** `Py4GWCoreLib/Builds/Mesmer/Me_Any/Energy Surge.py`

**Problem:** `Air_of_Superiority_ID` was in `required_skills`, so the build would only match bars that include it. Users running the ESurge bar without Air of Superiority would fall through to HeroAI default.

**Fix:** Moved `Air_of_Superiority_ID` from `required_skills` to `optional_skills`. Added `self.IsSkillEquipped(Air_of_Superiority_ID)` guard in `_run_local_skill_logic` so the skill is still used when equipped but the build matches without it.

---

## Session 2026-06-09 — Reconnect follow/combat regression fix (v3) + Drazach Thicket Redux

### Bug Fix — Follower reconnect: Following/Combat stay False after reconnect (v3)

**File changed:** `Py4GWCoreLib/GlobalCache/SharedMemory.py`

**Root cause (two bugs in v2):**

1. **Wrong inbox slot index.** `all_accounts.Inbox[account_slot_index].reset()` used the account's slot index, but `Inbox` is a free-pool — `SendMessage` picks any free slot, not the receiver's account-slot index. This cleared the wrong (usually empty) slot, leaving the stale command message active.

2. **HWND fallback consumes the email transition.** `_had_email: bool` was `True/False`. During reconnect, `Player.GetAccountEmail()` briefly returns `"{hwnd}@Py4GW"` (a non-empty HWND-fallback string) before the real email is populated. This truthy value caused the `False→True` transition to fire early on the HWND string. When the real email arrived, `_had_email` was already `True` → reset never fired.

**Fix:**
- Changed `self._had_email = False` → `self._prev_email = ""` (tracks actual previous email value, not a boolean).
- HWND fallback → real email is a distinct string change (`prev != email`) so the reset fires correctly. If `_find_account_slot_by_email(hwnd_string)` returns -1 the reset is skipped harmlessly.
- Fixed inbox clearing: scan all `SHMEM_MAX_PLAYERS` inbox slots and clear any where `msg.Active and msg.ReceiverEmail == email`.
- Added a `ConsoleLog` warning on reconnect detection to aid debugging.

### New File — VQ Drazach Thicket Redux

**File created:** `Widgets/Automation/Bots/Vanquish/Factions/Echovald Forest/Drazach Thicket Redux.py`

Converted `Drazach Thicket.py` (old `Botting`-class pattern) into the `BottingTree` / `ApoBottingLib.wrappers` pattern matching `VQ Mount Quinkai Redux.py`.

| Section | Detail |
|---|---|
| Map IDs | Inline constants: `ARBORSTONE_OUTPOST=222`, `DRAZACH_THICKET=195`, `HOUSE_ZU_HELZER=77` |
| `InitializeBot` | Travel to Arborstone (hard mode), create party (multibox invite), exit to Drazach Thicket |
| `Killroute` | Kurzick blessing at priest coords, 59-waypoint `VanquishNode`, resign back to Arborstone |
| `DonateFaction` | Kurzick faction donation at House zu Helzer, threshold 20 000 |

---

## Session 2026-06-11 — Tunnels of the Forsaken Farm Bot

### New File — Created

| File | Description |
|---|---|
| `Widgets/Automation/Bots/Missions/Dungeons/Tunnels of the Forsaken.py` | Multi-floor dungeon farm bot. Translates `TunnelsOfTheForsaken.au3` into the `BottingTree` / `ApoBottingLib.wrappers` pattern. |

### Route — 5 execution steps

| Step | Detail |
|---|---|
| `InitializeBot` | Travel to Piken Square (random district, hard mode), create party, abandon "The Dreamer and the Zealot" quest (safety reset) |
| `TheBreachApproach` | Walk through Piken Square to portal, 4-point `VanquishNode` through The Breach, enter Tunnels Level 1 |
| `Floor1` | Clear 3 groups → take quest (dialog `0x85B501`) → clear pts 4-6 with `LootItems` after each (Elemental Keystones) → clear pt 7 → exit to Floor 2 |
| `Floor2` | 14-waypoint `VanquishNode` (pts 8/9/10 at `Range.Nearby`) → exit to Floor 3 |
| `Floor3` | Clear beacon section + loot → open dungeon door (`MoveAndInteractWithGadget`) → clear to end → quest reward (dialog `0x85B507`) → open chest → loot |

### TODOs

- `TUNNELS_LVL_1/2/3` map IDs use placeholder values 877/878/879 — verify in-game via `Map.GetMapID()`
- `DREAMER_AND_ZEALOT_QUEST_ID` uses placeholder `0` — verify in-game; `_abandon_quest_node` silently no-ops when `0`


---

## 2026-06-15 — Tunnels of the Forsaken: fix followers not opening chest

### Bug Fixes

**`Widgets/Automation/Bots/Missions/Dungeons/Tunnels of the Forsaken.py`**

| Change | Detail |
|---|---|
| `_open_chest_sequential_node()` — phase 1: switch `OpenChest` → `InteractWithTarget` | `SharedCommandType.OpenChest` bails immediately when no lockpick is present. The TOTF dungeon chest needs no lockpick; followers just need to walk up and interact. Replaced with `SharedCommandType.InteractWithTarget`. |
| `_open_chest_sequential_node()` — phase 2: broadcast → sequential state machine | Sending to all followers simultaneously caused them to open the chest at the same time. Replaced with a 5-phase `WaitUntilNode` state machine (`init → wait_init → send → wait_active → wait_buffer`) that sends `InteractWithTarget` to one follower at a time in party-position order. Polls `GetAllMessages()` for `Active=False` to detect completion (1.5 s min-delivery guard + 3 s buffer before advancing). Timeout raised to 120 s. |
| `_open_chest_sequential_node()` — rewrite: drop message-polling, fix fall-through | Phase-polling via `_is_interact_active` was unreliable (`GetAllMessages` from the leader context may not expose follower inboxes, making the check immediately False). The whole `if`/`if`/`if` fall-through chain (init→wait_init→send within a single call) also caused unpredictable cascades. Replaced with a 4-phase explicit-return state machine: `init` (capture chest_id, build sorted follower list) → `wait_init` (2 s initial gap after leader opens) → `send` (dispatch InteractWithTarget, increment idx) → `wait_between` (10 s per-follower budget). Every phase has an explicit `return` — no fall-through. |
| `_follower_npc_dialog_node` — reduce wait from 8 s to 2 s per follower | The default `per_account_wait_ms=8000` produced ~20 s total wait for quest accept/reward dialogs. Reduced to `2000` (4 s total for 2 followers). |

---

## 2026-06-14 — Tunnels of the Forsaken: resign + multi-account dialogs + sequential chest

### Bug Fixes

**`Widgets/Automation/Bots/Missions/Dungeons/Tunnels of the Forsaken.py`**

| Change | Detail |
|---|---|
| Quest accept — `multi_account=True` | `BT.MoveAndDialog(QUEST_ACCEPT_DIALOG)` now broadcasts the accept dialog to all accounts so every party member receives the quest |
| Quest reward — `multi_account=True` | `BT.MoveAndDialog(QUEST_REWARD_DIALOG)` now broadcasts the hand-in dialog to all accounts |
| Resign after loot | Added `BT.Resign(wait_for_map_load=True, target_map_id=PIKEN_SQUARE, multi_account=True)` at the end of Floor 3 so the whole party returns to Piken Square and the loop restarts cleanly |
| Sequential chest opening — `_open_chest_sequential_node()` | After the leader opens the chest via `MoveAndInteractWithGadget`, a new `WaitUntilNode` fires `SharedCommandType.OpenChest` with `cascade=1` to the follower account at the lowest party position. The built-in cascade in `Messaging.py` then passes the command to each subsequent party member in order, ensuring no two accounts interact with the chest simultaneously. Waits `max(3 s, num_followers × 5 s)` before proceeding. |
| Hard Mode settings checkbox | Added `_use_hard_mode: bool` (default `True`) persisted to the bot's INI under `[Settings] use_hard_mode`. A **Bot Config** tab is added to the BottingTree window via `extra_tabs=[('Bot Config', _draw_bot_config)]` with a single `PyImGui.checkbox('Hard Mode', ...)`. `InitializeBot` now reads `_use_hard_mode` instead of the hardcoded `hard_mode=True`. |

---

## 2026-06-13 — SoS Healer build (Rt/Any)

### New Files — Created

| File | Description |
|---|---|
| `Py4GWCoreLib/Builds/Ritualist/Rt_Any/SoS_Healer.py` | Rt/Any hybrid SoS spirit summoner + healer. Required: Signet of Spirits, Bloodsong, Spirit Transfer. Optional: Mend Body and Soul, Spirit Light, Spirit Siphon, Weapon of Shadow, Death Pact Signet, EVAS, Great Dwarf Weapon, Technobabble. |

### Skill Layer — New Methods

| File | Methods Added |
|---|---|
| `Py4GWCoreLib/Builds/Skills/ritualist/RestorationMagic.py` | `Death_Pact_Signet` — finds nearest dead ally in spellcast range; skips if caster already under a death pact |
| `Py4GWCoreLib/Builds/Skills/ritualist/RestorationMagic.py` | `Weapon_of_Shadow` — weapon spell cast via `TargetAllyWeaponSpell` (same pattern as `Xinraes_Weapon`) |

### Skill priority in `_run_local_skill_logic`

**Always (regardless of aggro):**
1. Spirit Transfer — emergency at < 30% HP (requires spirit in spellcast range)
2. Spirit Light — emergency at < 30% HP
3. Mend Body and Soul — emergency at < 40% HP
4. Spirit Siphon — emergency energy refill at < 30% energy

**Out of combat only:** Death Pact Signet (rez dead allies), then return

**In combat / close to aggro:**
5. EVAS — PvE offensive support
6. Technobabble — PvE AoE interrupt
7. Great Dwarf Weapon — weapon spell on party martials
8. Signet of Spirits — recast when < 2 SoS spirits alive
9. Bloodsong — recast when no owned Bloodsong spirit
10. Weapon of Shadow — weapon spell on ally without active weapon spell
11. Spirit Siphon — opportunistic energy refill at < 70% energy
12. Spirit Light — normal tier at < 75% HP
13. Spirit Transfer — normal tier (default threshold)
14. Mend Body and Soul — normal tier at < 75% HP
15. Death Pact Signet — rez dead ally as last resort

---

## 2026-06-12 — VanquishNode step logging

### Modified Files

| File | Changes |
|---|---|
| `Sources/ApoSource/ApoBottingLib/wrappers.py` | Added `log: bool = False` parameter to `VanquishNode`; when enabled, wraps each step in an inline sequence with a `LogMessage` showing `Step N/Total: moving to (x, y)` before the `MoveAndKill` node |
| `Widgets/Automation/Bots/Vanquish/Factions/Echovald Forest/Drazach Thicket Redux.py` | Enabled `log=True` on `VanquishNode` call |

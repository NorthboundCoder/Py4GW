from __future__ import annotations

from typing import Callable

from Py4GWCoreLib.BottingTree import BottingTree
from Py4GWCoreLib.IniManager import IniManager

from Py4GWCoreLib.py4gwcorelib_src.BehaviorTree import BehaviorTree
from Py4GWCoreLib.routines_src.behaviourtrees_src.constants.lists import *
from Py4GWCoreLib.routines_src.behaviourtrees_src.constants import *
from Py4GWCoreLib.routines_src.BehaviourTrees import BT as RoutinesBT
from Sources.ApoSource.ApoBottingLib import wrappers as BT
from Py4GWCoreLib.enums import Range

MODULE_NAME = 'Tunnels of the Forsaken Farm'
INI_PATH = 'Widgets/Automation/Bots/Tunnels of the Forsaken Farm'
INI_FILENAME = 'Tunnels_of_the_Forsaken_Farm.ini'

# ── Map IDs ──────────────────────────────────────────────────────────────────
PIKEN_SQUARE = 40
THE_BREACH   = 102
TUNNELS_LVL_1 = 880
TUNNELS_LVL_2 = 881
TUNNELS_LVL_3 = 882

# ── Quest / Dialog IDs ────────────────────────────────────────────────────────
DREAMER_AND_ZEALOT_QUEST_ID = 1461
QUEST_ACCEPT_DIALOG         = 0x85B501
QUEST_REWARD_DIALOG         = 0x85B507

# ── Important interaction positions ─────────────────────────────────────────
QUEST_NPC_POS               = (-7400., -9462.)
QUEST_REWARD_NPC_POS        = (-16098., -8626.)
DUNGEON_CHEST_POS           = (-16066., -8370.)

# ── Aggro range ($RANGE_SPELLCAST + 100 from AutoIt) ─────────────────────────
TUNNELS_AGGRO_RANGE = Range.Spellcast.value + 100.0

initialized = False
ini_key     = ''
botting_tree: BottingTree | None = None

# ── Bot settings (persisted to INI) ──────────────────────────────────────────
_SETTINGS_SECTION = 'Settings'
_use_hard_mode: bool = True


def _load_settings() -> None:
    global _use_hard_mode
    if not ini_key:
        return
    _use_hard_mode = IniManager().read_bool(ini_key, _SETTINGS_SECTION, 'use_hard_mode', True)


def _save_settings() -> None:
    if not ini_key:
        return
    IniManager().write_key(ini_key, _SETTINGS_SECTION, 'use_hard_mode', str(_use_hard_mode))


def _draw_bot_config() -> None:
    import PyImGui
    global _use_hard_mode
    new_hm = PyImGui.checkbox('Hard Mode', _use_hard_mode)
    if new_hm != _use_hard_mode:
        _use_hard_mode = new_hm
        _save_settings()


def _draw_help_page() -> None:
    import PyImGui
    PyImGui.text('Tunnels of the Forsaken Farm')
    PyImGui.separator()
    PyImGui.text('Requirements')
    PyImGui.separator()
    PyImGui.text('- Multi-account bot: requires at least one follower account.')
    PyImGui.text('- Althea the Healer must have been unlocked in a previous run.')
    PyImGui.text('- No consumables required.')
    PyImGui.text('- Hard Mode toggle available in the Bot Config tab.')
    PyImGui.separator()
    PyImGui.text('Tested Setup')
    PyImGui.separator()
    PyImGui.text('- Tested in Normal Mode only.')
    PyImGui.text('- Tested with: TaO Ranger, Panic Mesmer, Inept Mesmer, SoS Healer.')
    PyImGui.separator()
    PyImGui.text('Route')
    PyImGui.separator()
    PyImGui.text('- Travels to Piken Square, enters The Breach, then clears all 3 floors.')
    PyImGui.text('- Accepts and rewards The Dreamer and the Zealot quest automatically.')
    PyImGui.text('- Abandons and re-takes the quest at the start of each run.')


def ensure_botting_tree() -> BottingTree:
    global botting_tree

    if botting_tree is None:
        botting_tree = BottingTree.Create(
            MODULE_NAME,
            main_routine=get_execution_steps(),
            routine_name='MultiAccountSequence',
            repeat=True,
            multi_account=True,
            configure_fn=lambda tree: tree.Config.ConfigureUpkeep(
                consumable_upkeeps=CONSUMABLE_UPKEEPS,
            ),
        )
        botting_tree.UI.override_draw_help(_draw_help_page)

    return botting_tree


def _abandon_quest_node() -> BehaviorTree:
    """Abandon the Dreamer and the Zealot quest so it can be re-taken next loop.
    Skips silently if DREAMER_AND_ZEALOT_QUEST_ID has not been filled in yet."""
    def _action() -> BehaviorTree.NodeState:
        if DREAMER_AND_ZEALOT_QUEST_ID > 0:
            from Py4GWCoreLib.Quest import Quest
            Quest.AbandonQuest(DREAMER_AND_ZEALOT_QUEST_ID)
        return BehaviorTree.NodeState.SUCCESS

    return BehaviorTree(
        BehaviorTree.ActionNode(
            name='AbandonDreamerAndZealot',
            action_fn=_action,
            aftercast_ms=250,
        )
    )


def InitializeBot() -> BehaviorTree:
    bot = ensure_botting_tree()
    return BT.Sequence(
        name='Initialize Bot',
        map_id_or_name=PIKEN_SQUARE,
        random_travel=True,
        hard_mode=_use_hard_mode,
        children=[
            bot.Config.Aggressive(multi_account=True),
            BT.CreateParty(multibox_invite=True),
            _abandon_quest_node(),
        ],
    )


def TheBreachApproach() -> BehaviorTree:
    # Walk through Piken Square to the portal, then clear The Breach to the
    # Tunnels entrance.
    breach_route = [
        (21264., 3562.),
        (18837., -919.),
        (19213., -4201.),
        (18004., -1686.),
    ]
    return BT.Sequence(
        name='The Breach Approach',
        children=[
            BT.MoveAndExitMap(
                [
                    (21030., 9015.), 
                    (20255., 8712.), 
                    (20180., 7500.)
                ],
                THE_BREACH,
            ),
            BT.VanquishNode(
                breach_route,
                clear_area_radius=TUNNELS_AGGRO_RANGE,
                name='BreachKillRoute',
            ),
            BT.MoveAndExitMap((17750., -1416.), TUNNELS_LVL_1),
        ],
    )


def Floor1ToNPC() -> BehaviorTree:
    return BT.Sequence(
        name='Floor 1 to NPC',
        children=[
            BT.VanquishNode(
                [
                    (-17442., -4638.),
                    (-12710., -6983.),
                    (-7836., -9115.),
                ],
                clear_area_radius=TUNNELS_AGGRO_RANGE,
                name='Floor1_Route_A',
            ),
        ],
    )


def _follower_npc_dialog_node(
    dialog_id: int,
    per_account_wait_ms: int = 2000,
    name: str = "FollowerNpcDialog",
) -> BehaviorTree:
    """Dispatch a quest/reward dialog to same-party follower accounts.

    Must be placed immediately after BT.MoveAndInteract in a Sequence.
    SequenceNode._tick_impl advances children via a while-loop in a single call,
    so the leader's current target is still the NPC when _dispatch fires —
    no additional target capture is needed.

    Uses SendDialogToTarget (agent-ID based) instead of SendManualDialog
    (coordinate-search based) to avoid relying on TargetNearestNPCXY on the
    follower, which can fail if the NPC array isn't populated in time.

    Filters to same-party accounts via Party.GetPlayers() cross-reference so
    bots running in other parties on the same machine are never dispatched to.
    """
    state: dict = {"done_at_ms": 0}

    def _dispatch(node: BehaviorTree.Node) -> BehaviorTree.NodeState:
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        from Py4GWCoreLib import Player, Party, Console
        from Py4GWCoreLib import ConsoleLog
        from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType
        from Py4GWCoreLib.Py4GWcorelib import Utils

        # BT.MoveAndInteract just returned SUCCESS in the same SequenceNode
        # _tick_impl call, so the leader's target is guaranteed to be the NPC.
        npc_id = int(Player.GetTargetID() or 0)

        sender_email = str(Player.GetAccountEmail() or "")
        all_accounts = list(GLOBAL_CACHE.ShMem.GetAllAccountData() or [])

        # Cross-reference ShMem accounts against Party roster to exclude bots in
        # other parties that happen to be running on the same machine.
        party_agent_ids: set[int] = set()
        for p in (Party.GetPlayers() or []):
            login = int(getattr(p, "login_number", 0) or 0)
            if login:
                pid = int(Party.Players.GetAgentIDByLoginNumber(login) or 0)
                if pid:
                    party_agent_ids.add(pid)

        followers = [
            a for a in all_accounts
            if str(getattr(a, "AccountEmail", "") or "") != sender_email
            and int(a.AgentData.AgentID or 0) in party_agent_ids
        ]
        num_followers = len(followers)

        ConsoleLog(
            MODULE_NAME,
            f"FollowerDialog dispatch: npc_id={npc_id}, dialog={dialog_id:#x}, party_followers={num_followers}",
            Console.MessageType.Info,
            True,
        )

        if npc_id > 0 and followers:
            for follower in followers:
                email = str(getattr(follower, "AccountEmail", "") or "")
                if email:
                    ConsoleLog(MODULE_NAME, f"  -> SendDialogToTarget({npc_id}, {dialog_id:#x}) -> {email}", Console.MessageType.Info, True)
                    GLOBAL_CACHE.ShMem.SendMessage(
                        sender_email,
                        email,
                        SharedCommandType.SendDialogToTarget,
                        (float(npc_id), float(dialog_id), 0.0, 0.0),
                    )
        elif npc_id == 0:
            ConsoleLog(MODULE_NAME, "  -> Skipped: leader has no NPC targeted (GetTargetID=0)", Console.MessageType.Warning, True)
        else:
            ConsoleLog(MODULE_NAME, "  -> Skipped: no same-party followers found", Console.MessageType.Warning, True)

        state["done_at_ms"] = int(Utils.GetBaseTimestamp()) + (num_followers * per_account_wait_ms if num_followers > 0 else 0)
        return BehaviorTree.NodeState.SUCCESS

    def _wait(node: BehaviorTree.Node) -> BehaviorTree.NodeState:
        from Py4GWCoreLib.Py4GWcorelib import Utils
        now = int(Utils.GetBaseTimestamp())
        return (
            BehaviorTree.NodeState.SUCCESS
            if now >= state["done_at_ms"]
            else BehaviorTree.NodeState.RUNNING
        )

    return RoutinesBT.Composite.Sequence(
        BehaviorTree(
            BehaviorTree.ActionNode(
                name="FollowerNpcDialogDispatch",
                action_fn=_dispatch,
            )
        ),
        BehaviorTree(
            BehaviorTree.WaitUntilNode(
                name="FollowerNpcDialogWait",
                condition_fn=_wait,
                throttle_interval_ms=500,
                timeout_ms=90000,
            )
        ),
        name=name,
    )


def NPCQuest() -> BehaviorTree:
    """Accept The Dreamer and the Zealot on all accounts."""
    return BT.Sequence(
        name='NPC Quest',
        children=[
            BT.MoveAndInteract(
                QUEST_NPC_POS,
                target_distance=Range.Area.value,
                log=True,
            ),
            _follower_npc_dialog_node(
                dialog_id=QUEST_ACCEPT_DIALOG,
                name='FollowerQuestAcceptDialog',
            ),
            BT.Wait(500, log=True),
            BT.SendDialog(QUEST_ACCEPT_DIALOG, log=True),
        ],
    )


def Floor1ToFloor2() -> BehaviorTree:
    return BT.Sequence(
        name='Floor 1 to Floor 2',
        children=[
            BT.VanquishNode([(-9672., -3286.)],  clear_area_radius=TUNNELS_AGGRO_RANGE, name='Floor1_Pt4'),
            BT.LootItems(),
            BT.VanquishNode([(-11186., -1788.)], clear_area_radius=TUNNELS_AGGRO_RANGE, name='Floor1_Pt5'),
            BT.LootItems(),
            BT.VanquishNode([(-10727., -304.)],  clear_area_radius=TUNNELS_AGGRO_RANGE, name='Floor1_Pt6'),
            BT.LootItems(),
            BT.VanquishNode([(-8618., 3132.)],   clear_area_radius=TUNNELS_AGGRO_RANGE, name='Floor1_Pt7'),
            BT.MoveAndExitMap((-8687., 4700.), TUNNELS_LVL_2),
        ],
    )


def Floor2() -> BehaviorTree:
    # Points 8, 9, 10 use RANGE_NEARBY in the original (crowded rooms).
    route = [
        (-991.,   10963.),
        (2007.,   15561.),
        (-764.,   17454.),
        (-643.,   20296.),
        (-8922.,  21419.),
        (-17622., 19010.),
        (-18139., 17292.),
        {'pos': (-16466., 15466.), 'clear_area_radius': Range.Nearby.value},
        {'pos': (-7110.,  18292.), 'clear_area_radius': Range.Nearby.value},
        {'pos': (-6065.,  14829.), 'clear_area_radius': Range.Nearby.value},
        (-10273., 14406.),
        (-11164., 16520.),
        (-16715.,  9618.),
        (-16748.,  5350.),
    ]
    return BT.Sequence(
        name='Floor 2',
        children=[
            BT.VanquishNode(route, clear_area_radius=TUNNELS_AGGRO_RANGE, name='Floor2_Route'),
            BT.MoveAndExitMap((-16780., 4324.), TUNNELS_LVL_3),
        ],
    )



def _open_chest_sequential_node() -> BehaviorTree:
    """Open the dungeon chest on follower accounts one at a time in party-position order.

    The leader has already opened the chest via MoveAndInteractWithGadget.
    Waits INITIAL_WAIT_MS after the leader opens, then sends InteractWithTarget to
    each follower in turn, waiting PER_FOLLOWER_MS between each dispatch.
    Uses InteractWithTarget (not OpenChest, which requires lockpicks) since the
    TOTF dungeon chest is unlocked.

    Each phase always returns explicitly — no fall-through between phases.
    """
    INITIAL_WAIT_MS = 2000    # let the leader's chest animation finish first
    PER_FOLLOWER_MS = 10000   # per-follower budget: walk + open animation + buffer

    state: dict = {
        "phase": "init",      # init | wait_init | send | wait_between
        "followers": [],
        "current_idx": 0,
        "chest_id": 0,
        "sender_email": "",
        "wait_until_ms": 0,
    }

    def _run(node: BehaviorTree.Node) -> BehaviorTree.NodeState:
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        from Py4GWCoreLib import Player, Party, Console
        from Py4GWCoreLib import ConsoleLog
        from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType
        from Py4GWCoreLib.Py4GWcorelib import Utils

        now = int(Utils.GetBaseTimestamp())

        if state["phase"] == "init":
            chest_id = int(Player.GetTargetID() or 0)
            sender_email = str(Player.GetAccountEmail() or "")

            players_list = list(Party.GetPlayers() or [])
            party_agent_ids: set[int] = set()
            for _p in players_list:
                _login = int(getattr(_p, "login_number", 0) or 0)
                if _login:
                    _pid = int(Party.Players.GetAgentIDByLoginNumber(_login) or 0)
                    if _pid:
                        party_agent_ids.add(_pid)

            all_followers = [
                a for a in (GLOBAL_CACHE.ShMem.GetAllAccountData() or [])
                if str(getattr(a, "AccountEmail", "") or "") != sender_email
                and int(a.AgentData.AgentID or 0) in party_agent_ids
            ]

            def _party_pos(account) -> int:
                agent_id = int(account.AgentData.AgentID or 0)
                for i, p in enumerate(players_list):
                    login = int(getattr(p, "login_number", 0) or 0)
                    if not login:
                        continue
                    pid = int(Party.Players.GetAgentIDByLoginNumber(login) or 0)
                    if pid == agent_id:
                        return i
                return 999

            state["chest_id"] = chest_id
            state["sender_email"] = sender_email
            state["followers"] = sorted(all_followers, key=_party_pos)
            state["current_idx"] = 0

            ConsoleLog(
                MODULE_NAME,
                f"ChestSequential: chest_id={chest_id}, followers={len(state['followers'])}",
                Console.MessageType.Info,
                True,
            )

            if chest_id == 0:
                ConsoleLog(MODULE_NAME, "ChestSequential: no chest targeted, skipping", Console.MessageType.Warning, True)
                return BehaviorTree.NodeState.SUCCESS
            if not state["followers"]:
                ConsoleLog(MODULE_NAME, "ChestSequential: no same-party followers, skipping", Console.MessageType.Warning, True)
                return BehaviorTree.NodeState.SUCCESS

            state["wait_until_ms"] = now + INITIAL_WAIT_MS
            state["phase"] = "wait_init"
            return BehaviorTree.NodeState.RUNNING

        if state["phase"] == "wait_init":
            if now < state["wait_until_ms"]:
                return BehaviorTree.NodeState.RUNNING
            state["phase"] = "send"
            return BehaviorTree.NodeState.RUNNING

        if state["phase"] == "send":
            idx = state["current_idx"]
            if idx >= len(state["followers"]):
                ConsoleLog(MODULE_NAME, "ChestSequential: all followers done", Console.MessageType.Info, True)
                return BehaviorTree.NodeState.SUCCESS

            follower = state["followers"][idx]
            email = str(getattr(follower, "AccountEmail", "") or "")
            ConsoleLog(
                MODULE_NAME,
                f"ChestSequential [{idx + 1}/{len(state['followers'])}]: InteractWithTarget -> {email}",
                Console.MessageType.Info,
                True,
            )
            if email:
                GLOBAL_CACHE.ShMem.SendMessage(
                    state["sender_email"],
                    email,
                    SharedCommandType.InteractWithTarget,
                    (float(state["chest_id"]), 0.0, 0.0, 0.0),
                )
            state["current_idx"] += 1
            state["wait_until_ms"] = now + PER_FOLLOWER_MS
            state["phase"] = "wait_between"
            return BehaviorTree.NodeState.RUNNING

        if state["phase"] == "wait_between":
            if now < state["wait_until_ms"]:
                return BehaviorTree.NodeState.RUNNING
            state["phase"] = "send"
            return BehaviorTree.NodeState.RUNNING

        return BehaviorTree.NodeState.SUCCESS

    tree = BehaviorTree(
        BehaviorTree.WaitUntilNode(
            name="OpenChestSequential",
            condition_fn=_run,
            throttle_interval_ms=500,
            timeout_ms=120000,
        )
    )
    orig_reset = tree.root.reset

    def _reset() -> None:
        state["phase"] = "init"
        state["followers"] = []
        state["current_idx"] = 0
        state["chest_id"] = 0
        state["sender_email"] = ""
        state["wait_until_ms"] = 0
        orig_reset()

    tree.root.reset = _reset
    return tree


def Floor3() -> BehaviorTree:
    return BT.Sequence(
        name='Floor 3',
        children=[
            # Clear to beacon trigger (points 1-6)
            BT.VanquishNode(
                [
                    (-11162., 3309.),
                    (-10127., 2505.),
                    (-17353., -952.),
                    (-16644., -3499.),
                    (-13208., -4395.),
                    (-12436., -5865.),
                ],
                clear_area_radius=TUNNELS_AGGRO_RANGE,
                name='Floor3_Route_A',
            ),
            BT.LootItems(),
            # Clear beacon area (points 7-9)
            BT.VanquishNode(
                [
                    (-13244., -2246.),
                    (-10537., -1300.),
                    (-10264., -4463.),  # Triggers the beacon
                ],
                clear_area_radius=TUNNELS_AGGRO_RANGE,
                name='Floor3_Route_B',
            ),
            # Clear post-beacon section (points 10-13)
            BT.VanquishNode(
                [
                    (-9819., -1276.),
                    (-7260.,  1425.),
                    (-3990.,  -940.),
                    (-6418., -4303.),
                ],
                clear_area_radius=TUNNELS_AGGRO_RANGE,
                name='Floor3_Route_C',
            ),
            BT.MoveAndInteractWithGadget((-6442., -4281.)),  # Open dungeon door
            # Clear to final boss (points 14-16)
            BT.VanquishNode(
                [
                    (-10642., -8052.),
                    (-13186., -8718.),
                    (-15949., -8561.),
                ],
                clear_area_radius=TUNNELS_AGGRO_RANGE,
                name='Floor3_Route_D',
            ),
            # Collect quest reward on all accounts. Followers receive
            # SendDialogToTarget so they interact with the reward NPC independently.
            BT.MoveAndInteract(
                QUEST_REWARD_NPC_POS,
                target_distance=Range.Area.value,
                log=True,
            ),
            _follower_npc_dialog_node(
                dialog_id=QUEST_REWARD_DIALOG,
                name='FollowerQuestRewardDialog',
            ),
            BT.Wait(500, log=True),
            BT.SendDialog(QUEST_REWARD_DIALOG, log=True),
            BT.MoveAndInteractWithGadget(DUNGEON_CHEST_POS),  # Leader opens chest
            _open_chest_sequential_node(),                     # Followers walk to and open chest
            BT.LootItems(),
            BT.Resign(wait_for_map_load=True, target_map_id=PIKEN_SQUARE, multi_account=True),
        ],
    )


def get_execution_steps() -> list[tuple[str, Callable[[], BehaviorTree]]]:
    return [
        ('Initialize Bot',        InitializeBot),
        ('The Breach Approach',   TheBreachApproach),
        ('Floor 1 to NPC',        Floor1ToNPC),
        ('NPC Quest',             NPCQuest),
        ('Floor 1 to Floor 2',    Floor1ToFloor2),
        ('Floor 2',               Floor2),
        ('Floor 3',               Floor3),
    ]


def main() -> None:
    global initialized, ini_key

    if not initialized:
        if not ini_key:
            ini_key = IniManager().ensure_key(INI_PATH, INI_FILENAME)
            if not ini_key:
                return
            IniManager().load_once(ini_key)
            _load_settings()

        ensure_botting_tree()
        initialized = True

    tree = ensure_botting_tree()
    tree.tick()
    tree.UI.draw_window(extra_tabs=[('Bot Config', _draw_bot_config)])


if __name__ == '__main__':
    main()

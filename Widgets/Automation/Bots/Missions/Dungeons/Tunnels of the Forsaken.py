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
                [(21030., 9015.), (20255., 8712.), (20180., 7500.)],
                THE_BREACH,
            ),
            BT.VanquishNode(
                breach_route,
                clear_area_radius=TUNNELS_AGGRO_RANGE,
                name='BreachKillRoute',
            ),
            BT.MoveAndExitMap((17771., -1416.), TUNNELS_LVL_1),
        ],
    )


def Floor1() -> BehaviorTree:
    # Clear to the quest NPC, take the quest, pick up three Elemental Keystones
    # across points 4-6, then exit to Floor 2.
    return BT.Sequence(
        name='Floor 1',
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
            BT.MoveAndAutoDialog((-7400., -9462.), buttons=0, multi_account=True),
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
    """Send OpenChest cascade to follower accounts in party-position order.

    The leader has already opened the chest via MoveAndInteractWithGadget.
    This triggers the cascade so each follower opens it in sequence, waiting
    long enough for all interactions to complete before the bot moves on.
    """
    CHEST_POS = (-16066., -8370.)
    CHEST_SEARCH_RADIUS = 600.0
    PER_ACCOUNT_WAIT_MS = 5000  # 5 s per follower for chest-open animation + round-trip

    state: dict = {"initialized": False, "done_at_ms": 0}

    def _run(node: BehaviorTree.Node) -> BehaviorTree.NodeState:
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        from Py4GWCoreLib import Player, Party, AgentArray
        from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType
        from Py4GWCoreLib.Py4GWcorelib import Utils

        now = int(Utils.GetBaseTimestamp())

        if state["initialized"]:
            return (
                BehaviorTree.NodeState.SUCCESS
                if now >= state["done_at_ms"]
                else BehaviorTree.NodeState.RUNNING
            )

        state["initialized"] = True

        # Find the chest gadget near its spawn point
        gadget_ids = list(AgentArray.GetGadgetArray() or [])
        gadget_ids = list(AgentArray.Filter.ByDistance(gadget_ids, CHEST_POS, CHEST_SEARCH_RADIUS) or [])
        chest_id = int(gadget_ids[0]) if gadget_ids else 0

        sender_email = str(Player.GetAccountEmail() or "")
        followers = [
            a for a in (GLOBAL_CACHE.ShMem.GetAllAccountData() or [])
            if str(getattr(a, "AccountEmail", "") or "") != sender_email
        ]
        num_followers = len(followers)

        if chest_id > 0 and followers:
            players_list = list(Party.GetPlayers() or [])

            def _party_pos(account) -> int:
                agent_id = int(getattr(account, "PlayerID", 0) or 0)
                for i, p in enumerate(players_list):
                    login = int(getattr(p, "login_number", 0) or 0)
                    if not login:
                        continue
                    pid = int(Party.Players.GetAgentIDByLoginNumber(login) or 0)
                    if pid == agent_id:
                        return i
                return 999

            followers.sort(key=_party_pos)
            first_email = str(getattr(followers[0], "AccountEmail", "") or "")
            if first_email:
                GLOBAL_CACHE.ShMem.SendMessage(
                    sender_email,
                    first_email,
                    SharedCommandType.OpenChest,
                    (float(chest_id), 1.0, 0.0, 0.0),
                )

        state["done_at_ms"] = now + max(3000, num_followers * PER_ACCOUNT_WAIT_MS)
        return BehaviorTree.NodeState.RUNNING

    tree = BehaviorTree(
        BehaviorTree.WaitUntilNode(
            name="OpenChestSequential",
            condition_fn=_run,
            throttle_interval_ms=500,
            timeout_ms=90000,
        )
    )
    orig_reset = tree.root.reset

    def _reset() -> None:
        state["initialized"] = False
        state["done_at_ms"] = 0
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
            # Collect quest reward then open chest
            BT.MoveAndAutoDialog((-16098., -8626.), buttons=0, multi_account=True),
            BT.MoveAndInteractWithGadget((-16066., -8370.)),  # Leader opens chest
            _open_chest_sequential_node(),                     # Followers open chest in party-position order
            BT.LootItems(),
            BT.Resign(wait_for_map_load=True, target_map_id=PIKEN_SQUARE, multi_account=True),
        ],
    )


def get_execution_steps() -> list[tuple[str, Callable[[], BehaviorTree]]]:
    return [
        ('Initialize Bot',        InitializeBot),
        ('The Breach Approach',   TheBreachApproach),
        ('Floor 1',               Floor1),
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

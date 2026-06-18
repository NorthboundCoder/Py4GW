from Py4GWCoreLib import Agent, Player, Profession, Routines, BuildMgr
from Py4GWCoreLib.Skill import Skill
from Py4GWCoreLib.Builds.Any.HeroAI import HeroAI as HeroAIBuild
from Py4GWCoreLib.Builds.Skills import SkillsTemplate


Signet_of_Spirits_ID = Skill.GetID("Signet_of_Spirits")
Bloodsong_ID = Skill.GetID("Bloodsong")
Spirit_Transfer_ID = Skill.GetID("Spirit_Transfer")
Mend_Body_and_Soul_ID = Skill.GetID("Mend_Body_and_Soul")
Spirit_Light_ID = Skill.GetID("Spirit_Light")
Spirit_Siphon_ID = Skill.GetID("Spirit_Siphon")
Weapon_of_Shadow_ID = Skill.GetID("Weapon_of_Shadow")
Death_Pact_Signet_ID = Skill.GetID("Death_Pact_Signet")
Ebon_Vanguard_Assassin_Support_ID = Skill.GetID("Ebon_Vanguard_Assassin_Support")
Great_Dwarf_Weapon_ID = Skill.GetID("Great_Dwarf_Weapon")
Technobabble_ID = Skill.GetID("Technobabble")


class SoS_Healer(BuildMgr):
    def __init__(self, match_only: bool = False):
        super().__init__(
            name="SoS Healer",
            required_primary=Profession.Ritualist,
            template_code="",
            required_skills=[
                Signet_of_Spirits_ID,
                Bloodsong_ID,
                Spirit_Transfer_ID,
            ],
            optional_skills=[
                Mend_Body_and_Soul_ID,
                Spirit_Light_ID,
                Spirit_Siphon_ID,
                Weapon_of_Shadow_ID,
                Death_Pact_Signet_ID,
                Ebon_Vanguard_Assassin_Support_ID,
                Great_Dwarf_Weapon_ID,
                Technobabble_ID,
            ],
        )
        if match_only:
            return

        self.SetFallback("HeroAI", HeroAIBuild(standalone_fallback=True))
        self.SetBlockedSkills([
            Signet_of_Spirits_ID,
            Bloodsong_ID,
            Spirit_Transfer_ID,
            Mend_Body_and_Soul_ID,
            Spirit_Light_ID,
            Spirit_Siphon_ID,
            Weapon_of_Shadow_ID,
            Death_Pact_Signet_ID,
            Ebon_Vanguard_Assassin_Support_ID,
            Great_Dwarf_Weapon_ID,
            Technobabble_ID,
        ])
        self.SetSkillCastingFn(self._run_local_skill_logic)
        self.skills: SkillsTemplate = SkillsTemplate(self)

    def _run_local_skill_logic(self):
        if not Routines.Checks.Skills.CanCast():
            return False

        # Emergency healing — fires regardless of aggro state.
        if (yield from self.skills.Ritualist.RestorationMagic.Spirit_Transfer(health_threshold=0.30)):
            return True

        if self.IsSkillEquipped(Spirit_Light_ID) and (yield from self.skills.Ritualist.RestorationMagic.Spirit_Light(health_threshold=0.30)):
            return True

        if self.IsSkillEquipped(Mend_Body_and_Soul_ID) and (yield from self.skills.Ritualist.RestorationMagic.Mend_Body_and_Soul(health_threshold=0.40)):
            return True

        # Emergency energy refill: Spirit Siphon when below 30% energy.
        if self.IsSkillEquipped(Spirit_Siphon_ID) and (yield from self.skills.Ritualist.ChannelingMagic.Spirit_Siphon(max_self_energy_pct=0.30)):
            return True

        if not (self.IsInAggro() or self.IsCloseToAggro()):
            # Out of combat: rez dead party members.
            if self.IsSkillEquipped(Death_Pact_Signet_ID) and (yield from self.skills.Ritualist.RestorationMagic.Death_Pact_Signet()):
                return True
            return False

        # PvE offensive support.
        if self.IsSkillEquipped(Ebon_Vanguard_Assassin_Support_ID) and (yield from self.skills.Any.PvE.Ebon_Vanguard_Assassin_Support()):
            return True

        if self.IsSkillEquipped(Technobabble_ID) and (yield from self.skills.Any.PvE.Technobabble()):
            return True

        if self.IsSkillEquipped(Great_Dwarf_Weapon_ID) and (yield from self.skills.Any.NoAttribute.Great_Dwarf_Weapon()):
            return True

        # Core spirit maintenance.
        if (yield from self.skills.Ritualist.ChannelingMagic.Signet_of_Spirits()):
            return True

        if (yield from self.skills.Ritualist.ChannelingMagic.Bloodsong()):
            return True

        # Weapon of Shadow on a martial ally without an active weapon spell.
        if self.IsSkillEquipped(Weapon_of_Shadow_ID) and (yield from self.skills.Ritualist.RestorationMagic.Weapon_of_Shadow()):
            return True

        # Opportunistic energy refill: Spirit Siphon when below 70% energy.
        if self.IsSkillEquipped(Spirit_Siphon_ID) and (yield from self.skills.Ritualist.ChannelingMagic.Spirit_Siphon(max_self_energy_pct=0.70)):
            return True

        # Normal healing tiers.
        if self.IsSkillEquipped(Spirit_Light_ID) and (yield from self.skills.Ritualist.RestorationMagic.Spirit_Light(health_threshold=0.75)):
            return True

        if (yield from self.skills.Ritualist.RestorationMagic.Spirit_Transfer()):
            return True

        if self.IsSkillEquipped(Mend_Body_and_Soul_ID) and (yield from self.skills.Ritualist.RestorationMagic.Mend_Body_and_Soul(health_threshold=0.75)):
            return True

        # Rez dead party members when combat permits.
        if self.IsSkillEquipped(Death_Pact_Signet_ID) and (yield from self.skills.Ritualist.RestorationMagic.Death_Pact_Signet()):
            return True

        return False

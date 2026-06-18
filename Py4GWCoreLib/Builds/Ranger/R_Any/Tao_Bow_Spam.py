from Py4GWCoreLib import Agent, Party, Profession, BuildMgr, Routines, Player
from Py4GWCoreLib.Skill import Skill
from Py4GWCoreLib.Builds.Any.HeroAI import HeroAI_Build
from Py4GWCoreLib.Builds.Skills import SkillsTemplate


class Tao_Bow_Spam(BuildMgr):
    def __init__(self, match_only: bool = False):
        self.Together_as_one_ID = Skill.GetID("Together_as_one")
        self.Expert_Focus_ID = Skill.GetID("Expert_Focus")
        self.Sundering_Attack_ID = Skill.GetID("Sundering_Attack")
        self.Penetrating_Attack_ID = Skill.GetID("Penetrating_Attack")
        self.Needling_Shot_ID = Skill.GetID("Needling_Shot")
        self.Never_Rampage_Alone_ID = Skill.GetID("Never_Rampage_Alone")
        self.Comfort_Animal_ID = Skill.GetID("Comfort_Animal")
        self.Ebon_Battle_Standard_of_Honor_ID = Skill.GetID("Ebon_Battle_Standard_of_Honor")
        self.I_Am_the_Strongest_ID = Skill.GetID("I_Am_the_Strongest")
        self.Whirling_Defense_ID = Skill.GetID("Whirling_Defense")
        self.Asuran_Scan_ID = Skill.GetID("Asuran_Scan")

        super().__init__(
            name="Tao Bow Spam",
            required_primary=Profession.Ranger,
            template_code="",
            required_skills=[
                self.Together_as_one_ID,
                self.Expert_Focus_ID,
                self.Sundering_Attack_ID,
            ],
            optional_skills=[
                self.Penetrating_Attack_ID,
                self.Needling_Shot_ID,
                self.Never_Rampage_Alone_ID,
                self.Comfort_Animal_ID,
                self.Ebon_Battle_Standard_of_Honor_ID,
                self.I_Am_the_Strongest_ID,
                self.Whirling_Defense_ID,
                self.Asuran_Scan_ID,
            ],
        )

        if match_only:
            return

        self.SetFallback("HeroAI", HeroAI_Build(standalone_fallback=True))
        self.SetSkillCastingFn(self._run_local_skill_logic)
        self.skills: SkillsTemplate = SkillsTemplate(self)

    def _run_local_skill_logic(self):
        player_agent_id = Player.GetAgentID()

        if not Routines.Checks.Skills.CanCast():
            yield from Routines.Yield.wait(100)
            return False

        yield from self.AutoAttack()

        # Expert Focus — cast when approaching or in combat
        if (self.IsInAggro() or self.IsCloseToAggro()) and self.IsSkillEquipped(self.Expert_Focus_ID):
            if not Routines.Checks.Agents.HasEffect(player_agent_id, self.Expert_Focus_ID):
                if (yield from self.CastSkillID(
                    skill_id=self.Expert_Focus_ID,
                    log=False,
                    aftercast_delay=250,
                )):
                    return True

        if not self.IsInAggro():
            if (
                Agent.GetHealth(player_agent_id) < 0.5
                and not Routines.Checks.Agents.HasEffect(player_agent_id, self.Together_as_one_ID)
                and self.CanCastSkillID(self.Together_as_one_ID)
            ):
                if (yield from self.CastSkillID(
                    skill_id=self.Together_as_one_ID,
                    log=False,
                    aftercast_delay=250,
                )):
                    return True
            return False

        # Together as One — party heal + energy
        if (yield from self.skills.Ranger.Expertise.Together_as_One()):
            return True

        # I Am the Strongest! — self damage buff; maintain
        if self.IsSkillEquipped(self.I_Am_the_Strongest_ID):
            if not Routines.Checks.Agents.HasEffect(player_agent_id, self.I_Am_the_Strongest_ID):
                if (yield from self.CastSkillID(
                    skill_id=self.I_Am_the_Strongest_ID,
                    log=False,
                    aftercast_delay=250,
                )):
                    return True

        # Never Rampage Alone — stance for bonus damage while pet is alive; maintain
        if self.IsSkillEquipped(self.Never_Rampage_Alone_ID):
            if not Routines.Checks.Agents.HasEffect(player_agent_id, self.Never_Rampage_Alone_ID):
                if (yield from self.CastSkillID(
                    skill_id=self.Never_Rampage_Alone_ID,
                    log=False,
                    aftercast_delay=250,
                )):
                    return True

        # Asuran Scan — guaranteed hits + bonus damage on target; use on cooldown
        if self.IsSkillEquipped(self.Asuran_Scan_ID) and self.CanCastSkillID(self.Asuran_Scan_ID):
            if (yield from self.CastSkillID(
                skill_id=self.Asuran_Scan_ID,
                log=False,
                aftercast_delay=250,
            )):
                return True

        # Sundering Attack — required attack
        if (yield from self.CastSkillID(
            skill_id=self.Sundering_Attack_ID,
            log=False,
            aftercast_delay=250,
        )):
            return True

        # Penetrating Attack — armor-penetrating attack
        if self.IsSkillEquipped(self.Penetrating_Attack_ID):
            if (yield from self.CastSkillID(
                skill_id=self.Penetrating_Attack_ID,
                log=False,
                aftercast_delay=250,
            )):
                return True

        # Needling Shot — bow attack filler
        if self.IsSkillEquipped(self.Needling_Shot_ID):
            if (yield from self.CastSkillID(
                skill_id=self.Needling_Shot_ID,
                log=False,
                aftercast_delay=250,
            )):
                return True

        # Ebon Battle Standard of Honor — AoE damage buff; place when off cooldown
        if self.IsSkillEquipped(self.Ebon_Battle_Standard_of_Honor_ID) and self.CanCastSkillID(self.Ebon_Battle_Standard_of_Honor_ID):
            if (yield from self.CastSkillID(
                skill_id=self.Ebon_Battle_Standard_of_Honor_ID,
                log=False,
                aftercast_delay=250,
            )):
                return True

        # Comfort Animal — pet heal/resurrect; only when dead or below 30% health
        if self.IsSkillEquipped(self.Comfort_Animal_ID):
            pet_id = Party.Pets.GetPetID(player_agent_id)
            if pet_id and (not Agent.IsAlive(pet_id) or Agent.GetHealth(pet_id) < 0.30):
                if (yield from self.CastSkillID(
                    skill_id=self.Comfort_Animal_ID,
                    log=False,
                    aftercast_delay=250,
                )):
                    return True

        # Whirling Defense — projectile-blocking stance; only when Never Rampage Alone is not active
        if self.IsSkillEquipped(self.Whirling_Defense_ID):
            if (
                not Routines.Checks.Agents.HasEffect(player_agent_id, self.Whirling_Defense_ID)
                and not Routines.Checks.Agents.HasEffect(player_agent_id, self.Never_Rampage_Alone_ID)
            ):
                if (yield from self.CastSkillID(
                    skill_id=self.Whirling_Defense_ID,
                    log=False,
                    aftercast_delay=250,
                )):
                    return True

        if (yield from self.AutoAttack()):
            return True

        yield

"""Independently seeded lake hazards."""
import random

from .settings import DEFAULTS


class Lakes:
    def __init__(self, sim, seed):
        self.sim = sim
        self.rules = DEFAULTS["lakes"]
        for key in ("alligator_damage", "alligator_cooldown"):
            if type(self.rules[key]) is not int or self.rules[key] < 1:
                raise ValueError(f"lakes.{key} must be a positive integer")
        if not 0 <= self.rules["alligator_probability"] <= 1:
            raise ValueError("lakes.alligator_probability must be between zero and one")
        self.hazard_random = {actor.id: random.Random(seed + 12001 + index * 7919)
                              for index, actor in enumerate(sim.agents)}

    def encounter(self, actor):
        if (not self.sim.features["alligators"] or not actor.alive or self.sim.world.tile(actor.position).terrain.value != "lake"
                or self.sim.world.tile(actor.position).shelter_owner is not None
                or self.sim.tick < actor.next_alligator_tick or actor.last_alligator_check == self.sim.tick):
            return
        actor.last_alligator_check = self.sim.tick
        self.sim.trace.record("lake.hazard_checked", {"agent": actor.id, "position": actor.position})
        if self.hazard_random[actor.id].random() >= self.rules["alligator_probability"]:
            return
        # The first encounter is survivable even for an already injured survivor.
        damage = min(actor.health - 1, self.rules["alligator_damage"]) if actor.alligator_attacks == 0 else min(actor.health, self.rules["alligator_damage"])
        damage = max(0, damage)
        actor.health -= damage
        actor.alligator_attacks += 1
        actor.next_alligator_tick = self.sim.tick + self.rules["alligator_cooldown"]
        if actor.sleep_remaining:
            self.sim._wake(actor, "alligator attack", interrupted=True)
        self.sim.homestead.record(actor, "alligator.attacked", position=actor.position,
                                  damage=damage, health=actor.health, attacks=actor.alligator_attacks)
        self.sim.event_log.appendleft(f"{actor.name}: alligator attack, {damage:g} damage")
        actor.last_action = f"alligator hit for {damage:g} damage"
        if actor.health <= 0:
            actor.alive = False
            actor.death_cause = "alligator attack"
            actor.death_tick = self.sim.tick

"""Finite-stock fishing nets and independently seeded lake hazards."""
from dataclasses import dataclass
import random

from bbagents import Observation, ToolCall
from .settings import DEFAULTS


@dataclass
class FishingNet:
    owner: str
    position: tuple[int, int]
    placed_tick: int
    catch: int = 0
    last_checked: int = -1


class Lakes:
    def __init__(self, sim, seed):
        self.sim = sim
        self.nets = {}
        self.rules = DEFAULTS["lakes"]
        for key in ("net_capacity", "net_interval", "alligator_damage", "alligator_cooldown"):
            if type(self.rules[key]) is not int or self.rules[key] < 1:
                raise ValueError(f"lakes.{key} must be a positive integer")
        if not 0 <= self.rules["alligator_probability"] <= 1:
            raise ValueError("lakes.alligator_probability must be between zero and one")
        self.hazard_random = {actor.id: random.Random(seed + 12001 + index * 7919)
                              for index, actor in enumerate(sim.agents)}

    def owned(self, actor):
        return next((net for net in self.nets.values() if net.owner == actor.id), None)

    def accessible(self, actor, net):
        owner = next((agent for agent in self.sim.agents if agent.id == net.owner), None)
        return (net.owner == actor.id or owner is None or not owner.alive) and self.sim.distance(actor.position, net.position) <= 1

    def site(self, actor):
        return next((pos for pos in sorted(self.sim.world.positions_within(actor.position, 1))
                     if self.sim.world.tile(pos).terrain.value == "lake" and pos not in self.nets), None)

    def place(self, actor):
        if not self.sim.features["fishing_nets"]:
            raise ValueError("net fishing is disabled")
        if "net_fishing" not in actor.learned_skills:
            raise ValueError("net_fishing skill required")
        site = self.site(actor)
        if site is None or self.owned(actor):
            raise ValueError("requires a free adjacent lake tile and no other deployed net")
        self.sim.homestead.spend(actor, {"fishing_net": 1}, 3)
        self.nets[site] = FishingNet(actor.id, site, self.sim.tick)
        self.sim.homestead.record(actor, "net.placed", position=site)
        return Observation("place_net", "placed a woven wooden-strip fishing net", {"position": site})

    def collect(self, actor, retrieve=False):
        if not self.sim.features["fishing_nets"]:
            raise ValueError("net fishing is disabled")
        net = next((net for _, net in sorted(self.nets.items())
                    if self.accessible(actor, net) and (retrieve or net.catch)), None)
        if net is None:
            raise ValueError("no accessible net with fish" if not retrieve else "no accessible net")
        self.sim.homestead.spend(actor, {}, 2)
        amount = net.catch
        actor.inventory["fish"] += amount
        net.catch = 0
        if retrieve:
            actor.inventory["fishing_net"] += 1
            del self.nets[net.position]
        self.sim.homestead.record(actor, "net.retrieved" if retrieve else "net.collected",
                                  position=net.position, fish=amount)
        return Observation("retrieve_net" if retrieve else "collect_net", f"collected {amount} fish", {"fish": amount})

    def available(self, actor):
        if not self.sim.features["fishing_nets"] or not actor.alive or actor.sleep_remaining:
            return []
        calls = []
        if ("net_fishing" in actor.learned_skills and actor.inventory["fishing_net"]
                and actor.energy >= 3 and not self.owned(actor) and self.site(actor) is not None):
            calls.append(ToolCall("place_net"))
        if actor.energy >= 2:
            for net in self.nets.values():
                if self.accessible(actor, net):
                    calls.append(ToolCall("retrieve_net"))
                    if net.catch:
                        calls.append(ToolCall("collect_net"))
                    break
        return calls

    def context(self, actor):
        return [{"position": net.position, "owner": net.owner, "fish": net.catch,
                 "capacity": self.rules["net_capacity"]}
                for net in self.nets.values()
                if net.owner == actor.id or net.position in actor.known_tiles]

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

    def update(self):
        if not self.sim.features["fishing_nets"]:
            return
        for pos, net in sorted(self.nets.items()):
            age = self.sim.tick - net.placed_tick
            tile = self.sim.world.tile(pos)
            if age > 0 and age % self.rules["net_interval"] == 0 and net.last_checked != self.sim.tick:
                net.last_checked = self.sim.tick
            else:
                continue
            if tile.fish_stock > 0 and net.catch < self.rules["net_capacity"]:
                tile.fish_stock -= 1
                net.catch += 1
                self.sim.trace.record("net.caught", {"agent": net.owner, "position": pos,
                    "fish": net.catch, "remaining": tile.fish_stock})

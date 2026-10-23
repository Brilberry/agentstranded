"""Canonical gameplay fingerprints, excluding clocks and diagnostic identities."""
from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import json


def canonical(value):
    if is_dataclass(value):
        return canonical({field.name: getattr(value, field.name) for field in fields(value)})
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): canonical(item) for key, item in sorted(value.items(), key=lambda row: str(row[0]))}
    if isinstance(value, (set, frozenset)):
        return sorted((canonical(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, (list, tuple)):
        return [canonical(item) for item in value]
    return value


def encode(value):
    return json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def gameplay_state(sim):
    fields = ("id", "position", "health", "hunger", "thirst", "energy", "alive",
              "inventory", "home", "learned_skills", "death_tick", "death_cause",
              "sleep_remaining", "cold_exposure", "leather_equipped")
    return {"tick": sim.tick, "agents": [{key: getattr(agent, key) for key in fields}
                                         for agent in sim.agents],
            "predators": sim.predators, "wildlife": sim.wildlife.animals,
            "climate": sim.conditions,
            "plots": sim.homestead.plots, "fires": sim.homestead.fires,
            "reservoirs": sim.homestead.reservoirs}


def initial_environment_digest(sim):
    """Call before stepping; excludes team traits and incidental zero counters."""
    tiles = [[{"terrain": tile.terrain, "resources": {key: value for key, value in tile.resources.items() if value},
               "fish_stock": tile.fish_stock, "fish_capacity": tile.fish_capacity}
              for tile in row] for row in sim.world.tiles]
    return hashlib.sha256(encode({"tiles": tiles, "wildlife": sim.wildlife.animals,
                                  "spawn_slots": [agent.position for agent in sim.agents],
                                  "climate": sim.conditions})).hexdigest()


class ReplayDigest:
    """Hash the ordered gameplay state after every tick, plus the final world."""
    def __init__(self):
        self.digest = hashlib.sha256()

    def record(self, sim):
        self.digest.update(encode(gameplay_state(sim)) + b"\n")

    def finish(self, sim):
        result = self.digest.copy()
        result.update(encode(sim.world.tiles))
        return result.hexdigest()

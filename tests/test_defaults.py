from copy import deepcopy
import json

from agentstranded import Simulation
from agentstranded.competition import DEFAULT_BEHAVIOR, MAPS
from agentstranded.settings import CONFIG_DIRECTORY, DEFAULTS, SIMULATION_DEFAULTS


def test_normal_simulation_reads_packaged_defaults():
    data = json.loads((CONFIG_DIRECTORY / "defaults.json").read_text(encoding="utf-8"))
    sim = Simulation()
    assert sim.world.size == data["simulation"]["size"]
    assert len(sim.agents) == data["simulation"]["agents"]
    assert [agent.name for agent in sim.agents] == [row["name"] for row in data["survivors"]]
    for agent, row in zip(sim.agents, data["survivors"], strict=True):
        assert row["intelligence_range"][0] <= agent.intelligence <= row["intelligence_range"][1]
    assert DEFAULT_BEHAVIOR == data["behavior"]
    assert MAPS == data["maps"]
    assert sim.predator_interval == SIMULATION_DEFAULTS["predator_interval"]
    for field, expected in data["survivor_state"].items():
        assert getattr(sim.agents[0], field) == expected


def test_default_survivor_data_is_used_not_hardcoded(monkeypatch):
    profiles = deepcopy(DEFAULTS["survivors"])
    profiles[0].update(name="Test survivor", intelligence_range=[43, 43],
                       personality_range=[17, 17], objective="Test objective")
    monkeypatch.setitem(DEFAULTS, "survivors", profiles)
    agent = Simulation(agents=1).agents[0]
    assert agent.name == "Test survivor"
    assert agent.intelligence == 43
    assert agent.social_traits.generosity == 17

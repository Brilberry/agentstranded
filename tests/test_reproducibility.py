import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from agentstranded import Simulation
from agentstranded.reproducibility import encode, initial_environment_digest

SCRIPT = '''
import json, sys
from collections import deque
from agentstranded.competition import load, create_simulation, score
from agentstranded.reproducibility import ReplayDigest
rules = load("agentstranded/configs/competition.json")
rules.update(seeds=[int(sys.argv[1])], max_ticks=1600)
team = load("agentstranded/configs/team.json5", json5=True)
def reverse_keys(value):
    if isinstance(value, dict):
        return {key: reverse_keys(value[key]) for key in reversed(value)}
    if isinstance(value, list):
        return [reverse_keys(item) for item in value]
    return value
if int(sys.argv[2]) != 1:
    team, rules = reverse_keys(team), reverse_keys(rules)
sim = create_simulation(team, rules, rules["seeds"][0])
sim.trace.events = deque(sim.trace.events, maxlen=100)
digest = ReplayDigest()
digest.record(sim)
while not sim.game_over:
    sim.step()
    digest.record(sim)
print(json.dumps({"digest": digest.finish(sim), "score": score(sim)}))
'''


def replay(seed, hashseed):
    result = subprocess.run([sys.executable, "-c", SCRIPT, str(seed), str(hashseed)],
                            cwd=Path(__file__).parents[1],
                            env={**os.environ, "PYTHONHASHSEED": str(hashseed)},
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("seed", [17, 42])
def test_competition_replays_across_processes_and_hash_seeds(seed):
    first = replay(seed, 1)
    assert first == replay(seed, 271)
    expected = {
        17: "abeb2bec81387034aed90a6046a946d40ac23e9076b80f4c7b80aecd9612cd5c",
        42: "4ce8528ab91b5939b8257c08d95b0820ab2c37a9b4b3f28fca20e8024584cf16",
    }
    assert first["digest"] == expected[seed]
    assert first["score"]["score"] == {17: 8704, 42: 12034}[seed]


def test_different_environment_seeds_change_replay():
    assert replay(17, 1)["digest"] != replay(42, 1)["digest"]


def test_equal_distance_resource_targets_have_explicit_coordinate_tiebreak():
    sim = Simulation(agents=1, predator_interval=None)
    actor = sim.agents[0]
    actor.position = (10, 10)
    actor.known_resources["wood"] = {(11, 10), (9, 10)}
    for pos in actor.known_resources["wood"]:
        sim.world.tile(pos).resources["wood"] = 5
    assert sim.policy._nearest_resource(actor, "wood") == (9, 10)


def test_fingerprint_encoding_ignores_dictionary_and_set_iteration_order():
    assert encode({"b": {"z", "a"}, "a": [1, 2]}) == encode({"a": [1, 2], "b": {"a", "z"}})
    assert encode([1, 2]) != encode([2, 1])  # Player-controlled array order matters.


def test_different_teams_receive_identical_initial_environment():
    from copy import deepcopy
    from agentstranded.competition import load, create_simulation
    root = Path(__file__).parents[1] / "agentstranded/configs"
    rules = load(root / "competition.json")
    first = load(root / "team.json5", json5=True)
    second = deepcopy(first)
    second["survivors"].reverse()
    a = create_simulation(first, rules, rules["seeds"][0])
    b = create_simulation(second, rules, rules["seeds"][0])
    assert initial_environment_digest(a) == initial_environment_digest(b)

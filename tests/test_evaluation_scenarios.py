from collections import deque
import gzip
import json
from pathlib import Path

import pytest

from agentstranded import Simulation
from agentstranded.evaluation_scenarios import SCENARIOS, ScenarioContractGrader, evaluate_scenarios, prepare_scenario, validate_suite
from agentstranded.reproducibility import ReplayDigest, initial_environment_digest
from agentstranded.simulation import Terrain


def suite(tmp_path, names=None, seeds=None):
    path = tmp_path / "suite.json"
    path.write_text(json.dumps({"schema_version": 1, "seeds": seeds or [17],
                               "scenarios": names or list(SCENARIOS)}), encoding="utf-8")
    return path


def test_all_controlled_scenarios_complete_and_keep_evidence(tmp_path):
    report = evaluate_scenarios(suite(tmp_path), tmp_path / "results", events=True)
    assert len(report["runs"]) == len(SCENARIOS)
    for run in report["runs"]:
        assert run["status"] == "completed", run
        assert all(run["checks"].values()), run
        assert run["end_tick"] <= SCENARIOS[run["variant"]].horizon
        assert len(run["metrics"]["survivors"]) == 1
        with gzip.open(tmp_path / "results" / run["events_file"], "rt", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle]
        assert rows[0]["event"] == "evaluation.scenario_prepared"
        assert rows[-1]["event"] == "simulation.ended"
        assert not any(row["event"] == "wildlife.spawned" for row in rows)
    assert not report["comparisons"]  # Never pair unrelated scenarios as causal ablations.
    html = (tmp_path / "results/report.html").read_text(encoding="utf-8")
    assert "Controlled scenarios" in html and "fixed-duel" in html
    assert "not competition scores" in html
    assert (tmp_path / "results/results.json").exists()
    with pytest.raises(FileExistsError):
        evaluate_scenarios(suite(tmp_path), tmp_path / "results")


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_preparation_replay_and_measurement_are_reproducible(name):
    hashes = []
    for bounded in (False, True):
        spec = SCENARIOS[name]
        sim = Simulation(agents=1, seed=42, max_ticks=spec.horizon, predator_interval=None,
                         lightning_probability=0, berry_regrowth=0,
                         features={"fishing_nets": False, "alligators": False})
        try:
            manifest = prepare_scenario(sim, name)
            assert manifest["initial_actor"]["strength"] == 5
            assert sim.world.tile((0, 0)).terrain == Terrain.MOUNTAIN
            assert sim.world.tile((12, 12)).terrain == Terrain.GRASS
            assert not sim.agents[0].known_resources
            if bounded:
                sim.trace.events = deque(sim.trace.events, maxlen=256)
                sim.trace.listeners.append(lambda row: None)
            replay = ReplayDigest()
            replay.record(sim)
            environment = initial_environment_digest(sim)
            while not sim.game_over:
                sim.step()
                replay.record(sim)
            hashes.append((environment, replay.finish(sim)))
        finally:
            sim.trace.close()
    assert hashes[0] == hashes[1]


def test_bear_duels_and_shelter_have_interpretable_outcomes(tmp_path):
    report = evaluate_scenarios(suite(tmp_path, ["bear-unarmed", "bear-spear", "bear-shelter"]), tmp_path / "results")
    runs = {run["variant"]: run for run in report["runs"]}
    assert not runs["bear-unarmed"]["endpoints"]["alive_at_cap"]
    assert runs["bear-unarmed"]["endpoints"]["predator_attacks"] > 0
    assert "bear_defeated" in runs["bear-spear"]["endpoints"]  # Seeded hits can miss.
    assert runs["bear-shelter"]["endpoints"]["final_hp"] == 100


def test_hunting_negative_controls_are_real_tool_rejections(tmp_path):
    report = evaluate_scenarios(suite(tmp_path, ["hunt-no-bow", "hunt-untrained"]), tmp_path / "results")
    for run in report["runs"]:
        assert run["endpoints"]["rejected_hunts"] == 1
        assert run["endpoints"]["prey_kills"] == run["endpoints"]["meat_meals"] == 0


@pytest.mark.parametrize("update", [
    {"schema_version": True}, {"seeds": [True]}, {"seeds": [1, 1]}, {"seeds": []},
    {"scenarios": ["bear-spear", "bear-spear"]}, {"scenarios": ["code.py"]},
    {"scenarios": []}, {"scenarios": [{}]}, {"extra": 1},
])
def test_suite_rejects_unknown_values_and_executable_extensions(update):
    config = {"schema_version": 1, "seeds": [17], "scenarios": ["water-carried"], **update}
    with pytest.raises(ValueError):
        validate_suite(config)


def test_shipped_suite_is_valid():
    path = Path(__file__).parents[1] / "agentstranded/configs/evaluation-controlled.json"
    config = validate_suite(json.loads(path.read_text(encoding="utf-8")))
    assert len(config["seeds"]) == 20
    assert set(config["scenarios"]) == set(SCENARIOS)


def test_failed_scenario_contract_is_distinct_from_execution_failure():
    from types import SimpleNamespace
    trial = SimpleNamespace(outcome={"status": "completed", "checks": {"available_water_used": False}})
    grade = ScenarioContractGrader().grade(trial)
    assert not grade.passed
    assert "available_water_used" in grade.reason

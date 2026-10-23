from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from agentstranded import Simulation
from agentstranded.competition import create_simulation, load
from agentstranded.evaluate import evaluate, validate_config
from agentstranded.evaluation_metrics import FoodLedger, Metrics
from agentstranded.reproducibility import ReplayDigest

CONFIG = Path(__file__).parents[1] / "agentstranded/configs"


def evaluation_config(tmp_path, **updates):
    config = load(CONFIG / "evaluation.json")
    config.update(team=str(CONFIG / "team.json5"), competition=str(CONFIG / "competition.json"),
                  seeds=[17], max_ticks=40)
    config.update(updates)
    path = tmp_path / "evaluation.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_headless_evaluation_censoring_pairing_and_framework_contracts(tmp_path):
    config = evaluation_config(tmp_path)
    report = evaluate(config, tmp_path / "results", events=True)
    assert len(report["runs"]) == 3
    assert report["framework_experiment"]["summary"]["passed"] == 3
    assert len({run["initial_environment_sha256"] for run in report["runs"]}) == 1
    for run in report["runs"]:
        assert run["status"] == "completed" and run["termination"] == "tick_limit"
        assert all(actor["censored"] for actor in run["metrics"]["survivors"])
        assert all(actor["death_cause"] is None for actor in run["metrics"]["survivors"])
        assert run["duration_seconds"] > 0 and run["peak_python_bytes"] is None
        with gzip.open(tmp_path / "results" / run["events_file"], "rt", encoding="utf-8") as handle:
            assert any(json.loads(line)["event"] == "simulation.ended" for line in handle)
    assert all(comparison["paired_seeds"] == 1 for comparison in report["comparisons"])
    assert (tmp_path / "results/report.html").exists()
    with pytest.raises(FileExistsError):
        evaluate(config, tmp_path / "results")


def test_measurement_does_not_change_gameplay(tmp_path):
    config = evaluation_config(tmp_path, max_ticks=1200,
                               variants=[{"name": "baseline", "overrides": {}}])
    report = evaluate(config, tmp_path / "results")
    rules = load(CONFIG / "competition.json")
    rules["max_ticks"] = 1200
    team = load(CONFIG / "team.json5", json5=True)
    sim = create_simulation(team, rules, 17)
    replay = ReplayDigest()
    replay.record(sim)
    while not sim.game_over:
        sim.step()
        replay.record(sim)
    assert report["runs"][0]["replay_sha256"] == replay.finish(sim)


def test_fifo_food_provenance_survives_cooking_trades_and_inheritance():
    metrics = Metrics()
    def event(name, **data):
        metrics.consume({"event": name, "tick": 1, **data})
    event("wildlife.killed", agent="a", kind="rabbit", meat=1)
    event("wildlife.killed", agent="a", kind="deer", meat=4)
    event("inventory.transferred", sender="a", recipient="b", items={"meat": 1})
    event("food.cooked", agent="b", raw="meat", cooked="cooked_meat")
    event("survivor.estate_stored", agent="b", position=[1, 2], items={"cooked_meat": 1})
    event("shelter.claimed", agent="c", position=[1, 2], inherited={"cooked_meat": 1})
    event("food.consumed", agent="c", item="cooked_meat", amount=1, nutrition=55,
          effective_nutrition=20)
    assert metrics.actor("c")["meals_by_source_fifo"] == {"rabbit": 1}
    assert metrics.actor("c")["wasted_nutrition"] == 35
    assert metrics.food.take("a", "meat", 4) == {"deer": 4}
    event("food.consumed", agent="c", item="meat", amount=1, nutrition=35, effective_nutrition=35)
    assert metrics.actor("c")["unknown_meat_meals"] == 1


def test_unknown_inventory_never_gets_fabricated_species():
    ledger = FoodLedger()
    ledger.reconcile("a", {"meat": 2})
    assert ledger.take("a", "meat", 2) == {"unknown": 2}


def test_swap_reconciles_unknown_existing_food_before_receiving_known_food():
    metrics = Metrics()
    metrics.consume({"event": "wildlife.killed", "tick": 1, "agent": "a", "kind": "rabbit", "meat": 1})
    metrics.consume({"event": "inventory.transferred", "tick": 2, "sender": "a", "recipient": "b",
        "items": {"meat": 1}, "sender_inventory_before": {"meat": 1}, "recipient_inventory_before": {"meat": 1}})
    metrics.consume({"event": "inventory.transferred", "tick": 2, "sender": "b", "recipient": "a",
        "items": {"meat": 1}, "sender_inventory_before": {"meat": 2}, "recipient_inventory_before": {"meat": 0}})
    assert metrics.food.take("a", "meat", 1) == {"unknown": 1}
    assert metrics.food.take("b", "meat", 1) == {"rabbit": 1}


def test_skill_crafting_and_using_are_distinct_and_uses_not_double_counted():
    metrics = Metrics()
    metrics.consume({"event": "skill.learned", "tick": 1, "agent": "a", "skill": "fishing", "source": "discovery"})
    for tick, name, args, metadata in [(2, "craft", {"item": "fishing_rod"}, {}), (3, "fish", {}, {})]:
        metrics.consume({"event": "tool.started", "tick": tick, "agent": "a", "tool_name": name, "arguments": args})
        metrics.consume({"event": "tool.finished", "tick": tick, "agent": "a", "tool_name": name,
                         "status": "completed", "result_metadata": metadata})
    skill = metrics.actor("a")["skills"]["fishing"]
    assert skill["crafts"] == 1 and skill["uses"] == 1 and skill["first_use_tick"] == 3


def test_repeated_state_at_one_tick_is_not_double_counted():
    sim = Simulation(agents=1, predator_interval=None)
    metrics = Metrics()
    sim.trace.listeners.append(metrics.consume)
    actor = sim.agents[0]
    actor.thirst = 80
    actor.inventory["water"] = 1
    sim.tick = 1
    sim._record_states()
    sim._record_states()
    assert metrics.actor(actor.id)["samples"] == 1
    assert metrics.actor(actor.id)["exposure_ticks"]["thirst_with_carried_water"] == 1


def test_water_failure_and_stall_metrics_have_bounded_evidence():
    metrics = Metrics(stall_ticks=3)
    for tick in range(1, 101):
        metrics.consume({"event": "tool.started", "tick": tick, "agent": "a",
                         "tool_name": "observe_surroundings"})
    actor = metrics.actor("a")
    assert actor["max_observe_streak"] == 100
    assert actor["suspected_observe_stalls"] == 1
    assert len(metrics.evidence["suspected_observe_stall"]) <= 3


def test_consumption_event_measures_actual_capped_relief():
    sim = Simulation(agents=1, predator_interval=None)
    metrics = Metrics()
    sim.trace.listeners.append(metrics.consume)
    actor = sim.agents[0]
    actor.hunger = 3
    actor.inventory["berries"] = 1
    sim.eat(actor, "berries")
    data = metrics.actor(actor.id)
    assert data["food_units"] == {"berries": 1}
    assert data["nutrition"] == {"berries": 3}
    assert data["wasted_nutrition"] == 7


def test_disabled_features_remove_discovery_policy_and_hazards():
    from agentstranded.progression import ready
    from agentstranded.simulation import Terrain
    sim = Simulation(agents=1, predator_interval=None, features={"fishing_nets": False, "alligators": False})
    actor = sim.agents[0]
    actor.learned_skills.add("fishing")
    actor.known_resources["wood"] = {(1, 1)}
    actor.known_tiles[(1, 1)] = Terrain.LAKE
    sim.tick = 5000
    assert not ready(sim, actor, "net_fishing")
    assert sim.policy._net_action(actor) is None
    with pytest.raises(ValueError, match="disabled"):
        sim.learn_skill(actor, "net_fishing", "teacher")
    with pytest.raises(ValueError, match="disabled"):
        sim.craft(actor, "fishing_net")
    sim.world.tile(actor.position).terrain = Terrain.LAKE
    sim.lakes.rules = {**sim.lakes.rules, "alligator_probability": 1}
    sim.lakes.encounter(actor)
    assert actor.health == 100


@pytest.mark.parametrize("change", [
    {"seeds": [17, 17]}, {"seeds": [True]}, {"max_ticks": 0},
    {"variants": [{"name": "../bad", "overrides": {}}]},
    {"variants": [{"name": "bad", "overrides": {"seed": 8}}]},
    {"variants": [{"name": "bad", "overrides": {"features": {"alligators": 0}}}]},
])
def test_invalid_evaluation_configuration_is_rejected(change):
    config = deepcopy(load(CONFIG / "evaluation.json"))
    config.update(change)
    with pytest.raises(ValueError):
        validate_config(config)


def test_html_escapes_untrusted_names_and_unicode(tmp_path):
    config = evaluation_config(tmp_path)
    config_data = load(config)
    team = load(CONFIG / "team.json5", json5=True)
    team["survivors"][0]["name"] = '<script>“Ari”</script>'
    path = tmp_path / "team.json"
    path.write_text(json.dumps(team, ensure_ascii=False), encoding="utf-8")
    config_data["team"] = str(path)
    config.write_text(json.dumps(config_data), encoding="utf-8")
    evaluate(config, tmp_path / "results")
    text = (tmp_path / "results/report.html").read_text(encoding="utf-8")
    assert "<script>" not in text
    assert "&lt;script&gt;“Ari”&lt;/script&gt;" in text


def test_failed_cases_are_explicit_and_excluded_from_comparisons(monkeypatch, tmp_path):
    from agentstranded import evaluate as module
    config = evaluation_config(tmp_path)
    monkeypatch.setattr(module.Simulation, "step", lambda self: (_ for _ in ()).throw(RuntimeError("fixture failure")))
    report = evaluate(config, tmp_path / "results")
    assert all(run["status"] == "error" for run in report["runs"])
    assert all(comparison["paired_seeds"] == 0 and comparison["mean_score_delta"] is None for comparison in report["comparisons"])
    assert report["framework_experiment"]["summary"]["failed"] == 3


def test_ctrl_c_preserves_partial_results_without_models(monkeypatch, tmp_path):
    from agentstranded import evaluate as module
    def interrupt(self):
        raise KeyboardInterrupt
    monkeypatch.setattr(module.Simulation, "step", interrupt)
    report = evaluate(evaluation_config(tmp_path), tmp_path / "results")
    assert report["interrupted"] and report["runs"][0]["status"] == "interrupted"
    assert (tmp_path / "results/results.json").exists()


def test_optional_memory_measurement_records_python_peak_and_releases_tracer(tmp_path):
    import tracemalloc
    config = evaluation_config(tmp_path, max_ticks=5, variants=[{"name": "baseline", "overrides": {}}])
    report = evaluate(config, tmp_path / "results", memory=True)
    assert report["runs"][0]["peak_python_bytes"] > 0
    assert not tracemalloc.is_tracing()

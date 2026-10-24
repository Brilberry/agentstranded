"""Authored diagnostic arenas; no player code, models or competition balance verdicts."""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean
from uuid import uuid4

from bbagents import ToolCall
from bbagents.evaluation import Grade
from bbagents.experiments import Dataset, EvaluationCase, run_dataset
from bbagents.memory import MemoryStore

from .climate import Conditions
from .competition import engine_metadata, load, validate_competition, validate_team
from .evaluate import IntegrityGrader, aggregate_metrics, isolated_environment, render_report, simulate_case
from .reproducibility import canonical, encode
from .simulation import Predator, Terrain, Tile
from .wildlife import Animal, SPECIES
from .weapons import snapshot as weapon_snapshot


@dataclass(frozen=True)
class Scenario:
    family: str
    controller: str
    horizon: int
    weapon: str | None = None
    sheltered: bool = False
    water: str = "none"
    prey: str | None = None
    trained: bool = True
    weapon_uses: int | None = None


SCENARIOS = {
    "bear-unarmed": Scenario("bear", "fixed-duel", 40),
    "bear-spear": Scenario("bear", "fixed-duel", 40, weapon="spear"),
    "bear-worn-spear": Scenario("bear", "fixed-duel", 40, weapon="spear", weapon_uses=4),
    "bear-shelter": Scenario("bear", "fixed-wait", 40, sheltered=True),
    "bear-policy": Scenario("bear", "normal-policy", 40, weapon="spear"),
    "water-adjacent": Scenario("water", "normal-policy", 80, water="adjacent"),
    "water-distant": Scenario("water", "normal-policy", 80, water="distant"),
    "water-carried": Scenario("water", "normal-policy", 80, water="carried"),
    "water-absent": Scenario("water", "normal-policy", 80),
    "hunt-rabbit": Scenario("hunting", "fixed-hunter", 80, weapon="bow", prey="rabbit"),
    "hunt-deer": Scenario("hunting", "fixed-hunter", 80, weapon="bow", prey="deer"),
    "hunt-boar": Scenario("hunting", "fixed-hunter", 80, weapon="bow", prey="boar"),
    "hunt-rabbit-policy": Scenario("hunting", "normal-policy", 80, weapon="bow", prey="rabbit"),
    "hunt-no-bow": Scenario("hunting", "fixed-hunter", 80, prey="rabbit"),
    "hunt-untrained": Scenario("hunting", "fixed-hunter", 80, weapon="bow", prey="rabbit", trained=False),
}


class ScenarioContractGrader:
    def grade(self, trial):
        if trial.outcome["status"] != "completed":
            return Grade(False, "No completed scenario to check")
        checks = trial.outcome["checks"]
        failed = [name for name, passed in checks.items() if not passed]
        return Grade(not failed, ", ".join(failed) if failed else
                     "Applicable contracts passed" if checks else "No per-trial balance threshold; descriptive only")


class MildClimate:
    """Fixed warm spring weather removes temperature/weather as confounders."""
    def at(self, tick, day_length):
        return Conditions("spring", "sunny", 20)


class ProbePolicy:
    """Scripted tool choices, executed through the real registry and simulation step."""
    def __init__(self, sim, scenario, delegate):
        self.sim, self.scenario, self.delegate = sim, scenario, delegate

    def replan(self, actor, reason):
        # Scripted probes have no strategic plan to revise after a rejected tool.
        actor.current_plan = None

    def decide(self, actor):
        sim, spec = self.sim, self.scenario
        actor.decision_source = spec.controller
        if spec.controller == "fixed-wait":
            return ToolCall("observe_surroundings")
        if spec.controller == "fixed-duel":
            bear = sim.predators[0]
            if bear.alive and actor.energy >= 4 and sim.tick >= actor.next_attack_tick:
                return ToolCall("attack", {"predator_id": bear.id})
            return ToolCall("observe_surroundings")
        prey = sim.wildlife.animals[0]
        # Negative controls make one real, invalid request, then wait. No fake kill.
        if not spec.trained or spec.weapon is None:
            return ToolCall("hunt", {"animal_id": prey.id}) if sim.tick == 1 else ToolCall("observe_surroundings")
        if actor.inventory["meat"] and actor.hunger >= 35:
            return ToolCall("eat", {"item": "meat"})
        if actor.thirst >= 64 and sim.distance(actor.position, (12, 11)) <= 1:
            return ToolCall("drink")
        if prey.alive:
            if sim.wildlife.can_hunt(actor, prey):
                return ToolCall("hunt", {"animal_id": prey.id})
            if sim.distance(actor.position, prey.position) > 1 and actor.energy >= 3:
                return ToolCall("move", {"direction": self.delegate._direction_for(actor, prey.position)})
        return ToolCall("observe_surroundings")


def prepare_scenario(sim, name):
    """Replace generated terrain before observation, instrumentation and replay start."""
    spec = SCENARIOS[name]
    for y, row in enumerate(sim.world.tiles):
        for x in range(len(row)):
            row[x] = Tile(Terrain.GRASS if 9 <= x <= 17 and 9 <= y <= 17 else Terrain.MOUNTAIN,
                          fish_stock=0, fish_capacity=0)
    sim.climate = MildClimate()
    sim.conditions = sim.climate.at(0, sim.day_length)
    sim.predators.clear()
    sim.wildlife.animals.clear()
    sim.trace.events.clear()  # Discard generated-world events: they describe a different world.
    sim.event_log.clear()
    actor = sim.agents[0]
    actor.position = (12, 12)
    actor.health, actor.hunger, actor.thirst, actor.energy = 100, 0, 0, 100
    actor.visibility, actor.intelligence, actor.strength, actor.endurance = 3, 50, 5, 5
    actor.inventory.clear()
    actor.weapon_durability.clear()
    actor.known_tiles.clear()
    actor.known_resources.clear()
    # Constructor observation/memory belongs to the discarded generated island.
    actor.memory = MemoryStore()
    actor.feedback.clear()
    actor.current_plan = None
    actor.home, actor.sheltered, actor.seen_wildlife = None, False, False
    actor.objective = "Explore independently"
    actor.learned_skills.clear()
    if spec.weapon:
        actor.inventory[spec.weapon] = 1
        if spec.weapon_uses is not None:
            actor.weapon_durability[spec.weapon] = [spec.weapon_uses]
    if spec.family == "bear":
        sim.predators.append(Predator("scenario-bear", "bear", (13, 12), 150, hunger=90, thirst=0))
    if spec.sheltered:
        tile = sim.world.tile(actor.position)
        tile.shelter_owner = actor.id
        tile.shelter_residents.add(actor.id)
        actor.home, actor.sheltered = actor.position, True
    if spec.family == "water":
        actor.thirst = 80
        if spec.water in ("adjacent", "distant"):
            position = (12, 11) if spec.water == "adjacent" else (16, 16)
            sim.world.tile(position).terrain = Terrain.RIVER
        if spec.water == "carried":
            actor.inventory.update(flask=1, water=2)
        # Known terrain isolates water access/navigation from exploration luck.
        actor.known_tiles = {(x, y): tile.terrain for y, row in enumerate(sim.world.tiles)
                             for x, tile in enumerate(row)}
    if spec.family == "hunting":
        actor.hunger = 65
        sim.world.tile((12, 11)).terrain = Terrain.RIVER
        if spec.trained:
            actor.learned_skills.update(("bow", "hunting"))
        sim.wildlife.animals.append(Animal("scenario-prey", spec.prey, (13, 12), SPECIES[spec.prey]["health"]))
    manifest = {"name": name, "version": 1, **asdict(spec),
        "initial_actor": {"position": actor.position, "health": actor.health, "hunger": actor.hunger,
            "thirst": actor.thirst, "energy": actor.energy, "inventory": dict(actor.inventory),
            "skills": sorted(actor.learned_skills), "weapon_durability": weapon_snapshot(actor), "intelligence": actor.intelligence,
            "strength": actor.strength, "endurance": actor.endurance, "visibility": actor.visibility},
        "arena": "9x9 grass, mountain boundary, no resource regrowth, fixed sunny 20C spring",
        "initial_predators": canonical(sim.predators), "initial_wildlife": canonical(sim.wildlife.animals)}
    sim.trace.record("evaluation.scenario_prepared", manifest)
    sim.observe(actor)
    delegate = sim.policy
    if spec.controller == "normal-policy":
        delegate._update_objective(actor)
        delegate.replan(actor, "controlled scenario")
    else:
        sim.policy = ProbePolicy(sim, spec, delegate)
    sim._record_states()
    return manifest


def endpoints(sim, run):
    actor = sim.agents[0]
    metrics = run["metrics"]["survivors"][0]
    name = run["variant"]
    spec = SCENARIOS[name]
    facts = {"alive_at_cap": actor.alive, "final_hp": actor.health,
        "final_thirst": actor.thirst, "death_cause": actor.death_cause,
        "prey_kills": sum(metrics["kills"].values()),
        "meat_meals": sum(metrics["food_units"].get(item, 0) for item in ("meat", "cooked_meat")),
        "predator_attacks": run["metrics"]["events"].get("predator.attacked", 0),
        "bear_defeated": bool(sim.predators and not sim.predators[0].alive),
        "drinks": sum(metrics["drinks"].values()),
        "hunting_attempts": sum(metrics["hunts"].values()),
        "rejected_hunts": metrics["failures"].get("hunt", 0)}
    facts["final_weapon_durability"] = weapon_snapshot(actor)
    facts["broken_weapons"] = run["metrics"]["events"].get("weapon.broken", 0)
    checks = {}
    if spec.sheltered:
        checks["shelter_blocks_attacks"] = facts["predator_attacks"] == 0
    if spec.family == "hunting" and (not spec.trained or spec.weapon is None):
        checks["unqualified_hunt_rejected"] = facts["rejected_hunts"] == 1 and facts["prey_kills"] == 0
    if spec.family == "water":
        if spec.water == "none":
            checks["absent_water_cannot_be_consumed"] = facts["drinks"] == 0
        else:
            checks["available_water_used"] = facts["drinks"] > 0
    return {"endpoints": facts, "checks": checks}


def validate_suite(config):
    if not isinstance(config, dict) or set(config) != {"schema_version", "seeds", "scenarios"}:
        raise ValueError("controlled suite requires schema_version, seeds, scenarios")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ValueError("unsupported schema_version")
    seeds, names = config["seeds"], config["scenarios"]
    if (not isinstance(seeds, list) or not 1 <= len(seeds) <= 1000
            or any(type(seed) is not int or not 0 <= seed <= 4294967295 for seed in seeds)
            or len(set(seeds)) != len(seeds)):
        raise ValueError("seeds must be 1–1000 unique nonnegative 32-bit integers")
    if (not isinstance(names, list) or not names or any(not isinstance(name, str) or name not in SCENARIOS for name in names)
            or len(set(names)) != len(names)):
        raise ValueError("scenarios must be unique names from SCENARIOS")
    return config


def evaluate_scenarios(config_path, output, *, events=False, progress=False):
    config, output = validate_suite(load(Path(config_path))), Path(output)
    root = Path(__file__).parent / "configs"
    rules = validate_competition(load(root / "competition.json"))
    team = validate_team(load(root / "team.json5", json5=True), rules)
    team = deepcopy(team)
    team["survivors"] = team["survivors"][:1]
    # A diagnostic subject, not a tournament-valid entry; all configurable traits fixed.
    profile = team["survivors"][0]
    profile["attributes"] = dict.fromkeys(profile["attributes"], 5)
    profile["personality"] = dict.fromkeys(profile["personality"], 5)
    profile["behavior"] = {}
    variants = [{"name": name, "overrides": {"predator_interval": None, "lightning_probability": 0,
        "berry_regrowth": 0, "features": {"alligators": False}}} for name in config["scenarios"]]
    configuration = {**config, "suite": "controlled-v1", "team": team, "competition": rules,
        "variants": variants, "stall_ticks": 20, "engine": engine_metadata(), "events_archived": events,
        "max_ticks": None, "measure_python_memory": False}
    output.mkdir(parents=True, exist_ok=False)
    runs = []
    def execute(case, holder, trial_id, settings):
        name = case.input["variant"]["name"]
        settings = {**settings, "max_ticks": SCENARIOS[name].horizon}
        trial = simulate_case(case, holder, trial_id, settings, team, rules, output, events=events,
            prepare=lambda sim: prepare_scenario(sim, name))
        outcome = dict(trial.outcome)
        if outcome["status"] == "completed":
            outcome.update(endpoints(holder["simulation"], outcome))
        runs.append(outcome)
        if progress:
            print(f"{case.id}: {outcome['status']}", flush=True)
        if outcome["status"] == "interrupted":
            raise KeyboardInterrupt
        return replace(trial, outcome=canonical(outcome), configuration=configuration)
    cases = tuple(EvaluationCase(f"{variant['name']}:seed-{seed}", {"seed": seed, "variant": variant})
                  for seed in config["seeds"] for variant in variants)
    experiment, interrupted = None, False
    try:
        experiment = run_dataset(Dataset("agentstranded-controlled", "1", cases), configuration=configuration,
            environment=isolated_environment, execute=execute,
            graders={"execution_integrity": IntegrityGrader(), "scenario_contract": ScenarioContractGrader()})
    except KeyboardInterrupt:
        interrupted = True
    summary = {}
    for name in config["scenarios"]:
        rows = [run for run in runs if run["variant"] == name and run["status"] == "completed"]
        points = [run["endpoints"] for run in rows]
        checks = [value for run in rows for value in run["checks"].values()]
        summary[name] = {"controller": SCENARIOS[name].controller, "completed": len(rows),
            "alive_at_cap": sum(point["alive_at_cap"] for point in points),
            "mean_final_hp": round(mean(point["final_hp"] for point in points), 2) if points else None,
            "mean_drinks": round(mean(point["drinks"] for point in points), 2) if points else None,
            "survival_fraction": sum(point["alive_at_cap"] for point in points) / len(points) if points else None,
            "mean_hp_of_survivors": mean(point["final_hp"] for point in points if point["alive_at_cap"])
                if any(point["alive_at_cap"] for point in points) else None,
            "prey_kills": sum(point["prey_kills"] for point in points),
            "meat_meals": sum(point["meat_meals"] for point in points),
            "checks_passed": sum(checks), "checks_checked": len(checks)}
    report = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "interrupted": interrupted, "configuration": configuration,
        "configuration_sha256": hashlib.sha256(encode(configuration)).hexdigest(), "runs": runs,
        "framework_experiment": asdict(experiment) if experiment else None,
        "aggregates": canonical(aggregate_metrics(runs, variants)), "comparisons": [], "scenario_summary": summary}
    (output / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    render_report(report, output)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(Path(__file__).parent / "configs/evaluation-controlled.json"))
    parser.add_argument("--output")
    parser.add_argument("--events", action="store_true")
    args = parser.parse_args()
    output = args.output or str(Path("evaluation-runs") / (datetime.now().strftime("%Y%m%d-%H%M%S-controlled-") + uuid4().hex[:8]))
    try:
        report = evaluate_scenarios(args.config, output, events=args.events, progress=True)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Controlled report: {(Path(output) / 'report.html').resolve()}")
    if report["interrupted"]:
        raise SystemExit(130)
    if any(run["status"] != "completed" or not all(run["checks"].values()) for run in report["runs"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

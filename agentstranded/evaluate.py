"""Headless rules-only evaluation: paired seeds, streaming metrics and HTML reports."""
from collections import Counter, deque
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import html
import json
import math
from pathlib import Path
import re
from statistics import mean, median
from time import perf_counter
import tracemalloc
from uuid import uuid4

from bbagents.evaluation import Grade, TrialEvidence
from bbagents.experiments import Dataset, EvaluationCase, run_dataset

from .competition import MAPS, engine_metadata, load, score, validate_competition, validate_team
from .evaluation_metrics import Metrics
from .progression import RULES
from .reproducibility import ReplayDigest, canonical, encode, initial_environment_digest
from .simulation import Simulation
from .tracing import row_for


def validate_config(config):
    required = {"schema_version", "team", "competition", "seeds", "max_ticks", "variants"}
    if not isinstance(config, dict) or not required <= set(config) <= required | {"stall_ticks"}:
        raise ValueError("evaluation requires schema_version, team, competition, seeds, max_ticks, variants")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ValueError("unsupported evaluation schema_version")
    for key in ("team", "competition"):
        if not isinstance(config[key], str) or not config[key]:
            raise ValueError(f"{key} must be a path")
    seeds = config["seeds"]
    if (not isinstance(seeds, list) or not 1 <= len(seeds) <= 1000
            or any(type(seed) is not int or not 0 <= seed <= 4294967295 for seed in seeds)
            or len(set(seeds)) != len(seeds)):
        raise ValueError("seeds must be 1–1000 distinct nonnegative 32-bit integers")
    for key, value in (("max_ticks", config["max_ticks"]), ("stall_ticks", config.get("stall_ticks", 20))):
        if type(value) is not int or not 1 <= value <= 1000000:
            raise ValueError(f"{key} must be an integer from 1 to 1000000")
    variants = config["variants"]
    if not isinstance(variants, list) or not 1 <= len(variants) <= 20:
        raise ValueError("variants must contain 1–20 entries; first is baseline")
    names = set()
    allowed = {"features", "predator_interval", "resource_scale", "berry_regrowth", "lightning_probability", "starting_season"}
    for variant in variants:
        if not isinstance(variant, dict) or set(variant) != {"name", "overrides"}:
            raise ValueError("variant requires name and overrides")
        name, overrides = variant["name"], variant["overrides"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", name) or name in names:
            raise ValueError("variant names must be unique lowercase identifiers, max 32 characters")
        names.add(name)
        if not isinstance(overrides, dict) or set(overrides) - allowed:
            raise ValueError(f"override keys must be in {sorted(allowed)}")
        for key, value in overrides.items():
            if key == "features":
                if (not isinstance(value, dict) or set(value) - {"fishing_nets", "alligators"}
                        or any(type(flag) is not bool for flag in value.values())):
                    raise ValueError("features supports boolean fishing_nets and alligators")
            elif key == "starting_season":
                if value not in ("spring", "summer", "autumn", "winter"):
                    raise ValueError("invalid starting_season")
            elif key == "predator_interval":
                if value is not None and (type(value) is not int or value < 1):
                    raise ValueError("predator_interval must be positive or null")
            elif key == "berry_regrowth":
                if type(value) is not int or not 0 <= value <= 100:
                    raise ValueError("berry_regrowth must be an integer 0–100")
            elif (type(value) not in (int, float) or not math.isfinite(value)
                  or not (0 <= value <= 1 if key == "lightning_probability" else 0 < value <= 10)):
                raise ValueError(f"invalid numeric override {key}")
    return {"stall_ticks": 20, **config}


class IntegrityGrader:
    def grade(self, trial):
        okay = trial.outcome["status"] == "completed"
        return Grade(okay, "Simulation completed" if okay else "Simulation failed/interrupted; exclude from balance averages")


@contextmanager
def isolated_environment(case):
    holder = {"simulation": None}
    try:
        yield holder
    finally:
        if holder["simulation"] is not None:
            holder["simulation"].trace.close()


def simulate_case(case, holder, trial_id, configuration, team, rules, output, *, events=False, memory=False):
    seed, variant = case.input["seed"], case.input["variant"]
    metrics = Metrics(configuration["stall_ticks"])
    started = perf_counter()
    archive = None
    measured_memory = memory and not tracemalloc.is_tracing()
    if measured_memory:
        tracemalloc.start()
    result = {"seed": seed, "variant": variant["name"], "status": "error", "case_id": case.id}
    try:
        preset = MAPS[rules["map_name"]]
        parameters = {"agents": len(team["survivors"]), "seed": seed, "team": team,
            "resource_scale": preset["resources"], "berry_regrowth": preset["regrowth"],
            "predator_interval": preset["predator_interval"], "max_ticks": configuration["max_ticks"],
            "starting_season": rules["starting_season"], **variant["overrides"]}
        sim = Simulation(**parameters)
        holder["simulation"] = sim
        distances = sim._water_distances()
        result["initial_water_distance_by_slot"] = {actor.id: distances.get(actor.position) for actor in sim.agents}
        result["initial_environment_sha256"] = initial_environment_digest(sim)
        result["features"] = sim.features
        for event in sim.trace.events:
            metrics.consume(row_for(event))
        sim.trace.events = deque(sim.trace.events, maxlen=256)
        sim.trace.listeners.append(metrics.consume)
        if events:
            path = output / f"{variant['name']}-seed-{seed}.jsonl.gz"
            archive = gzip.open(path, "wt", encoding="utf-8")
            for event in sim.trace.events:
                archive.write(json.dumps(row_for(event)) + "\n")
            sim.trace.listeners.append(lambda row: archive.write(json.dumps(row) + "\n"))
            result["events_file"] = path.name
        replay = ReplayDigest()
        replay.record(sim)
        while not sim.game_over:
            sim.step()
            replay.record(sim)
        result.update(status="completed", end_tick=sim.tick,
            termination="all_dead" if not any(actor.alive for actor in sim.agents) else "tick_limit",
            replay_sha256=replay.finish(sim), score=score(sim), metrics=metrics.finish(sim))
    except KeyboardInterrupt:
        result.update(status="interrupted", error="KeyboardInterrupt")
    except Exception as exc:
        result.update(error=f"{type(exc).__name__}: {exc}")
    finally:
        if archive is not None:
            archive.close()
        result["duration_seconds"] = perf_counter() - started
        result["peak_python_bytes"] = tracemalloc.get_traced_memory()[1] if measured_memory else None
        if measured_memory:
            tracemalloc.stop()
        result["ticks_per_second"] = result.get("end_tick", 0) / result["duration_seconds"]
    if result["status"] != "completed" and holder["simulation"] is not None:
        result.update(end_tick=holder["simulation"].tick, partial_metrics=metrics.finish(holder["simulation"]))
    return TrialEvidence(case.id, trial_id, "Structured simulation measurements", (), canonical(result),
                         configuration,
                         result["duration_seconds"], cost=0)


def paired_comparisons(runs, variants):
    baseline = variants[0]["name"]
    indexed = {(run["variant"], run["seed"]): run for run in runs}
    comparisons = []
    for variant in variants[1:]:
        pairs = []
        for candidate in runs:
            if candidate["variant"] != variant["name"]:
                continue
            base = indexed.get((baseline, candidate["seed"]))
            if not base or base["status"] != "completed" or candidate["status"] != "completed":
                continue
            pairs.append({"seed": candidate["seed"],
                "score_delta": candidate["score"]["score"] - base["score"]["score"],
                "survivor_ticks_delta": candidate["metrics"]["summary"]["survivor_ticks"] - base["metrics"]["summary"]["survivor_ticks"],
                "initial_environment_matches": candidate["initial_environment_sha256"] == base["initial_environment_sha256"]})
        comparisons.append({"baseline": baseline, "candidate": variant["name"], "paired_seeds": len(pairs),
            "mean_score_delta": mean(pair["score_delta"] for pair in pairs) if pairs else None,
            "improved": sum(pair["score_delta"] > 0 for pair in pairs),
            "worsened": sum(pair["score_delta"] < 0 for pair in pairs),
            "unchanged": sum(pair["score_delta"] == 0 for pair in pairs), "pairs": pairs})
    return comparisons


def aggregate_metrics(runs, variants):
    result = {}
    for variant in variants:
        rows = [run for run in runs if run["variant"] == variant["name"] and run["status"] == "completed"]
        actors = [actor for run in rows for actor in run["metrics"]["survivors"]]
        samples = sum(actor["samples"] for actor in actors)
        food, nutrition, sources, damage, exposure, first_skills, events = (Counter() for _ in range(7))
        skills = {name: {"learners": 0, "users": 0, "crafts": 0, "uses": 0, "discovery_ticks": []}
                  for name in RULES}
        for run in rows:
            events.update(run["metrics"]["events"])
        for actor in actors:
            food.update(actor["food_units"])
            nutrition.update(actor["nutrition"])
            sources.update(actor["meals_by_source_fifo"])
            damage.update(actor["damage_reported"])
            exposure.update(actor["exposure_ticks"])
            if actor["learning_order"]:
                first_skills[actor["learning_order"][0]] += 1
            for name, data in actor["skills"].items():
                entry = skills.setdefault(name, {"learners": 0, "users": 0, "crafts": 0, "uses": 0, "discovery_ticks": []})
                entry["learners"] += 1
                entry["users"] += data["uses"] > 0
                entry["crafts"] += data["crafts"]
                entry["uses"] += data["uses"]
                entry["discovery_ticks"].append(data["learned_tick"])
        for data in skills.values():
            ticks = data.pop("discovery_ticks")
            data["median_learning_tick"] = median(ticks) if ticks else None
            data["learners_fraction_of_starters"] = data["learners"] / len(actors) if actors else None
        result[variant["name"]] = {"completed_runs": len(rows), "survivors": len(actors),
            "restricted_mean_lifetime": mean(actor["lifetime"] for actor in actors) if actors else None,
            "deaths_by_recorded_cause": Counter(actor["death_cause"] for actor in actors if not actor["alive"]),
            "sampled_survivor_ticks": samples, "food_units": food, "effective_nutrition": nutrition,
            "meal_sources_fifo": sources, "damage_reported": damage, "exposure_ticks": exposure,
            "exposure_fractions": {name: count / samples if samples else None for name, count in exposure.items()},
            "first_skills": first_skills, "skills": skills,
            "deaths_with_water": sum(run["metrics"]["summary"]["deaths_with_water"] for run in rows),
            "suspected_observe_stalls": sum(actor["suspected_observe_stalls"] for actor in actors),
            "unknown_meat_meals": sum(actor["unknown_meat_meals"] for actor in actors),
            "events": events}
    return result


def render_report(report, output):
    def escape(value):
        return html.escape(str(value))
    sections = ["<!doctype html><html><head><meta charset='utf-8'>",
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        "<title>Agent Stranded evaluation</title><style>body{font:16px system-ui;max-width:1150px;margin:30px auto;padding:0 20px}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ccc}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}</style></head><body>",
        "<h1>Agent Stranded evaluation</h1><p>Descriptive results, not an automatic balance verdict. Positive paired deltas favor the candidate. Living survivors at the cap are censored, not dead.</p>",
        "<p>Read <a href='results.json'>results.json</a> for all machine-readable measurements.</p>",
        "<h2>Variant overview</h2><table><tr><th>Variant</th><th>Completed/error</th><th>Mean score</th><th>Median score</th><th>Survivors at cap</th><th>Seconds</th></tr>"]
    for variant in report["configuration"]["variants"]:
        rows = [row for row in report["runs"] if row["variant"] == variant["name"]]
        completed = [row for row in rows if row["status"] == "completed"]
        scores = [row["score"]["score"] for row in completed]
        values = (variant["name"], f"{len(completed)}/{len(rows)-len(completed)}",
            round(mean(scores), 2) if scores else "N/A", median(scores) if scores else "N/A",
            sum(row["metrics"]["summary"]["alive"] for row in completed), round(sum(row["duration_seconds"] for row in rows), 2))
        sections.append("<tr>" + "".join(f"<td>{escape(value)}</td>" for value in values) + "</tr>")
    sections.append("</table><h2>Paired comparisons</h2>")
    for comparison in report["comparisons"]:
        sections.append(f"<h3>{escape(comparison['candidate'])} versus {escape(comparison['baseline'])}</h3><pre>{escape(json.dumps(comparison, indent=2))}</pre>")
    sections.append("<h2>Food, water, damage and learning</h2><p>Rates use observed end-of-tick samples, not eligible-opportunity estimates. Learning fractions use all starters, not just eligible survivors.</p>")
    for name, metrics in report["aggregates"].items():
        sections.append(f"<h3>{escape(name)}</h3><table><tr><th>Food</th><th>Units eaten</th><th>Effective nutrition</th></tr>")
        for item in sorted(set(metrics["food_units"]) | set(metrics["effective_nutrition"])):
            count = metrics["food_units"].get(item, 0)
            sections.append(f"<tr><td>{escape(item)}</td><td>{count}</td><td>{metrics['effective_nutrition'].get(item, 0):.1f}</td></tr>")
        sections.append("</table><h4>Sources, water and injury</h4><pre>" + escape(json.dumps({
            key: metrics[key] for key in ("restricted_mean_lifetime", "deaths_by_recorded_cause", "meal_sources_fifo", "unknown_meat_meals", "exposure_ticks",
                "exposure_fractions", "deaths_with_water", "damage_reported", "suspected_observe_stalls")}, indent=2)) + "</pre>")
        sections.append("<h4>Skill adoption</h4><table><tr><th>Skill</th><th>Learners / starters</th><th>Users</th><th>Median learned tick</th><th>Crafts / uses</th></tr>")
        for skill, data in metrics["skills"].items():
            learned = data["median_learning_tick"] if data["median_learning_tick"] is not None else "N/A"
            sections.append(f"<tr><td>{escape(skill)}</td><td>{data['learners']} / {metrics['survivors']}</td><td>{data['users']}</td><td>{learned}</td><td>{data['crafts']} / {data['uses']}</td></tr>")
        sections.append("</table><p>First skills: " + escape(json.dumps(metrics["first_skills"])) + "</p>")
    sections.append("<h2>Per-run measurements and evidence</h2><p>Stalls are suspicion signals, not proof. Food sources use FIFO accounting; unknown sources are not attributed to rabbits.</p>")
    for run in report["runs"]:
        sections.append(f"<details><summary>{escape(run['variant'])} · seed {run['seed']} · {escape(run['status'])}</summary><pre>{escape(json.dumps(run, indent=2, ensure_ascii=False))}</pre></details>")
    sections.append("</body></html>")
    (output / "report.html").write_text("\n".join(sections), encoding="utf-8")


def evaluate(config_path, output, *, events=False, memory=False, progress=False):
    config_path, output = Path(config_path), Path(output)
    config = validate_config(load(config_path))
    team_path, rules_path = (config_path.parent / config[key] for key in ("team", "competition"))
    rules = validate_competition(load(rules_path))
    team = validate_team(load(team_path, json5=team_path.suffix == ".json5"), rules)
    # A result directory belongs to exactly one invocation; never overwrite evidence.
    output.mkdir(parents=True, exist_ok=False)
    configuration = {**config, "team": team, "competition": rules, "events_archived": events,
                     "measure_python_memory": memory, "engine": engine_metadata()}
    runs, grades = [], []
    cases = [EvaluationCase(f"{variant['name']}:seed-{seed}", {"seed": seed, "variant": variant})
             for seed in config["seeds"] for variant in config["variants"]]
    def execute(case, holder, trial_id, settings):
        trial = simulate_case(case, holder, trial_id, settings, team, rules, output, events=events, memory=memory)
        runs.append(trial.outcome)
        grades.append(asdict(IntegrityGrader().grade(trial)))
        if progress:
            print(f"{case.id}: {trial.outcome['status']} ({trial.duration_seconds:.2f}s)", flush=True)
        if trial.outcome["status"] == "interrupted":
            raise KeyboardInterrupt
        return trial
    experiment = None
    interrupted = False
    try:
        experiment = run_dataset(Dataset("agentstranded-v1", "1", tuple(cases)),
            configuration=configuration, environment=isolated_environment, execute=execute,
            graders={"execution_integrity": IntegrityGrader()})
    except KeyboardInterrupt:
        interrupted = True
    report = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "interrupted": interrupted, "configuration": configuration,
        "configuration_sha256": hashlib.sha256(encode(configuration)).hexdigest(),
        "runs": runs, "execution_grades": grades,
        "framework_experiment": asdict(experiment) if experiment else None,
        "aggregates": canonical(aggregate_metrics(runs, config["variants"])),
        "comparisons": paired_comparisons(runs, config["variants"])}
    (output / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    render_report(report, output)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(Path(__file__).parent / "configs/evaluation.json"))
    parser.add_argument("--output", help="New output directory; must not exist")
    parser.add_argument("--events", action="store_true", help="Stream complete per-run JSONL gzip evidence")
    parser.add_argument("--memory", action="store_true", help="Measure peak Python allocations (slower; not RSS)")
    args = parser.parse_args()
    output = args.output or str(Path("evaluation-runs") / (datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8]))
    try:
        report = evaluate(args.config, output, events=args.events, memory=args.memory, progress=True)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Evaluation report: {(Path(output) / 'report.html').resolve()}")
    if report["interrupted"]:
        raise SystemExit(130)
    if any(run["status"] != "completed" for run in report["runs"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

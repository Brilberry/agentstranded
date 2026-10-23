# Headless evaluation, V1

Read the complete [metric catalog](METRICS_CATALOG.md) for the longer-term backlog.
V1 answers basic survival, food, water, learning, policy-stall and performance
questions through structured evidence. It is not an automatic judge of game fun
or a complete causal/encounter-analysis system.

## Run

From the repository with its virtualenv activated (development dependencies installed):

```sh
python -m agentstranded.evaluate --config agentstranded/configs/evaluation-smoke.json
```

This runs two seeds × three variants × at most 1,600 ticks, without pygame, a model,
postmortem inference or browser launch. It prints progress and the report path.
Open the generated `evaluation-runs/<run>/report.html` yourself. `results.json`
contains all machine-readable results and provenance.

For the larger development suite (20 seeds, 4,000 ticks, same three variants):

```sh
python -m agentstranded.evaluate
```

Optional:

```sh
python -m agentstranded.evaluate \
  --config agentstranded/configs/evaluation-smoke.json \
  --output evaluation-runs/my-first-comparison --events --memory
```

The output directory must not already exist: runs never overwrite prior evidence.
`--events` streams full per-case UTF-8 JSONL gzip archives alongside the metrics.
Without it, only counters, summaries and at most three examples per diagnostic
category are retained. The simulation's in-memory trace is capped at 256 events.
`--memory` measures peak Python allocations via tracemalloc, NOT process RSS/GPU
memory, and slows execution. Durations/ticks-per-second include evaluation and
optional logging/replay/memory instrumentation: compare equivalent settings only.
No external-model cost is incurred; that does not measure financial compute cost.

Ctrl+C preserves available partial results and returns exit code 130. Failed cases
are explicit, retain partial metrics where possible, and are excluded from paired
balance comparisons. Exit code 1 means at least one case failed. Results are
descriptive: an execution-integrity pass is not a declaration that balance is good.

## Experiment JSON

Paths are relative to the evaluation JSON file, not the working directory.

| Key | Values |
| --- | --- |
| `schema_version` | `1` |
| `team` | Path to validated team JSON or JSON5 |
| `competition` | Path to validated competition JSON |
| `seeds` | 1–1,000 distinct integers, 0–4,294,967,295 |
| `max_ticks` | Integer 1–1,000,000; same horizon for every variant |
| `stall_ticks` | Optional integer 1–1,000,000; default 20 consecutive observation actions |
| `variants` | 1–20 entries with unique lowercase `name` and `overrides`; first is baseline |

The evaluation seed list/horizon explicitly override the competition seed list/horizon.
Other competition validation (team budget/count, map, season, rules-only mode) stays
in effect. Cases get fresh worlds and stable team-array spawn slots. Evaluations
are separate experiments, NOT official tournament results using the original settings.

Allowed variant overrides:

- `features`: optional booleans `fishing_nets` / `alligators`; omitted flags use
  organizer defaults. Nets disabled means no discovery, teaching, crafting,
  deployment, passive catching or automatic net-policy investment. Alligators
  disabled removes attacks and caution-based avoidance, not just damage.
- `predator_interval`: positive integer or null (disable scheduled predators).
- `resource_scale`: finite number greater than zero, at most 10.
- `berry_regrowth`: integer 0–100.
- `lightning_probability`: finite number 0–1.
- `starting_season`: spring/summer/autumn/winter.

No arbitrary code, class names, models or unrecognized configuration keys are
accepted. Change one thing per candidate to make results interpretable. For
example, baseline versus no-nets estimates the effect of removing nets, not the
effect of adding them (the delta sign is candidate minus baseline).

## Implemented measurements

| Area | V1 measurements |
| --- | --- |
| Survival | Per-survivor lifetime, dead/right-censored status, final cause/needs, total survivor-ticks, all-alive ticks, alive-at-cap and competition score |
| Injury | Reported damage by recorded source, combined need-damage buckets, bounded event examples, distinct visible predator IDs and alligator counts |
| Food | Units eaten, actual capped hunger relief, wasted nutrition, food sources under FIFO accounting, hunting attempts/kills by species |
| Water | Mean/peak thirst, ticks at urgency threshold, urgent thirst with carried water, dehydration deaths with water, drinks/relief by natural/carried/reservoir source |
| Exposure | Post-tick samples with hunger ≥68, thirst ≥64, energy ≤30, carried food during hunger, physical shelter and lake occupancy; hazard checks |
| Skills | Learning order, tick/source, crafts, actual successful uses, first-use tick, equipment-use counts; suite first-skill distribution and median learning ticks |
| Policy | Tool attempts/failures, policy-source shares, longest repeated-observation/failure streak, suspected observation stalls, five-failure episodes |
| Performance | Case runtime, instrumented ticks/sec, optional traced Python memory peak and event counts |
| Comparison | Paired per-seed score/survivor-tick differences, mean score delta, improved/worse/unchanged counts, initial-environment match flags |

Threshold counts are end-of-tick samples, not exact continuous-time integrals or
proof that an action was feasible throughout the interval. Repeated observations
are a stall suspicion, not a proven deadlock: waiting can be legitimate. Changing
`stall_ticks` changes the diagnostic, not gameplay.
Each case also records initial terrain-path distance from each spawn slot to water;
this is an observer supply/access proxy, not a claim that the survivor knows that
route, that it is safe, or that its travel cost accounts for swimming delays.
Automatic predator-kill hunger/hydration rewards are recorded separately from meals.

Damage aggregates use effective `hp_lost` when explicitly available (predator
attacks), otherwise the recorded damage. A multi-cause need-damage event remains
a combined bucket: V1 does not invent how to split fatal/overkill damage among causes.
Distinct predators seen are not formal encounter episodes or encounter lethality.

Skill learning fractions use ALL starters; V1 does not yet compute prerequisite
opportunity/eligibility denominators. “Not learned” is not automatically a failure.
Learning age equals tick only for current tick-zero starters. First use means a
successful tool/equipment activity, not proof of net benefit; V1 has no payback grader.

## Food provenance: what rabbit consumption means

The inventory currently treats meat as fungible. The observer maintains a FIFO
accounting ledger from wildlife kills, cooking, committed trades, estates and
inheritance. If rabbit meat enters first, then one unit is cooked/transferred and
eaten, that unit is attributed to rabbit under this stated convention. It does
not infer species from nearby kills or narrative text.

The ledger follows known batches through cooking/transfers and reconciles against
inventory snapshots. Missing acquisitions become `unknown`, never guessed rabbit
meat. This is transparent accounting, NOT a hidden physical item identity in the
game. Older logs without structured consumption or transfer events cannot support
equivalent provenance; V1 evaluates fresh runs, not arbitrary old Markdown reports.

For mixed foods, distinguish units from effective nutrition. A meat portion eaten
with only three hunger can be a meal but supplies only three effective nutrition.
Failed actions do not count as food consumption, crafting or successful skill use.

## Evidence and experiment integrity

The harness reuses bbagents `Dataset`, `EvaluationCase`, `run_dataset`, `TrialEvidence`
and `Grade`. Each trial owns a fresh simulation and cleanup. Actual structured
outcomes feed the execution-integrity grader; there is no model judging another
model's narrative. Full transcripts are not retained in each TrialEvidence: bounded
evidence and outcomes live in the result, optional full logs are streamed to disk.

The result records normalized inputs, game/framework source fingerprints, runtime,
initial-environment and gameplay hashes. Observer-on/off replay tests ensure
measurement does not change game decisions. Rules-only repeats are deterministic;
report timestamps, trial IDs, timing/memory readings and compressed log headers are not.
Local Git checkouts also report commit and dirty-worktree status (null when Git
metadata is unavailable). Prefer clean, frozen checkouts for reproducible baselines.

Compare only completed paired seeds; missing/error/interrupted cases are not zero
scores. Inspect the per-seed differences and evidence, not only the average. All
alive-at-cap survivors are censored; V1 reports restricted lifetimes and does not
pretend to estimate their eventual deaths or provide Kaplan–Meier estimates.

Initial-environment hashes should match for net/alligator ablations. Resource or
starting-season experiments intentionally change that hash and are labeled rather
than silently treated as matching environments. Validate conclusions on held-out
seeds and more maps/teams/seasons before changing default balance.

## Next increments (not implemented)

Controlled bear/water/hunting scenarios; explicit encounter and emergency episodes;
full skill eligibility/adoption funnels; resource conservation/supply accounting;
calibrated predeclared balance graders; cross-revision report comparison; uncertainty
intervals and survival analysis; offline ingestion of legacy logs; and model-assisted
trials. See METRICS_CATALOG.md for the complete backlog, not a promise of current coverage.

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

This runs two seeds × two variants × at most 1,600 ticks, without pygame, a model,
postmortem inference or browser launch. It prints progress and the report path.
Open the generated `evaluation-runs/<run>/report.html` yourself. `results.json`
contains all machine-readable results and provenance.

For the larger development suite (20 seeds, 29,200 ticks, baseline and no-alligators):

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

- `features`: optional boolean `alligators`; omitted flags use
  organizer defaults. Fishing nets have been removed entirely. Legacy
  `fishing_nets: false` is accepted as a no-op; `true` is rejected. Alligators
  disabled removes attacks and caution-based avoidance, not just damage.
- `predator_interval`: positive integer or null (disable scheduled predators).
- `resource_scale`: finite number greater than zero, at most 10.
- `berry_regrowth`: integer 0–100.
- `lightning_probability`: finite number 0–1.
- `starting_season`: spring/summer/autumn/winter.

No arbitrary code, class names, models or unrecognized configuration keys are
accepted. Change one thing per candidate to make results interpretable. For
example, disabling alligators removes attacks AND cautious routing, not just damage
(the delta sign is candidate minus baseline). Archived pre-removal net comparisons
are historical results, not configurations to rerun against this engine.

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

Initial-environment hashes should match for alligator ablations. Resource or
starting-season experiments intentionally change that hash and are labeled rather
than silently treated as matching environments. Validate conclusions on held-out
seeds and more maps/teams/seasons before changing default balance.

## Controlled scenarios

```sh
python -m agentstranded.evaluation_scenarios --events
```

The default [controlled suite](configs/evaluation-controlled.json) runs 20 seeds ×
15 authored cases. Like the broad runner, it writes `results.json`, `report.html`
and optional compressed per-case event archives into a new `evaluation-runs/`
directory. `--output` selects a new destination; `--config` selects a JSON containing
exactly `schema_version: 1`, `seeds` (same limits as above) and `scenarios` (a nonempty
list of distinct names from the table). No executable plugins or arbitrary setup
overrides are accepted. There is no model, UI or automatic browser launch.

| Scenario | Controller | Condition / question | Tick cap |
| --- | --- | --- | --- |
| `bear-unarmed` | Fixed duel | Unarmed survivor versus one hungry 150-HP bear | 40 |
| `bear-spear` | Fixed duel | Same scene, spear supplied; preparedness changes the duel | 40 |
| `bear-worn-spear` | Fixed duel | Same scene, only four spear uses remaining | 40 |
| `bear-shelter` | Fixed wait | Survivor stays in an owned shelter; attacks must remain zero | 40 |
| `bear-policy` | Normal policy | Spear supplied, but survivor can choose flight instead of fighting | 40 |
| `water-adjacent` | Normal policy | Thirst 80, known river one cell away | 80 |
| `water-distant` | Normal policy | Same needs, known river eight Manhattan steps away | 80 |
| `water-carried` | Normal policy | Two water units and a flask, no natural water | 80 |
| `water-absent` | Normal policy | No water at all: negative availability control | 80 |
| `hunt-rabbit` | Fixed hunter | Skilled bow user versus one rabbit | 80 |
| `hunt-deer` | Fixed hunter | Same equipment, one deer | 80 |
| `hunt-boar` | Fixed hunter | Same equipment, one retaliating boar | 80 |
| `hunt-rabbit-policy` | Normal policy | Same rabbit scene; does normal policy hunt and eat it? | 80 |
| `hunt-no-bow` | Fixed negative control | One hunt request without a bow must be rejected | 80 |
| `hunt-untrained` | Fixed negative control | Bow supplied without bow/hunting knowledge; request must be rejected | 80 |

Each trial has one standardized survivor (intelligence 50 internally, strength and
endurance 5, personality 50 internally, visibility 3), a 9×9 grass arena bounded by
mountains, fixed sunny spring weather at 20°C, no scheduled predators/lightning,
no berries/wood/stone, and no alligators/nets. Hunger/thirst start at zero except
water cases (thirst 80) and hunting cases (hunger 65). The survivor starts at
(12,12), the bear/prey at (13,12). The hunting arena includes a river at (12,11).
Natural needs, cooldowns, animal movement/fleeing, hit randomness, damage, tool
validation, resource rewards and food consumption still use production code.
Seeded RNG streams remain in use; maps/weather/traits are fixed, not randomized.
Known terrain is supplied in water cases to isolate access/navigation from discovery.
Hunting skills/equipment are supplied, so these cases do not measure skill learning.

Fixed duels repeatedly attack when legal and wait during cooldowns, without moving
or recovering. The fixed hunter tracks the authored prey's position even outside
visibility, pursues it, shoots only through the normal visibility/tool checks, and
eats raw meat when hungry. It is an explicitly privileged mechanics probe, NOT a
legal competition controller. Negative controls request one illegal hunt and then
wait. Normal-policy cases retain the game's unmodified rules/behavior selectors.
All actions execute through the real tool registry and `Simulation.step()`.
Artificial arenas and supplied equipment are evaluation-only; gameplay is unchanged.

Reports add survival/HP, bear defeat/attack counts, drinks, prey kills, meat meals,
hunting attempts/rejections, a prepared-state manifest and per-case replay hashes.
The bbagents runner grades execution integrity separately from narrow scenario
contracts: shelter protection, use of available water, absence of phantom water,
and rejection of unqualified hunting. The scoped 20% fresh-spear bear target is
evaluated over the larger combat suite, not as a pass/fail on an individual duel.
No hunting-success target is declared yet. Zero applicable checks is not proof of good balance.
CLI exit 1 can therefore mean a **completed diagnostic found a policy/mechanics
problem**, not just a runner error. Failed checks are highlighted in HTML; evidence
is preserved. Ctrl+C saves partial results and exits 130. Unrelated scenarios are
not combined into paired score deltas. Competition score shown by the shared report
is not a meaningful arena ranking; use scenario endpoints instead.

Initial validation found `water-carried` failing: with no known natural source,
the normal policy remained in `locate-water`. This is now fixed: carried water or
a stocked valid home reservoir satisfy that plan prerequisite. The diagnostic
remains active as a regression check. Original reports are preserved unchanged.

## One-year and combat balance experiments

See [Combat and year-survival rules](COMBAT_AND_LONGEVITY.md) for the assumptions,
weapon lifetimes and limits of the 20% bear target.

```sh
python -m agentstranded.evaluate --config agentstranded/configs/evaluation-easy-year.json --events
python -m agentstranded.evaluation_scenarios --config agentstranded/configs/evaluation-combat.json --events
```

A year is `365 × 80 = 29,200` ticks. The easy-year configuration has three initial
development seeds, all seasons, the real easy map and an explicitly budget-valid
100-point candidate team. It is a hypothesis about useful settings, not an optimal
team or a guarantee. The team concentrates intelligence/endurance/perception in
two survivors, avoids combat, uses private shelters and responds to needs early.
The remaining survivors have fewer points; all five spawn normally. Inspect
`survived_one_year` per survivor and in each run summary; do not count early deaths
as reaching the target simply because the configured horizon is one year. A
living survivor at the cap has achieved the target but is still right-censored.
The small smoke suite remains a quick regression tool, not a longevity benchmark.

## Next increments (not implemented)

Explicit natural encounter and emergency episodes; full skill eligibility/adoption
funnels; resource conservation/supply accounting;
calibrated predeclared balance graders; cross-revision report comparison; uncertainty
intervals and survival analysis; offline ingestion of legacy logs; and model-assisted
trials. See METRICS_CATALOG.md for the complete backlog, not a promise of current coverage.

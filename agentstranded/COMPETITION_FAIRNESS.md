# Competition fairness and reproducibility

## Official execution

Run competitions with the headless, rules-only runner:

```sh
python -m agentstranded.competition \
  --team agentstranded/configs/team.json5 \
  --competition agentstranded/configs/competition.json
```

An organizer must freeze and publish the game revision, bbagents dependency,
Python version, packaged defaults/map presets, competition JSON, seed list, and
scoring formula before accepting results. Run all entries on the same controlled
environment. Participants submit data, not Python code; installing or executing
participant code is not part of this competition format.

The runner validates both files, rejects unsupported settings, evaluates every
configured seed with a fresh world, and reports the mean score. Do not compare
entries run with different engine/configuration fingerprints. A GUI run selects
one seed and is useful for observation, not a replacement for the multi-seed result.
Models are prohibited in competition mode: asynchronous inference and wall-clock
cooldowns are not deterministic. Postmortems are commentary, never scoring inputs.

## What a seed fixes

For an identical validated team, configuration, engine, and supported runtime,
the rules-only simulation is expected to reproduce tick-by-tick gameplay and scores.
Map generation, initial resources, spawn slots, wildlife populations, random
traits, weather, lightning and predator arrivals use explicit seeded generators.
Different subsystems have separate streams, so extra survivor exploration does not
consume the weather or predator-spawn random sequence.

Calendar/weather are functions of the seed, starting season and simulation tick.
Lightning is sampled only during rain. All tiles are equally eligible targets.
Neither frame rate, pauses nor processing speed enters rules-only decisions or
scoring; the final result depends on simulation ticks, not real elapsed time.

Every team receives the same ordered starting slots for a seed. Survivor array
order assigns those slots and also determines the fixed action-processing order.
Players can reorder their team deliberately; the organizer must not silently
reorder entries. Sequential processing can favor earlier actors when resources
are contested; it is a public rule, not simultaneous resolution or equal slot value.

Different teams do NOT receive a frozen replay of all animal movements. Survivors
change resource stocks, trigger fleeing, provoke predators and alter movement
opportunities. Those responses, hunting attempts and their random draws depend on
the actions actually taken. Same seed means matching initial/exogenous conditions,
not identical subsequent encounters regardless of decisions.

## Stable ordering

Resource targets tied on distance use lexicographic `(x, y)` order. Social offer
maintenance and advertised inventory use sorted identifiers/item names rather
than hash-dependent set iteration. Other ordered lists, fixed direction order,
and seeded random tie-breaking remain game rules. JSON object key order is not a
player strategy; survivor and priority arrays are deliberately ordered.

## Result fingerprints

The result JSON includes:

- `engine_sha256`: game/framework Python and packaged JSON/JSON5 contents, with
  relative paths and no checkout-dependent absolute paths.
- `configuration_sha256`: canonical validated team and competition settings.
- `runtime`: Python implementation/version and operating-system information.
- `replay_format` and each run's `replay_sha256`: a canonical digest of survivor,
  animal, climate and homestead state after each tick, plus the final tile state.
- Per-survivor lifetimes, all-alive ticks, per-seed score and mean score.
- Each seed's `initial_environment_sha256`: initial terrain/resources, wildlife,
  ordered spawn slots and climate, excluding survivor traits. This should match
  across competing teams given the same environment settings and survivor count.

The gameplay fingerprint excludes report timestamps, run/span IDs, filesystem
paths and memory-record IDs. It is a regression/comparison aid, not a full saved
game, proof of honest execution, or a way to resume play. It does not hash every
internal memory/plan or each intermediate tile mutation. Trusted scoring requires
the organizer to run entries, not accept an unverified participant-provided hash.

## Verification and limits

Replay tests run matching teams/seeds in separate processes with different
`PYTHONHASHSEED` values. CI runs on Python 3.11 on Linux, macOS and Windows and
checks committed reference fingerprints. A deliberate rules/config change may
change those fingerprints; inspect the change and regenerate fixtures explicitly,
never automatically bless a mismatch.

These tests cover representative finite runs, not a mathematical guarantee for
every possible configuration or future dependency version. Use the frozen
organizer environment as the authoritative result. Pin exact dependency versions
for a tournament; a score from another Python/framework/game version is not
automatically equivalent. Historical reports and LLM summaries are not expected
to be byte-identical even when gameplay is identical.

Using several predeclared seeds reduces dependence on a lucky spawn, but publishing
them lets players tune to them. If generalization matters, precommit to an additional
held-out seed set and reveal it after submissions close; the organizer must apply
that same set to every entry. This is tournament policy, not implemented secrecy.

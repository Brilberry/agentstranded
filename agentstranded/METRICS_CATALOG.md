# Simulation evaluation metric catalog

This is the persistent evaluation backlog. A metric being listed here does not
mean it is implemented. V1 scope and supported fields are documented separately
in EVALUATION.md. Never manufacture a value when the available evidence cannot
support it: report null/N/A and an instrumentation limitation.

## Measurement contract

Every metric needs a definition, unit, event/state source, denominator, aggregation
level (survivor/team/seed/suite), censoring treatment and evidence references.
Separate observations, associations and experimental effects. Zero opportunities
means N/A, not a 0% success rate. Bound online counters/samples; stream optional
raw evidence rather than loading entire Markdown histories into RAM.

Freeze game/framework/runtime versions, settings and input fingerprints. Compare
paired seeds and teams. Deterministic repetitions of one case are reproducibility
checks, not independent statistical evidence. Distinguish all-dead, tick-limited,
interrupted and failed runs. Living survivors at a time limit are right-censored,
not deaths at that time. Do not infer final causes from temporal coincidence.

## 1. Identity and reproducibility

- Game revision, framework version, engine/configuration/environment/replay hashes.
- Seed, map, starting season, team order and every submitted attribute/behavior.
- Feature flags and parameter overrides; baseline/candidate identity.
- Decision mode, model/version and inference settings.
- Tick limit, actual final tick, termination reason and partial/error status.
- Python implementation/version/platform, evaluator schema/version and scenario ID.

## 2. Team survival

- Each survivor's lifetime and censored/dead status.
- First/subsequent/final death times; total survivor-ticks and all-alive ticks.
- Alive counts and survival probability at predefined checkpoints.
- Fraction reaching the limit; competition score and its components.
- Median and tail outcomes across seeds, seed-to-seed spread and worst cases.
- Concentration of survival among team members; attribute/profile associations.
- Survival curves by map, season, profile and variant, with censoring disclosed.

## 3. Death, injury and recovery

- Final recorded cause; cumulative and final-window damage by wolves, bears,
  boars, alligators, starvation, dehydration, exhaustion and hypothermia.
- Fatal-event health, needs, exposure, inventory and physical shelter status.
- Time below health thresholds; near-death episodes and repeat injuries.
- Recovery speed, time to recovery, recovered/died fractions after injury.
- Death with food/water carried, near usable resources, or shortly after a new
  activity; label temporal associations rather than causal findings.
- Distinguish reported attack damage/overkill from effective HP loss.

## 4. Hunger, nutrition and food use

- Average/peak hunger, warning/emergency/damage-threshold exposure.
- Emergency count/duration, starvation damage, response time and time to relief.
- Hunger emergencies with edible carried food; interrupted/restarted food plans.
- Acquisition, consumption, transfer, loss and unused reserves by food type.
- Nominal versus effective nutrition, capped/wasted relief and nutrition shares.
- Food diversity, single-source dependency periods, raw versus cooked meals.
- Feasible cooking opportunities missed; food reserves at death.
- Actions, travel, energy and material investment per effective nutrition unit.

## 5. Adoption funnels

- Berries: discovered → approached → gathered → consumed.
- Rods: fishing learned → rod crafted → lake reached → fish caught → consumed.
- Nets: skill learned → crafted → deployed → caught → collected → consumed.
- Hunting: prey observed → pursued/attempted → killed → meat acquired → consumed.
- Gardens: skill learned → inputs acquired → planted → matured → harvested → consumed.
- Cooking: skill learned → raw food available → fire available → cooked → consumed.
- At every stage: participants/opportunities, conversion rate, elapsed time,
  failures/abandonment, material/energy/travel costs, survival until payoff.

## 6. Water availability and use

- Source distribution and reachable distance from spawns/homes/regions.
- Water routes requiring crossings or blocked/threatened by predators.
- First discovery/drink times; mean/peak thirst and threshold exposure.
- Thirst-emergency count/duration, dehydration damage/deaths, response/relief latency.
- Travel/energy costs; natural/carried/reservoir drinking shares.
- Flasks filled, drunk, traded, lost and inherited.
- Urgent thirst with carried water, adjacent source, or usable home reservoir.
- Repeated trips despite carried water; shortages versus discovery/access/policy failures.
- Reservoir learning/crafting/installation/fill/use funnel, utilization, empty periods,
  refill costs, inherited use and lightning loss; paired effect on travel/survival.

## 7. Energy, rest and sleep

- Mean/min energy, low/exhausted exposure, expenditure by action, exhaustion damage.
- Recovery by rest/sleep; work-rest oscillation and interrupted recovery.
- Ticks blocked from intended work by energy; productive time lost to recovery.
- Nights slept/skipped, sleep timing/duration, indoors/outdoors, interruptions/causes.
- Failed sleep attempts, bed/ownership conflicts, sleep healing and emergency rest.

## 8. Predator balance

- Spawns, initial needs, encounters per survivor-day and detection distance.
- Calm/hunting/provoked state, pack sizes/mergers, lone/group encounters.
- Encounter duration and repeated encounters with the same predator.
- Fight/flee/shelter/recovery choices; escape rate/time/distance/energy cost.
- Damage dealt/received, cooldown use, kills by weapon and ally count.
- Death during/after encounters, residual HP/energy, predators beaten before death.
- Outmatched fights, terrain/energy-blocked escapes; sheltered attacks (must be zero).
- Predator time pursuing/feeding/drinking/roaming.
- Stratify by species, survivor equipment/health/allies. Use controlled encounters
  alongside natural runs: bear kill rate alone is not a balance target.

## 9. Wildlife, hunting and food provenance

- Initial/time-varying rabbit/deer/boar populations; observations and hunting opportunities.
- Attempts, hits/misses, injury, escape, kills, pursuit time/distance and energy per kill.
- Meat produced, cooked, consumed, traded, inherited, lost or unused, by source species.
- Predator versus survivor kills, boar retaliation/damage, local/global extinction.
- Failed hunts followed by food emergencies; equipped hunting opportunities ignored.
- Preserve source through transfers/cooking; generic meat cannot prove rabbit
  consumption by temporal inference. Disclose any FIFO accounting convention and
  unknown provenance rather than pretending fungible items have physical identities.

## 10. Ecosystem and finite resources

- Initial/remaining stocks by type/region; extraction and regeneration rates.
- Consumption shares among survivors, wildlife, bears, rods and nets.
- Local depletion duration and remaining supplies near homes.
- Congestion/contention, depletion failures, stale resource knowledge and relocation.
- Fish-stock use/recovery and berry competition; resources remaining at termination.
- Inventory/resource conservation checks; distinguish local scarcity from global abundance.

## 11. Skills and knowledge spread

- Prerequisites reached, discovery eligibility, actual learning and eligibility-to-learning lag.
- Personal age/intelligence at discovery, source (self/taught), order/rank per survivor.
- Common first/second/third skills, prerequisite bottlenecks, eligible-but-unlearned skills.
- Learned-but-unused skills, first successful use, use count, investment/payoff before death.
- Death before eligibility; skills never discovered across the suite.
- Lesson requests/offers/acceptance/rejection/deferral, paid/free lessons, time saved.
- Knowledge diffusion beyond the first discoverer and loss of unique knowledge at death.
- Report rates among all starters AND eligible survivors; do not penalize late-game
  skills simply because many survivors died before reaching their prerequisites.

## 12. Crafting and tool usefulness

- Eligibility, attempts/success/failure, age at first craft, resources/energy/time invested.
- Meaningful uses, unused/duplicate crafts, trade/inheritance/abandonment/destruction.
- Payback time where measurable; observational adoption outcomes and paired feature effects.
- Nets: deployed occupancy, full/forgotten time, caught-versus-collected fish,
  travel/work per collection, interaction with rods/bears, ownership failures/recovery.

## 13. Shelters and inheritance

- First shelter time, solo/shared work/material/energy/elapsed costs.
- Projects started/completed/stalled/abandoned; shelters per survivor/map.
- Empty/occupied/shared/abandoned counts, physical shelter time and hazard-time use.
- Home-food-water travel, unauthorized/full-bed attempts, predator protection.
- Lightning destruction, rebuilding/claim latency, resources/tools inherited and used.
- Shelters and stored resources unused at game end.

## 14. Climate, fire and clothing

- Seasonal/weather exposure, outdoor hazardous-weather time and protective response latency.
- Exposure distribution, hypothermia episodes/damage/deaths, heat-driven extra thirst.
- Available shelter ignored; fires lit/refueled/expired, fuel used, useful/unattended warmth.
- Clothing progression/equipping/use and unequipped-but-available protection.
- Crop frost/drought losses; lightning/shelter hits, contents lost and recovery cost.
- Measure actual exposure/health benefit, not merely garment possession.

## 15. Exploration and lake risk

- Unique tiles, exploration overlap, discovery of water/food/home sites/prey.
- Distance/travel energy, revisits, loops, movement failures, travel per successful acquisition.
- River/lake crossings, lake-occupancy ticks including swim delays.
- Alligator attacks per exposure tick, first-hit survival, repeat-hit deaths.
- Caution/risk knowledge versus water exposure, known safer routes, dry-detour costs.
- Stranding/repeated rerouting; do not normalize lake attacks by survivor count alone.

## 16. Social behavior

- Encounters/first contact, messages by topic/intent, information received and used.
- Stale information acted upon; answers/refusals/prices/ignored requests.
- Trade offers/acceptance/expiry/cancellation, nutrition/hydration transferred and relieved needs.
- Reserve violations (must be zero), collaboration invitations/acceptance/contributions.
- Shared-project payoff, interrupted collaboration and partner death.
- Helping versus own reserves, communication/trade loops without useful outcomes.

## 17. Policy and plan failures

- Controller action shares, emergency response latency, tool rejections and causes.
- Repeated identical failures, plans started/completed/interrupted/abandoned/resumed.
- Milestone durations/replanning, restarted goals without progress.
- Repeated uninformative observations, suspected stalls, defensive deadlocks.
- Optional work displacing emergencies; legal useful lifesaving actions ignored.
- Inventory/memory inconsistency and missing-skill/material attempts.
- Recovery from stale observations. Define feasible action precisely; hindsight
  speculation is not evidence of a policy bug. Legitimate waiting is not a deadlock.

## 18. Model effectiveness and cost

- Requests admitted/deferred/completed/failed/timed out, per survivor/day.
- Tokens, latency, inference waiting, cache hits, schema/evidence failures.
- Plan acceptance/completion, useful milestones, model versus fallback actions.
- Superseded plans, infeasible proposals, cost per useful milestone.
- Survival/resource/tool-diversity changes versus rules-only baselines.
- Postmortem completeness/failures/unsupported claims; model timing requires repeated
  trials distinct from deterministic rules-only replay checks.

## 19. Performance and observability

- Headless ticks/second and runtime per day/year; traced peak Python allocations,
  process RSS where available (name the measurement, not a generic memory claim).
- Events/trace bytes per day, report-generation time/size, buffer/queue high-water marks.
- Pathfinding/policy/wildlife/reporting time; inference CPU/GPU cost separately.
- Crashes, incomplete runs, reproducibility mismatches, malformed/missing events.
- Missing provenance, conservation failures, incomplete analyses and encoding compatibility.

## 20. Feature comparisons

- Paired per-seed survival/score/first-death/checkpoint differences.
- Changed damage/emergency burden, adoption/use, investment/payoff and other-feature effects.
- Ecosystem depletion, profile/map/season interactions and performance overhead.
- Improved/unchanged/worse fractions, worst regressions, evidence and opportunity counts.
- Report insufficient evidence when exposure is rare. Predeclare desired ranges;
  do not assume every survivor should learn every skill or defeat every bear.
- Feature switches must remove the mechanic AND policy incentives. Keep unrelated
  RNG streams intact. Use development and held-out seeds, not only handpicked wins.

## Initial delivery priority

V1: survival/censoring, recorded damage/death causes, food consumption and explicit
provenance accounting, water-use failures, learning order and basic skill adoption,
suspected policy stalls/tool failures, performance, paired comparisons and evidence.
Controlled scenario suites, full eligibility funnels, encounter analyses, calibrated
graders, advanced survival statistics and model-assisted trials follow separately.

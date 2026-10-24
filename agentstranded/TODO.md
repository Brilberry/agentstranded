# Agent Stranded — feature backlog

Unchecked entries are future ideas; sections marked DONE are implemented.
Each numbered section can be selected as a separate implementation task.

## 1. General skill progression — DONE

- [x] Extend the existing fishing-learning mechanism into a reusable progression system.
- [x] Give each skill explicit prerequisites: personal survival time, intelligence,
  prerequisite skills, tools, materials, or relevant discoveries.
- [x] Let intelligence influence learning speed, without making every survivor
  learn every skill at the same simulation tick.
- [x] Support learning from other knowledgeable survivors where appropriate,
  retaining individual communication, teaching, and trading policies.
- [x] Record discoveries, lessons, prerequisites, and unlocks in memory and traces;
  make them understandable to players and available to agent decisions.

Implemented in `progression.py` with bbagents SkillSource/Skill guidance, procedural
memory, shared recipe gates, and prerequisite-aware free/paid lessons.

## 2. Growing vegetables — DONE

- [x] Add a learnable vegetable-growing skill with explicit prerequisites.
- [x] Define planting inputs, suitable ground, growth time, and harvesting.
- [x] Let survivors decide whether investing in a future harvest is preferable
  to gathering or fishing now.
- [x] Connect crop growth and survival to seasons, rain, frost, and heat drought.

Depends on: **1**. Seasonal integration can follow **10** separately.

## 3. Fishing nets — REMOVED after evaluation

Previously implemented; removed from skills, recipes, tools, policies, model tasks,
trading and rendering. Rod fishing remains. Original evaluation reports are kept
as historical evidence; no further net work is planned.

## 4. Bow crafting and hunting — DONE

- [x] Add a learnable bow-crafting skill and recipe.
- [x] Unlock hunting as an activity once the survivor has the required knowledge
  and suitable tool; do not give every survivor effective hunting immediately.
- [x] Let survivors hunt deer, boars, and rabbits, not just fight predators.
- [x] Define pursuit, escape, attack, and meat collection, including time and
  energy costs and the possibility of an unsuccessful hunt.
- [x] Let survivors compare hunting with other food sources based on risk and need.

Implemented with learned bow/hunting skills, the `hunt(animal_id)` tool, local
and model-plan food controllers, finite meat yields, misses, cooldowns, energy
costs, boar retaliation, traces, and deterministic tests. See the example guide
for balance values. Cooking is implemented under **9**.

Depends on: **1** and **5**. Cooking can be added afterward through **9**.

## 5. Wildlife present from the start — DONE

- [x] Populate the island with deer, boars, and rabbits at tick zero.
- [x] Let animals roam independently before survivors learn to hunt.
- [x] Give animals food preferences and resource-seeking behavior (berries in v1).
- [x] Make deer and rabbits flee from dangerous animals and approaching hunters.
- [x] Define initial populations and any later reproduction or replenishment rules.

Initial populations: five deer, four boars, eight rabbits. No reproduction or
replacement spawns in v1; hunting can exhaust the population. Wildlife spawn,
movement, and hunting randomness are separate from scheduled calamities and
predator arrivals. Predator diets are implemented under **6**.

Can be implemented before hunting; supports **4** and **6**.

## 6. Food competition and predator diets — DONE

Implemented finite fish stocks shared by survivors and bears, daily bounded
replenishment, wildlife berry consumption, bear fish feeding and active pursuit
of deer/rabbits when human prey is not in range. Feeding changes hunger and uses
the shared attack cooldown; deer/rabbits retain their escape behavior.

- [x] Make wildlife consume the same finite resources available to survivors:
  for example, deer eat berries and bears eat fish.
- [x] Extend predator food choices beyond attacking humans. Bears may prefer
  humans but can also pursue deer or eat fish when appropriate.
- [x] Make deer difficult prey because they can detect danger and escape.
- [x] Make feeding affect hunger and subsequent hunting decisions.
- [x] Define finite lake fish availability and shared consumption/replenishment.

Depends on: **5**. Builds on existing predator hunger and thirst.

## 7. Live sports-style commentary — PLAN ONLY

- [ ] Produce short, lively sports-broadcast commentary every 500 ticks, not continuously.
- [ ] Allow significant events to trigger an update: deaths, new skills/tools,
  narrow escapes, major collaboration, calamities and season changes.
- [ ] Coalesce bursts and enforce bounded asynchronous inference using the shared gate.
- [ ] Ground every factual claim in recorded ticks; clearly mark interpretation.
- [ ] Keep commentary observer-only and excluded from survivor context, decisions and scoring.
- [ ] Provide a concise live panel and report transcript, with a deterministic no-model fallback.

Detailed proposal, scheduling, framework reuse and acceptance tests:
[Live commentary plan](LIVE_COMMENTARY_PLAN.md). No commentary implementation yet.

Independent of the ecosystem work; builds on current traces and postmortems.

## 8. Rare alligator encounters in lakes — DONE

- [x] Add a very small risk of an alligator attack while crossing lake water.
- [x] Define encounter probability, damage, warning signs, and escape options.
- [x] Let cautious survivors weigh a longer land route against a risky crossing.
- [x] Decide how survivors discover or learn about the danger without granting
  them hidden knowledge of alligator positions.
- [x] Preserve existing water-crossing slowdowns and include encounter evidence in traces.

Defaults: 0.2% per lake-occupancy tick, 55 HP, 12-tick encounter cooldown.
The first attack leaves at least 1 HP; two unhealed attacks kill. Shores and rivers
are safe from alligators. Healing between attacks can prevent two-hit death.

Builds on current lake crossing. Route choice should reflect individual caution.

## 9. Fire-making and cooking — DONE

- [x] Add a learnable fire-making skill with tools/material prerequisites.
- [x] Let survivors light and maintain fires, with fuel and time costs.
- [x] Add roasting of fish and meat, making cooked food more nutritious than raw food.
- [x] Define the nutritional differences and cooking costs before balancing food preferences.
- [x] Let fires provide warmth in cold conditions.

Depends on: **1**. Fish cooking can precede hunting; meat cooking follows **4**.
Warmth integrates with **11**.

## 10. Seasons, weather, and temperature — DONE

- [x] Introduce a seasonal cycle and changing ambient temperature.
- [x] Add weather conditions, including summer thunderstorms and extreme heat or cold.
- [x] Make survivors observe conditions and adjust plans: for example, spend more
  time sheltered during dangerous weather.
- [x] Define seasonal timing and weather durations: a 365-day year, three-month seasons, daily weather,
  and a shared temperate profile across all maps. Per-map climate tuning is deferred.
- [x] Integrate thunderstorms with the existing lightning system.

Spring is the default and gentlest start; competition JSON can select any season.
The seeded cycle, temperatures, conditions, shelter response, heat-driven thirst,
and cold exposure are implemented, documented, and tested.

Environmental foundation for **11**; crop effects can be added to **2** later.

## 11. Exposure, hypothermia, heat, and warmth — DONE

Exposure, hypothermia, heat-driven thirst, shelter protection, fire warmth, and
equipped leather protection are implemented.

- [x] Track cold exposure and make dangerous cold cause health loss and potentially
  fatal hypothermia.
- [x] Make hot conditions increase thirst more rapidly.
- [x] Give shelter a meaningful protective effect against temperature and storms.
- [x] Let a maintained fire provide warmth and influence the decision to stay nearby.
- [x] Explain weather-related injuries and deaths in traces, reports, and summaries.

Depends on: **10**; fire-based warmth also requires **9**.

## 12. Explicit per-tick shelter status in traces and postmortems — DONE

- [x] Add an `in_shelter` field to every `survivor.state` event: integer `1` when
  the survivor is physically on a tile containing an intact shelter, otherwise `0`.
- [x] Compute the flag from current position and world state when recording the
  event, rather than inferring it from home ownership or a potentially stale cache.
- [x] Preserve the flag in the single-file survival report and model postmortem
  context, so analyses do not have to guess shelter occupancy from coordinates.
- [x] Explain the field in the postmortem instructions. A value of `0` means
  outside a shelter; an absent field in older logs means unknown, not outside.
- [x] Test entering/leaving a shelter, visiting a shelter owned by somebody else,
  and destruction by lightning to verify the flag reflects that tick's state.

Independent observability improvement; also supports weather/exposure analysis
in **10–11**. Shelter presence is distinct from ownership and sleeping-bed capacity.

## 13. Shelter water reservoirs — DONE

- [x] Add a learnable recipe for crafting a water reservoir kept at a shelter.
- [x] Give each reservoir a finite capacity and track its current water volume.
- [x] Let residents drink stored water at their shelter instead of traveling to
  a lake or river each time; drinking must consume the stored supply.
- [x] Define construction materials, capacity, and refill methods/costs before
  implementation. A reservoir stores water; it does not create unlimited water.
- [x] Let survivor plans account for remaining water and decide when to refill.
- [x] Define access for shared shelters, inheritance when residents die, and what
  happens to the reservoir and its contents when a shelter is destroyed.
- [x] Expose capacity and remaining water in observations, traces, and reports.

Builds on existing crafting, water collection, shelters, and inheritance. Weather
or rain-based collection can be considered later with **10**, not assumed in v1.

## 14. Skinning and leather garments — DONE

- [x] Add a learnable skinning skill for sufficiently experienced survivors who
  already know how to hunt, with explicit intelligence/time/tool prerequisites.
- [x] Let a successful hunt provide an opportunity to skin the animal for a hide;
  prevent repeated harvesting of the same carcass.
- [x] Define eligible animals, hide yields, required tools, and whether hides need
  processing into leather before garment crafting.
- [x] Add a leather-garment recipe and a way to equip the finished clothing.
- [x] Make equipped leather clothing reduce cold exposure or hypothermia damage,
  rather than grant complete immunity to freezing conditions.
- [x] Include learning, skinning, crafting, equipment, and cold protection in
  observations, memory, traces, and reports.

Depends on existing hunting and skill progression. Cold-protection effects require
**10–11**; skinning and garment crafting can be implemented before those systems.

## 15. Evaluation harness — V1 DONE; extended metrics backlog remains

- [x] Persist the full metric catalog in METRICS_CATALOG.md.
- [x] Headless paired-seed baseline/candidate runs with isolated bbagents trials.
- [x] Streaming survival, food provenance/consumption, water, learning, stalls and performance metrics.
- [x] JSON results, standalone HTML comparisons and optional compressed event evidence.
- [x] Feature-off ablations remove both mechanics and policy incentives.
- [x] Controlled bear, water-access and hunting scenarios with separate scripted/normal-policy cases, HTML reports and explicit diagnostic contracts.
- [x] Fix carried-water prerequisite handling; add weapon wear and scoped bear calibration; remove fishing nets.
- [x] Add full-year easy-mode candidate configs and year-survival metrics; demonstrate year-long survival on a development seed.
- [ ] Validate year-long easy survival across held-out seeds/teams (initial candidate reached a year on only one of three seeds).
- [ ] Full opportunity/eligibility funnels and calibrated balance targets.
- [ ] Extended metrics and statistical analyses from METRICS_CATALOG.md.

See [Evaluation guide](EVALUATION.md). Execution-integrity checks are not balance verdicts.

## Cross-cutting requirements for each feature

- [ ] Keep mechanics configurable and document new JSON5 options, prerequisites,
  tools, and allowed values when introduced.
- [ ] Preserve competition fairness: common initial conditions and independent
  environmental randomness, without allowing survivor choices to alter future
  scheduled calamities or spawns. Natural ecosystem consequences may diverge.
- [ ] Reuse bbagents planning, tools, memory, authorization, and tracing where they fit;
  identify genuine framework gaps rather than hiding them in example-specific code.
- [ ] Add deterministic tests, evaluate survival balance and performance, and
  update the example documentation.

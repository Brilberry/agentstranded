# Fishing nets, lake encounters, and shelter evidence

## Fishing nets

`net_fishing` is learned after fishing, at personal age `1000 - 4 × intelligence`
ticks (internal intelligence is 0–100), with remembered wood and lake terrain.
Nearby survivors may teach it through the existing free/paid knowledge protocol;
lessons still require prerequisite fishing knowledge.

| Tool | Requirements and effects |
| --- | --- |
| `craft("fishing_net")` | Net-fishing knowledge, eight wood, two energy; woven wooden strips, no metal |
| `place_net()` | Three energy, one carried net, adjacent lake; one deployed net per survivor, one per tile |
| `collect_net()` | Two energy, within one tile of an accessible net; transfers its entire catch, leaves net deployed |
| `retrieve_net()` | Two energy, within one tile; returns net and any catch to inventory |

A net catches one fish every 20 ticks, up to three fish in storage. It consumes
the same finite stock as rod fishing and bear feeding. Full nets stop consuming;
empty lakes yield nothing. Existing daily bounded replenishment still applies.
Nets produce a batch of up to three fish per collection, reducing active fishing
actions, not outperforming a rod at instant catch speed or creating new food.
Net updates occur in sorted tile order before survivor actions and daily regrowth.
This is a public competition rule, including when nets contest limited stocks.

Living owners retain exclusive collection/retrieval access. A deceased owner's
net becomes accessible to others; recovery returns the item once. Carrying or
trading a recovered net does not bypass knowledge or the one-deployed-net limit.
Nets persist until retrieved; no automatic replacement fish or net spawning.
The viewer marks nets with a tan outline and catch count; hover reveals ownership.

Rule policies prepare nets when safe and locally useful, unless food preferences
favor berries or exploration outranks learning; they can return to collect catches.
Models can choose `set_fishing_net` and use `gather_food` to collect stocked nets.
Tools go through the existing actor-scoped bbagents ActionRuntime. SkillSource,
procedural/episodic memory, observations, tool feedback and traces carry the feature.

## Alligator encounters

Lake water has a default **0.2% chance per occupied tick per survivor** of an
alligator attack, including swimming delays. Entry through movement or fleeing
also checks the hazard, at most once for that survivor/tick. Rivers, dry shores
and intact shelters are safe from this hazard. Rod fishing/net collection from
shore do not require entering water.

Default damage is **55 HP**, with a **12-tick cooldown** between encounters for
that survivor. The first attack is capped to leave at least 1 HP, even if already
injured. Two attacks without intervening healing kill; healing can make a later
attack survivable. An attack wakes a sleeper and is recorded with damage, health,
location and encounter count. Death is attributed to `alligator attack`.

Seeing lake terrain records a general risk warning in memory; it does not reveal
alligator locations. Caution 70+ survivors penalize known lake tiles in goal-route
planning and can take a longer dry route. Unknown lake tiles are not magically
avoided; urgent predator escape still prioritizes escape. Existing multi-cell
water-crossing slowdowns remain unchanged.

Each survivor has a separate seeded hazard stream. Different routes or amounts of
time in lake water naturally change encounters; they do not consume weather,
predator-spawn, wildlife or another survivor's hazard RNG sequence.

Net capacity/interval and alligator probability/damage/cooldown are organizer-owned
values in `configs/defaults.json` under `lakes`. They are included in the engine
fingerprint; competitors must use the same defaults. Changing them changes the
ruleset, not an individual survivor's allocated attributes.

## Explicit shelter evidence

Every new `survivor.state` event includes integer `in_shelter`: `1` means physically
on an intact shelter tile, `0` means outside. It is computed directly from current
position and world state, not home ownership, sleeping-bed permission or a cached
flag. A visitor can be physically sheltered without being entitled to sleep there.
Lightning destruction changes the next recorded flag to zero.

The flag is embedded in Markdown/HTML event history and available in model
postmortem context. Missing values in older logs mean **unknown**, not zero.

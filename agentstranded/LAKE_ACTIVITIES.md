# Lake encounters and shelter evidence

Fishing nets have been removed after evaluation. Rod fishing, finite lake fish
stocks, bear feeding and alligator hazards remain.

## Alligator encounters

Lake water has a default **0.2% chance per occupied tick per survivor** of an
alligator attack, including swimming delays. Entry through movement or fleeing
also checks the hazard, at most once for that survivor/tick. Rivers, dry shores
and intact shelters are safe from this hazard. Rod fishing from
shore does not require entering water.

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

Alligator probability/damage/cooldown are organizer-owned
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

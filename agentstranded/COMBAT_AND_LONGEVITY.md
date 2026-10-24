# Combat, weapon condition and year-long survival

## Water-policy correction

The `locate-water` prerequisite now recognizes carried water and a stocked valid
home reservoir, even when no natural source is known. The existing reach/drink
steps still enforce access, navigation and consumption. This prevents searching
indefinitely while carrying a filled flask; it does not create water or reveal
unknown rivers. `water-carried` remains a controlled regression scenario.

## Weapons

| Item | Uses per new copy | Activities that consume a use |
| --- | --- | --- |
| Spear | 12 | Melee attacks, including misses |
| Bow | 24 | Hunting shots or adjacent predator attacks, including misses |
| Stone axe | 32 | Successful wood gathering or melee attacks |
| Stone knife | 20 | Skinning or melee attacks |

The last use still completes, then the item breaks and is removed. Rejected tools
consume no uses. Each copy has its own remaining-use count; acquiring/crafting a
second copy does not repair the first. The freshest available copy is used.
Crafting requires the ordinary skill, resources and energy. No repair primitive
or metal item is introduced. Rods/flasks/clothing are not weapons and are not
included in this wear system.

Condition follows weapons through trades, death estates and shelter inheritance.
Survivors and model context receive `weapon_durability`; traces add `weapon.used`
and `weapon.broken`. State/replay evidence includes condition. The skill catalog
still controls knowledge; tool validation and world mutation remain game-owned.

Intelligence at least 70 internally (7 in team JSON) enables anticipatory spear
replacement: at half durability or less, a survivor with recent danger or cautious
predator preparation can craft a spare before the old one breaks. This is not
guaranteed: knowledge, supplies, priorities and opportunity still matter. The
policy caps this preemptive behavior at one spare, avoiding unlimited stockpiling.

## Bear target and its assumptions

The calibrated case is **one 100-HP, strength-5, energy-100 survivor with a fresh
spear, adjacent to one hungry 150-HP bear**, forced to fight without fleeing,
healing, shelter or allies. Survivor attacks first at tick 1, then every three
ticks. Bear attacks at ticks 2, 8 and 14, for 35 damage each. A spear hit deals
30 base damage (formerly 25), scaled by `0.5 + strength / 10`.

For this fixture, five successful spear hits at ticks 1,4,7,10,13 kill the bear
before its third attack. Bear-melee hit probability is `0.2 ** (1/5)`, approximately
72.48%, making the modeled survival probability **20%**. A winner has 30 HP,
not the previous deterministic 10 HP. A miss ordinarily makes this forced duel
fatal. This is stochastic action resolution, not a single scripted winner/loser
coin flip. Combat uses a separate per-survivor seeded random stream.

This is NOT a universal 20% guarantee: strength, prior damage, timing, durability,
allies, terrain and fleeing change the result. Stronger survivors need fewer hits;
a badly worn weapon may break before enough hits. Non-bear melee hits have a 90%
chance. Axe/bow/knife base melee damage is 12/20/8; hands deal 5. Existing wildlife
hunting hit probabilities remain species-specific and unchanged.

Normal policy still treats a lone bear as outmatching the survivor and prefers
flight. Fleeing now seeks a known intact shelter within eight path steps, avoiding
predator-occupied cells, before reverting to maximizing distance. It never
discovers an unseen shelter. Entering a shelter stops the two-cell escape move
and blocks predator attacks; shelter sleeping permissions remain unchanged.

All capacities and combat parameters are organizer rules in `configs/defaults.json`,
not player-budget settings. These changes intentionally invalidate old replay
goldens; the replay format is `gameplay-state-v3`.

## Fishing

Fishing nets are removed from knowledge, crafting, tools, policies, model tasks,
trade items and rendering. Fishing rods, finite lake stocks, daily replenishment
and bears fishing remain. Historical evaluation evidence is retained unchanged.
Old `fishing_nets: false` experiment flags are accepted as a compatibility no-op;
attempting to enable the removed feature is rejected.

## A year is a real evaluation target

One day is 80 ticks; one year is **29,200 ticks** (365 days). At normal unpaused
speed this is one real hour. The default competition and broad evaluation now
use that horizon; smoke tests remain short. `survived_one_year` distinguishes
achieving this target from simply running a configuration that specifies it.

Easy mode retains 2× initial resources and four daily berries per forest tile,
but now schedules predators every 2,000 rather than 500 ticks. Balanced/hard
arrival rates remain 250/125. Predator health, attack rules, hunger, thirst,
weather, alligators and shelter protection are shared rules: easy survivors do
not receive hidden immunity or free water.

The budget-valid example in `configs/team-easy-year.json` allocates 100 points
unevenly (30/24/16/15/15). It invests most heavily in intelligence, endurance and
perception, avoids combat, favors private shelters, and responds earlier to needs.
It is an initial candidate, not a proven optimal build. Generosity/cooperation
remain moderate; collaboration can emerge but is not required for a survivor's
initial functionality. The competition/config files are separate and explicit.

```sh
python -m agentstranded.evaluate --config agentstranded/configs/evaluation-easy-year.json --events
```

To watch the same team and rules interactively (omit `--model` for reproducibility):

```sh
python -m agentstranded.app --team agentstranded/configs/team-easy-year.json \
  --competition agentstranded/configs/competition-easy-year.json --seed 17
```

Evaluate additional held-out seeds, teams and maps before claiming broad balance
or guaranteed year-long survival. See [Evaluation guide](EVALUATION.md).

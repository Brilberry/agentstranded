from collections import deque
from types import SimpleNamespace

import pytest

from agentstranded import Simulation
from agentstranded.evaluation_scenarios import prepare_scenario
from agentstranded.simulation import Predator
from agentstranded.weapons import CAPACITY, remaining, snapshot, transfer, use


@pytest.mark.parametrize("item", CAPACITY)
def test_each_weapon_breaks_after_exactly_its_capacity(item):
    sim = Simulation(agents=1, predator_interval=None)
    actor = sim.agents[0]
    actor.inventory[item] = 1
    for index in range(CAPACITY[item]):
        assert remaining(actor, item) == CAPACITY[item] - index
        use(sim, actor, item, "test")
    assert actor.inventory[item] == remaining(actor, item) == 0
    assert len(sim.trace.events_named("weapon.broken")) == 1


def test_misses_wear_spears_and_last_use_still_attacks():
    sim = Simulation(agents=1, predator_interval=None)
    actor = sim.agents[0]
    actor.inventory["spear"] = 1
    actor.weapon_durability["spear"] = [1]
    sim.predators = [Predator("bear", "bear", actor.position, 150)]
    sim.combat_random[actor.id] = SimpleNamespace(random=lambda: 1)
    result = sim.attack(actor, "bear")
    assert result.metadata["equipment"] == "spear" and not result.metadata["hit"]
    assert actor.inventory["spear"] == 0
    sim.tick += 3
    sim.combat_random[actor.id] = SimpleNamespace(random=lambda: 0)
    result = sim.attack(actor, "bear")
    assert result.metadata["equipment"] == "hands"


def test_rejected_attack_does_not_wear_equipment():
    sim = Simulation(agents=1, predator_interval=None)
    actor = sim.agents[0]
    actor.inventory["spear"] = 1
    with pytest.raises(ValueError):
        sim.attack(actor, "absent")
    assert remaining(actor, "spear") == CAPACITY["spear"]


def test_trading_and_inheritance_do_not_repair_weapons():
    sim = Simulation(agents=2, predator_interval=None)
    first, second = sim.agents
    first.inventory["spear"] = 1
    first.weapon_durability["spear"] = [2]
    transfer(first, second, {"spear": 1})
    first.inventory["spear"] -= 1
    second.inventory["spear"] += 1
    assert remaining(second, "spear") == 2
    second.home = second.position
    tile = sim.world.tile(second.position)
    tile.shelter_owner = second.id
    second.alive = False
    sim.settle_estates()
    assert tile.weapon_durability["spear"] == [2]
    first.position = second.position
    sim.claim_shelter(first)
    assert remaining(first, "spear") == 2


def test_crafting_a_spare_preserves_old_condition_and_selects_fresh():
    sim = Simulation(agents=1, predator_interval=None)
    actor = sim.agents[0]
    actor.inventory.update(spear=1, wood=3)
    actor.weapon_durability["spear"] = [3]
    actor.learned_skills.add("spear")
    sim.craft(actor, "spear")
    assert sorted(snapshot(actor)["spear"]) == [3, 12]
    use(sim, actor, "spear", "attack")
    assert sorted(snapshot(actor)["spear"]) == [3, 11]


def test_smart_survivor_prepares_a_spare_when_safe():
    sim = Simulation(agents=1, predator_interval=250)
    actor = sim.agents[0]
    actor.learned_skills.add("spear")
    actor.inventory.update(spear=1, wood=3)
    actor.weapon_durability["spear"] = [4]
    actor.intelligence = 90
    actor.last_threat_tick = sim.tick
    assert sim.policy.tool_objective(actor) == "Prepare personal defenses"
    assert sim.policy.defend(actor).tool_name == "craft"
    actor.intelligence = 20
    assert sim.policy.tool_objective(actor) != "Prepare personal defenses"


def test_bear_duel_calibration_is_seeded_and_near_twenty_percent():
    from agentstranded.settings import DEFAULTS
    assert DEFAULTS["combat"]["bear_melee_hit_chance"] ** 5 == pytest.approx(0.2)
    wins = 0
    for seed in range(300):
        sim = Simulation(agents=1, seed=seed, predator_interval=None, lightning_probability=0, max_ticks=40)
        try:
            prepare_scenario(sim, "bear-spear")
            sim.trace.events = deque(sim.trace.events, maxlen=64)
            while not sim.game_over:
                sim.step()
            if sim.agents[0].alive:
                wins += 1
                assert sim.agents[0].health == 30
                assert not sim.predators[0].alive
        finally:
            sim.trace.close()
    assert 0.14 <= wins / 300 <= 0.26

from copy import deepcopy

import pytest

from agentstranded import Simulation
from agentstranded.progression import ready
from agentstranded.simulation import Terrain


def scene(count=1):
    sim = Simulation(agents=count, predator_interval=None, lightning_probability=0)
    actor = sim.agents[0]
    actor.position = (10, 10)
    for pos in sim.world.positions_within(actor.position, 3):
        tile = sim.world.tile(pos)
        tile.terrain = Terrain.GRASS
        tile.shelter_owner = None
        tile.fish_stock = 0
    lake = sim.world.tile((11, 10))
    lake.terrain, lake.fish_stock, lake.fish_capacity = Terrain.LAKE, 3, 3
    actor.known_tiles[(11, 10)] = Terrain.LAKE
    actor.known_resources["wood"] = {(10, 9)}
    sim.world.tile((10, 9)).resources["wood"] = 20
    sim.lakes.rules = deepcopy(sim.lakes.rules)
    sim.lakes.rules["alligator_probability"] = 0
    return sim, actor


def learn_net(sim, actor):
    sim.learn_skill(actor, "fishing", "teacher")
    sim.learn_skill(actor, "net_fishing", "teacher")
    actor.inventory["wood"] = 8
    sim.craft(actor, "fishing_net")


def test_net_progression_and_atomic_deployment():
    sim, actor = scene()
    sim.tick = 2000
    assert not ready(sim, actor, "net_fishing")
    sim.learn_skill(actor, "fishing", "teacher")
    assert ready(sim, actor, "net_fishing")
    with pytest.raises(ValueError):
        sim.homestead.execute(actor, "place_net")
    learn_net(sim, actor)
    sim.homestead.execute(actor, "place_net")
    assert actor.inventory["fishing_net"] == 0
    assert len(sim.lakes.nets) == 1
    actor.inventory["fishing_net"] = 1
    with pytest.raises(ValueError):
        sim.homestead.execute(actor, "place_net")
    assert actor.inventory["fishing_net"] == 1


def test_net_capacity_stock_conservation_collection_and_retrieval():
    sim, actor = scene()
    learn_net(sim, actor)
    sim.homestead.execute(actor, "place_net")
    for tick in (20, 40, 60, 80):
        sim.tick = tick
        sim.lakes.update()
        sim.lakes.update()  # Repeated update calls cannot catch twice in one tick.
    net = sim.lakes.owned(actor)
    assert net.catch == 3
    assert sim.world.tile(net.position).fish_stock == 0
    sim.homestead.execute(actor, "collect_net")
    assert actor.inventory["fish"] == 3 and net.catch == 0
    sim.tick = 100
    sim.lakes.update()
    assert net.catch == 0  # No free fish from an empty lake.
    sim.homestead.execute(actor, "retrieve_net")
    assert actor.inventory["fishing_net"] == 1 and not sim.lakes.nets


def test_net_access_abandonment_and_bound_actor_validation():
    sim, owner = scene(2)
    visitor = sim.agents[1]
    visitor.position = owner.position
    learn_net(sim, owner)
    sim.homestead.execute(owner, "place_net")
    with pytest.raises(ValueError):
        sim.homestead.execute(visitor, "retrieve_net")
    with pytest.raises(ValueError):
        sim.homestead.execute(owner, "collect_net", actor=visitor.id)
    owner.alive = False
    sim.homestead.execute(visitor, "retrieve_net")
    assert visitor.inventory["fishing_net"] == 1


def test_rule_policy_crafts_and_deploys_net():
    sim, actor = scene()
    learn_net(sim, actor)
    call = sim.policy._net_action(actor)
    assert call.tool_name == "place_net"
    sim.homestead.execute(actor, call.tool_name)
    sim.lakes.owned(actor).catch = 2
    assert sim.policy._fishing_food(actor).tool_name == "collect_net"


def test_model_net_milestone_executes_validated_tools():
    from bbagents import PlanStep
    from agentstranded.model_policy import ModelPolicy
    sim, actor = scene()
    learn_net(sim, actor)
    policy = ModelPolicy(sim, model="fake")
    try:
        step = PlanStep("net", "Deploy a net", description="set_fishing_net")
        call, done = policy._task_call(actor, step)
        assert call.tool_name == "place_net" and not done
        assert sim.action_is_available(call, sim.available_actions(actor))
        sim.homestead.execute(actor, call.tool_name)
        assert policy._task_call(actor, step)[1]
    finally:
        policy.close()


def test_shelter_flag_is_available_to_model_postmortem(tmp_path):
    from agentstranded.reporting import ReportManager
    sim, actor = scene()
    sim.world.tile(actor.position).shelter_owner = actor.id
    def requester(endpoint, model, request):
        assert '"in_shelter": 1' in request.context.content
        assert "Missing in older logs means unknown" in request.system
        return {"summary": "Died in shelter.", "likely_contributors": [],
                "uncertainties": [], "evidence_ticks": [1]}
    manager = ReportManager(sim, directory=tmp_path, model="fake", requester=requester)
    actor.health, actor.hunger = 1, 95
    sim.step()
    manager.close()
    assert "Died in shelter." in (tmp_path / "survival-report.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("owner", [None, "agent-1", "someone-else"])
def test_shelter_flag_is_physical_not_ownership_or_cache(owner):
    sim, actor = scene()
    sim.world.tile(actor.position).shelter_owner = owner
    actor.sheltered = owner is None  # Deliberately stale.
    sim._record_states()
    event = sim.trace.events_named("survivor.state")[-1]
    assert type(event.attributes["in_shelter"]) is int
    assert event.attributes["in_shelter"] == int(owner is not None)
    if owner:
        sim.lightning_strike(actor.position)
        sim._record_states()
        assert sim.trace.events_named("survivor.state")[-1].attributes["in_shelter"] == 0


def test_shelter_flag_changes_on_entry_and_exit_and_reaches_report(tmp_path):
    from agentstranded.reporting import ReportManager
    sim, actor = scene()
    sim.world.tile((10, 9)).shelter_owner = "someone-else"
    manager = ReportManager(sim, directory=tmp_path)
    sim.move(actor, "north")
    sim._record_states()
    assert sim.trace.events_named("survivor.state")[-1].attributes["in_shelter"] == 1
    sim.move(actor, "south")
    sim._record_states()
    assert sim.trace.events_named("survivor.state")[-1].attributes["in_shelter"] == 0
    manager.close(generate=False)
    assert '"in_shelter": 1' in (tmp_path / "survival-report.md").read_text(encoding="utf-8")


def test_alligator_two_unhealed_hits_are_lethal_with_cooldown():
    sim, actor = scene()
    sim.lakes.rules["alligator_probability"] = 1
    actor.position = (11, 10)
    sim.lakes.encounter(actor)
    assert actor.alive and actor.health == 45
    sim.lakes.encounter(actor)
    assert actor.health == 45
    sim.tick += sim.lakes.rules["alligator_cooldown"]
    sim.lakes.encounter(actor)
    assert not actor.alive and actor.death_cause == "alligator attack"
    assert len(sim.trace.events_named("alligator.attacked")) == 2


@pytest.mark.parametrize("terrain", [Terrain.GRASS, Terrain.RIVER])
def test_alligators_never_attack_on_shore_or_river(terrain):
    sim, actor = scene()
    sim.lakes.rules["alligator_probability"] = 1
    sim.world.tile(actor.position).terrain = terrain
    sim.lakes.encounter(actor)
    assert actor.health == 100


def test_first_alligator_attack_is_survivable_when_injured():
    sim, actor = scene()
    actor.health = 20
    actor.position = (11, 10)
    sim.lakes.rules["alligator_probability"] = 1
    sim.lakes.encounter(actor)
    assert actor.alive and actor.health == 1


def test_cautious_survivor_avoids_known_lake_but_not_hidden_water():
    from agentstranded.social import SocialTraits
    sim, actor = scene()
    actor.known_tiles[(11, 10)] = Terrain.LAKE
    actor.knows_lake_risk = True
    actor.social_traits = SocialTraits(caution=95)
    assert sim.policy._direction_for(actor, (12, 10)) != "east"
    actor.known_tiles.clear()
    assert sim.policy._direction_for(actor, (12, 10)) == "east"


def test_alligator_hazard_stream_is_seeded_and_independent():
    a, actor_a = scene()
    b, actor_b = scene()
    a.random.random()
    a.weather_random.random()
    assert [a.lakes.hazard_random[actor_a.id].random() for _ in range(100)] == [
        b.lakes.hazard_random[actor_b.id].random() for _ in range(100)]

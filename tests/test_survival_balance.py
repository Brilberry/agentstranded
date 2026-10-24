from bbagents import PlanStep
import pytest

from agentstranded import Simulation
from agentstranded.homestead import Reservoir
from agentstranded.model_policy import TASKS
from agentstranded.progression import RECIPES, RULES
from agentstranded.simulation import Predator, Terrain


@pytest.mark.parametrize("source", ["carried", "reservoir"])
def test_locate_water_accepts_existing_supplies_without_known_river(source):
    sim = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    actor = sim.agents[0]
    actor.known_tiles = {actor.position: Terrain.GRASS}
    actor.inventory.clear()
    if source == "carried":
        actor.inventory.update(water=1)
    else:
        actor.home = actor.position
        sim.world.tile(actor.position).shelter_owner = actor.id
        sim.homestead.reservoirs[actor.home] = Reservoir(water=1)
    call, done = sim.policy._call_for_step(actor, PlanStep("locate-water", "Locate water"))
    assert done and call.tool_name == "observe_surroundings"


def test_flee_enters_known_shelter_instead_of_running_to_map_edge():
    sim = Simulation(agents=1, predator_interval=None)
    actor = sim.agents[0]
    actor.position = (10, 10)
    for pos in sim.world.positions_within(actor.position, 3):
        sim.world.tile(pos).terrain = Terrain.GRASS
        sim.world.tile(pos).shelter_owner = None
    shelter = (10, 12)
    sim.world.tile(shelter).shelter_owner = actor.id
    actor.known_tiles[shelter] = Terrain.GRASS
    sim.predators = [Predator("bear", "bear", (9, 10), 150, hunger=90)]
    sim.flee(actor)
    assert actor.position == shelter
    sim.tick = 2
    sim._update_predators()
    assert actor.health == 100


def test_flee_does_not_discover_an_unknown_shelter():
    sim = Simulation(agents=1, predator_interval=None)
    actor = sim.agents[0]
    actor.position = (10, 10)
    actor.known_tiles.clear()
    for pos in sim.world.positions_within(actor.position, 2):
        sim.world.tile(pos).terrain = Terrain.GRASS
        sim.world.tile(pos).shelter_owner = None
    sim.world.tile((10, 12)).shelter_owner = actor.id
    sim.predators = [Predator("bear", "bear", (10, 11), 150, hunger=90)]
    sim.flee(actor)
    assert actor.position != (10, 12)


def test_removed_nets_have_no_executable_surface():
    sim = Simulation(agents=1, predator_interval=None)
    actor = sim.agents[0]
    assert "net_fishing" not in RULES and "fishing_net" not in RECIPES
    assert "set_fishing_net" not in TASKS
    assert not {"place_net", "collect_net", "retrieve_net"} & sim.homestead.descriptions.keys()
    assert all("net" not in call.tool_name for call in sim.available_actions(actor))
    with pytest.raises(ValueError, match="removed"):
        Simulation(features={"fishing_nets": True})


def test_year_evaluation_configs_are_valid_and_unevenly_budgeted():
    from agentstranded.competition import load, validate_competition, validate_team
    from agentstranded.settings import CONFIG_DIRECTORY
    rules = validate_competition(load(CONFIG_DIRECTORY / "competition-easy-year.json"))
    team = validate_team(load(CONFIG_DIRECTORY / "team-easy-year.json"), rules)
    assert rules["max_ticks"] == 365 * 80
    assert [sum(actor["attributes"].values()) for actor in team["survivors"]] == [30, 24, 16, 15, 15]

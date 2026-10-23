import random
from unittest.mock import Mock

import pytest

from agentstranded import Simulation
from agentstranded.climate import Climate, Conditions, SEASONS, SEASON_DAYS


@pytest.mark.parametrize("weather,storm,expected", [
    ("sunny", False, 0), ("snowy", False, 0),
    ("sunny", True, 0), ("rainy", False, 1), ("rainy", True, 1),
])
def test_scheduled_lightning_requires_rain(weather, storm, expected):
    sim = Simulation(agents=1, predator_interval=None, lightning_probability=1)
    sim.climate.at = lambda *args: Conditions("spring", weather, 20, thunderstorm=storm)
    sim.weather_random.random = lambda: 0
    sim.step()
    assert len(sim.trace.events_named("calamity.lightning")) == expected


def test_rain_frequency_varies_by_season_and_remains_seeded():
    rainy = {}
    for season in SEASONS:
        rainy[season] = sum(Climate(seed, season).at(0, 80).weather == "rainy"
                            for seed in range(2000)) / 2000
        assert rainy[season] == sum(Climate(seed, season).at(0, 80).weather == "rainy"
                                    for seed in range(2000)) / 2000
    for season, probability in {"spring": .25, "summer": .20, "autumn": .40, "winter": .25}.items():
        assert rainy[season] == pytest.approx(probability, abs=.04)
    assert rainy["autumn"] > rainy["spring"] > rainy["summer"]
    assert sum(SEASON_DAYS.values()) == 365


def test_shelters_do_not_change_random_strike_locations():
    bare = Simulation(agents=0)
    built = Simulation(agents=0)
    bare.weather_random = random.Random(19)
    built.weather_random = random.Random(19)
    for y, row in enumerate(built.world.tiles):
        for x, tile in enumerate(row):
            if (x + y) % 3 == 0:
                tile.shelter_owner = "test-owner"
    for _ in range(500):
        first = bare.lightning_strike().metadata["position"]
        second = built.lightning_strike().metadata["position"]
        assert first == second


def test_random_targeting_can_hit_every_tile_including_water_and_shelters():
    simulation = Simulation(agents=0)
    size = simulation.world.size
    coordinates = [(x, y) for y in range(size) for x in range(size)]
    simulation.world.tile((0, 0)).shelter_owner = "test-owner"
    simulation.weather_random = Mock()
    simulation.weather_random.randrange.side_effect = [value for pos in coordinates for value in pos]
    for position in coordinates:
        assert simulation.lightning_strike().metadata["position"] == position
    assert simulation.weather_random.randrange.call_count == 2 * size * size
    assert all(call.args == (size,) for call in simulation.weather_random.randrange.call_args_list)
    simulation.weather_random.random.assert_not_called()
    simulation.weather_random.choice.assert_not_called()

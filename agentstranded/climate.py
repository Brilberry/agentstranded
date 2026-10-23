"""Northern temperate climate, reproducible independently of survivor actions."""
from dataclasses import dataclass
import random

SEASONS = ("spring", "summer", "autumn", "winter")
SEASON_DAYS = {"spring": 92, "summer": 92, "autumn": 91, "winter": 90}
DAYS_PER_YEAR = sum(SEASON_DAYS.values())
TICKS_PER_DAY = 80
SECONDS_PER_YEAR = 3600
NORMAL_TICKS_PER_SECOND = DAYS_PER_YEAR * TICKS_PER_DAY / SECONDS_PER_YEAR


def time_of_day(tick, day_length=TICKS_PER_DAY):
    """24-hour clock; each default tick advances 18 simulated minutes."""
    minutes = (tick % day_length) * 24 * 60 // day_length
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass(frozen=True)
class Conditions:
    season: str
    weather: str
    temperature: float
    thunderstorm: bool = False
    heatwave: bool = False

    @property
    def hazardous(self):
        return self.temperature < 5 or self.temperature >= 32 or self.thunderstorm or self.weather == "snowy"


class Climate:
    def __init__(self, seed, starting_season="spring"):
        if starting_season not in SEASONS:
            raise ValueError(f"starting_season must be one of {SEASONS}")
        self.seed, self.starting_season = seed, starting_season

    def at(self, tick, day_length):
        day = tick // day_length
        remaining = day % DAYS_PER_YEAR
        start = SEASONS.index(self.starting_season)
        for offset in range(4):
            season = SEASONS[(start + offset) % 4]
            if remaining < SEASON_DAYS[season]:
                break
            remaining -= SEASON_DAYS[season]
        rng = random.Random(self.seed + 1101 + day * 7919)
        roll = rng.random()
        rain = {"spring": 0.25, "summer": 0.2, "autumn": 0.4, "winter": 0.25}[season]
        weather = "snowy" if season == "winter" and roll < 0.2 else "rainy" if roll < rain + (0.2 if season == "winter" else 0) else "sunny"
        heatwave = season == "summer" and weather == "sunny" and rng.random() < 0.12
        storm = weather == "rainy" and rng.random() < (0.4 if season == "summer" else 0.1)
        low, high = {"spring": (16, 23), "summer": (24, 31), "autumn": (9, 18), "winter": (-5, 7)}[season]
        temperature = rng.uniform(36, 40) if heatwave else rng.uniform(low, high)
        if weather == "rainy":
            temperature -= 3
        elif weather == "snowy":
            temperature = min(0, temperature - 4)
        if tick % day_length >= int(day_length * 0.68):
            temperature -= 5
        return Conditions(season, weather, round(temperature, 1), storm, heatwave)

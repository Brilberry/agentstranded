"""Streaming descriptive metrics; no model, game mutations or log-text parsing."""
from collections import Counter, defaultdict, deque

from .progression import NUTRITION, RECIPES

EQUIPMENT_SKILLS = {"axe": "axe", "spear": "spear", "bow": "bow",
                    "fishing_rod": "fishing", "fishing_net": "net_fishing"}

class FoodLedger:
    """FIFO attribution for fungible food. Unknown acquisitions stay unknown."""
    def __init__(self):
        self.stock = defaultdict(deque)

    def add(self, owner, item, amount, source):
        if amount > 0:
            queue = self.stock[owner, item]
            if queue and queue[-1][0] == source:
                queue[-1][1] += amount
            else:
                queue.append([source, amount])

    def take(self, owner, item, amount):
        result = Counter()
        queue = self.stock[owner, item]
        while amount and queue:
            source, count = queue[0]
            taken = min(count, amount)
            result[source] += taken
            amount -= taken
            queue[0][1] -= taken
            if not queue[0][1]:
                queue.popleft()
        if amount:
            result["unknown"] += amount
        return result

    def transfer(self, sender, recipient, items):
        for item, amount in items.items():
            if item in NUTRITION:
                for source, count in self.take(sender, item, amount).items():
                    self.add(recipient, item, count, source)

    def reconcile(self, owner, inventory):
        for item in NUTRITION:
            actual = inventory.get(item, 0)
            recorded = sum(row[1] for row in self.stock[owner, item])
            if recorded > actual:
                self.take(owner, item, recorded - actual)
            elif actual > recorded:
                self.add(owner, item, actual - recorded, "unknown")


def stash(position):
    return "shelter:" + ":".join(map(str, position))


class Metrics:
    def __init__(self, stall_ticks=20):
        self.stall_ticks = stall_ticks
        self.agents = {}
        self.events = Counter()
        self.evidence = defaultdict(list)
        self.food = FoodLedger()
        self.calls = {}
        self.streaks = defaultdict(Counter)

    def actor(self, identity):
        if identity not in self.agents:
            self.agents[identity] = {
                "samples": 0, "last_tick": -1, "last_state": {},
                "exposure_ticks": Counter({key: 0 for key in ("hunger_urgent", "thirst_urgent", "energy_low",
                    "thirst_with_carried_water", "hunger_with_food", "in_shelter")}), "food_units": Counter(),
                "nutrition": Counter(), "wasted_nutrition": 0.0,
                "meals_by_source_fifo": Counter(), "unknown_meat_meals": 0,
                "damage_reported": Counter(), "tools": Counter(), "failures": Counter(),
                "crafts": Counter(), "learning_order": [], "skills": {},
                "equipment_uses": Counter(), "drinks": Counter(), "thirst_relief": Counter(),
                "hunts": Counter(), "kills": Counter(), "policy_sources": Counter(),
                "max_observe_streak": 0, "max_failure_streak": 0,
                "suspected_observe_stalls": 0, "repeated_failure_episodes": 0,
                "thirst_sum": 0.0, "peak_thirst": 0.0, "inventory_at_death": None,
                "visible_predator_ids": set(), "lake_ticks": 0, "hazard_checks": 0, "alligator_attacks": 0,
            }
        return self.agents[identity]

    def note(self, metric, row):
        if len(self.evidence[metric]) < 3:
            self.evidence[metric].append({key: row[key] for key in
                ("event", "tick", "agent", "tool_name", "position", "health", "thirst", "inventory", "error", "cause", "kind") if key in row})

    def consume(self, row):
        event, tick, identity = row["event"], row.get("tick", 0), row.get("agent")
        self.events[event] += 1
        actor = self.actor(identity) if identity else None
        if event == "survivor.died":
            self.note("death:" + identity, row)
        if event == "inventory.transferred":
            if "sender_inventory_before" in row:
                self.food.reconcile(row["sender"], row["sender_inventory_before"])
                self.food.reconcile(row["recipient"], row["recipient_inventory_before"])
            self.food.transfer(row["sender"], row["recipient"], row["items"])
        elif event == "survivor.estate_stored":
            actor["inventory_at_death"] = dict(row["items"])
            self.food.reconcile(identity, row["items"])
            self.food.transfer(identity, stash(row["position"]), row["items"])
        elif event == "shelter.claimed":
            self.food.transfer(stash(row["position"]), identity, row["inherited"])
        elif event == "calamity.lightning" and row.get("destroyed_shelter"):
            for item in NUTRITION:
                self.food.stock.pop((stash(row["position"]), item), None)
        elif event == "wildlife.killed" and identity:
            actor["kills"][row["kind"]] += 1
            self.food.add(identity, "meat", row["meat"], row["kind"])
            self.note("hunt_kill:" + identity, row)
        elif event == "wildlife.hunted" and identity:
            actor["hunts"][row["kind"]] += 1
        elif event == "resource.fished":
            self.food.add(identity, "fish", 1, "rod")
        elif event in {"net.collected", "net.retrieved"}:
            self.food.add(identity, "fish", row["fish"], "net")
        elif event == "garden.harvested":
            self.food.add(identity, "vegetables", row["amount"], "garden")
        elif event == "food.cooked":
            for source, amount in self.food.take(identity, row["raw"], 1).items():
                self.food.add(identity, row["cooked"], amount, source)
        elif event == "food.consumed":
            item = row["item"]
            sources = self.food.take(identity, item, row["amount"])
            actor["food_units"][item] += row["amount"]
            actor["nutrition"][item] += row["effective_nutrition"]
            actor["wasted_nutrition"] += row["nutrition"] - row["effective_nutrition"]
            actor["meals_by_source_fifo"].update(sources)
            if item in {"meat", "cooked_meat"}:
                actor["unknown_meat_meals"] += sources["unknown"]
            self.note("food_consumed", row)
        elif event == "water.consumed":
            actor["drinks"][row["source"]] += 1
            actor["thirst_relief"][row["source"]] += row["relief"]
        elif event == "survivor.kill_reward":
            actor["nutrition"]["predator_kill_reward"] += row["hunger_recovered"]
            actor["thirst_relief"]["predator_kill_reward"] += row["thirst_recovered"]
        elif event == "lake.hazard_checked":
            actor["hazard_checks"] += 1
        elif event == "skill.learned":
            actor["learning_order"].append(row["skill"])
            actor["skills"][row["skill"]] = {"learned_tick": tick,
                "source": row["source"], "crafts": 0, "uses": 0, "first_use_tick": None}
        elif event in {"survivor.damage", "predator.attacked", "wildlife.attacked", "alligator.attacked"}:
            source = "+".join(sorted(row.get("causes", []))) or row.get("kind") or event
            actor["damage_reported"][source] += row.get("hp_lost", row.get("damage", 0))
            if event == "alligator.attacked":
                actor["alligator_attacks"] += 1
            self.note("damage", row)
        elif event == "tool.started":
            self.calls[identity] = row
            actor["tools"][row["tool_name"]] += 1
            actor["policy_sources"][row.get("source", "unknown")] += 1
            streak = self.streaks[identity]
            streak["observe"] = streak["observe"] + 1 if row["tool_name"] == "observe_surroundings" else 0
            actor["max_observe_streak"] = max(actor["max_observe_streak"], streak["observe"])
            if streak["observe"] == self.stall_ticks:
                actor["suspected_observe_stalls"] += 1
                self.note("suspected_observe_stall", row)
        elif event == "tool.finished":
            self._tool_finished(row, actor)
        elif event == "survivor.state" and tick > actor["last_tick"]:
            actor["last_tick"] = tick
            actor["last_state"] = row
            if not row["alive"] and actor["inventory_at_death"] is None:
                actor["inventory_at_death"] = dict(row["inventory"])
            self.food.reconcile(identity, row["inventory"])
            if tick == 0:
                return
            actor["samples"] += 1
            actor["lake_ticks"] += int(row.get("in_lake", 0))
            thirst = row["thirst"]
            actor["thirst_sum"] += thirst
            actor["peak_thirst"] = max(actor["peak_thirst"], thirst)
            for name, condition in {
                "hunger_urgent": row["hunger"] >= 68,
                "thirst_urgent": thirst >= 64,
                "energy_low": row["energy"] <= 30,
                "thirst_with_carried_water": thirst >= 64 and row["inventory"].get("water", 0) > 0,
                "hunger_with_food": row["hunger"] >= 68 and any(row["inventory"].get(item, 0) for item in NUTRITION),
                "in_shelter": row.get("in_shelter") == 1,
            }.items():
                if condition:
                    actor["exposure_ticks"][name] += 1
                    if name == "thirst_with_carried_water":
                        self.note(name, row)
            actor["visible_predator_ids"].update(item["id"] for item in row.get("visible_predators", []))
            if row.get("sleep_remaining"):
                self.streaks[identity]["observe"] = 0

    def _tool_finished(self, row, actor):
        identity, tick = row["agent"], row["tick"]
        streak = self.streaks[identity]
        if row["status"] != "completed":
            actor["failures"][row["tool_name"]] += 1
            streak["failure"] += 1
            actor["max_failure_streak"] = max(actor["max_failure_streak"], streak["failure"])
            if streak["failure"] == 5:
                actor["repeated_failure_episodes"] += 1
                self.note("repeated_tool_failure", row)
            return
        streak["failure"] = 0
        call = self.calls.get(identity, {})
        args = call.get("arguments", {})
        equipment = row.get("result_metadata", {}).get("equipment") or {
            "hunt": "bow", "fish": "fishing_rod", "skin": "knife",
            "collect_net": "fishing_net", "place_net": "fishing_net"}.get(row["tool_name"])
        if equipment and equipment != "hands":
            actor["equipment_uses"][equipment] += 1
            skill = EQUIPMENT_SKILLS.get(equipment)
            if skill in actor["skills"]:
                entry = actor["skills"][skill]
                entry["uses"] += 1
                if entry["first_use_tick"] is None:
                    entry["first_use_tick"] = tick
        if row["tool_name"] == "gather" and args.get("resource") == "berries":
            self.food.add(identity, "berries", row.get("result_metadata", {}).get("amount", 0), "forage")
        if row["tool_name"] == "craft":
            item = args.get("item")
            actor["crafts"][item] += 1
            skill, _ = RECIPES.get(item, (None, {}))
            if skill in actor["skills"]:
                actor["skills"][skill]["crafts"] += 1
            if item == "ration":
                self.food.take(identity, "berries", 2)
                self.food.add(identity, "ration", 1, "forage")
        else:
            skill = {"fish": "fishing", "hunt": "hunting", "plant": "gardening", "harvest": "gardening",
                "light_fire": "fire", "cook": "cooking", "skin": "skinning", "tan_hide": "leatherworking",
                "equip": "leatherworking", "install_reservoir": "reservoir", "fill_reservoir": "reservoir",
                "place_net": "net_fishing", "collect_net": "net_fishing", "retrieve_net": "net_fishing"}.get(row["tool_name"])
            equipment_skill = EQUIPMENT_SKILLS.get(equipment)
            if skill in actor["skills"] and skill != equipment_skill:
                entry = actor["skills"][skill]
                entry["uses"] += 1
                if entry["first_use_tick"] is None:
                    entry["first_use_tick"] = tick

    def finish(self, sim):
        survivors = []
        for agent in sim.agents:
            data = dict(self.actor(agent.id))
            state = data.pop("last_state")
            data.pop("last_tick")
            data["distinct_predators_seen"] = len(data.pop("visible_predator_ids"))
            data["mean_thirst"] = data.pop("thirst_sum") / data["samples"] if data["samples"] else None
            data.update(id=agent.id, name=agent.name, alive=agent.alive, censored=agent.alive,
                lifetime=agent.death_tick if agent.death_tick is not None else sim.tick,
                death_cause=agent.death_cause, intelligence=agent.intelligence,
                final_needs={key: state.get(key) for key in ("health", "hunger", "thirst", "energy")})
            survivors.append(data)
        lifetimes = [entry["lifetime"] for entry in survivors]
        return {"survivors": survivors, "events": self.events, "evidence": dict(self.evidence),
            "summary": {"survivor_ticks": sum(lifetimes), "all_alive_ticks": min(lifetimes, default=0),
                "alive": sum(agent.alive for agent in sim.agents),
                "deaths_with_water": sum("dehydration" in (entry["death_cause"] or "")
                    and bool((entry["inventory_at_death"] or {}).get("water")) for entry in survivors),
                "death_causes": Counter(entry["death_cause"] for entry in survivors if not entry["alive"])}}

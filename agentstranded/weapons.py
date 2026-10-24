"""Per-item weapon condition, including honest trade and shelter inheritance."""
from .settings import DEFAULTS

CAPACITY = DEFAULTS["weapons"]


def synchronize(holder):
    """Lazily initialize supplied/crafted equipment; inventory counts stay authoritative."""
    for item, maximum in CAPACITY.items():
        uses = holder.weapon_durability.setdefault(item, [])
        count = holder.inventory.get(item, 0)
        if len(uses) < count:
            uses.extend([maximum] * (count - len(uses)))
        elif len(uses) > count:
            del uses[count:]
    return holder.weapon_durability


def remaining(holder, item):
    return max(synchronize(holder)[item], default=0)


def snapshot(holder):
    return {item: list(uses) for item, uses in synchronize(holder).items() if uses}


def use(sim, actor, item, activity):
    """One validated attempt wears the best available copy, hit or miss."""
    if item not in CAPACITY:
        return
    uses = synchronize(actor)[item]
    if not uses:
        raise ValueError(f"no {item} to use")
    index = max(range(len(uses)), key=uses.__getitem__)
    before = uses[index]
    uses[index] -= 1
    sim.trace.record("weapon.used", {"agent": actor.id, "item": item, "activity": activity,
        "remaining_before": before, "remaining": uses[index], "capacity": CAPACITY[item]})
    if uses[index] == 0:
        uses.pop(index)
        actor.inventory[item] -= 1
        sim.trace.record("weapon.broken", {"agent": actor.id, "item": item, "activity": activity})
        sim.event_log.appendleft(f"{actor.name}'s {item} broke")


def transfer(sender, recipient, items):
    """Call BEFORE changing item counts; never refresh a worn weapon in a trade."""
    source, target = synchronize(sender), synchronize(recipient)
    moved = {}
    for item, count in items.items():
        if item not in CAPACITY:
            continue
        moved[item] = []
        for _ in range(count):
            best = max(source[item])
            source[item].remove(best)
            target[item].append(best)
            moved[item].append(best)
    return moved

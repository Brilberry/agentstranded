from types import MappingProxyType

import pytest

from bbagents import ToolCall
from bbagents.behavior import Abstain, Proposal, PolicySelector
from agentstranded import Simulation
from agentstranded.behavior import (
    BehaviorContext, PreparedChoice, PreparedPolicy, make_selector,
)
from agentstranded.model_policy import ModelPolicy
from agentstranded.simulation import Predator, Terrain


def test_prepared_adapter_is_read_only_and_does_not_execute_or_advance():
    sim = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    actor = sim.agents[0]
    original_plan = actor.current_plan
    statuses = [step.status for step in original_plan.steps]
    original_inventory = dict(actor.inventory)
    context = BehaviorContext.from_choice(PreparedChoice("local_plan", ToolCall("rest"), "Recover"))
    policy = PreparedPolicy("local_plan")
    first = policy.propose(context)
    assert policy.propose(context) == first == Proposal(ToolCall("rest"), "Recover")
    assert isinstance(PreparedPolicy("defense").propose(context), Abstain)
    assert actor.current_plan is original_plan
    assert [step.status for step in original_plan.steps] == statuses
    assert dict(actor.inventory) == original_inventory
    assert not sim.trace.events_named("tool.started")
    with pytest.raises(TypeError):
        context.candidates["defense"] = first


def test_framework_selector_orders_proposals_and_attributes_trace():
    sim = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    actor = sim.agents[0]
    selector = make_selector(sim, actor.id)
    assert isinstance(selector, PolicySelector)
    context = BehaviorContext(MappingProxyType({
        "weather": Proposal(ToolCall("rest"), "Storm"),
        "defense": Proposal(ToolCall("flee"), "Danger"),
    }))
    selection = selector.select(context)
    assert selection.policy == "defense"
    assert len(selection.considered) == 1
    event = sim.trace.events_named("behavior.selected")[-1]
    assert event.attributes["agent"] == actor.id
    assert event.attributes["tick"] == sim.tick
    assert "reason" not in event.attributes
    assert "arguments" not in event.attributes


def test_rule_decisions_use_selector_without_bypassing_tool_preconditions():
    sim = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    actor = sim.agents[0]
    actor.position, actor.energy = (10, 10), 0
    sim.world.tile(actor.position).terrain = Terrain.GRASS
    sim.world.tile(actor.position).shelter_owner = None
    sim.predators = [Predator("wolf", "wolf", (11, 10), 45, hunger=90, thirst=0)]
    sim.wildlife.animals.clear()
    action = sim.policy.decide(actor)
    assert action.tool_name == "rest"
    assert sim.policy.last_selections[actor.id].policy == "defense"
    actor.energy = 20
    with pytest.raises(ValueError):
        sim.rest(actor)  # Earlier selection is not an authorization bypass.


def test_model_plan_decisions_and_pending_fallback_use_framework_selectors():
    sim = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    actor = sim.agents[0]
    policy = ModelPolicy(sim, model="fake", initial_stagger=False, tick_range=(0, 0),
                         cooldown=0, clock=lambda: 0, requester=lambda *args: {
                             "goal": "Explore", "milestones": ["explore"]})
    sim.policy = policy
    try:
        policy.decide(actor)
        assert actor.id in policy.last_selections
        policy.pending[actor.id][1].result(timeout=3)
        policy.decide(actor)
        assert policy.last_selections[actor.id].policy == "model_plan"
    finally:
        policy.close()


def test_empty_prepared_context_has_explicit_no_match():
    sim = Simulation(agents=1, predator_interval=None)
    selection = make_selector(sim, sim.agents[0].id).select(BehaviorContext(MappingProxyType({})))
    assert selection.action is None
    assert all(attempt.outcome == "abstained" for attempt in selection.considered)

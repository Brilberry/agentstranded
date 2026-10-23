"""Pure bbagents proposal adapters over application-prepared decisions.

Legacy game controllers also perform plan/message bookkeeping. That lifecycle
preparation stays outside propose(); selecting a candidate never executes a tool
or advances a plan. This compatibility boundary preserves competition behavior.
"""
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from bbagents import ToolCall
from bbagents.behavior import Abstain, PolicyRule, PolicySelector, Proposal


RULE_ORDER = ("defense", "homestead", "weather", "garden", "social", "local_plan")
MODEL_ORDER = ("model_social", "model_plan")


@dataclass(frozen=True, slots=True)
class PreparedChoice:
    policy: str
    action: ToolCall
    reason: str


@dataclass(frozen=True, slots=True)
class BehaviorContext:
    candidates: Mapping[str, Proposal]

    @classmethod
    def from_choice(cls, choice):
        return cls(MappingProxyType({choice.policy: Proposal(choice.action, choice.reason)}))


@dataclass(frozen=True, slots=True)
class PreparedPolicy:
    name: str

    def propose(self, context: BehaviorContext) -> Proposal | Abstain:
        return context.candidates.get(self.name, Abstain("No prepared action for this controller"))


class SurvivorSelectionTrace:
    def __init__(self, simulation, agent_id):
        self.simulation, self.agent_id = simulation, agent_id

    def record(self, event, payload=None):
        self.simulation.trace.record(event, {**(payload or {}), "agent": self.agent_id})


def make_selector(simulation, agent_id, order=RULE_ORDER):
    return PolicySelector([
        PolicyRule(name, PreparedPolicy(name), priority=len(order) - index)
        for index, name in enumerate(order)
    ], trace=SurvivorSelectionTrace(simulation, agent_id), error_mode="raise")

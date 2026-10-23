# Behavior policy integration (bbagents 0.2.1)

Agent Stranded uses `bbagents.behavior.PolicySelector`, `PolicyRule`, `Proposal`
and `Abstain` for final behavior selection. `PreparedPolicy` adapters are pure
readers of an immutable candidate mapping. Selection emits framework
`behavior.policy_evaluated`, `behavior.selected` or `behavior.no_match` events,
attributed to the survivor and simulation tick by an application trace adapter.
Reasons remain available in `policy.last_selections[agent_id]`; context and action
arguments are not copied to selection traces. Errors propagate rather than silently
skipping a broken controller. Tools and authorization remain separate.

## Compatibility boundary

This is an incremental migration, not a replacement of every game controller.
Existing methods mix action preparation with message consumption, plan updates,
checkpoints and replanning. Those operations remain in `_prepare_rule_choice`
and the existing model lifecycle, OUTSIDE `propose()` and `PolicySelector.select()`.
Preparation short-circuits in the original order and produces one candidate.
The selector then evaluates pure adapters and selects that prepared action.
Thus a trace abstention means **no action was prepared for that adapter**, not that
the original domain controller was called again inside the selector.

The current compatibility order is:

1. Defense/recovery.
2. Optional homestead improvements.
3. Hazardous weather response.
4. Gardens.
5. Local social decisions.
6. Local plan execution (including urgent needs/night-preparation lifecycle).

Optional activities keep their existing emergency/suspended-plan gates. Model
operation retains local emergency fallback, inference scheduling, cooldowns,
response validation and plan progress; prepared social actions precede prepared
model milestones. Model-free fallback goes through the same rule selector.

These are the EXISTING game priorities, not the illustrative order from the design
spec. This migration does not make priorities safely user-reorderable: preparation
still has ordered lifecycle effects. A later refactor can separate individual
controllers fully and prepare multiple independent proposals before arbitration;
that needs its own replay-preserving work, not speculative evaluation of mutating
controllers or world copies.

## Execution and feedback

The selector never executes tools, starts inference, consumes resources or advances
a milestone. The simulation continues to execute ToolCalls through its existing
ToolRegistry/ActionRuntime paths. Model `on_result` and local plan evidence handling
remain unchanged. A selected action can still fail current precondition or
authorization checks. No additional authority is granted by selection.

## Dependency and reproducibility

The dependency is pinned to bbagents commit
`0aea6a022f1d3082cbea6124334bc3a5f641b601`, whose package version is 0.2.1.
This avoids requiring a PyPI version that was not available when this migration
was prepared. Installing the declared dependencies selects that exact revision;
local editable overrides remain an explicit development choice.

Existing golden gameplay fingerprints and scores must stay unchanged. New selection
events alter logs, event counts and performance measurements, not gameplay state.
Engine/dependency fingerprints naturally change and old/new engine results must
still be distinguished in competition manifests.

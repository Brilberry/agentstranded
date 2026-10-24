# Live commentary proposal — not implemented

## Experience

Treat the island like a sports broadcast: short play-by-play and occasional
analysis, not continuous narration or another death report. Example style:

> Tick 1,000: Ari has caught her first fish! That opens another food option,
> but Bo is still searching for shelter as night approaches.

Names, actions and timing must be supported by events. Avoid invented thoughts,
claims of causation, guaranteed predictions or imaginary rivalry. Distinguish
“the log shows” from “this may help.” A death gets a respectful short update;
detailed causes remain the postmortem's job.

## Triggers and scheduling

1. Schedule a round-up every **500 simulation ticks** (500, 1,000, 1,500, ...).
2. Queue event-driven highlights: survivor death, newly learned skill, first
   successful craft/use of a tool, alligator encounter, narrowly survived attack,
   completed shared shelter, substantial trade, shelter destruction or new season.
3. Track first-use milestones per survivor so routine gathering, fish catches,
   observations and repeated crafts do not flood the broadcast.
4. Coalesce events in a short tick window, prioritizing deaths and serious danger.
   If a periodic update and a highlight coincide, emit one combined update.
5. Allow at most one pending/in-flight commentary request. Use a real-time
   commentary cooldown (proposed 15 seconds), in addition to the shared inference
   gate; merge queued highlights while it is busy. Never block the simulation.
6. At natural game end, request one final wrap-up covering remaining highlights.
   Ctrl+C must not start or wait for commentary generation. Drop stale queued
   commentary on shutdown; cancellation of in-flight requests needs explicit testing.

## Evidence and framework reuse

- Consume the trace as a read-only observer; retain bounded event references and
  a last-announced tick/milestone ledger, not another complete in-memory journal.
- Use `ContextBuilder` for a bounded facts snapshot: trigger events, current public
  standings, relevant actions and already announced highlights. Proposed budget:
  12,000 characters and a response around 60–100 words.
- Use `DecisionRuntime` with a structured schema: `headline`, `commentary`,
  `evidence_ticks`, `featured_survivors`, and explicit `interpretations`.
  Validate all named survivors and cited ticks against the provided snapshot.
- Reuse the shared `InferenceGate` and optional Ollama connection. Gameplay and
  postmortem requests take priority; commentary must not create an independent
  unthrottled model stream or delay survival decisions.
- Use a bounded summary/announcement ledger to prevent repeats. This is observer
  memory, not a shared survivor memory or knowledge channel.
- Treat survivor messages and model output as untrusted data. No commentary tool
  can move survivors, alter state, call game tools, or publish executable markup.

## Presentation and configuration

- A small broadcast panel shows the latest update, its simulation tick and whether
  it is model-generated or a deterministic event description. An expandable history
  exposes evidence references without replacing the survivor/event panels.
- Save the commentary transcript inside the existing single Markdown/HTML report;
  HTML remains opt-in. Include model failures as diagnostics, not fictional narration.
- Provide enable/disable and proposed config keys for interval (default 500 ticks),
  event triggers, real-time cooldown, context/output limits, and optional model.
  These keys do not exist yet and require schema/documentation changes at implementation.
- Without a model, use concise deterministic event templates; no inference requests.
  A commentary toggle affects presentation only, never game speed or survivor policy.

## Competition boundaries

Commentary observes the organizer's full match but is never supplied to competing
agents or used for scoring. Spectator output may reveal locations, so any future
interactive competition must define delayed/public visibility separately.
Rules-only competition remains rules-only even if a separate spectator model is
configured. Asynchronous commentary completion is not deterministic: tests must
prove it cannot change gameplay fingerprints, resource allocation or scores.

## Acceptance tests before marking DONE

- Periodic triggers fire once per 500 ticks; event bursts coalesce, with no duplicate
  skill/first-tool announcements and no continuous inference loop.
- Slow, failing or unavailable models never stall ticks; queues and history stay bounded.
- Schema validation rejects fabricated names/ticks; rendering escapes markup.
- Commentary on/off and different completion timings produce identical competition
  gameplay fingerprints and scores for the same team, settings and seeds.
- Shared inference limits hold under concurrent gameplay, commentary and postmortems.
- Ctrl+C starts no new requests; natural completion may produce a final wrap-up.
- UI, keyboard help, JSON reference, transcript export and no-model fallback are tested.

No new bbagents primitive is required initially. A generic priority-aware inference
scheduler or reusable event-trigger/coalescing utility might merit framework support;
the existing gate only serializes calls, so priority admission needs an explicit
application coordinator rather than being claimed as already available.

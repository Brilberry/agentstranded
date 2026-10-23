import json

from agentstranded import Simulation
from agentstranded.reporting import ReportManager, last_window, survivor_events
from agentstranded.simulation import Predator


def test_no_model_report_explicitly_says_disabled(tmp_path):
    sim = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    manager = ReportManager(sim, directory=tmp_path)
    sim.agents[0].health, sim.agents[0].hunger = 1, 95
    sim.step()
    manager.close()
    report = (tmp_path / "survival-report.md").read_text()
    assert "Model analysis status: disabled" in report
    assert "no model summary will be generated" in report
    assert "If model analysis was enabled" not in report


def test_background_worker_failure_is_not_left_pending(monkeypatch, tmp_path):
    from agentstranded import reporting
    def fail(*args, **kwargs):
        raise RuntimeError("summary preparation failed")
    monkeypatch.setattr(reporting, "summarize", fail)
    sim = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    manager = ReportManager(sim, directory=tmp_path, model="fake")
    sim.agents[0].health, sim.agents[0].hunger = 1, 95
    sim.step()
    manager.close()
    report = (tmp_path / "survival-report.md").read_text()
    assert "Analysis failed: summary preparation failed" in report
    assert "Model analysis status: pending" not in report


def test_pending_analysis_is_replaced_with_completed_summary(tmp_path):
    from threading import Event
    entered, release = Event(), Event()
    def requester(*args):
        entered.set()
        assert release.wait(5)
        return {"summary": "Evidence based summary.", "likely_contributors": [],
                "uncertainties": [], "evidence_ticks": [1]}
    sim = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    manager = ReportManager(sim, directory=tmp_path, model="fake", requester=requester)
    sim.agents[0].health, sim.agents[0].hunger = 1, 95
    sim.step()
    try:
        manager.update()
        assert entered.wait(5)
        manager.save()
        assert "Model analysis status: pending" in (tmp_path / "survival-report.md").read_text()
    finally:
        release.set()
        manager.close()
    report = (tmp_path / "survival-report.md").read_text()
    assert "Evidence based summary." in report
    assert "Model analysis status: pending" not in report


def test_interrupted_run_saves_evidence_without_requesting_postmortems(tmp_path):
    sim = Simulation(agents=2, predator_interval=None, lightning_probability=0)
    manager = ReportManager(sim, directory=tmp_path, model="fake",
                            requester=lambda *args: (_ for _ in ()).throw(AssertionError("unexpected inference")))
    sim.agents[0].health, sim.agents[0].hunger = 1, 95
    sim.step()
    manager.update(generate=False)
    assert not manager.futures and not manager.submitted
    manager.close(generate=False)
    assert not manager.futures
    assert "Died at tick" in (tmp_path / "survival-report.md").read_text()


def test_deferred_analysis_replaces_alive_placeholder_at_completion(tmp_path):
    sim = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    manager = ReportManager(sim, directory=tmp_path, model="fake", requester=lambda *args: {
        "summary": "Death explained.", "likely_contributors": [],
        "uncertainties": [], "evidence_ticks": [1]})
    manager.save()
    sim.agents[0].health, sim.agents[0].hunger = 1, 95
    sim.step()
    manager.update(generate=False)
    manager.close()
    report = (tmp_path / "survival-report.md").read_text()
    assert "Death explained." in report
    assert "this survivor is alive at this save" not in report


def test_damage_and_death_are_attributed_once_to_survivor():
    simulation = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    agent = simulation.agents[0]
    agent.health = 1
    agent.hunger = 95
    agent.thirst = 95
    simulation.step()
    simulation.step()
    deaths = simulation.trace.events_named("survivor.died")
    assert len(deaths) == 1
    assert agent.death_tick == 1
    assert agent.death_cause == "starvation, dehydration"
    damage = simulation.trace.events_named("survivor.damage")[0]
    assert damage.attributes["agent"] == agent.id
    assert damage.attributes["damage"] == 1
    assert damage.attributes["tick"] == 1


def test_predator_death_is_recorded_after_combat():
    simulation = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    simulation.wildlife.animals.clear()  # Isolate survivor combat from opportunistic feeding.
    agent = simulation.agents[0]
    agent.health = 1
    agent.energy = 0
    simulation.tick = 1
    simulation.predators.append(Predator("bear-test", "bear", agent.position, 150))
    simulation.step()
    assert agent.death_cause == "bear attack (bear-test)"
    assert agent.death_tick == 2
    assert simulation.trace.events_named("survivor.died")


def test_last_window_is_200_ticks_and_includes_received_messages():
    events = [{"agent": "a", "tick": tick, "event": "survivor.state"} for tick in range(301)]
    events += [{"agent": "b", "recipient": "a", "tick": 200, "event": "message.sent"},
               {"agent": "b", "tick": 200, "event": "tool.started"}]
    selected = last_window(survivor_events(events, "a"), 250)
    assert min(row["tick"] for row in selected) == 51
    assert max(row["tick"] for row in selected) == 250
    assert sum(row["event"] == "survivor.state" for row in selected) == 200
    assert any(row["event"] == "message.sent" for row in selected)
    assert not any(row["event"] == "tool.started" for row in selected)


def test_reports_save_per_survivor_logs_and_model_postmortem(tmp_path):
    simulation = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    agent = simulation.agents[0]
    agent.health, agent.hunger = 1, 95
    simulation.step()
    requests = []

    def requester(endpoint, model, request):
        requests.append(request)
        assert "starvation" in request.context.content
        return {"summary": "Ari died from starvation at tick 1.",
                "likely_contributors": ["Hunger was already critical."],
                "uncertainties": ["A different policy was not tested."], "evidence_ticks": [1]}

    manager = ReportManager(simulation, directory=tmp_path, model="fake", requester=requester)
    manager.update()
    manager.update()  # No duplicate analysis submissions.
    manager.close()
    assert len(requests) == 1
    assert "starvation" in (tmp_path / "survival-report.md").read_text()
    report = (tmp_path / "survival-report.md").read_text()
    assert "Ari died from starvation" in report
    assert "### Final 200 ticks" in report
    assert report.count("## Model postmortem:") == 1
    assert not list(tmp_path.glob("*.summary.md"))
    manager.save()  # Repeated exports retain the completed analysis and timeline.
    assert (tmp_path / "survival-report.md").read_text() == report
    assert list(tmp_path.iterdir()) == [tmp_path / "survival-report.md"]
    history = report.split("## Complete event history\n", 1)[1].split("```jsonl\n", 1)[1].split("```", 1)[0]
    rows = [json.loads(line) for line in history.splitlines()]
    assert any(row["event"] == "survivor.died" for row in rows)
    assert any(row.get("agent") == agent.id for row in rows)
    assert simulation.trace.events_named("decision.completed")


def test_invalid_model_evidence_does_not_replace_raw_reports(tmp_path):
    simulation = Simulation(agents=1, predator_interval=None, lightning_probability=0)
    agent = simulation.agents[0]
    agent.health, agent.hunger = 1, 95
    simulation.step()
    manager = ReportManager(simulation, directory=tmp_path, model="fake", requester=lambda *args: {
        "summary": "Unsupported claim", "likely_contributors": [], "uncertainties": [],
        "evidence_ticks": [999999]})
    manager.close()
    report = (tmp_path / "survival-report.md").read_text()
    assert "unavailable" in report
    assert "### Final 200 ticks" in report
    assert not list(tmp_path.glob("*.summary.md"))
    assert "survivor.died" in report
    assert len(simulation.trace.events_named("decision.failed")) == 2


def test_no_model_still_produces_inspectable_histories(tmp_path):
    simulation = Simulation(predator_interval=None, lightning_probability=0)
    simulation.step()
    manager = ReportManager(simulation, directory=tmp_path)
    manager.close()
    report = (tmp_path / "survival-report.md").read_text()
    assert "## Complete event history" in report
    assert "agent-5" in report
    assert len(list(tmp_path.iterdir())) == 1
    assert not list(tmp_path.glob("*.summary.md"))


def test_multiple_postmortems_stay_in_their_own_sections(tmp_path):
    simulation = Simulation(agents=2, predator_interval=None, lightning_probability=0)
    for agent in simulation.agents:
        agent.health, agent.hunger = 1, 95
    simulation.step()

    def requester(endpoint, model, request):
        identity = request.metadata["agent"]
        return {"summary": f"Analysis for {identity} only.", "likely_contributors": [],
                "uncertainties": [], "evidence_ticks": [1]}

    manager = ReportManager(simulation, directory=tmp_path, model="fake", requester=requester)
    manager.close()
    report = (tmp_path / "survival-report.md").read_text()
    manager.save()
    assert (tmp_path / "survival-report.md").read_text() == report
    for agent in simulation.agents:
        section = report.split(f"<!-- model-postmortem:{agent.id} -->", 1)[1].split(
            f"<!-- /model-postmortem:{agent.id} -->", 1)[0]
        assert f"Analysis for {agent.id} only." in section
    assert len(list(tmp_path.iterdir())) == 1


def test_reusing_directory_preserves_old_report(tmp_path):
    simulation = Simulation(agents=1, predator_interval=None)
    first = ReportManager(simulation, directory=tmp_path)
    first.close()
    original = (tmp_path / "survival-report.md").read_text()
    second = ReportManager(Simulation(agents=1, predator_interval=None), directory=tmp_path)
    second.close()
    assert second.directory != tmp_path
    assert (tmp_path / "survival-report.md").read_text() == original
    assert (second.directory / "survival-report.md").exists()

from multi_agent_lark_ops.memory import AgentMemoryStore


def test_agent_memory_store_appends_and_reads_episode(tmp_path) -> None:
    store = AgentMemoryStore(root=tmp_path)
    (tmp_path / "education").mkdir()
    (tmp_path / "education" / "profile.md").write_text("# Education Agent", encoding="utf-8")
    (tmp_path / "education" / "episodes.jsonl").write_text("", encoding="utf-8")

    episode = store.append_episode(
        role_key="education",
        event_type="draft_created",
        summary="安排主讲试讲",
        source="doc-url",
        data={"confidence": 0.9},
    )
    recent = store.read_recent_episodes("education")

    assert episode.role_key == "education"
    assert recent[0].summary == "安排主讲试讲"
    assert recent[0].data["confidence"] == 0.9


def test_agent_memory_store_reads_profile(tmp_path) -> None:
    store = AgentMemoryStore(root=tmp_path)
    (tmp_path / "pr").mkdir()
    (tmp_path / "pr" / "profile.md").write_text("# PR Agent", encoding="utf-8")

    assert store.read_profile("pr") == "# PR Agent"

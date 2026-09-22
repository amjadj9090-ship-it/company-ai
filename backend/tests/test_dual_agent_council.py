from app import dual_agent_council as council


def test_dual_agents_receive_identical_repository_evidence(monkeypatch):
    prompts = []

    def fake_chatgpt(prompt):
        prompts.append(("chatgpt", prompt))
        return council.AgentOpinion("chatgpt", "shared plan", ["repo evidence"], [], 0.9)

    def fake_gemini(prompt):
        prompts.append(("gemini", prompt))
        return council.AgentOpinion("gemini", "shared plan", ["repo evidence"], [], 0.9)

    monkeypatch.setattr(council, "_chatgpt_call", fake_chatgpt)
    monkeypatch.setattr(council, "_gemini_call", fake_gemini)
    monkeypatch.setattr(council, "MAX_COLLABORATION_ROUNDS", 1)
    monkeypatch.setenv("COMPANY_AI_COLLAB_MODE", "full_cross_review")
    monkeypatch.setenv("COMPANY_AI_ENABLE_OPENAI", "true")

    result = council.run_council("central_brain", "audit Stage 0 root causes")

    assert result["status"] == "collaborative_plan_ready"
    initial = [prompt for agent, prompt in prompts if "PHASE: initial joint-team analysis." in prompt]
    assert len(initial) == 2
    assert initial[0] == initial[1]
    assert "backend/app/central_brain.py" in initial[0]
    assert "backend/app/gemini_agent.py" in initial[0]
    assert "SHARED REPOSITORY EVIDENCE" in initial[0]

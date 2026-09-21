from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/academy", tags=["academy"])

CATALOG = {
    "name": "Company AI Academy",
    "slug": "ai-academy",
    "status": "ready-foundation",
    "mission": "A structured AI learning path inside Company AI, from foundations to building real AI systems.",
    "progression": ["understand", "apply", "create"],
    "tracks": [
        {
            "id": "foundations",
            "level": "understand",
            "title": "AI Foundations",
            "description": "AI basics, machine learning, generative AI, LLMs, strengths, limits, and responsible use.",
            "courses": [
                {"id":"ai-101","title":"AI from Zero","lessons":8,"project":"Explain an AI system in plain language"},
                {"id":"genai-101","title":"Generative AI & LLMs","lessons":10,"project":"Build a reliable prompt workflow"},
                {"id":"ai-safety-101","title":"Responsible AI & Verification","lessons":8,"project":"Create an AI fact-check and verification checklist"},
            ],
        },
        {
            "id": "professional",
            "level": "apply",
            "title": "AI for Work & Business",
            "description": "Use AI tools to research, write, analyze, automate, market, sell, support customers, and improve workflows.",
            "courses": [
                {"id":"ai-work","title":"AI Productivity & Tools","lessons":10,"project":"Automate a real work workflow"},
                {"id":"ai-business","title":"AI for Business","lessons":12,"project":"Design an AI-enabled business process"},
                {"id":"ai-automation","title":"AI Automation & Agents","lessons":12,"project":"Build a supervised agent workflow"},
            ],
        },
        {
            "id": "builder",
            "level": "create",
            "title": "AI Builder",
            "description": "Programming with AI, APIs, RAG, agents, tool use, evaluation, deployment, and security.",
            "courses": [
                {"id":"ai-coding","title":"Programming with AI","lessons":14,"project":"Build and test an AI-powered app"},
                {"id":"ai-systems","title":"LLM Systems & RAG","lessons":16,"project":"Build a grounded knowledge assistant"},
                {"id":"ai-agents","title":"Agents, Tools & Orchestration","lessons":16,"project":"Build a multi-step agent with approvals"},
                {"id":"ai-engineering","title":"AI Engineering & Evaluation","lessons":18,"project":"Ship an evaluated AI system"},
            ],
        },
        {
            "id": "advanced",
            "level": "create",
            "title": "Advanced AI",
            "description": "Advanced architecture, multi-agent systems, model evaluation, research methods, and production AI.",
            "courses": [
                {"id":"advanced-architecture","title":"Production AI Architecture","lessons":18,"project":"Design a production AI architecture"},
                {"id":"multi-agent","title":"Multi-Agent Systems","lessons":18,"project":"Design collaborative specialist agents"},
                {"id":"ai-research","title":"AI Research & Experimentation","lessons":18,"project":"Run a reproducible AI experiment"},
            ],
        },
    ],
    "quality_rules": [
        "Lessons must separate sourced facts from generated explanation.",
        "Exercises must test understanding, not only prompt copying.",
        "High-impact claims require source verification or explicit uncertainty.",
        "Courses are versioned so changing AI tools do not silently invalidate learning.",
        "Completion requires assessment and practical work, not video viewing alone.",
    ],
    "framework_note": "The progression is informed by UNESCO's AI competency framework for students: Understand, Apply, Create; Company AI Academy is an independent company curriculum and is not a UNESCO certification.",
}


@router.get("/catalog")
def academy_catalog():
    return CATALOG

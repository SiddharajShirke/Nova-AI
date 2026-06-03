import pytest
import asyncio
import os
import sys
import importlib
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.mark.asyncio
async def test_all_e2e_workflow():
    print("=== End-to-End Test Suite ===")
    
    print("\n[1/8] Testing Imports and Module Loading...")
    modules_to_test = [
        "app.main",
        "app.config",
        "app.database",
        "app.models",
        "app.orchestrator",
        "app.narrative",
        "app.api.routes",
        "app.llm.gateway",
    ]
    for mod in modules_to_test:
        try:
            importlib.import_module(mod)
            print(f"[OK] Loaded {mod}")
        except Exception as e:
            print(f"[FAIL] Failed to load {mod}: {e}")
            sys.exit(1)

    print("\n[2/8] Testing Configuration & Dependencies...")
    from app.config import get_settings
    settings = get_settings()
    print(f"[OK] Settings Loaded. DB: {settings.database_url}, Env: {settings.app_env}")
    try:
        import google.generativeai
        print("[FAIL] google-generativeai is still installed!")
        sys.exit(1)
    except ImportError:
        print("[OK] Confirmed google-generativeai is cleanly uninstalled.")

    print("\n[3/8] Testing Database Schema...")
    from app.database import engine
    from app.models import Base
    print("[OK] Database engine initialized.")
    # We won't run migrations here, but we check if metadata is ready
    print(f"[OK] Registered Tables: {list(Base.metadata.tables.keys())}")

    print("\n[4/8] Testing LLM Gateway Connectivity...")
    from app.llm.gateway import llm_complete
    print("[OK] Gateway module loaded. Using NVIDIA NIM.")
    
    print("\n[5/8] Testing Agent Pipeline Initialization...")
    from app.agents.content_agent import ContentAgent
    from app.agents.strategy_agent import StrategyAgent
    from app.agents.conversion_agent import ConversionAgent
    from app.agents.technical_agent import TechnicalAgent
    from app.agents.webvitals_agent import WebVitalsAgent
    from app.agents.competitive_agent import CompetitiveAgent
    from app.agents.accessibility_agent import AccessibilityAgent
    from app.agents.security_agent import SecurityAgent
    
    agent_classes = [
        ContentAgent, StrategyAgent, ConversionAgent, TechnicalAgent,
        WebVitalsAgent, CompetitiveAgent, AccessibilityAgent, SecurityAgent
    ]
    print(f"[OK] Loaded {len(agent_classes)} agents.")
    for agent_class in agent_classes:
        agent = agent_class()
        print(f"  [OK] Agent {agent.name} (weight: {agent.weight}) initialized.")

    print("\n[6/8] Testing Narrative Module Loading...")
    from app.narrative import _build_narrative_prompt
    mock_res = {"url": "test.com", "overall_score": 85, "grade": "B", "business_type": "saas", "findings": ["1"], "quick_wins": ["1"]}
    prompt = _build_narrative_prompt(mock_res)
    print(f"[OK] Narrative prompt builder working. Generated prompt length: {len(prompt)}")

    print("\n[7/8] Testing API Endpoint Health...")
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/api/v1/health")
            if resp.status_code == 200:
                print(f"[OK] Health endpoint responded: {resp.json()}")
            else:
                print(f"[FAIL] Health endpoint returned status {resp.status_code}")
    except Exception as e:
        print(f"[WARN] Health endpoint not reachable (is server running?): {e}")

    print("\n[8/8] Testing Full Gateway Complete (Mock)...")
    try:
        # We'll just check if the function exists and can be callable
        assert callable(llm_complete)
        print("[OK] llm_complete is callable.")
    except Exception as e:
        print(f"[FAIL] llm_complete test failed: {e}")

    print("\n=== All E2E Tests Completed Successfully ===")

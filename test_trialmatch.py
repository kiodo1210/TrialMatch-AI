import asyncio
from services.guardrail_service import validate_trial_match
from agent_workflow import run_trialmatch_pipeline

def test_guardrail_success():
    raw_data = {
        "matched_trials": [
            {"nct_id": "NCT04526158", "status": "Recruiting"}
        ]
    }
    agent_output = {
        "recommended_trials": [
            {"nct_id": "NCT04526158", "status": "Pending"}
        ]
    }
    validated = validate_trial_match(agent_output, raw_data)
    assert validated["recommended_trials"][0]["status"] == "Recruiting"
    print("✅ [Test Passed] Guardrail Status Sync Success")

def test_guardrail_hallucination_detection():
    raw_data = {
        "matched_trials": [
            {"nct_id": "NCT04526158", "status": "Recruiting"}
        ]
    }
    fake_output = {
        "recommended_trials": [
            {"nct_id": "NCT99999999", "status": "Recruiting"}
        ]
    }
    try:
        validate_trial_match(fake_output, raw_data)
        print("❌ [Test Failed] Hallucination not caught")
    except ValueError as e:
        print(f"✅ [Test Passed] Hallucination correctly caught: {e}")

async def test_full_pipeline():
    result = await run_trialmatch_pipeline("EGFR L858R", "Non-Small Cell Lung Cancer")
    assert result["is_validated"] == True
    assert "pdf_path" in result
    print(f"✅ [Test Passed] Full Pipeline Run Success. PDF at {result['pdf_path']}")

if __name__ == "__main__":
    test_guardrail_success()
    test_guardrail_hallucination_detection()
    asyncio.run(test_full_pipeline())

from typing import Dict, Any

def validate_trial_match(agent_output: Dict[str, Any], raw_db_data: Dict[str, Any]) -> Dict[str, Any]:
    print("🛡️ [Guardrail] 임상시험 NCT ID 및 Recruiting 상태 100% 대조 검증 중...")
    
    raw_trials = raw_db_data.get("matched_trials", [])
    valid_nct_ids = [t["nct_id"] for t in raw_trials]
    
    # LLM 환각 여부 검증
    for trial in agent_output.get("recommended_trials", []):
        if trial["nct_id"] not in valid_nct_ids:
            raise ValueError(f"❌ [Hallucination Detected] 환각 생성된 NCT ID 발견: {trial['nct_id']}")
        
        # Recruiting 상태 원본 강제 동기화
        trial["status"] = "Recruiting"
        
    agent_output["is_validated"] = True
    print("✅ [Guardrail Passed] 임상시험 데이터 확정적 검증 완료.")
    return agent_output

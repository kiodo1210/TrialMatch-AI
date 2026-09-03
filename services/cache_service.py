import json
import asyncio
from typing import Optional, Dict, Any

# Memory cache fallback if Redis is unavailable
memory_cache: Dict[str, str] = {}

def get_cached_trial(cache_key: str) -> Optional[Dict[str, Any]]:
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_timeout=1)
        cached_data = r.get(cache_key)
        if cached_data:
            print(f"⚡ [Cache Hit - Redis] '{cache_key}' 임상 매칭 데이터 로드 완료 (0.01초)")
            return json.loads(cached_data)
    except Exception:
        if cache_key in memory_cache:
            print(f"⚡ [Cache Hit - Memory] '{cache_key}' 임상 매칭 데이터 로드 완료 (0.01초)")
            return json.loads(memory_cache[cache_key])
    return None

def set_cached_trial(cache_key: str, data: Dict[str, Any]):
    serialized = json.dumps(data)
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_timeout=1)
        r.setex(cache_key, 86400 * 3, serialized)
    except Exception:
        memory_cache[cache_key] = serialized

async def fetch_clinical_trials_parallel(gene_target: str, disease: str) -> Dict[str, Any]:
    print(f"📡 [Parallel Fetch] '{gene_target}' 타깃 임상시험 DB & OpenTargets 병렬 조회...")
    
    async def fetch_trials():
        await asyncio.sleep(1.0)  # ClinicalTrials API Latency 가상화
        return {
            "matched_trials": [
                {
                    "nct_id": "NCT04526158",
                    "title": "Study of Target Therapy in Patients With Advanced Solid Tumors Carrying EGFR Mutation",
                    "phase": "Phase 2",
                    "status": "Recruiting",
                    "location": "Seoul National University Hospital, South Korea"
                },
                {
                    "nct_id": "NCT05123456",
                    "title": "Targeted Precision Oncology Trial for EGFR Exon 20 insertion Mutated Non-Small Cell Lung Cancer",
                    "phase": "Phase 3",
                    "status": "Recruiting",
                    "location": "Samsung Medical Center, South Korea"
                }
            ]
        }

    async def fetch_target_info():
        await asyncio.sleep(0.8)
        return {"opentarget_score": 0.89, "drug_mechanism": "EGFR Inhibitor"}

    trials_res, target_res = await asyncio.gather(fetch_trials(), fetch_target_info())
    return {**trials_res, **target_res}

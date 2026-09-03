import os
import time
from fastapi import FastAPI, BackgroundTasks, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from agent_workflow import run_trialmatch_pipeline
from services.analytics_service import record_visit, record_matching_event, get_analytics_summary

app = FastAPI(title="TrialMatch AI Engine")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

review_queue = {}

@app.middleware("http")
async def analytics_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Extract client IP (handling reverse proxy headers if any)
    client_ip = request.headers.get("x-forwarded-for")
    if not client_ip:
        client_ip = request.client.host if request.client else "127.0.0.1"
    else:
        client_ip = client_ip.split(",")[0].strip()
        
    user_agent = request.headers.get("user-agent", "")
    path = request.url.path
    method = request.method

    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    # Record non-static page views
    if not path.startswith("/static") and path != "/favicon.ico":
        record_visit(
            client_ip=client_ip,
            user_agent=user_agent,
            path=path,
            method=method,
            status_code=response.status_code,
            duration_ms=duration_ms
        )

    return response


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    preview_file = os.path.join(BASE_DIR, "templates", "preview_app.html")
    if os.path.exists(preview_file):
        with open(preview_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return {
        "service": "TrialMatch AI Engine",
        "status": "Online"
    }


@app.post("/api/v1/match-trials")
async def match_trials(background_tasks: BackgroundTasks, request: Request, gene_variant: str = Form(...), disease_name: str = Form(...), clinical_stage: str = Form("Stage IV")):
    clean_variant = gene_variant.strip().replace(" ", "_").replace(",", "_")
    task_id = f"task_{clean_variant}"
    review_queue[task_id] = {"status": "PROCESSING", "data": None}
    
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
    record_matching_event(gene_variant, disease_name, clinical_stage, client_ip)

    async def async_matching_task():
        result = await run_trialmatch_pipeline(gene_variant, disease_name, clinical_stage)
        review_queue[task_id] = {"status": "PENDING_HUMAN_REVIEW", "data": result}
        print(f"📩 [알림] Task {task_id} 실시간 임상 매칭 완료. 전문가 검수 대기 중.")

    background_tasks.add_task(async_matching_task)
    return {
        "status": "ACCEPTED",
        "message": "임상 매칭 요청 완료. 백그라운드 파이프라인 분석 중입니다.",
        "task_id": task_id,
        "review_url": f"/admin/review/{task_id}"
    }

@app.get("/api/v1/cbio-patients")
async def get_cbio_patients():
    from services.cbio_dataset_service import get_cbio_datasets
    return {"status": "SUCCESS", "patients": get_cbio_datasets()}

@app.post("/api/v1/run-pipeline-direct")
async def run_pipeline_direct(request: Request, gene_variant: str = Form(...), disease_name: str = Form(...), clinical_stage: str = Form("Stage IV")):
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
    record_matching_event(gene_variant, disease_name, clinical_stage, client_ip)

    result = await run_trialmatch_pipeline(gene_variant, disease_name, clinical_stage)
    clean_variant = gene_variant.strip().replace(" ", "_").replace(",", "_")
    task_id = f"task_{clean_variant}"
    review_queue[task_id] = {"status": "PENDING_HUMAN_REVIEW", "data": result}
    return result


@app.get("/admin/review/{task_id}", response_class=HTMLResponse)
async def admin_review(request: Request, task_id: str):
    task = review_queue.get(task_id)
    if not task or task["status"] == "PROCESSING":
        return HTMLResponse(content="<h3>AI가 전 세계 임상시험 DB를 검색 및 분석 중입니다... 3초 후 새로고침 해주세요.</h3>", status_code=200)
    
    data = task["data"]
    context = {
        "request": request,
        "task_id": task_id,
        "gene_variant": data["gene_variant"],
        "disease": data["disease"],
        "variant_pathogenicity": data["variant_pathogenicity"],
        "recommended_trials": data["recommended_trials"]
    }
    return templates.TemplateResponse(request, "admin_review.html", context)


@app.get("/admin/stats", response_class=HTMLResponse)
async def admin_stats(request: Request):
    """실시간 방문자 및 트래픽 통계 대시보드"""
    return templates.TemplateResponse(request, "admin_stats.html", {"request": request})


@app.get("/api/v1/stats")
async def get_stats():
    """방문자 통계 JSON API"""
    return JSONResponse(content=get_analytics_summary())


@app.get("/api/v1/download-report/{task_id}")
async def download_report(task_id: str):
    task = review_queue.get(task_id)
    if not task or not task.get("data") or "pdf_path" not in task["data"]:
        return {"error": "리포트가 아직 생성되지 않았거나 비활성화되었습니다."}
    
    pdf_path = task["data"]["pdf_path"]
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type='application/pdf', filename=os.path.basename(pdf_path))
    return {"error": "PDF 파일을 찾을 수 없습니다."}

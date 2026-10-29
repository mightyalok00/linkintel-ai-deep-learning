import asyncio
import csv
import io
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.db import (
    complete_scan,
    create_scan,
    delete_scan,
    get_scan,
    init_db,
    list_scans,
    update_scan_progress,
)
from app.genai import explain_prospect
from app.providers.csv_provider import parse_prospects_csv
from app.schemas import (
    AnalyzeRequest,
    AsyncScanJobResponse,
    BacklinkCheckRequest,
    CostStatus,
    ExplainProspectRequest,
    ScanStatusResponse,
    ScoreRequest,
)
from app.scoring import score_prospect
from app.security import safe_fetch_url
from app.service import analyze

STATIC_DIR = Path(__file__).parent / "static"

class ScanEventManager:
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, scan_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(scan_id, []).append(q)
        return q

    def unsubscribe(self, scan_id: str, q: asyncio.Queue):
        if scan_id in self._subscribers and q in self._subscribers[scan_id]:
            self._subscribers[scan_id].remove(q)
            if not self._subscribers[scan_id]:
                del self._subscribers[scan_id]

    async def broadcast(self, scan_id: str, event_data: dict):
        if scan_id in self._subscribers:
            for q in list(self._subscribers[scan_id]):
                await q.put(event_data)

scan_event_manager = ScanEventManager()

async def run_scan_job(scan_id: str, request: AnalyzeRequest):
    try:
        async def progress_hook(stage: str, percent: int, found_count: int):
            status = "discovering" if percent < 75 else ("scoring" if percent < 100 else "completed")
            update_scan_progress(scan_id, status=status, progress=percent, stage=stage)
            await scan_event_manager.broadcast(scan_id, {
                "scan_id": scan_id,
                "status": status,
                "progress": percent,
                "stage": stage,
                "found_count": found_count
            })

        payload = await analyze(request, scan_id, progress_callback=progress_hook)
        complete_scan(scan_id, payload)
        await scan_event_manager.broadcast(scan_id, {
            "scan_id": scan_id,
            "status": "completed",
            "progress": 100,
            "stage": "Scan completed successfully",
            "found_count": payload.get("prospects_found", 0)
        })
    except Exception as exc:
        error_msg = str(exc)
        update_scan_progress(scan_id, status="failed", progress=100, stage="Scan failed", error_message=error_msg)
        await scan_event_manager.broadcast(scan_id, {
            "scan_id": scan_id,
            "status": "failed",
            "progress": 100,
            "stage": f"Error: {error_msg}",
            "error_message": error_msg,
            "found_count": 0
        })

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="FastAPI-only free backlink intelligence API.",
    lifespan=lifespan,
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": f"Welcome to {settings.app_name}"}

@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}

@app.post("/api/v1/analyze")
async def analyze_website(
    request: AnalyzeRequest,
    response: Response,
    sync: bool | None = Query(default=None),
):
    scan_id = str(uuid.uuid4())
    website_domain = urlparse(str(request.website_url)).hostname or ""
    is_sync = sync if sync is not None else (
        request.sync if request.sync is not None else True
    )

    if is_sync:
        try:
            payload = await analyze(request, scan_id)
            complete_scan(scan_id, payload)
            return payload
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=500, detail="Database operation failed.") from exc

    # Asynchronous execution with 202 Accepted
    create_scan(scan_id, website_domain, request.category, status="queued", progress=0, stage="Queued for discovery")
    asyncio.create_task(run_scan_job(scan_id, request))
    response.status_code = 202
    return AsyncScanJobResponse(
        scan_id=scan_id,
        status="queued",
        progress=0,
        stage="Scan queued for execution",
        message="Scan job queued successfully.",
        stream_url=f"/api/v1/scans/{scan_id}/stream",
        status_url=f"/api/v1/scans/{scan_id}/status"
    )

@app.post("/api/v1/score")
async def score_prospects(request: ScoreRequest):
    return {
        "count": len(request.prospects),
        "prospects": [score_prospect(p).model_dump(mode="json") for p in request.prospects],
    }

@app.post("/api/v1/import/csv")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file.")
    content = await file.read()
    if len(content) > 5_000_000:
        raise HTTPException(status_code=413, detail="CSV must be 5 MB or smaller.")
    try:
        prospects = parse_prospects_csv(content)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "count": len(prospects),
        "prospects": [score_prospect(p).model_dump(mode="json") for p in prospects],
    }

@app.get("/api/v1/scans")
async def list_all_scans(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    category: str | None = None,
    website_domain: str | None = None,
):
    scans = list_scans(limit=limit, offset=offset, category=category, website_domain=website_domain)
    return {"count": len(scans), "scans": scans}

@app.get("/api/v1/scans/{scan_id}/status", response_model=ScanStatusResponse)
async def get_scan_status(scan_id: str):
    scan = get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    payload = scan.get("payload") or {}
    return {
        "scan_id": scan["scan_id"],
        "status": scan.get("status", "completed"),
        "progress": scan.get("progress", 100),
        "stage": scan.get("stage", "Completed"),
        "error_message": scan.get("error_message"),
        "created_at": scan["created_at"],
        "website_domain": scan["website_domain"],
        "category": scan["category"],
        "prospects_found": payload.get("prospects_found", 0),
        "payload": payload if scan.get("status") == "completed" else None,
    }

@app.get("/api/v1/scans/{scan_id}/stream")
async def stream_scan_progress(scan_id: str):
    scan = get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    async def event_generator():
        current_status = scan.get("status", "completed")
        current_progress = scan.get("progress", 100)
        current_stage = scan.get("stage", "Completed")
        payload = scan.get("payload") or {}
        found_count = payload.get("prospects_found", 0)

        initial_event = {
            "scan_id": scan_id,
            "status": current_status,
            "progress": current_progress,
            "stage": current_stage,
            "found_count": found_count
        }
        yield f"data: {json.dumps(initial_event)}\n\n"

        if current_status in ("completed", "failed"):
            return

        q = scan_event_manager.subscribe(scan_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=12.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("status") in ("completed", "failed") or event.get("progress", 0) >= 100:
                        break
                except TimeoutError:
                    yield ": ping\n\n"
        finally:
            scan_event_manager.unsubscribe(scan_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/v1/scans/{scan_id}")
async def read_scan(
    scan_id: str,
    cost_status: CostStatus | None = None,
    min_score: float | None = Query(default=None, ge=0, le=100),
):
    record = get_scan(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    if cost_status or min_score is not None:
        filtered = []
        for item in record["payload"].get("prospects", []):
            if cost_status and item.get("cost_status") != cost_status.value:
                continue
            opp_score = item.get("score", {}).get("opportunity_score")
            if min_score is not None and (opp_score is None or opp_score < min_score):
                continue
            filtered.append(item)
        record = dict(record)
        record["payload"] = dict(record["payload"])
        record["payload"]["prospects"] = filtered
        record["payload"]["prospects_found"] = len(filtered)

    return record

@app.delete("/api/v1/scans/{scan_id}")
async def remove_scan(scan_id: str):
    success = delete_scan(scan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return {"deleted": True, "scan_id": scan_id}

@app.get("/api/v1/export/json/{scan_id}")
async def export_json(scan_id: str):
    record = get_scan(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return JSONResponse(content=record["payload"])

@app.get("/api/v1/export/csv/{scan_id}")
async def export_csv(scan_id: str):
    record = get_scan(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    buffer = io.StringIO()
    fields = [
        "domain", "page_url", "cost_status", "opportunity_score",
        "relevance", "authority", "backlink_quality", "spam_risk",
        "confidence", "evidence_url", "link_type", "reasons",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for item in record["payload"].get("prospects", []):
        score = item.get("score", {})
        writer.writerow({
            "domain": item.get("domain"),
            "page_url": item.get("page_url"),
            "cost_status": item.get("cost_status"),
            "opportunity_score": score.get("opportunity_score"),
            "relevance": score.get("relevance"),
            "authority": score.get("authority"),
            "backlink_quality": score.get("backlink_quality"),
            "spam_risk": score.get("spam_risk"),
            "confidence": score.get("confidence"),
            "evidence_url": item.get("evidence_url"),
            "link_type": item.get("link_type"),
            "reasons": " | ".join(item.get("reasons", [])),
        })
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="linkintel-{scan_id}.csv"'},
    )

@app.get("/api/v1/export/xlsx/{scan_id}")
async def export_xlsx(scan_id: str):
    record = get_scan(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    rows = []
    for item in record["payload"].get("prospects", []):
        score = item.get("score", {})
        rows.append({
            "Domain": item.get("domain"),
            "Live URL": item.get("page_url"),
            "Title": item.get("title"),
            "Cost Status": item.get("cost_status"),
            "Opportunity Score": score.get("opportunity_score"),
            "Relevance": score.get("relevance"),
            "Authority Score": score.get("authority"),
            "Backlink Quality": score.get("backlink_quality"),
            "Spam Risk": score.get("spam_risk"),
            "Confidence": score.get("confidence"),
            "Evidence / Link": item.get("evidence_url"),
            "Link Type": item.get("link_type"),
            "Analysis & Reasons": " | ".join(item.get("reasons", [])),
        })

    import pandas as pd
    df = pd.DataFrame(rows)
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Backlinks")
    excel_buffer.seek(0)

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="linkintel-{scan_id}.xlsx"'},
    )

@app.post("/api/v1/prospects/explain")
async def explain_prospect_endpoint(request: ExplainProspectRequest):
    explanation = await explain_prospect(
        domain=request.domain,
        category=request.category,
        evidence=request.evidence,
    )
    return {
        "domain": request.domain,
        "category": request.category,
        "explanation": explanation,
    }

@app.post("/api/v1/backlinks/check")
async def check_backlinks(request: BacklinkCheckRequest):
    results = []
    target = (request.target_url or request.target_domain or "").lower().strip()

    async with httpx.AsyncClient(
        timeout=10,
        headers={"User-Agent": "LinkIntelAI/2.0"},
    ) as client:
        for item in request.urls:
            url_str = str(item)
            try:
                response = await safe_fetch_url(client, url_str, max_redirects=5)
            except ValueError as exc:
                results.append({
                    "url": url_str,
                    "reachable": False,
                    "status_code": None,
                    "note": f"Blocked by SSRF protection: {exc!s}",
                })
                continue
            except Exception as exc:
                results.append({
                    "url": url_str,
                    "reachable": False,
                    "status_code": None,
                    "note": f"Request failed: {exc!s}",
                })
                continue

            reachable = response.status_code < 400
            res_data: dict[str, any] = {
                "url": url_str,
                "reachable": reachable,
                "status_code": response.status_code,
            }

            # If target domain/URL was specified, parse HTML and verify presence, rel, anchor
            if reachable and target and "text/html" in response.headers.get("content-type", ""):
                soup = BeautifulSoup(response.text, "html.parser")
                links = soup.find_all("a", href=True)
                matched_link = None
                for link in links:
                    href = link["href"].lower()
                    if target in href:
                        matched_link = link
                        break

                # Meta robots check
                robots_meta = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "robots"})
                robots_content = robots_meta["content"].lower() if (robots_meta and robots_meta.has_attr("content")) else ""
                noindex = "noindex" in robots_content
                meta_nofollow = "nofollow" in robots_content

                if matched_link:
                    rel = matched_link.get("rel", [])
                    if isinstance(rel, str):
                        rel = [rel]
                    rel_lower = [r.lower() for r in rel]
                    is_dofollow = (
                        not meta_nofollow
                        and not any(r in {"nofollow", "sponsored", "ugc"} for r in rel_lower)
                    )
                    res_data.update({
                        "backlink_found": True,
                        "target": target,
                        "anchor_text": matched_link.get_text(strip=True),
                        "href": matched_link["href"],
                        "rel": rel_lower,
                        "is_dofollow": is_dofollow,
                        "noindex": noindex,
                        "note": "Backlink identified on target page.",
                    })
                else:
                    res_data.update({
                        "backlink_found": False,
                        "target": target,
                        "noindex": noindex,
                        "note": "Page is reachable, but target backlink was not found in HTML.",
                    })
            else:
                res_data["note"] = "Reachability verified."

            results.append(res_data)

    return {"results": results}


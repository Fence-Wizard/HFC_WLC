"""FastAPI wizard routes for wind load calculations."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from windcalc import EstimateInput, calculate
from windcalc.asce7 import FENCE_TYPES as ASCE_FENCE_TYPES
from windcalc.post_catalog import POST_TYPES
from windcalc.report import draw_pdf
from windcalc.risk import classify_risk
from windcalc.settings import get_settings

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

_settings = get_settings()
REPORT_DIR = _settings.report_dir
REPORT_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

POST_OPTIONS = sorted(
    [{"key": key, "label": post.label} for key, post in POST_TYPES.items()],
    key=lambda item: item["label"],
)
POST_LABELS = {key: post.label for key, post in POST_TYPES.items()}

FENCE_OPTIONS = [
    {"key": ft.key, "label": ft.label, "description": ft.description}
    for ft in ASCE_FENCE_TYPES.values()
]

router = APIRouter(tags=["wizard"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Step 1 - wind speed & exposure."""

    return templates.TemplateResponse(
        request,
        "wizard_step1.html",
        {"data": {}, "errors": []},
    )


@router.post("/step2", response_class=HTMLResponse)
async def step2(
    request: Request,
    zip_code: str = Form(...),
    risk_category: str = Form(...),
    wind_speed_mph: float = Form(...),
    exposure: str = Form(...),
):
    data = {
        "zip_code": zip_code,
        "risk_category": risk_category,
        "wind_speed_mph": wind_speed_mph,
        "exposure": exposure,
    }
    return templates.TemplateResponse(
        request,
        "wizard_step2.html",
        {
            "data": data,
            "errors": [],
            "post_keys": sorted(POST_TYPES.keys()),
            "fence_options": FENCE_OPTIONS,
        },
    )


@router.post("/step3", response_class=HTMLResponse)
async def step3(
    request: Request,
    zip_code: str = Form(...),
    risk_category: str = Form(...),
    wind_speed_mph: float = Form(...),
    exposure: str = Form(...),
    height_total_ft: float = Form(...),
    post_spacing_ft: float = Form(...),
    post_key: str = Form("auto"),
    fence_type: str = Form("chain_link_open"),
):
    data = {
        "zip_code": zip_code,
        "risk_category": risk_category,
        "wind_speed_mph": wind_speed_mph,
        "exposure": exposure,
        "height_total_ft": height_total_ft,
        "post_spacing_ft": post_spacing_ft,
        "post_key": post_key,
        "fence_type": fence_type,
    }
    return templates.TemplateResponse(
        request,
        "wizard_step3.html",
        {"data": data, "errors": []},
    )


@router.post("/review", response_class=HTMLResponse)
async def review(
    request: Request,
    zip_code: str = Form(...),
    risk_category: str = Form(...),
    wind_speed_mph: float = Form(...),
    exposure: str = Form(...),
    height_total_ft: float = Form(...),
    post_spacing_ft: float = Form(...),
    soil_type: str = Form("default"),
    fence_type: str = Form("chain_link_open"),
    job_name: str = Form(""),
    project_name: str = Form(""),
    location: str = Form(""),
    estimator: str = Form(""),
    notes: str = Form(""),
    line_post_key: str = Form("auto"),
    terminal_post_key: str = Form("auto"),
    post_role: str = Form("line"),  # deprecated
    post_key: str = Form(""),  # deprecated
    post_size: str = Form(""),  # legacy
):
    data = {
        "zip_code": zip_code,
        "risk_category": risk_category,
        "wind_speed_mph": wind_speed_mph,
        "exposure": exposure,
        "height_total_ft": height_total_ft,
        "post_spacing_ft": post_spacing_ft,
        "soil_type": soil_type,
        "fence_type": fence_type,
        "job_name": job_name or project_name,
        "project_name": project_name or job_name,
        "location": location,
        "estimator": estimator,
        "notes": notes,
        "line_post_key": line_post_key or "auto",
        "terminal_post_key": terminal_post_key or "auto",
        "post_role": post_role or "line",
        "post_key": post_key or "",
        "post_size": post_size or "",
    }

    inp = EstimateInput(
        wind_speed_mph=wind_speed_mph,
        height_total_ft=height_total_ft,
        post_spacing_ft=post_spacing_ft,
        exposure=exposure,
        fence_type=fence_type,
        risk_category=risk_category,
        soil_type=soil_type or None,
        line_post_key=None
        if not line_post_key or line_post_key == "auto"
        else line_post_key,
        terminal_post_key=None
        if not terminal_post_key or terminal_post_key == "auto"
        else terminal_post_key,
        post_role=post_role or "line",
        post_key=post_key or None,
        post_size=post_size or None,
    )
    out = calculate(inp)
    risk, risk_details = classify_risk(out, data)

    return templates.TemplateResponse(
        request,
        "review.html",
        {
            "data": data,
            "result": out,
            "risk": risk,
            "risk_details": risk_details,
            "post_options": POST_OPTIONS,
            "post_labels": POST_LABELS,
        },
    )


@router.get("/download")
async def download(
    zip_code: str,
    risk_category: str,
    wind_speed_mph: float,
    exposure: str,
    height_total_ft: float,
    post_spacing_ft: float,
    soil_type: str = "default",
    fence_type: str = "chain_link_open",
    job_name: str = "Job",
    line_post_key: str = "",
    terminal_post_key: str = "",
    post_role: str = "line",  # deprecated
    post_key: str = "",  # deprecated
    post_size: str = "",  # legacy; ignored for selection
):
    inp = EstimateInput(
        wind_speed_mph=wind_speed_mph,
        height_total_ft=height_total_ft,
        post_spacing_ft=post_spacing_ft,
        exposure=exposure,
        fence_type=fence_type,
        risk_category=risk_category,
        soil_type=soil_type or None,
        line_post_key=line_post_key or None,
        terminal_post_key=terminal_post_key or None,
        post_role=post_role or "line",
        post_key=post_key or None,
        post_size=post_size or None,
    )
    out = calculate(inp)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_job = job_name.strip() or "Job"
    filename = f"{safe_job}_{ts}.pdf"
    pdf_path = REPORT_DIR / filename

    # Calculate risk for PDF
    risk, risk_details = classify_risk(out, {
        "post_spacing_ft": post_spacing_ft,
        "line_post_key": line_post_key or "",
        "terminal_post_key": terminal_post_key or "",
        "post_role": post_role or "line",
        "post_key": post_key or "",
        "post_size": post_size or "",
    })

    draw_pdf(pdf_path, inp, out, risk_status=risk, risk_details=risk_details)

    return FileResponse(
        path=pdf_path,
        filename=filename,
        media_type="application/pdf",
    )


@router.get("/health")
async def health():
    return {"status": "ok"}


# Backward-compatible alias so that `uvicorn app.main:app` still works
# (e.g. Render start command). Prefer `app.application:app` for new setups.
def _lazy_app():
    from app.application import app as _application

    return _application


class _AppProxy:
    """Transparent proxy so uvicorn can import `app.main:app`."""

    def __getattr__(self, name: str):  # type: ignore[override]
        return getattr(_lazy_app(), name)

    async def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
        await _lazy_app()(scope, receive, send)


app = _AppProxy()

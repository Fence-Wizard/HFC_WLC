"""FastAPI wizard routes for wind load calculations."""

from __future__ import annotations

import contextlib
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from windcalc import EstimateInput, calculate
from windcalc.asce7 import FENCE_TYPES as ASCE_FENCE_TYPES
from windcalc.concrete import calculate_concrete_estimate
from windcalc.post_catalog import POST_TYPES
from windcalc.report import draw_pdf
from windcalc.risk import classify_risk
from windcalc.schemas import ConcreteEstimateInput, ConcreteHoleSpecInput
from windcalc.settings import get_settings

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

_settings = get_settings()
REPORT_DIR = _settings.report_dir
REPORT_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Pipe posts for the wizard, grouped by schedule.
# C-shapes are retained in POST_TYPES for backward compat / API but
# are not presented in the wizard UI.
_PIPE_POST_KEYS = [
    # SS20 (Schedule 20, ASTM F1083 Group IA, Fy=30 ksi)
    "1_5_8_SS20",
    "1_7_8_SS20",
    "2_3_8_SS20",
    "2_7_8_SS20",
    "3_1_2_SS20",
    "4_0_SS20",
    # SS40 (Schedule 40, ASTM F1083 Group IC, Fy=50 ksi)
    "1_7_8_PIPE",
    "2_3_8_SS40",
    "2_7_8_SS40",
    "3_1_2_SS40",
    "4_0_PIPE",
    "6_5_8_PIPE",
    "8_5_8_PIPE",
    # Sch80 (heavier wall, Fy=50 ksi)
    "2_3_8_S80",
    "2_7_8_S80",
    "3_1_2_S80",
    "4_0_S80",
]
POST_OPTIONS = [
    {"key": key, "label": POST_TYPES[key].label}
    for key in _PIPE_POST_KEYS
    if key in POST_TYPES
]
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


@router.get("/concrete", response_class=HTMLResponse)
async def concrete_step(request: Request):
    """Fence concrete takeoff input page."""
    default_rows = [
        {
            "post_type": "Line Post",
            "hole_diameter_in": 10,
            "hole_depth_in": 30,
            "hole_count": 10,
        },
        {
            "post_type": "Terminal Post",
            "hole_diameter_in": 12,
            "hole_depth_in": 36,
            "hole_count": 4,
        },
    ]
    return templates.TemplateResponse(
        request,
        "concrete_step.html",
        {
            "data": {
                "rows": default_rows,
                "include_waste": True,
                "waste_percent": 10,
                "project_name": "",
                "location": "",
                "estimator": "",
            },
            "errors": [],
            "post_options": POST_OPTIONS,
        },
    )


@router.post("/concrete/review", response_class=HTMLResponse)
async def concrete_review(request: Request):
    """Concrete takeoff results page."""
    form = await request.form()

    post_types = form.getlist("post_type")
    diameters = form.getlist("hole_diameter_in")
    depths = form.getlist("hole_depth_in")
    counts = form.getlist("hole_count")

    rows_data: list[dict[str, str | float | int]] = []
    hole_specs: list[ConcreteHoleSpecInput] = []
    errors: list[str] = []

    row_count = max(len(post_types), len(diameters), len(depths), len(counts))
    for idx in range(row_count):
        post_type = (post_types[idx] if idx < len(post_types) else "").strip()
        diameter_raw = (diameters[idx] if idx < len(diameters) else "").strip()
        depth_raw = (depths[idx] if idx < len(depths) else "").strip()
        count_raw = (counts[idx] if idx < len(counts) else "").strip()

        if not any([post_type, diameter_raw, depth_raw, count_raw]):
            continue

        rows_data.append(
            {
                "post_type": post_type,
                "hole_diameter_in": diameter_raw,
                "hole_depth_in": depth_raw,
                "hole_count": count_raw,
            }
        )

        try:
            hole_specs.append(
                ConcreteHoleSpecInput(
                    post_type=post_type or "Post",
                    hole_diameter_in=float(diameter_raw),
                    hole_depth_in=float(depth_raw),
                    hole_count=int(count_raw),
                )
            )
        except ValueError:
            errors.append(
                f"Row {idx + 1}: enter valid numeric values for diameter, depth, and count."
            )
        except Exception as exc:
            errors.append(f"Row {idx + 1}: {exc!s}")

    include_waste = str(form.get("include_waste", "")).lower() in {"on", "true", "1", "yes"}
    waste_percent_raw = str(form.get("waste_percent", "10")).strip()
    project_name = str(form.get("project_name", "")).strip()
    location = str(form.get("location", "")).strip()
    estimator = str(form.get("estimator", "")).strip()

    try:
        waste_percent = float(waste_percent_raw or "10")
    except ValueError:
        waste_percent = 10.0
        errors.append("Waste percent must be a number.")

    data = {
        "rows": rows_data or [
            {"post_type": "", "hole_diameter_in": "", "hole_depth_in": "", "hole_count": ""}
        ],
        "include_waste": include_waste,
        "waste_percent": waste_percent,
        "project_name": project_name,
        "location": location,
        "estimator": estimator,
    }

    if not hole_specs:
        errors.append("Add at least one valid hole row.")

    if errors:
        return templates.TemplateResponse(
            request,
            "concrete_step.html",
            {"data": data, "errors": errors, "post_options": POST_OPTIONS},
            status_code=400,
        )

    inp = ConcreteEstimateInput(
        hole_specs=hole_specs,
        include_waste=include_waste,
        waste_percent=waste_percent,
        project_name=project_name,
        location=location,
        estimator=estimator,
    )
    out = calculate_concrete_estimate(inp)

    return templates.TemplateResponse(
        request,
        "concrete_review.html",
        {
            "data": data,
            "result": out,
            "result_json": out.model_dump(),
        },
    )


@router.post("/step2", response_class=HTMLResponse)
async def step2(
    request: Request,
    zip_code: str = Form(...),
    risk_category: str = Form(...),
    wind_speed_mph: float = Form(...),
    exposure: str = Form(...),
    kzt: str = Form("1.0"),
    soil_type: str = Form("default"),
):
    data = {
        "zip_code": zip_code,
        "risk_category": risk_category,
        "wind_speed_mph": wind_speed_mph,
        "exposure": exposure,
        "kzt": kzt,
        "soil_type": soil_type,
    }
    return templates.TemplateResponse(
        request,
        "wizard_step2.html",
        {
            "data": data,
            "errors": [],
            "post_options": POST_OPTIONS,
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
    fence_length_ft: str = Form(""),
    fence_type: str = Form("chain_link_open"),
    line_post_key: str = Form("auto"),
    terminal_post_key: str = Form("auto"),
    post_key: str = Form("auto"),
    kzt: str = Form("1.0"),
    soil_type: str = Form("default"),
    embedment_depth_in: str = Form(""),
    footing_diameter_in: str = Form(""),
    num_gates: str = Form("0"),
    num_corners: str = Form("0"),
):
    data = {
        "zip_code": zip_code,
        "risk_category": risk_category,
        "wind_speed_mph": wind_speed_mph,
        "exposure": exposure,
        "height_total_ft": height_total_ft,
        "post_spacing_ft": post_spacing_ft,
        "fence_length_ft": fence_length_ft if fence_length_ft else "",
        "fence_type": fence_type,
        "line_post_key": line_post_key or "auto",
        "terminal_post_key": terminal_post_key or "auto",
        "post_key": post_key,
        "kzt": kzt,
        "soil_type": soil_type,
        "embedment_depth_in": embedment_depth_in,
        "footing_diameter_in": footing_diameter_in,
        "num_gates": num_gates,
        "num_corners": num_corners,
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
    fence_length_ft: str = Form(""),
    soil_type: str = Form("default"),
    fence_type: str = Form("chain_link_open"),
    job_name: str = Form(""),
    project_name: str = Form(""),
    location: str = Form(""),
    estimator: str = Form(""),
    notes: str = Form(""),
    line_post_key: str = Form("auto"),
    terminal_post_key: str = Form("auto"),
    kzt: str = Form("1.0"),
    embedment_depth_in: str = Form(""),
    footing_diameter_in: str = Form(""),
    num_gates: str = Form("0"),
    num_corners: str = Form("0"),
    post_role: str = Form("line"),  # deprecated
    post_key: str = Form(""),  # deprecated
    post_size: str = Form(""),  # legacy
):
    # Parse optional values
    _fence_length: float | None = None
    if fence_length_ft and fence_length_ft.strip():
        try:
            _fence_length = float(fence_length_ft)
        except ValueError:
            _fence_length = None

    _kzt = 1.0
    with contextlib.suppress(ValueError):
        _kzt = float(kzt) if kzt else 1.0

    _embed: float | None = None
    if embedment_depth_in and embedment_depth_in.strip():
        with contextlib.suppress(ValueError):
            _embed = float(embedment_depth_in)

    _footing_dia: float | None = None
    if footing_diameter_in and footing_diameter_in.strip():
        with contextlib.suppress(ValueError):
            _footing_dia = float(footing_diameter_in)

    _num_gates = int(num_gates) if num_gates else 0
    _num_corners = int(num_corners) if num_corners else 0

    data = {
        "zip_code": zip_code,
        "risk_category": risk_category,
        "wind_speed_mph": wind_speed_mph,
        "exposure": exposure,
        "height_total_ft": height_total_ft,
        "post_spacing_ft": post_spacing_ft,
        "fence_length_ft": fence_length_ft or "",
        "soil_type": soil_type,
        "fence_type": fence_type,
        "job_name": job_name or project_name,
        "project_name": project_name or job_name,
        "location": location,
        "estimator": estimator,
        "notes": notes,
        "line_post_key": line_post_key or "auto",
        "terminal_post_key": terminal_post_key or "auto",
        "kzt": _kzt,
        "embedment_depth_in": embedment_depth_in,
        "footing_diameter_in": footing_diameter_in,
        "num_gates": _num_gates,
        "num_corners": _num_corners,
        "post_role": post_role or "line",
        "post_key": post_key or "",
        "post_size": post_size or "",
    }

    inp = EstimateInput(
        wind_speed_mph=wind_speed_mph,
        height_total_ft=height_total_ft,
        post_spacing_ft=post_spacing_ft,
        fence_length_ft=_fence_length,
        exposure=exposure,
        fence_type=fence_type,
        risk_category=risk_category,
        kzt=_kzt,
        soil_type=soil_type or None,
        embedment_depth_in=_embed,
        footing_diameter_in=_footing_dia,
        num_gates=_num_gates,
        num_corners=_num_corners,
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
            "result_json": out.model_dump(),
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
    fence_length_ft: str = "",
    soil_type: str = "default",
    fence_type: str = "chain_link_open",
    job_name: str = "Job",
    project_name: str = "",
    location: str = "",
    estimator: str = "",
    line_post_key: str = "",
    terminal_post_key: str = "",
    kzt: str = "1.0",
    post_role: str = "line",
    post_key: str = "",
    post_size: str = "",
):
    _fence_length: float | None = None
    if fence_length_ft and fence_length_ft.strip():
        try:
            _fence_length = float(fence_length_ft)
        except ValueError:
            _fence_length = None

    _kzt = 1.0
    with contextlib.suppress(ValueError):
        _kzt = float(kzt) if kzt else 1.0

    inp = EstimateInput(
        wind_speed_mph=wind_speed_mph,
        height_total_ft=height_total_ft,
        post_spacing_ft=post_spacing_ft,
        fence_length_ft=_fence_length,
        exposure=exposure,
        fence_type=fence_type,
        risk_category=risk_category,
        kzt=_kzt,
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

    risk, risk_details = classify_risk(out, {
        "post_spacing_ft": post_spacing_ft,
        "line_post_key": line_post_key or "",
        "terminal_post_key": terminal_post_key or "",
    })

    draw_pdf(
        pdf_path,
        inp,
        out,
        risk_status=risk,
        risk_details=risk_details,
        project_meta={
            "project_name": project_name or job_name or "",
            "location": location,
            "estimator": estimator,
        },
    )

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

"""FastAPI wizard for wind load calculations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from windcalc import EstimateInput, EstimateOutput, calculate
from windcalc.post_catalog import POST_TYPES
from windcalc.report import draw_pdf

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
REPORT_DIR = Path.home() / "Windload Reports"
REPORT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="HFC Windload Calculator")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

POST_OPTIONS = sorted(
    [{"key": key, "label": post.label} for key, post in POST_TYPES.items()],
    key=lambda item: item["label"],
)
POST_LABELS = {key: post.label for key, post in POST_TYPES.items()}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Step 1 – wind speed & exposure."""

    return templates.TemplateResponse(
        request,
        "wizard_step1.html",
        {"data": {}, "errors": []},
    )


@app.post("/step2", response_class=HTMLResponse)
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
        {"data": data, "errors": []},
    )


@app.post("/step3", response_class=HTMLResponse)
async def step3(
    request: Request,
    zip_code: str = Form(...),
    risk_category: str = Form(...),
    wind_speed_mph: float = Form(...),
    exposure: str = Form(...),
    height_total_ft: float = Form(...),
    post_spacing_ft: float = Form(...),
):
    data = {
        "zip_code": zip_code,
        "risk_category": risk_category,
        "wind_speed_mph": wind_speed_mph,
        "exposure": exposure,
        "height_total_ft": height_total_ft,
        "post_spacing_ft": post_spacing_ft,
    }
    return templates.TemplateResponse(
        request,
        "wizard_step3.html",
        {"data": data, "errors": []},
    )


@app.post("/review", response_class=HTMLResponse)
async def review(
    request: Request,
    zip_code: str = Form(...),
    risk_category: str = Form(...),
    wind_speed_mph: float = Form(...),
    exposure: str = Form(...),
    height_total_ft: float = Form(...),
    post_spacing_ft: float = Form(...),
    soil_type: str = Form("default"),
    job_name: str = Form(""),
    line_post_key: str = Form(""),
    terminal_post_key: str = Form(""),
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
        "job_name": job_name,
        "line_post_key": line_post_key or "",
        "terminal_post_key": terminal_post_key or "",
        "post_role": post_role or "line",
        "post_key": post_key or "",
        "post_size": post_size or "",
    }

    inp = EstimateInput(
        wind_speed_mph=wind_speed_mph,
        height_total_ft=height_total_ft,
        post_spacing_ft=post_spacing_ft,
        exposure=exposure,
        soil_type=soil_type or None,
        line_post_key=line_post_key or None,
        terminal_post_key=terminal_post_key or None,
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


@app.get("/download")
async def download(
    zip_code: str,
    risk_category: str,
    wind_speed_mph: float,
    exposure: str,
    height_total_ft: float,
    post_spacing_ft: float,
    soil_type: str = "default",
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


@app.get("/health")
async def health():
    return {"status": "ok"}


def classify_risk(
    out: EstimateOutput,
    data: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    Classify risk status (GREEN/YELLOW/RED).

    GREEN / YELLOW / RED are based on spacing vs table limits.
    Bending check is kept as advisory information only and does
    NOT override the spacing-based status.
    """
    details: dict[str, Any] = {
        "spacing_ratio": None,
        "moment_ratio": None,  # kept for display as "bending capacity"
        "reasons": [],
        "advanced_reasons": [],
    }
    post_role = (data.get("post_role") or "line").lower()

    # --- Spacing ratio (governing) ---
    spacing_ratio = None
    if hasattr(out, "max_spacing_ft") and out.max_spacing_ft is not None and out.max_spacing_ft > 0:
        post_spacing = data.get("post_spacing_ft", 0)
        if post_spacing > 0:
            spacing_ratio = post_spacing / out.max_spacing_ft
            details["spacing_ratio"] = spacing_ratio
            details["max_spacing_ft"] = out.max_spacing_ft

    # --- Bending ratio (advisory only) ---
    moment_ratio = None
    if (
        hasattr(out, "M_allow_ft_lb")
        and out.M_allow_ft_lb is not None
        and out.M_allow_ft_lb > 0
        and hasattr(out, "M_demand_ft_lb")
        and out.M_demand_ft_lb is not None
    ):
        moment_ratio = out.M_demand_ft_lb / out.M_allow_ft_lb
        details["moment_ratio"] = moment_ratio
        details["M_demand_ft_lb"] = out.M_demand_ft_lb
        details["M_allow_ft_lb"] = out.M_allow_ft_lb

    # --- Base status from spacing only ---
    status = "GREEN"

    # RED if spacing is well beyond table limit
    if spacing_ratio is not None and spacing_ratio > 1.15:
        status = "RED"
        max_spacing = details.get("max_spacing_ft", getattr(out, "max_spacing_ft", None) or 0)
        details["reasons"].append(
            f"Spacing at {spacing_ratio*100:.0f}% of limit "
            f"({data.get('post_spacing_ft', 0):.2f} ft vs {max_spacing:.2f} ft max)"
        )

    # YELLOW if spacing is slightly above limit, but not RED
    elif spacing_ratio is not None and 1.0 < spacing_ratio <= 1.15:
        status = "YELLOW"
        max_spacing = details.get(
            "max_spacing_ft",
            out.max_spacing_ft if hasattr(out, "max_spacing_ft") else 0,
        )
        details["reasons"].append(
            f"Spacing at {spacing_ratio*100:.0f}% of limit "
            f"({data.get('post_spacing_ft', 0):.2f} ft vs {max_spacing:.2f} ft max)"
        )

    # --- Optional advisory note about bending capacity (does NOT change status) ---
    if moment_ratio is not None:
        m_demand = details.get("M_demand_ft_lb", 0)
        m_allow = details.get("M_allow_ft_lb", 0)
        advisory_label = "Advisory – Simplified cantilever bending check (conservative): "
        msg_body = (
            f"{moment_ratio*100:.0f}% "
            f"({m_demand:.1f} ft·lb demand / {m_allow:.1f} ft·lb capacity)"
        )
        if post_role == "terminal":
            msg = f"Bending check (terminal post): {msg_body}"
            if moment_ratio > 1.0:
                status = "RED"
                msg += " — exceeds capacity"
            details["reasons"].append(msg)
        else:
            msg = f"{advisory_label}{msg_body}"
            if moment_ratio > 1.0:
                msg += " — exceeds capacity (advisory only)"
            details["advanced_reasons"].append(msg)

    # --- If we have no ratios at all, fall back to warnings only ---
    if spacing_ratio is None and moment_ratio is None:
        if out.warnings:
            lowered = " ".join(w.lower() for w in out.warnings)
            if "exceeds" in lowered or "outside" in lowered or "pe review" in lowered:
                status = "RED"
                details["reasons"].append("Configuration exceeds simplified design limits")
            else:
                status = "YELLOW"
                details["reasons"].append("Review warnings carefully")
        else:
            status = "GREEN"
            details["reasons"].append("Configuration is within recommended limits")
    else:
        # If we got here with spacing_ratio <= 1.0, call that out explicitly
        if status == "GREEN":
            details["reasons"].append("Configuration is within recommended table limits")

    return status, details


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

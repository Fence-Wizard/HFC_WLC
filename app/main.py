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
        "job_name": job_name,
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
        soil_type=soil_type or None,
        line_post_key=None if not line_post_key or line_post_key == "auto" else line_post_key,
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
        "reasons": [],
        "advanced_reasons": [],
        "line_spacing_ratio": None,
        "line_max_spacing_ft": None,
        "terminal_bending_ratio": None,
    }

    status = out.overall_status if hasattr(out, "overall_status") else "GREEN"

    # Line spacing info
    if hasattr(out, "line") and out.line.max_spacing_ft:
        spacing_ratio = data.get("post_spacing_ft", 0) / out.line.max_spacing_ft
        details["line_spacing_ratio"] = spacing_ratio
        details["line_max_spacing_ft"] = out.line.max_spacing_ft
        if spacing_ratio > 1.15:
            details["reasons"].append(
                f"Line spacing at {spacing_ratio*100:.0f}% of limit "
                f"({data.get('post_spacing_ft', 0):.2f} ft vs {out.line.max_spacing_ft:.2f} ft max)"
            )
        elif spacing_ratio > 1.0:
            details["reasons"].append(
                f"Line spacing slightly above limit "
                f"({data.get('post_spacing_ft', 0):.2f} ft vs {out.line.max_spacing_ft:.2f} ft max)"
            )

    # Terminal bending info
    if hasattr(out, "terminal") and out.terminal.M_allow_ft_lb:
        ratio = (
            out.terminal.M_demand_ft_lb / out.terminal.M_allow_ft_lb
            if out.terminal.M_demand_ft_lb and out.terminal.M_allow_ft_lb
            else None
        )
        details["terminal_bending_ratio"] = ratio
        if ratio is not None:
            msg = (
                f"Terminal bending utilization: {ratio*100:.0f}% "
                f"({out.terminal.M_demand_ft_lb:.1f} / {out.terminal.M_allow_ft_lb:.1f} ft·lb)"
            )
            details["reasons"].append(msg)

    # Line bending advisory
    if hasattr(out, "line") and out.line.M_allow_ft_lb:
        ratio = (
            out.line.M_demand_ft_lb / out.line.M_allow_ft_lb
            if out.line.M_demand_ft_lb and out.line.M_allow_ft_lb
            else None
        )
        if ratio is not None:
            msg = (
                "Advisory – Simplified cantilever bending check (conservative): "
                f"{ratio*100:.0f}% "
                f"({out.line.M_demand_ft_lb:.1f} / {out.line.M_allow_ft_lb:.1f} ft·lb)"
            )
            details["advanced_reasons"].append(msg)

    return status, details


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

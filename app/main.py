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
from windcalc.report import draw_pdf

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
REPORT_DIR = Path.home() / "Windload Reports"
REPORT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="HFC Windload Calculator")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


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
    post_size: str = Form(""),
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
        "post_size": post_size or "",
    }

    inp = EstimateInput(
        wind_speed_mph=wind_speed_mph,
        height_total_ft=height_total_ft,
        post_spacing_ft=post_spacing_ft,
        exposure=exposure,
        soil_type=soil_type or None,
        post_size=post_size or None,
    )
    out = calculate(inp)
    risk, risk_details = classify_risk(out, data)

    return templates.TemplateResponse(
        request,
        "review.html",
        {"data": data, "result": out, "risk": risk, "risk_details": risk_details},
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
    post_size: str = "",
):
    inp = EstimateInput(
        wind_speed_mph=wind_speed_mph,
        height_total_ft=height_total_ft,
        post_spacing_ft=post_spacing_ft,
        exposure=exposure,
        soil_type=soil_type or None,
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
    Classify risk status (GREEN/YELLOW/RED) based on spacing and moment checks.
    
    Returns:
        (status, details) where details contains ratios and reasons
    """
    details: dict[str, Any] = {
        "spacing_ratio": None,
        "moment_ratio": None,
        "reasons": [],
    }
    
    # Calculate spacing ratio
    spacing_ratio = None
    if out.max_spacing_ft and out.max_spacing_ft > 0:
        spacing_ratio = data.get("post_spacing_ft", 0) / out.max_spacing_ft
        details["spacing_ratio"] = spacing_ratio
        details["max_spacing_ft"] = out.max_spacing_ft
    
    # Calculate moment ratio
    moment_ratio = None
    if out.M_allow_ft_lb and out.M_allow_ft_lb > 0 and out.M_demand_ft_lb is not None:
        moment_ratio = out.M_demand_ft_lb / out.M_allow_ft_lb
        details["moment_ratio"] = moment_ratio
        details["M_demand_ft_lb"] = out.M_demand_ft_lb
        details["M_allow_ft_lb"] = out.M_allow_ft_lb
    
    # Determine status based on ratios
    status = "GREEN"
    
    # Check for RED conditions first (any one triggers RED)
    if spacing_ratio is not None and spacing_ratio > 1.15:
        status = "RED"
        details["reasons"].append(
            f"Spacing at {spacing_ratio*100:.0f}% of limit ({data.get('post_spacing_ft', 0):.2f} ft vs {out.max_spacing_ft:.2f} ft max)"
        )
    elif moment_ratio is not None and moment_ratio > 1.0:
        status = "RED"
        details["reasons"].append(
            f"Moment exceeds allowable by {(moment_ratio-1.0)*100:.0f}% ({out.M_demand_ft_lb:.1f} ft·lb vs {out.M_allow_ft_lb:.1f} ft·lb allowable)"
        )
    
    # Check for YELLOW conditions (only if not already RED)
    if status != "RED":
        if spacing_ratio is not None and 1.0 < spacing_ratio <= 1.15:
            status = "YELLOW"
            details["reasons"].append(
                f"Spacing at {spacing_ratio*100:.0f}% of limit ({data.get('post_spacing_ft', 0):.2f} ft vs {out.max_spacing_ft:.2f} ft max)"
            )
        elif moment_ratio is not None and 0.85 <= moment_ratio < 1.0:
            status = "YELLOW"
            details["reasons"].append(
                f"Moment at {moment_ratio*100:.0f}% of allowable ({out.M_demand_ft_lb:.1f} ft·lb vs {out.M_allow_ft_lb:.1f} ft·lb allowable)"
            )
    
    # Check for warnings that might elevate status
    if out.warnings:
        warning_text = " ".join(w.lower() for w in out.warnings)
        if "exceeds" in warning_text or "outside" in warning_text or "pe review" in warning_text:
            if status == "GREEN":
                status = "YELLOW"
            elif status == "YELLOW":
                status = "RED"
    
    # If no specific ratios available but we have warnings, use warning-based logic
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
    
    # Final GREEN confirmation
    if status == "GREEN":
        if spacing_ratio is not None and spacing_ratio <= 1.0 and (moment_ratio is None or moment_ratio < 0.85):
            details["reasons"].append("Configuration is within recommended limits")
        elif spacing_ratio is None and moment_ratio is None:
            details["reasons"].append("Configuration is within recommended limits")
    
    return status, details


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

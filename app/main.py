"""FastAPI wizard for wind load calculations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from windcalc import EstimateInput, calculate
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
    }

    inp = EstimateInput(
        wind_speed_mph=wind_speed_mph,
        height_total_ft=height_total_ft,
        post_spacing_ft=post_spacing_ft,
        exposure=exposure,
        soil_type=soil_type or None,
    )
    out = calculate(inp)
    risk = classify_risk(out)

    return templates.TemplateResponse(
        request,
        "review.html",
        {"data": data, "result": out, "risk": risk},
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
):
    inp = EstimateInput(
        wind_speed_mph=wind_speed_mph,
        height_total_ft=height_total_ft,
        post_spacing_ft=post_spacing_ft,
        exposure=exposure,
        soil_type=soil_type or None,
    )
    out = calculate(inp)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_job = job_name.strip() or "Job"
    filename = f"{safe_job}_{ts}.pdf"
    pdf_path = REPORT_DIR / filename

    draw_pdf(pdf_path, inp, out)

    return FileResponse(
        path=pdf_path,
        filename=filename,
        media_type="application/pdf",
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


def classify_risk(out: Any) -> str:
    if getattr(out, "warnings", None):
        lowered = " ".join(w.lower() for w in out.warnings)
        if "outside table" in lowered or "pe review" in lowered:
            return "RED"
        return "YELLOW"
    return "GREEN"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

import os
import uuid
from datetime import datetime, time
from typing import Optional

from fastapi import FastAPI, Depends, Form, Request, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from starlette.middleware.sessions import SessionMiddleware

from .database import Base, engine, get_db, SessionLocal
from .models import FIR
from .classifier import classify_crime_type

app = FastAPI(title="CIRIS - FIR Management & Dashboard")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("CIRIS_SECRET_KEY", "super-secret-change-this")
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

ADMIN_USERNAME = os.getenv("CIRIS_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("CIRIS_ADMIN_PASSWORD", "admin123")


def seed_data():
    db = SessionLocal()
    try:
        count = db.query(FIR).count()
        if count > 0:
            return

        samples = [
            FIR(
                fir_number="FIR-2026-001",
                title="Chain snatching near bus stand",
                station_name="Central Station",
                district="Hyderabad",
                incident_date=datetime.strptime("2026-03-01", "%Y-%m-%d").date(),
                incident_time=time(21, 15),
                legal_section="379, 356",
                crime_type="Theft",
                priority="Medium",
                status="Open",
                complainant_name="Ravi Kumar",
                accused_name="Unknown",
                location_text="MGBS Bus Stand",
                description="Complainant reported chain snatching by two bike riders near bus stand at night.",
                raw_fir_text="Chain snatching complaint...",
                evidence_summary="CCTV footage from nearby shop pending review.",
                tags="night-crime, vehicle, public-place"
            ),
            FIR(
                fir_number="FIR-2026-002",
                title="Street fight with knife injury",
                station_name="North Zone PS",
                district="Hyderabad",
                incident_date=datetime.strptime("2026-03-03", "%Y-%m-%d").date(),
                incident_time=time(22, 5),
                legal_section="323, 324, 506",
                crime_type="Assault / Hurt",
                priority="High",
                status="Under Investigation",
                complainant_name="Suresh",
                accused_name="Naresh",
                location_text="Secunderabad Junction",
                description="Fight broke out and victim suffered injury with knife. Threats were also issued.",
                raw_fir_text="Street fight FIR...",
                evidence_summary="Knife recovered, one eyewitness statement recorded.",
                tags="night-crime, weapon, public-place"
            ),
            FIR(
                fir_number="FIR-2026-003",
                title="Mobile theft in market",
                station_name="Old City PS",
                district="Hyderabad",
                incident_date=datetime.strptime("2026-02-20", "%Y-%m-%d").date(),
                incident_time=time(18, 40),
                legal_section="379",
                crime_type="Theft",
                priority="Medium",
                status="Open",
                complainant_name="Aisha",
                accused_name="Unknown",
                location_text="Charminar Market",
                description="Victim reported mobile phone stolen in crowded market.",
                raw_fir_text="Mobile theft report...",
                evidence_summary="No direct CCTV, witnesses being traced.",
                tags="public-place"
            ),
            FIR(
                fir_number="FIR-2026-004",
                title="Fraudulent bank OTP scam",
                station_name="Cyber Cell",
                district="Hyderabad",
                incident_date=datetime.strptime("2026-02-10", "%Y-%m-%d").date(),
                incident_time=time(11, 10),
                legal_section="420",
                crime_type="Fraud",
                priority="Medium",
                status="Open",
                complainant_name="Lavanya",
                accused_name="Unknown",
                location_text="Online",
                description="Victim shared OTP and lost money through fake bank call scam.",
                raw_fir_text="Cyber fraud complaint...",
                evidence_summary="Call recordings and bank statement uploaded.",
                tags=""
            ),
            FIR(
                fir_number="FIR-2026-005",
                title="Kidnapping complaint",
                station_name="South PS",
                district="Warangal",
                incident_date=datetime.strptime("2026-03-05", "%Y-%m-%d").date(),
                incident_time=time(7, 30),
                legal_section="363",
                crime_type="Kidnapping",
                priority="Critical",
                status="High Alert",
                complainant_name="Madhavi",
                accused_name="Unknown",
                location_text="Hanamkonda",
                description="Minor child reported missing and suspected abducted by unknown person.",
                raw_fir_text="Kidnapping complaint...",
                evidence_summary="School gate CCTV requested.",
                tags=""
            ),
            FIR(
                fir_number="FIR-2026-006",
                title="Property damage during local clash",
                station_name="Rural PS",
                district="Warangal",
                incident_date=datetime.strptime("2026-01-16", "%Y-%m-%d").date(),
                incident_time=time(16, 15),
                legal_section="427",
                crime_type="Property Damage",
                priority="Low",
                status="Closed",
                complainant_name="Shop Owner",
                accused_name="Known persons",
                location_text="Village Market",
                description="Shops damaged during local group clash.",
                raw_fir_text="Damage report...",
                evidence_summary="Photos of damaged property attached.",
                tags="public-place"
            ),
        ]

        db.add_all(samples)
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    seed_data()


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get("user"))


def redirect_if_not_logged_in(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=303)
    return None


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["user"] = username
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password"}
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    redirect = redirect_if_not_logged_in(request)
    if redirect:
        return redirect

    total_firs = db.query(func.count(FIR.id)).scalar() or 0
    open_cases = db.query(func.count(FIR.id)).filter(FIR.status.in_(["Open", "Under Investigation", "High Alert"])).scalar() or 0
    critical_cases = db.query(func.count(FIR.id)).filter(FIR.priority == "Critical").scalar() or 0
    high_priority = db.query(func.count(FIR.id)).filter(FIR.priority.in_(["High", "Critical"])).scalar() or 0

    top_districts = (
        db.query(FIR.district, func.count(FIR.id).label("count"))
        .group_by(FIR.district)
        .order_by(desc("count"))
        .limit(5)
        .all()
    )

    crime_distribution = (
        db.query(FIR.crime_type, func.count(FIR.id).label("count"))
        .group_by(FIR.crime_type)
        .order_by(desc("count"))
        .all()
    )

    monthly_trend = (
        db.query(func.strftime("%Y-%m", FIR.incident_date).label("month"), func.count(FIR.id).label("count"))
        .group_by("month")
        .order_by("month")
        .all()
    )

    recent_firs = db.query(FIR).order_by(FIR.created_at.desc()).limit(5).all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": request.session.get("user"),
            "total_firs": total_firs,
            "open_cases": open_cases,
            "critical_cases": critical_cases,
            "high_priority": high_priority,
            "top_districts": [{"district": row[0], "count": row[1]} for row in top_districts],
            "crime_distribution": [{"crime_type": row[0], "count": row[1]} for row in crime_distribution],
            "monthly_trend": [{"month": row[0], "count": row[1]} for row in monthly_trend],
            "recent_firs": recent_firs,
        },
    )


@app.get("/firs", response_class=HTMLResponse)
def fir_list(
    request: Request,
    district: Optional[str] = None,
    crime_type: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db)
):
    redirect = redirect_if_not_logged_in(request)
    if redirect:
        return redirect

    query = db.query(FIR)

    if district:
        query = query.filter(FIR.district == district)

    if crime_type:
        query = query.filter(FIR.crime_type == crime_type)

    if q:
        like_pattern = f"%{q}%"
        query = query.filter(
            or_(
                FIR.fir_number.ilike(like_pattern),
                FIR.title.ilike(like_pattern),
                FIR.station_name.ilike(like_pattern),
                FIR.description.ilike(like_pattern),
                FIR.location_text.ilike(like_pattern),
            )
        )

    firs = query.order_by(FIR.incident_date.desc(), FIR.id.desc()).all()

    districts = [row[0] for row in db.query(FIR.district).distinct().order_by(FIR.district).all()]
    crime_types = [row[0] for row in db.query(FIR.crime_type).distinct().order_by(FIR.crime_type).all()]

    return templates.TemplateResponse(
        "fir_list.html",
        {
            "request": request,
            "firs": firs,
            "districts": districts,
            "crime_types": crime_types,
            "selected_district": district,
            "selected_crime_type": crime_type,
            "q": q or "",
        },
    )


@app.get("/firs/new", response_class=HTMLResponse)
def new_fir_form(request: Request):
    redirect = redirect_if_not_logged_in(request)
    if redirect:
        return redirect

    return templates.TemplateResponse("fir_form.html", {"request": request, "error": None})


@app.post("/firs/new", response_class=HTMLResponse)
def create_fir(
    request: Request,
    entry_method: str = Form("manual"),
    fir_number: Optional[str] = Form(None),
    fir_number_upload: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    station_name: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    incident_date: Optional[str] = Form(None),
    incident_time: Optional[str] = Form(None),
    priority: Optional[str] = Form(None),
    legal_section: Optional[str] = Form(""),
    complainant_name: Optional[str] = Form(""),
    accused_name: Optional[str] = Form(""),
    location_text: Optional[str] = Form(""),
    description: Optional[str] = Form(None),
    raw_fir_text: Optional[str] = Form(""),
    evidence_summary: Optional[str] = Form(""),
    status: str = Form("Open"),
    fir_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    redirect = redirect_if_not_logged_in(request)
    if redirect:
        return redirect

    current_fir_no = fir_number if entry_method == "manual" else fir_number_upload
    if not current_fir_no:
         return templates.TemplateResponse("fir_form.html", {"request": request, "error": "FIR number is required"})

    existing = db.query(FIR).filter(FIR.fir_number == current_fir_no).first()
    if existing:
        return templates.TemplateResponse(
            "fir_form.html",
            {"request": request, "error": f"FIR number {current_fir_no} already exists"}
        )

    # Date parsing
    parsed_date = datetime.now().date()
    if incident_date:
        try:
            parsed_date = datetime.strptime(incident_date, "%Y-%m-%d").date()
        except ValueError:
            return templates.TemplateResponse("fir_form.html", {"request": request, "error": "Invalid date format"})
    
    parsed_time = None
    if incident_time:
        try:
            parsed_time = datetime.strptime(incident_time, "%H:%M").time()
        except ValueError:
            pass

    image_path = None
    if fir_image and fir_image.filename:
        ext = os.path.splitext(fir_image.filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
        save_path = os.path.join("app", "static", "uploads", filename)
        with open(save_path, "wb") as buffer:
            buffer.write(fir_image.file.read())
        image_path = f"uploads/{filename}"

    # Default values for upload mode
    final_title = title or f"Document Upload: {current_fir_no}"
    final_station = station_name or "Pending Review"
    final_district = district or "Unassigned"
    final_description = description or "Automated entry via document upload. Manual verification required."
    
    classification = classify_crime_type(description=final_description, legal_section=legal_section)

    fir = FIR(
        fir_number=current_fir_no,
        title=final_title,
        station_name=final_station,
        district=final_district,
        incident_date=parsed_date,
        incident_time=parsed_time,
        legal_section=legal_section,
        crime_type=classification["crime_type"],
        priority=priority or classification["priority"],
        status=status,
        complainant_name=complainant_name,
        accused_name=accused_name,
        location_text=location_text,
        description=final_description,
        raw_fir_text=raw_fir_text,
        evidence_summary=evidence_summary,
        image_path=image_path,
        tags=classification["tags"],
    )

    db.add(fir)
    db.commit()
    db.refresh(fir)

    return RedirectResponse("/firs", status_code=303)


@app.get("/api/dashboard")
def api_dashboard(request: Request, db: Session = Depends(get_db)):
    if not is_authenticated(request):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    total_firs = db.query(func.count(FIR.id)).scalar() or 0
    crime_distribution = (
        db.query(FIR.crime_type, func.count(FIR.id).label("count"))
        .group_by(FIR.crime_type)
        .order_by(desc("count"))
        .all()
    )
    top_districts = (
        db.query(FIR.district, func.count(FIR.id).label("count"))
        .group_by(FIR.district)
        .order_by(desc("count"))
        .limit(5)
        .all()
    )

    return {
        "total_firs": total_firs,
        "crime_distribution": [{"crime_type": row[0], "count": row[1]} for row in crime_distribution],
        "top_districts": [{"district": row[0], "count": row[1]} for row in top_districts]
    }


@app.get("/api/firs")
def api_firs(request: Request, db: Session = Depends(get_db)):
    if not is_authenticated(request):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    firs = db.query(FIR).order_by(FIR.incident_date.desc(), FIR.id.desc()).all()

    return [
        {
            "id": fir.id,
            "fir_number": fir.fir_number,
            "title": fir.title,
            "station_name": fir.station_name,
            "district": fir.district,
            "incident_date": str(fir.incident_date),
            "incident_time": str(fir.incident_time) if fir.incident_time else None,
            "legal_section": fir.legal_section,
            "crime_type": fir.crime_type,
            "priority": fir.priority,
            "status": fir.status,
            "complainant_name": fir.complainant_name,
            "accused_name": fir.accused_name,
            "location_text": fir.location_text,
            "description": fir.description,
            "evidence_summary": fir.evidence_summary,
            "tags": fir.tags,
        }
        for fir in firs
    ]
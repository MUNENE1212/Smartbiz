from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging
import os
from dotenv import load_dotenv

from models.database import connect_to_mongo, close_mongo_connection, get_database
from routers import auth, inventory, sales, suppliers, reporting, customer_feedback
from routers.auth import get_current_user, ACCESS_TOKEN_EXPIRE_HOURS, create_access_token
from services.alert_service import AlertService
from passlib.context import CryptContext
from routers.auth import get_current_user_from_cookie, get_manager_user_from_cookie


# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SmartBiz Manager", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(sales.router)
app.include_router(suppliers.router,prefix="/api")
app.include_router(reporting.router)
app.include_router(customer_feedback.router,prefix="/api")

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    logger.info("Connected to MongoDB")
    db = await get_database()
    alert_service = AlertService(db)
    result = await alert_service.send_low_stock_alerts()
    logger.info(f"Startup low stock check: {result}")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    logger.info("Disconnected from MongoDB")

@app.get("/")
async def root():
    return {"message": "Welcome to SmartBiz Manager API"}

@app.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "session_token": None})

@app.post("/login")
async def login_post(
    request: Request,
    id_number: str = Form(...),
    password: str = Form(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = await db.users.find_one({"id_number": id_number})
    if not user or not pwd_context.verify(password, user["password"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials", "session_token": None}
        )
    if not user["is_active"]:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Account is inactive", "session_token": None}
        )
    token_data = {"sub": str(user["_id"]), "role": user["role"]}
    token = create_access_token(token_data)
    response = RedirectResponse(
        url="/manager_dashboard" if user["role"] == "manager" else "/operator_dashboard",
        status_code=303
    )
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600
    )
    return response


@app.get("/register")
async def register_form(request: Request, current_user: dict = Depends(get_manager_user_from_cookie)):
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "user_name": current_user["full_name"], "role": current_user["role"], "session_token": "Bearer_token"}
    )

@app.get("/manager_dashboard")
async def manager_dashboard(request: Request, current_user: dict = Depends(get_manager_user_from_cookie)):
    return templates.TemplateResponse(
        "manager_dashboard.html",
        {"request": request, "user_name": current_user["full_name"], "role": "manager", "session_token": "Bearer_token"}
    )

@app.get("/operator_dashboard")
async def operator_dashboard(request: Request, current_user: dict = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse(
        "operator_dashboard.html",
        {"request": request, "user_name": current_user["full_name"], "role": current_user["role"], "session_token": "Bearer_token"}
    )

@app.get("/inventory")
async def inventory_page(request: Request, current_user: dict = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "user_name": current_user["full_name"], "role": current_user["role"], "session_token": "Bearer_token"}
    )

@app.get("/sales")
async def sales_page(request: Request, current_user: dict = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse(
        "sales.html",
        {"request": request, "user_name": current_user["full_name"], "role": current_user["role"], "session_token": "Bearer_token"}
    )

# THEN define template routes
@app.get("/manage_suppliers")
async def suppliers_page(request: Request, current_user: dict = Depends(get_manager_user_from_cookie)):
    logger.info("Rendering suppliers.html template")
    try:
        return templates.TemplateResponse(
            "suppliers.html",
            {"request": request, "user_name": current_user["full_name"], "role": current_user["role"], "session_token": "Bearer_token"}
        )
    except Exception as e:
        logger.error(f"Error rendering suppliers page: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to render suppliers page")

@app.get("/submit_feedback")
async def feedback_page(request: Request, current_user: dict = Depends(get_current_user_from_cookie)):
    logger.info("Rendering feedback.html template")
    try:
        return templates.TemplateResponse(
            "feedback.html",
            {"request": request, "user_name": current_user["full_name"], "role": current_user["role"], "session_token": "Bearer_token"}
        )
    except Exception as e:
        logger.error(f"Error rendering feedback page: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to render feedback page")

@app.get("/reporting")
async def reporting_page(request: Request, current_user: dict = Depends(get_manager_user_from_cookie)):
    return templates.TemplateResponse(
        "reporting.html",
        {"request": request, "user_name": current_user["full_name"], "role": "manager", "session_token": "Bearer_token"}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": exc.detail, "session_token": None},
        status_code=exc.status_code
    )

@app.get("/logout")
async def logout(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "success": "Logged out successfully", "session_token": None}
    )
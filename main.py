from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app =FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   )
import os
import shutil
import uuid
import json
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from google import genai

from database import SessionLocal, init_db, InvoiceModel

# 1. Environment variables (.env file) ko load karna (Gemini API key ke liye)
load_dotenv()

# 2. Database tables create karna (agar pehle se nahi bani hui)
init_db()

# FastAPI app initialize karna
app = FastAPI(title="AI Invoice Processing API", version="1.0")

# Dependency: Database session manage karne ke liye
# Yeh function har request ke sath database ka connection open karta hai aur kaam khatam hone par band kar deta hai.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Uploaded files ko save karne ke liye folder ka path
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==========================================
# 1. HEALTH ENDPOINT
# ==========================================
@app.get("/health")
def health_check():
    """Server ka status check karne ke liye simple endpoint."""
    return {"status": "healthy"}


# ==========================================
# 2. UPLOAD ENDPOINT
# ==========================================
@app.post("/upload")
async def upload_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """User se PDF ya Image receive karta hai, validate karta hai, aur database mein save karta hai."""
    
    # Step A: File format validation (Sirf PDF aur Images allowed hain)
    if not file.filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF and images are allowed.")
    
    # Step B: Unique file name banana taake file ka naam duplicate hone par conflict na ho
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Step C: File ko local 'uploads/' folder mein write karna
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Step D: Unique Invoice ID generate karna
    invoice_id = str(uuid.uuid4())
    
    # Step E: Database mein record save karna
    db_invoice = InvoiceModel(
        invoice_id=invoice_id,
        filename=file.filename,
        file_path=file_path,
        validation_status="Uploaded"
    )
    db.add(db_invoice)
    db.commit()
    
    return {"invoiceId": invoice_id, "filename": file.filename, "status": "Uploaded"}


# ==========================================
# 3. EXTRACT ENDPOINT (Gemini AI + Validation)
# ==========================================
@app.post("/extract/{invoice_id}")
async def extract_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Invoice file ko Gemini API ke zariye process kar ke data extract karta hai aur validate karta hai."""
    
    # Step A: Check karna ke invoice database mein mojood hai ya nahi
    db_invoice = db.query(InvoiceModel).filter(InvoiceModel.invoice_id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    try:
        # Step B: Gemini Client initialize karna (.env se API key utha kar)
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Step C: File ko Gemini par upload karna
        uploaded_file = client.files.upload(file=db_invoice.file_path)
        
        # Step D: Prompt define karna ke Gemini se kya nikalwana hai
        prompt = """
        Extract invoice details into exact JSON format with these exact keys:
        vendor, invoiceNumber, invoiceDate, currency, netAmount, vatAmount, grossAmount, paymentDue.
        Ensure amounts are numbers, not strings. If a field is missing, return null.
        """
        
        # Step E: Gemini model ko call karna (Structured JSON response ke sath)
        response = client.models.generate_content(
        model='gemini-3.6-flash',
            contents=[uploaded_file, prompt],
            config={
                "response_mime_type": "application/json"
            }
        )
        
        # AI ke response ko Python dictionary mein convert karna
        extracted_data = json.loads(response.text)
        
        # Step F: Extracted data ko database object mein assign karna
        db_invoice.vendor = extracted_data.get("vendor")
        db_invoice.invoice_number = extracted_data.get("invoiceNumber")
        db_invoice.invoice_date = extracted_data.get("invoiceDate")
        db_invoice.currency = extracted_data.get("currency")
        db_invoice.net_amount = extracted_data.get("netAmount")
        db_invoice.vat_amount = extracted_data.get("vatAmount")
        db_invoice.gross_amount = extracted_data.get("grossAmount")
        db_invoice.payment_due = extracted_data.get("paymentDue")
        
        # ==========================================
        # STEP G: AUTOMATED VALIDATION LOGIC
        # ==========================================
        issues = []
        net = db_invoice.net_amount or 0.0
        vat = db_invoice.vat_amount or 0.0
        gross = db_invoice.gross_amount or 0.0
        
        # 1. Math Check: Net + VAT == Gross (rounding errors se bachne ke liye round(..., 2) use kiya hai)
        if round(net + vat, 2) != round(gross, 2):
            issues.append("Gross amount does not equal Net + VAT.")
            
        # 2. Missing Mandatory Fields Check
        mandatory_fields = ["vendor", "invoice_number", "invoice_date", "gross_amount"]
        for field in mandatory_fields:
            if not getattr(db_invoice, field):
                issues.append(f"Missing mandatory field: {field}")
                
        # 3. Duplicate Invoice Number Check (Database mein pehle se hai ya nahi)
        if db_invoice.invoice_number:
            existing_invoice = db.query(InvoiceModel).filter(
                InvoiceModel.invoice_number == db_invoice.invoice_number,
                InvoiceModel.invoice_id != invoice_id
            ).first()
            if existing_invoice:
                issues.append("Duplicate invoice number detected.")
                
        # Step H: Final Validation Status assign karna
        validation_status = "Verified" if not issues else "Requires Review"
        db_invoice.validation_status = validation_status
        db_invoice.issues = issues
        
        # Database mein changes commit karna
        db.commit()
        db.refresh(db_invoice)
        
        return {
            "invoiceId": db_invoice.invoice_id,
            "extractedData": extracted_data,
            "validation": {
                "status": validation_status,
                "issues": issues
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 4. GET INVOICE DETAILS ENDPOINT
# ==========================================
@app.get("/invoice/{invoice_id}")
def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Database se specific invoice ki details aur validation status retrieve karta hai."""
    
    db_invoice = db.query(InvoiceModel).filter(InvoiceModel.invoice_id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    return {
        "invoiceId": db_invoice.invoice_id,
        "filename": db_invoice.filename,
        "status": db_invoice.validation_status,
        "extractedData": {
            "vendor": db_invoice.vendor,
            "invoiceNumber": db_invoice.invoice_number,
            "invoiceDate": db_invoice.invoice_date,
            "currency": db_invoice.currency,
            "netAmount": db_invoice.net_amount,
            "vatAmount": db_invoice.vat_amount,
            "grossAmount": db_invoice.gross_amount,
            "paymentDue": db_invoice.payment_due
        },
        "validation": {
            "status": db_invoice.validation_status,
            "issues": db_invoice.issues
        }
    }
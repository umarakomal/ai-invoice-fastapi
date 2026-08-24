AI-Powered Invoice Processing API
A production-quality, automated invoice processing backend built with FastAPI, Google Gemini API, SQLite, and automated data validation rules.

Features
RESTful Endpoints: Supports file uploading, AI-driven extraction, invoice retrieval, and health checks.

AI Extraction: Leverages Google Gemini to accurately extract vendor names, invoice numbers, dates, currency, net amounts, VAT, gross amounts, and payment due dates.
Automatic Validation: Validates calculations (Gross Amount = Net + VAT), checks for missing mandatory fields, and flags anomalies.

Database Integration: Uses SQLite to store invoice metadata, extracted fields, validation statuses, and timestamps.

Robust Logging: Tracks upload events, extraction durations, errors, and validation failures.
Tech Stack
Backend Framework: FastAPI (Python)

AI Model: Google Gemini API (gemini-1.5-flash)

Database: SQLite

Validation & Data: Pydantic

Project Structure

ai-invoice-fastapi/
│
├── main.py              # FastAPI app endpoints and routing logic
├── database.py          # SQLite database configuration and models
├── requirements.list    # Project dependencies
├── .env                 # Environment variables (local only)
└── README.md            # Project documentation
Setup & Installation Instructions
1. Clone the Repository

2. git clone https://github.com/umarakomal/ai-invoice-fastapi.git
cd ai-invoice-fastapi


4. 2. Create a Virtual Environment & Install Dependencies
   3. python -m venv venv
  
      
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt

3. Configure Environment Variables
Create a .env file in the root directory and add your Google Gemini API key:
GEMINI_API_KEY=your_actual_gemini_api_key_here
4. Run the Application locally
5. uvicorn main:app --reload

6. The API will be live at: [http://127.0.0.1:8000](http://127.0.0.1:8000)

Interactive API Docs (Swagger UI) can be accessed at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
Method,Endpoint,Description
POST,/upload,Upload a PDF or image invoice for processing.
POST,/extract/{invoiceId},Extract structured data using Google Gemini AI.
GET,/invoice/{invoiceId},Retrieve processed invoice details and validation status.
GET,/health,Returns the health status of the API.
Sample JSON Response (Extraction)
{
  "vendor": "TECH SUPPLIES INC.",
  "invoiceNumber": "INV-2026-001",
  "invoiceDate": "2026-07-26",
  "currency": "USD",
  "netAmount": 200.00,
  "vatAmount": 20.00,
  "grossAmount": 220.00,
  "paymentDue": "2026-08-26"
}
Sample JSON Response (Validation)
{
  "status": "Verified",
  "issues": []
}

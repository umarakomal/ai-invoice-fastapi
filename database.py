import os
from sqlalchemy import create_engine, Column, String, Float, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# 1. Database ka path set karna
# Yeh command batati hai ke current folder mein 'invoices.db' ke naam se aik SQLite file ban jaye.
DATABASE_URL = "sqlite:///./invoices.db"

# 2. Database Engine create karna
# 'check_same_thread=False' SQLite ke sath FastAPI mein multi-threading errors se bachne ke liye zaroori hota hai.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 3. SessionLocal banana
# Jab bhi API ko database se baat karni hogi (data save ya read karne ke liye), yeh session use hoga.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Base class create karna
# Saare database models is Base class ko inherit karein ge taake SQLAlchemy unhein table samajh sakay.
Base = declarative_base()

# 5. Database Table Structure (Model) banana
class InvoiceModel(Base):
    __tablename__ = "invoices"  # Database mein table ka naam 'invoices' hoga

    # Columns definition (Har aik column ka data type aur constraints)
    invoice_id = Column(String, primary_key=True, index=True) # Unique ID (UUID) jo primary key hogi
    filename = Column(String, nullable=False)                  # Original file ka naam
    file_path = Column(String, nullable=False)                 # Server par file kahan save hai uska path
    vendor = Column(String, nullable=True)                     # AI extraction ke baad vendor ka naam
    invoice_number = Column(String, nullable=True, index=True) # Invoice number (duplicates check karne ke liye index)
    invoice_date = Column(String, nullable=True)               # Invoice ki date
    currency = Column(String, nullable=True)                   # Currency (e.g., EUR, USD)
    net_amount = Column(Float, nullable=True)                  # Net amount (baghair tax ke)
    vat_amount = Column(Float, nullable=True)                  # Tax / VAT amount
    gross_amount = Column(Float, nullable=True)                # Total amount (Net + VAT)
    payment_due = Column(String, nullable=True)                # Payment ki last date
    validation_status = Column(String, default="Uploaded")     # Status: 'Uploaded', 'Verified', ya 'Requires Review'
    issues = Column(JSON, default=[])                          # Validation errors ki list (JSON format mein)
    created_at = Column(DateTime, default=datetime.utcnow)     # Record banne ka waqt (Timestamp)

# 6. Database Initialize function
# Yeh function call hone par SQLite file mein upar diye gaye structure ke mutabiq table create kar deta hai.
def init_db():
    Base.metadata.create_all(bind=engine)

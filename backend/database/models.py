from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database.db import Base


class Kisan(Base):
    __tablename__ = "kisan"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(String, unique=True, nullable=True, index=True)
    mobile        = Column(String, unique=True, nullable=True, index=True)
    first_name    = Column(String, nullable=True)
    last_name     = Column(String, nullable=True)
    naam          = Column(String, nullable=True)   # first+last ka combined (display ke liye)
    gender        = Column(String, nullable=True)
    role          = Column(String, default="kisan") # kisan ya vyapari
    otp           = Column(String, nullable=True)   # current OTP
    otp_expiry    = Column(DateTime, nullable=True) # OTP kitne time tak valid
    location      = Column(String, nullable=True)
    zameen_bigha  = Column(Float, nullable=True)
    khet_count    = Column(Integer, nullable=True)
    phone         = Column(String, nullable=True)
    village       = Column(String, nullable=True)
    district      = Column(String, nullable=True)
    state         = Column(String, nullable=True)
    main_crop     = Column(String, nullable=True)
    soil_type     = Column(String, nullable=True)
    irrigation    = Column(String, nullable=True)
    experience    = Column(Integer, default=0)
    profile_photo = Column(String, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    fasalein = relationship("KisanFasal", back_populates="kisan")
    scans    = relationship("DiseaseScan", back_populates="kisan")


class KisanFasal(Base):
    __tablename__ = "kisan_fasal"

    id         = Column(Integer, primary_key=True, index=True)
    kisan_id   = Column(Integer, ForeignKey("kisan.id"))
    fasal_naam = Column(String)
    bigha      = Column(Float, default=1.0)
    khet_no    = Column(Integer, default=1)
    season     = Column(String, default="Rabi 2026")
    status     = Column(String, default="Theek")

    kisan = relationship("Kisan", back_populates="fasalein")


class DiseaseScan(Base):
    __tablename__ = "disease_scan"

    id          = Column(Integer, primary_key=True, index=True)
    kisan_id    = Column(Integer, ForeignKey("kisan.id"), nullable=True)
    fasal       = Column(String, default="Gehu")
    disease     = Column(String)
    confidence  = Column(Float)
    severity    = Column(String, default="Low")
    solution    = Column(Text)
    precaution  = Column(Text)
    image_path  = Column(String, nullable=True)
    scan_date   = Column(DateTime(timezone=True), server_default=func.now())

    kisan = relationship("Kisan", back_populates="scans")


class Review(Base):
    __tablename__ = "review"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(String, nullable=True)
    role       = Column(String, nullable=True)
    name       = Column(String, nullable=True)
    location   = Column(String, nullable=True)
    fasal      = Column(String, nullable=True)
    stars      = Column(Integer, default=5)
    experience = Column(Text, nullable=True)
    photo_path = Column(String, nullable=True)
    approved   = Column(Boolean, default=False)
    date       = Column(String, nullable=True)
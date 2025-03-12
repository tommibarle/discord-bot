from sqlalchemy import Column, Integer, String, LargeBinary, DateTime, ForeignKey
from sqlalchemy.sql import func
from app import db

class Inspection(db.Model):
    __tablename__ = 'inspections'
    
    id = Column(Integer, primary_key=True)
    activity_name = Column(String(100), nullable=False, index=True)
    content = Column(LargeBinary, nullable=False)
    author_id = Column(String(100), nullable=False)
    author_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Sanction(db.Model):
    __tablename__ = 'sanctions'
    
    id = Column(Integer, primary_key=True)
    activity_name = Column(String(100), nullable=False, index=True)
    reason = Column(String(1000), nullable=False)
    sanction_text = Column(String(1000), nullable=False)
    author_id = Column(String(100), nullable=False)
    author_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

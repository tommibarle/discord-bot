from sqlalchemy import Column, Integer, String, LargeBinary, DateTime
from sqlalchemy.sql import func
from app import db

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    content = Column(LargeBinary, nullable=False)  # Qui verranno salvati i byte dell'immagine
    context = Column(String(50), nullable=False)  # Lunghezza ridotta per i valori predefiniti
    author_id = Column(String(100), nullable=False)
    author_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

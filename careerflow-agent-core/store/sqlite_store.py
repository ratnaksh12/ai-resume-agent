# store/sqlite_store.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import json

DB_PATH = os.getenv("CAREERFLOW_DB", "sqlite:///careerflow.db")
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="resume")
    created_at = Column(DateTime, default=datetime.utcnow)
    versions = relationship("ResumeVersion", back_populates="resume")

class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_text = Column(Text)
    metadata_json = Column(Text)  # renamed from `metadata` to avoid conflict with SQLAlchemy
    parent_version = Column(Integer, nullable=True)
    resume = relationship("Resume", back_populates="versions")

def init_db():
    Base.metadata.create_all(bind=engine)

class Store:
    def __init__(self):
        init_db()
        self.db = SessionLocal()

    def create_resume(self, name="resume"):
        r = Resume(name=name)
        self.db.add(r); self.db.commit(); self.db.refresh(r)
        return r

    def add_version(self, resume_id: int, raw_text: str, metadata: dict = None, parent_version: int = None):
        v = ResumeVersion(
            resume_id=resume_id,
            raw_text=raw_text,
            metadata_json=json.dumps(metadata or {}),
            parent_version=parent_version
        )
        self.db.add(v); self.db.commit(); self.db.refresh(v)
        return v

    def list_versions(self, resume_id: int):
        return self.db.query(ResumeVersion).filter_by(resume_id=resume_id).order_by(ResumeVersion.created_at.desc()).all()

    def get_version(self, version_id: int):
        return self.db.query(ResumeVersion).filter_by(id=version_id).first()

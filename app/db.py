import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, select, desc, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class Scan(Base):
    __tablename__ = "scans"
    scan_id = Column(String(36), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    website_domain = Column(String(253), nullable=False)
    category = Column(String(100), nullable=False)
    status = Column(String(20), default="completed", nullable=False)
    progress = Column(Integer, default=100, nullable=False)
    stage = Column(String(255), default="Completed", nullable=False)
    error_message = Column(Text, nullable=True)
    payload_json = Column(Text, default="{}", nullable=False)

def init_db():
    Base.metadata.create_all(bind=engine)
    if settings.database_url.startswith("sqlite"):
        with engine.connect() as conn:
            try:
                cursor = conn.execute(text("PRAGMA table_info(scans)"))
                existing_cols = {row[1] for row in cursor.fetchall()}
                if "status" not in existing_cols:
                    conn.execute(text("ALTER TABLE scans ADD COLUMN status VARCHAR(20) DEFAULT 'completed'"))
                if "progress" not in existing_cols:
                    conn.execute(text("ALTER TABLE scans ADD COLUMN progress INTEGER DEFAULT 100"))
                if "stage" not in existing_cols:
                    conn.execute(text("ALTER TABLE scans ADD COLUMN stage VARCHAR(255) DEFAULT 'Completed'"))
                if "error_message" not in existing_cols:
                    conn.execute(text("ALTER TABLE scans ADD COLUMN error_message TEXT DEFAULT NULL"))
                conn.commit()
            except Exception:
                pass

# Auto-initialize on import so database schema is always ready
init_db()

def create_scan(scan_id: str, website_domain: str, category: str, status: str = "queued", progress: int = 0, stage: str = "Queued"):
    with SessionLocal() as session:
        session.add(Scan(
            scan_id=scan_id,
            website_domain=website_domain,
            category=category,
            status=status,
            progress=progress,
            stage=stage,
            payload_json="{}"
        ))
        session.commit()

def update_scan_progress(scan_id: str, status: str, progress: int, stage: str, error_message: str | None = None):
    with SessionLocal() as session:
        row = session.get(Scan, scan_id)
        if row:
            row.status = status
            row.progress = progress
            row.stage = stage
            if error_message is not None:
                row.error_message = error_message
            session.commit()

def complete_scan(scan_id: str, payload: dict):
    with SessionLocal() as session:
        row = session.get(Scan, scan_id)
        if row:
            row.status = "completed"
            row.progress = 100
            row.stage = "Scan complete"
            row.payload_json = json.dumps(payload, default=str)
            session.commit()
        else:
            save_scan(scan_id, payload.get("website_domain", ""), payload.get("category", ""), payload)

def save_scan(scan_id: str, website_domain: str, category: str, payload: dict):
    with SessionLocal() as session:
        existing = session.get(Scan, scan_id)
        if existing:
            existing.status = "completed"
            existing.progress = 100
            existing.stage = "Scan complete"
            existing.payload_json = json.dumps(payload, default=str)
        else:
            session.add(Scan(
                scan_id=scan_id,
                website_domain=website_domain,
                category=category,
                status="completed",
                progress=100,
                stage="Scan complete",
                payload_json=json.dumps(payload, default=str)
            ))
        session.commit()

def get_scan(scan_id: str):
    with SessionLocal() as session:
        row = session.get(Scan, scan_id)
        if row is None:
            return None
        payload = json.loads(row.payload_json) if row.payload_json else {}
        return {
            "scan_id": row.scan_id,
            "created_at": row.created_at,
            "website_domain": row.website_domain,
            "category": row.category,
            "status": getattr(row, "status", "completed"),
            "progress": getattr(row, "progress", 100),
            "stage": getattr(row, "stage", "Completed"),
            "error_message": getattr(row, "error_message", None),
            "payload": payload
        }

def list_scans(limit: int = 50, offset: int = 0, category: str | None = None, website_domain: str | None = None):
    with SessionLocal() as session:
        stmt = select(Scan).order_by(desc(Scan.created_at))
        if category:
            stmt = stmt.where(Scan.category == category)
        if website_domain:
            stmt = stmt.where(Scan.website_domain == website_domain)
        stmt = stmt.limit(limit).offset(offset)
        rows = session.scalars(stmt).all()
        result = []
        for row in rows:
            payload = json.loads(row.payload_json) if row.payload_json else {}
            result.append({
                "scan_id": row.scan_id,
                "created_at": row.created_at,
                "website_domain": row.website_domain,
                "category": row.category,
                "status": getattr(row, "status", "completed"),
                "progress": getattr(row, "progress", 100),
                "stage": getattr(row, "stage", "Completed"),
                "prospects_found": payload.get("prospects_found", 0),
                "verified_free_count": payload.get("verified_free_count", 0)
            })
        return result

def delete_scan(scan_id: str) -> bool:
    with SessionLocal() as session:
        row = session.get(Scan, scan_id)
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True

import datetime
import hashlib
import json
import os
import uuid
from typing import List, Dict, Any, Optional

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, JSON, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship
from sqlalchemy.engine import Engine, create_engine

class Base(DeclarativeBase):
    pass

class Case(Base):
    __tablename__ = 'cases'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    investigator: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    status: Mapped[str] = mapped_column(String, default="open")

    evidence: Mapped[List["Evidence"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    findings: Mapped[List["Finding"]] = relationship(back_populates="case", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = 'evidence'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String, ForeignKey('cases.id'), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String, nullable=False)
    md5_hash: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    acquired_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    case: Mapped["Case"] = relationship(back_populates="evidence")

class Finding(Base):
    __tablename__ = 'findings'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String, ForeignKey('cases.id'), nullable=False)
    finding_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False) # high|medium|low
    description: Mapped[str] = mapped_column(String, nullable=False)
    account_ids: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    step_start: Mapped[int] = mapped_column(Integer, nullable=False)
    step_end: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    case: Mapped["Case"] = relationship(back_populates="findings")

class CaseManager:
    """Manages forensic cases, evidence, and findings via SQLite database."""

    def __init__(self, db_path: str):
        """
        Initializes the CaseManager and sets up the SQLite database.
        """
        db_url = f"sqlite:///{db_path}"
        self.engine: Engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_case(self, name: str, description: str, investigator: str) -> Case:
        """
        Creates a new case in the database.
        """
        with self.Session() as session:
            case = Case(
                name=name,
                description=description,
                investigator=investigator
            )
            session.add(case)
            session.commit()
            session.refresh(case)
            return case

    def add_evidence(self, case_id: str, filepath: str, notes: str = "") -> Evidence:
        """
        Adds an evidence file to a case, automatically computing SHA-256 and MD5 hashes.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Evidence file not found: {filepath}")

        # Compute hashes and file size
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()
        file_size = os.path.getsize(filepath)

        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
                sha256.update(chunk)

        md5_hash = md5.hexdigest()
        sha256_hash = sha256.hexdigest()
        filename = os.path.abspath(filepath)

        with self.Session() as session:
            # Check if case exists
            case = session.execute(select(Case).filter(Case.id == case_id)).scalar_one_or_none()
            if not case:
                raise ValueError(f"Case not found: {case_id}")

            evidence = Evidence(
                case_id=case_id,
                filename=filename,
                sha256_hash=sha256_hash,
                md5_hash=md5_hash,
                file_size=file_size,
                notes=notes
            )
            session.add(evidence)
            session.commit()
            session.refresh(evidence)
            return evidence

    def add_finding(
        self,
        case_id: str,
        finding_type: str,
        severity: str,
        description: str,
        account_ids: List[str],
        step_start: int,
        step_end: int,
        confidence: float
    ) -> Finding:
        """
        Adds a fraud pattern finding to a case.
        """
        with self.Session() as session:
            # Check if case exists
            case = session.execute(select(Case).filter(Case.id == case_id)).scalar_one_or_none()
            if not case:
                raise ValueError(f"Case not found: {case_id}")

            finding = Finding(
                case_id=case_id,
                finding_type=finding_type,
                severity=severity,
                description=description,
                account_ids=account_ids,
                step_start=step_start,
                step_end=step_end,
                confidence=confidence
            )
            session.add(finding)
            session.commit()
            session.refresh(finding)
            return finding

    def get_case_summary(self, case_id: str) -> Dict[str, Any]:
        """
        Returns a summary of a case, including evidence count, findings count,
        and findings breakdown by severity.
        """
        with self.Session() as session:
            case = session.execute(select(Case).filter(Case.id == case_id)).scalar_one_or_none()
            if not case:
                raise ValueError(f"Case not found: {case_id}")

            evidence_count = len(session.execute(select(Evidence).filter(Evidence.case_id == case_id)).scalars().all())
            findings = session.execute(select(Finding).filter(Finding.case_id == case_id)).scalars().all()

            findings_count = len(findings)
            findings_by_severity = {"high": 0, "medium": 0, "low": 0}
            for f in findings:
                if f.severity in findings_by_severity:
                    findings_by_severity[f.severity] += 1
                else:
                    findings_by_severity[f.severity] = 1

            return {
                "case": {
                    "id": case.id,
                    "name": case.name,
                    "description": case.description,
                    "investigator": case.investigator,
                    "created_at": case.created_at,
                    "status": case.status
                },
                "evidence_count": evidence_count,
                "findings_count": findings_count,
                "findings_by_severity": findings_by_severity
            }

    def list_cases(self) -> List[Case]:
        """
        Lists all cases in the database.
        """
        with self.Session() as session:
            cases = session.execute(select(Case)).scalars().all()
            session.expunge_all()
            # return as list for type hints
            return list(cases)

    def get_findings(self, case_id: str) -> List[Finding]:
        """
        Returns all findings for a specific case.
        """
        with self.Session() as session:
            findings = session.execute(select(Finding).filter(Finding.case_id == case_id)).scalars().all()
            session.expunge_all()
            return list(findings)
    def get_evidence(self, case_id: str) -> List[Evidence]:
        """
        Returns all evidence records for a specific case.
        """
        with self.Session() as session:
            evidence = session.execute(select(Evidence).filter(Evidence.case_id == case_id)).scalars().all()
            session.expunge_all()
            return list(evidence)

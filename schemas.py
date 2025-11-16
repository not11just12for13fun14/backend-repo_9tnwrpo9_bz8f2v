"""
Database Schemas for Ordne (Enterprise Architecture for SMBs)

Each Pydantic model represents a collection in your MongoDB database.
Collection name is the lowercase of the class name.

Examples:
- Application -> "application"
- Process -> "process"
- Role -> "role"
- DataAsset -> "dataasset"
- Risk -> "risk"
- ComplianceRequirement -> "compliancerequirement"
- Relationship -> "relationship"
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal

# Core business architecture primitives

class Application(BaseModel):
    name: str = Field(..., description="Application name")
    description: Optional[str] = Field(None, description="What it does in the business context")
    owner: Optional[str] = Field(None, description="Business owner (person/team)")
    technical_owner: Optional[str] = Field(None, description="Technical owner (person/team)")
    vendor: Optional[str] = Field(None, description="Vendor name if SaaS or purchased software")
    criticality: Literal["low", "medium", "high"] = Field("medium", description="Business criticality")
    lifecycle: Literal["ideation", "active", "sunset"] = Field("active", description="Lifecycle stage")
    gdpr_data: bool = Field(False, description="Processes GDPR personal data")
    tags: List[str] = Field(default_factory=list, description="Free-form labels")

class Process(BaseModel):
    name: str = Field(..., description="Business process name")
    description: Optional[str] = Field(None)
    owner: Optional[str] = Field(None)
    level: Optional[Literal["L1", "L2", "L3"]] = Field("L2", description="Process decomposition level")
    related_applications: List[str] = Field(default_factory=list, description="Linked application IDs or names")

class Role(BaseModel):
    name: str = Field(..., description="Role title (e.g., Sales Rep)")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    department: Optional[str] = Field(None)
    responsibilities: List[str] = Field(default_factory=list)

class DataAsset(BaseModel):
    name: str = Field(..., description="Data asset name (e.g., Customer PII)")
    category: Literal["PII", "Financial", "Operational", "Other"] = Field("Other")
    description: Optional[str] = Field(None)
    retention_period_months: Optional[int] = Field(None, ge=0)
    gdpr_basis: Optional[Literal["consent", "contract", "legal_obligation", "legitimate_interest", "vital_interest", "public_task"]] = None

class Risk(BaseModel):
    title: str = Field(..., description="Risk title")
    description: Optional[str] = None
    likelihood: Literal["low", "medium", "high"] = Field("low")
    impact: Literal["low", "medium", "high"] = Field("low")
    owner: Optional[str] = None
    related_assets: List[str] = Field(default_factory=list)

class ComplianceRequirement(BaseModel):
    framework: Literal["GDPR", "ISO27001", "SOC2", "Other"] = Field("GDPR")
    control_id: Optional[str] = Field(None, description="Control identifier (e.g., A.5.1)")
    title: str = Field(...)
    description: Optional[str] = None
    applicable: bool = Field(True)

class Relationship(BaseModel):
    """
    Generic relationship entity to connect nodes
    - source_type/target_type: e.g., application, process, role, dataasset
    - kind: e.g., uses, owns, produces, consumes, responsible_for
    """
    source_id: str = Field(...)
    source_type: str = Field(...)
    target_id: str = Field(...)
    target_type: str = Field(...)
    kind: str = Field(...)
    description: Optional[str] = None

# Helper utilities for schema endpoint

def list_models():
    """Return a dictionary of model name -> Pydantic model class for public models in this module."""
    import inspect, sys
    current_module = sys.modules[__name__]
    models = {}
    for name, obj in inspect.getmembers(current_module):
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
            models[name] = obj
    return models


def schema_summary():
    """Return a serializable summary of all models and their fields (used by /schema endpoint)."""
    out = {}
    for name, model in list_models().items():
        out[name] = {
            "collection": name.lower(),
            "fields": {
                f_name: {
                    "type": str(f.annotation) if hasattr(f, "annotation") else "Any",
                    "required": f.is_required(),
                    "default": None if f.default is None else f.default,
                    "description": f.field_info.description,
                }
                for f_name, f in model.model_fields.items()
            },
        }
    return out

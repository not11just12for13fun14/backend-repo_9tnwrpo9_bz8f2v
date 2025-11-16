import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Local modules
from database import create_document, get_documents, db
import schemas as ordne_schemas

app = FastAPI(title="Ordne API", description="Enterprise architecture for SMBs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"name": "Ordne API", "status": "ok"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from Ordne backend!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# -------- Schema Introspection ---------
@app.get("/schema")
def get_schema():
    """Return summary of all Ordne models and fields."""
    return ordne_schemas.schema_summary()


@app.get("/collections")
def list_collections():
    """Return list of supported collections derived from Pydantic models."""
    return {
        "collections": [name.lower() for name in ordne_schemas.list_models().keys()]
    }


# -------- Data Endpoints (Generic CRUD: Create + List) ---------
class GenericPayload(BaseModel):
    data: Dict[str, Any]


def _model_for_collection(collection: str):
    models = ordne_schemas.list_models()
    for name, model in models.items():
        if name.lower() == collection.lower():
            return model
    return None


@app.get("/documents/{collection}")
def get_collection_documents(collection: str, limit: Optional[int] = 100):
    model = _model_for_collection(collection)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown collection '{collection}'")

    docs = get_documents(collection.lower(), limit=limit)

    # Convert ObjectId to str
    def serialize(doc: Dict[str, Any]):
        out = {}
        for k, v in doc.items():
            if k == "_id":
                out["_id"] = str(v)
            else:
                try:
                    import datetime
                    if isinstance(v, (datetime.datetime, datetime.date)):
                        out[k] = v.isoformat()
                    else:
                        out[k] = v
                except Exception:
                    out[k] = v
        return out

    return {"items": [serialize(d) for d in docs]}


@app.post("/documents/{collection}")
def create_collection_document(collection: str, payload: GenericPayload):
    model_cls = _model_for_collection(collection)
    if model_cls is None:
        raise HTTPException(status_code=404, detail=f"Unknown collection '{collection}'")

    try:
        validated = model_cls(**payload.data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")

    inserted_id = create_document(collection.lower(), validated)
    return {"_id": inserted_id}


# -------- Graph Endpoint ---------
@app.get("/graph")
def get_graph():
    """Return a lightweight graph (nodes + edges) assembled from core collections.
    Nodes: application, process, role, dataasset, risk
    Edges: relationship (source_id, target_id, kind)
    """
    core = ["application", "process", "role", "dataasset", "risk"]
    nodes: List[Dict[str, Any]] = []
    id_map = {}

    for c in core:
        try:
            docs = get_documents(c, limit=100)
            for d in docs:
                _id = str(d.get("_id"))
                label = d.get("name") or d.get("title") or c.capitalize()
                nodes.append({
                    "id": _id,
                    "type": c,
                    "label": label,
                })
                id_map[_id] = True
        except Exception:
            # Collection may not exist yet; skip
            pass

    # Edges from relationship collection
    edges: List[Dict[str, Any]] = []
    try:
        rels = get_documents("relationship", limit=500)
        for r in rels:
            src = str(r.get("source_id"))
            tgt = str(r.get("target_id"))
            if not src or not tgt:
                continue
            edges.append({
                "source": src,
                "target": tgt,
                "kind": r.get("kind", "rel"),
                "id": str(r.get("_id")),
            })
    except Exception:
        pass

    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

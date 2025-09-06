from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from qiskit_ibm_runtime import QiskitRuntimeService
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict, Counter
import asyncio
import traceback

app = FastAPI(title="Quantum Job Tracker Backend", version="2.2")

# ---------------------------
# Users (replace with valid IBM Quantum credentials)
# ---------------------------
USERS = [
     {
        "name": "Varsha",
        "api_key": "NYtIsFdFa6S6O0rlcQ93oaeHrLBzM9mtjPH4x56n5MEt",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/33b9f303d2774265b1b179b2acad735c:826d5c2d-29c4-4149-9696-858758f5b084::"
    },
    {
        "name": "Hema",
        "api_key": "Ub1ZrxoqrXkW8bTnenYepRE6kis79Qc1LCMngA3eOJ6E",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/13d3bb6dd1e54359bded6b17df3fc250:129f4938-a096-40c2-8ffb-fd22cf167bfb::"
    },
    {
        "name": "Maggi",
        "api_key": "X5KFWQLUBRZOdUXY5HfPQqzaiHz1rRwqjL_DcmmhHduz",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/da72e8a1ec874188aef6f5a3ca0aec0b:ff15b69b-b901-4389-aab0-00c9d8894547::"
    },
    {
        "name": "Naini",
        "api_key": "Ct5e7UxUfNVD3FUMel72lQejDqH8PaaQ7nanMgMjSDep",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/f7e38dc4eac94d5d86212762421c4ee2:5cd44a17-612d-48c4-bbcb-e3bdfe64e3bf::"
    },
    {
        "name": "Gheya",
        "api_key": "WaJqjNnOOwSp1JxXfD1u61LgYzCqFbzTxcc-fj9gZa90",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/a902ce47818d4e7eabc377e79633e773:1740bed5-a954-45b4-98d0-ea081c0b659e::"
    },
    {
        "name": "Sania",
        "api_key": "1LhE70BbChF2sPuAeEuQv-0FRQyL0F62WVTtgkKIHWNl",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/69e167bece4c47ce8f09da1dcbc0e03f:57a20b44-3556-4e1a-8cc8-a1f77d84df4b::"
    },
    {
        "name": "Valli",
        "api_key": "wtNr4bJyacYj09jZ5nAqPhkszLZ5V59WumbAZ2qG3hle",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/ef234ff69b6340289a026f2771dae515:491ce5b3-5d5c-43f7-bc6d-196a0a547b18::"
    }
]

NOTIFY_POLL_INTERVAL = 15
_last_seen_job_status: Dict[str, str] = {}
_active_websockets: List[WebSocket] = []

# ---------------------------
# Helpers
# ---------------------------
def get_service(user: Dict) -> QiskitRuntimeService:
    return QiskitRuntimeService(
        channel="ibm_cloud",
        token=user["api_key"],
        instance=user["instance"]
    )

def safe_get_attr(obj, attr, default="Unknown"):
    try:
        value = getattr(obj, attr, None)
        if callable(value):
            return value()
        return value or default
    except Exception:
        return default

def extract_job_data(job) -> Dict:
    try:
        job_id = safe_get_attr(job, "job_id")
        try:
            status = job.status()
            status_name = getattr(status, "name", getattr(status, "value", str(status)))
        except:
            status_name = "Unknown"

        try:
            backend = job.backend()
            backend_name = getattr(backend, "name", str(backend))
        except:
            backend_name = "Unknown"

        creation_date = safe_get_attr(job, "creation_date")
        if creation_date and hasattr(creation_date, "isoformat"):
            creation_date = creation_date.isoformat()

        program_id = safe_get_attr(job, "program_id")

        try:
            tags = job.tags or []
        except:
            tags = []

        try:
            usage = job.usage()
            usage_data = {
                "quantum_seconds": getattr(usage, "quantum_seconds", 0),
                "seconds": getattr(usage, "seconds", 0)
            } if usage else {}
        except:
            usage_data = {}

        try:
            metrics = job.metrics()
            metrics_data = dict(metrics) if metrics else {}
        except:
            metrics_data = {}

        try:
            queue_info = job.queue_info()
            queue_data = {
                "position": getattr(queue_info, "position", None),
                "estimated_start_time": str(getattr(queue_info, "estimated_start_time", None))
            } if queue_info else {}
        except:
            queue_data = {}

        error_message = safe_get_attr(job, "error_message", None)

        return {
            "job_id": job_id,
            "status": status_name,
            "backend": backend_name,
            "creation_date": creation_date,
            "program_id": program_id,
            "tags": tags,
            "usage": usage_data,
            "metrics": metrics_data,
            "queue_info": queue_data,
            "error_message": error_message
        }
    except Exception as e:
        return {"job_id": "Error", "status": "Error", "backend": "Error", "error": str(e)}

# ---------------------------
# Background notifier
# ---------------------------
async def notify_poll_loop():
    global _last_seen_job_status, _active_websockets
    try:
        await asyncio.sleep(1)
        while True:
            try:
                for user in USERS:
                    try:
                        service = get_service(user)
                        jobs = service.jobs(limit=20)
                        for job in jobs:
                            job_id = safe_get_attr(job, "job_id")
                            try:
                                status = job.status()
                                current_status = getattr(status, "name", getattr(status, "value", str(status)))
                            except:
                                current_status = "Unknown"

                            last = _last_seen_job_status.get(job_id)
                            if last != current_status:
                                _last_seen_job_status[job_id] = current_status
                                event = {
                                    "type": "job_status_change",
                                    "user": user["name"],
                                    "job_id": job_id,
                                    "status": current_status,
                                    "backend": str(getattr(job.backend(), "name", "Unknown")),
                                    "timestamp": datetime.now().isoformat()
                                }
                                for ws in list(_active_websockets):
                                    try:
                                        await ws.send_json(event)
                                    except Exception:
                                        pass
                    except Exception:
                        continue
            except Exception:
                traceback.print_exc()
            await asyncio.sleep(NOTIFY_POLL_INTERVAL)
    except asyncio.CancelledError:
        print("Notification poll loop cancelled (server shutting down).")
        return

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(notify_poll_loop())

@app.websocket("/ws/notifications")
async def websocket_notifications(ws: WebSocket):
    await ws.accept()
    _active_websockets.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data.lower().strip() in ("ping", "hello"):
                await ws.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        if ws in _active_websockets:
            _active_websockets.remove(ws)

# ---------------------------
# Endpoints
# ---------------------------
@app.get("/")
def home():
    return {"message": "Quantum Job Tracker Backend Running 🚀", "version": "2.2"}

@app.get("/jobs/{user_name}")
def get_jobs(user_name: str, limit: int = Query(default=10, le=100)):
    user = next((u for u in USERS if u["name"].lower() == user_name.lower()), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        service = get_service(user)
        jobs = service.jobs(limit=limit)
        job_list = [extract_job_data(job) for job in jobs]
        return {"user": user_name, "total_jobs": len(job_list), "jobs": job_list}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error retrieving jobs: {str(e)}")

@app.get("/heatmap/backends")
def backend_heatmap():
    try:
        service = get_service(USERS[0])
        backends = service.backends()
        heatmap = []
        for backend in backends:
            try:
                status = backend.status()
                pending = getattr(status, "pending_jobs", 0) or 0
                operational = getattr(status, "operational", False)
                if pending == 0:
                    load = "green"
                elif pending <= 5:
                    load = "yellow"
                else:
                    load = "red"
                heatmap.append({
                    "backend": backend.name,
                    "operational": operational,
                    "pending_jobs": pending,
                    "load_level": load
                })
            except Exception as be:
                heatmap.append({"backend": getattr(backend, "name", "Unknown"), "error": str(be)})
        return {"timestamp": datetime.now().isoformat(), "heatmap": heatmap}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Heatmap error: {str(e)}")

@app.get("/users")
def get_all_users():
    return {"total_users": len(USERS), "users": [u["name"] for u in USERS]}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.2", "features_available": 10, "total_users": len(USERS)}


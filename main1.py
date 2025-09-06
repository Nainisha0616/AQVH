from fastapi import FastAPI
from qiskit_ibm_runtime import QiskitRuntimeService

app = FastAPI()

# ---------------------------
# 1. Initialize IBM Quantum Service
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
        "api_key": "SAlTAE4m4k6YcxWv44HuT7Tw3PEzFmH6-RIvWz0DHk0w",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/ef234ff69b6340289a026f2771dae515:491ce5b3-5d5c-43f7-bc6d-196a0a547b18::"
    },
]

# ---------------------------
# 2. Health Check
# ---------------------------
@app.get("/")
def home():
    return {"message": "Quantum Job Tracker Backend is Running 🚀"}

# ---------------------------
# 3. Endpoint: Get Jobs for a User
# ---------------------------
@app.get("/jobs/{user_name}")
def get_jobs(user_name: str):
    user = next((u for u in USERS if u["name"].lower() == user_name.lower()), None)
    if not user:
        return {"error": "User not found"}

    try:
        service = QiskitRuntimeService(
            channel="ibm_cloud",
            token=user["api_key"],
            instance=user["instance"]
        )

        jobs = service.jobs(limit=5)
        job_list = []

        for job in jobs:
            try:
                # Get job ID - using your original working approach
                job_id = getattr(job, "job_id", lambda: "Unknown")()
                
                # Get job status - corrected approach
                try:
                    status = job.status()
                    if hasattr(status, 'name'):
                        status_name = status.name
                    elif hasattr(status, 'value'):
                        status_name = status.value
                    else:
                        status_name = str(status)
                except Exception as status_error:
                    print(f"Status error for job {job_id}: {status_error}")
                    status_name = "Unknown"
                
                # Get backend name
                try:
                    backend = job.backend()
                    if hasattr(backend, 'name'):
                        backend_name = backend.name
                    else:
                        backend_name = str(backend)
                except Exception as backend_error:
                    print(f"Backend error for job {job_id}: {backend_error}")
                    backend_name = "Unknown"

                job_list.append({
                    "job_id": job_id,
                    "status": status_name,
                    "backend": backend_name
                })
                
            except Exception as job_error:
                print(f"Job processing error: {job_error}")
                job_list.append({
                    "job_id": "Error",
                    "status": "Error",
                    "backend": "Error",
                    "error": str(job_error)
                })

        return {"user": user_name, "jobs": job_list}

    except Exception as e:
        return {"error": str(e)}
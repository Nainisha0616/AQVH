from fastapi import FastAPI, HTTPException, Query
from qiskit_ibm_runtime import QiskitRuntimeService
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
from collections import defaultdict, Counter

app = FastAPI(title="Quantum Job Tracker Backend", version="2.0")

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
        "api_key": "wtNr4bJyacYj09jZ5nAqPhkszLZ5V59WumbAZ2qG3hle",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/ef234ff69b6340289a026f2771dae515:491ce5b3-5d5c-43f7-bc6d-196a0a547b18::"
    },
]

# ---------------------------
# Helper Functions
# ---------------------------

def get_service(user: Dict) -> QiskitRuntimeService:
    """Initialize Qiskit Runtime Service for a user"""
    return QiskitRuntimeService(
        channel="ibm_cloud",
        token=user["api_key"],
        instance=user["instance"]
    )

def safe_get_attr(obj, attr, default="Unknown"):
    """Safely get attribute from object"""
    try:
        value = getattr(obj, attr, None)
        if callable(value):
            return value()
        return value or default
    except Exception:
        return default

def extract_job_data(job) -> Dict:
    """Extract comprehensive job data"""
    try:
        # Basic job info
        job_id = safe_get_attr(job, "job_id")
        
        # Status
        try:
            status = job.status()
            status_name = getattr(status, 'name', getattr(status, 'value', str(status)))
        except:
            status_name = "Unknown"
        
        # Backend
        try:
            backend = job.backend()
            backend_name = getattr(backend, 'name', str(backend))
        except:
            backend_name = "Unknown"
        
        # Creation date
        creation_date = safe_get_attr(job, "creation_date")
        if creation_date and hasattr(creation_date, 'isoformat'):
            creation_date = creation_date.isoformat()
        
        # Program ID
        program_id = safe_get_attr(job, "program_id")
        
        # Tags
        try:
            tags = job.tags or []
        except:
            tags = []
        
        # Usage and metrics
        try:
            usage = job.usage()
            usage_data = {
                "quantum_seconds": getattr(usage, 'quantum_seconds', 0),
                "seconds": getattr(usage, 'seconds', 0)
            } if usage else {}
        except:
            usage_data = {}
        
        try:
            metrics = job.metrics()
            metrics_data = dict(metrics) if metrics else {}
        except:
            metrics_data = {}
        
        # Queue info
        try:
            queue_info = job.queue_info()
            queue_data = {
                "position": getattr(queue_info, 'position', None),
                "estimated_start_time": str(getattr(queue_info, 'estimated_start_time', None))
            } if queue_info else {}
        except:
            queue_data = {}
        
        # Error message (if any)
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
        return {
            "job_id": "Error",
            "status": "Error",
            "backend": "Error",
            "error": str(e)
        }

# ---------------------------
# 2. Health Check
# ---------------------------
@app.get("/")
def home():
    return {"message": "Quantum Job Tracker Backend is Running 🚀", "version": "2.0"}

# ---------------------------
# 3. Feature 1: Job Tracker
# ---------------------------
@app.get("/jobs/{user_name}")
def get_jobs(user_name: str, limit: int = Query(default=10, le=100)):
    """Get jobs for a specific user - Feature 1: Job Tracker"""
    user = next((u for u in USERS if u["name"].lower() == user_name.lower()), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        service = get_service(user)
        jobs = service.jobs(limit=limit)
        job_list = [extract_job_data(job) for job in jobs]
        
        return {
            "user": user_name,
            "total_jobs": len(job_list),
            "jobs": job_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# 4. Feature 2: Job Status Analyzer
# ---------------------------
@app.get("/analytics/job-status/{user_name}")
def analyze_job_status(user_name: str, days: int = Query(default=30, le=365)):
    """Analyze job status distribution - Feature 2: Job Status Analyzer"""
    user = next((u for u in USERS if u["name"].lower() == user_name.lower()), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        service = get_service(user)
        cutoff_date = datetime.now() - timedelta(days=days)
        jobs = service.jobs(limit=200, created_after=cutoff_date)
        
        status_counts = Counter()
        total_jobs = 0
        execution_times = []
        
        for job in jobs:
            job_data = extract_job_data(job)
            status_counts[job_data["status"]] += 1
            total_jobs += 1
            
            # Calculate execution time if available
            if job_data["usage"].get("seconds"):
                execution_times.append(job_data["usage"]["seconds"])
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        return {
            "user": user_name,
            "analysis_period_days": days,
            "total_jobs": total_jobs,
            "status_distribution": dict(status_counts),
            "success_rate": status_counts.get("DONE", 0) / total_jobs * 100 if total_jobs > 0 else 0,
            "average_execution_time": avg_execution_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# 5. Feature 3: Quantum Error Analyzer
# ---------------------------
@app.get("/analytics/errors/{user_name}")
def analyze_quantum_errors(user_name: str):
    """Analyze quantum execution errors - Feature 3: Quantum Error Analyzer"""
    user = next((u for u in USERS if u["name"].lower() == user_name.lower()), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        service = get_service(user)
        jobs = service.jobs(limit=100)
        
        error_analysis = {
            "total_jobs": 0,
            "failed_jobs": 0,
            "error_types": Counter(),
            "backend_reliability": defaultdict(lambda: {"total": 0, "failed": 0}),
            "common_errors": []
        }
        
        for job in jobs:
            job_data = extract_job_data(job)
            error_analysis["total_jobs"] += 1
            
            backend = job_data["backend"]
            error_analysis["backend_reliability"][backend]["total"] += 1
            
            if job_data["status"] in ["ERROR", "CANCELLED"]:
                error_analysis["failed_jobs"] += 1
                error_analysis["backend_reliability"][backend]["failed"] += 1
                
                if job_data["error_message"]:
                    error_analysis["error_types"][job_data["error_message"]] += 1
                    error_analysis["common_errors"].append({
                        "job_id": job_data["job_id"],
                        "error": job_data["error_message"],
                        "backend": backend
                    })
        
        # Calculate reliability percentages
        for backend_data in error_analysis["backend_reliability"].values():
            total = backend_data["total"]
            failed = backend_data["failed"]
            backend_data["reliability_percent"] = ((total - failed) / total * 100) if total > 0 else 100
        
        error_analysis["overall_error_rate"] = (error_analysis["failed_jobs"] / error_analysis["total_jobs"] * 100) if error_analysis["total_jobs"] > 0 else 0
        error_analysis["error_types"] = dict(error_analysis["error_types"])
        error_analysis["backend_reliability"] = dict(error_analysis["backend_reliability"])
        
        return {
            "user": user_name,
            "error_analysis": error_analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# 6. Feature 4: Quantum Resource Meter
# ---------------------------
@app.get("/analytics/resources/{user_name}")
def analyze_quantum_resources(user_name: str):
    """Analyze quantum resource usage - Feature 4: Quantum Resource Meter"""
    user = next((u for u in USERS if u["name"].lower() == user_name.lower()), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        service = get_service(user)
        jobs = service.jobs(limit=50)
        
        resource_analysis = {
            "total_quantum_seconds": 0,
            "total_execution_time": 0,
            "jobs_analyzed": 0,
            "resource_distribution": [],
            "average_resources": {
                "quantum_seconds": 0,
                "execution_seconds": 0
            }
        }
        
        quantum_seconds_list = []
        execution_seconds_list = []
        
        for job in jobs:
            job_data = extract_job_data(job)
            
            if job_data["usage"]:
                q_seconds = job_data["usage"].get("quantum_seconds", 0)
                e_seconds = job_data["usage"].get("seconds", 0)
                
                resource_analysis["total_quantum_seconds"] += q_seconds
                resource_analysis["total_execution_time"] += e_seconds
                resource_analysis["jobs_analyzed"] += 1
                
                quantum_seconds_list.append(q_seconds)
                execution_seconds_list.append(e_seconds)
                
                resource_analysis["resource_distribution"].append({
                    "job_id": job_data["job_id"],
                    "backend": job_data["backend"],
                    "quantum_seconds": q_seconds,
                    "execution_seconds": e_seconds,
                    "status": job_data["status"]
                })
        
        # Calculate averages
        if resource_analysis["jobs_analyzed"] > 0:
            resource_analysis["average_resources"]["quantum_seconds"] = resource_analysis["total_quantum_seconds"] / resource_analysis["jobs_analyzed"]
            resource_analysis["average_resources"]["execution_seconds"] = resource_analysis["total_execution_time"] / resource_analysis["jobs_analyzed"]
        
        return {
            "user": user_name,
            "resource_analysis": resource_analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# 7. Feature 5: Backend Performance Analyzer
# ---------------------------
@app.get("/analytics/backend-performance")
def analyze_backend_performance():
    """Analyze backend performance across all users - Feature 5: Backend Performance Analyzer"""
    try:
        # Use first user's service to get backend info
        service = get_service(USERS[0])
        backends = service.backends()
        
        backend_analysis = {}
        
        for backend in backends:
            try:
                backend_name = backend.name
                status = backend.status()
                
                backend_info = {
                    "name": backend_name,
                    "operational": getattr(status, 'operational', False),
                    "status_msg": getattr(status, 'status_msg', "Unknown"),
                    "pending_jobs": getattr(status, 'pending_jobs', 0)
                }
                
                # Get backend properties
                try:
                    properties = backend.properties()
                    if properties:
                        backend_info["last_update"] = str(getattr(properties, 'last_update_date', 'Unknown'))
                        backend_info["n_qubits"] = getattr(properties, 'n_qubits', 0)
                except:
                    backend_info["properties_available"] = False
                
                # Get configuration
                try:
                    config = backend.configuration()
                    if config:
                        backend_info["max_shots"] = getattr(config, 'max_shots', 0)
                        backend_info["coupling_map"] = len(getattr(config, 'coupling_map', []))
                except:
                    backend_info["config_available"] = False
                
                backend_analysis[backend_name] = backend_info
                
            except Exception as backend_error:
                backend_analysis[f"backend_error_{len(backend_analysis)}"] = {
                    "error": str(backend_error)
                }
        
        return {
            "total_backends": len(backend_analysis),
            "backend_analysis": backend_analysis,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# 8. Feature 6: Historical Job Trends
# ---------------------------
@app.get("/analytics/trends/{user_name}")
def analyze_job_trends(user_name: str, days: int = Query(default=90, le=365)):
    """Analyze historical job trends - Feature 6: Historical Job Trends"""
    user = next((u for u in USERS if u["name"].lower() == user_name.lower()), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        service = get_service(user)
        cutoff_date = datetime.now() - timedelta(days=days)
        jobs = service.jobs(limit=300, created_after=cutoff_date)
        
        trends_analysis = {
            "period_days": days,
            "daily_job_counts": defaultdict(int),
            "backend_usage_over_time": defaultdict(lambda: defaultdict(int)),
            "status_trends": defaultdict(lambda: defaultdict(int)),
            "peak_usage_day": "",
            "most_used_backend": ""
        }
        
        backend_totals = Counter()
        
        for job in jobs:
            job_data = extract_job_data(job)
            
            # Parse date
            if job_data["creation_date"] and job_data["creation_date"] != "Unknown":
                try:
                    job_date = datetime.fromisoformat(job_data["creation_date"].replace('Z', '+00:00'))
                    date_str = job_date.strftime('%Y-%m-%d')
                    
                    trends_analysis["daily_job_counts"][date_str] += 1
                    trends_analysis["backend_usage_over_time"][date_str][job_data["backend"]] += 1
                    trends_analysis["status_trends"][date_str][job_data["status"]] += 1
                    
                    backend_totals[job_data["backend"]] += 1
                except:
                    pass
        
        # Convert defaultdicts to regular dicts
        trends_analysis["daily_job_counts"] = dict(trends_analysis["daily_job_counts"])
        trends_analysis["backend_usage_over_time"] = {k: dict(v) for k, v in trends_analysis["backend_usage_over_time"].items()}
        trends_analysis["status_trends"] = {k: dict(v) for k, v in trends_analysis["status_trends"].items()}
        
        # Find peak usage day
        if trends_analysis["daily_job_counts"]:
            trends_analysis["peak_usage_day"] = max(trends_analysis["daily_job_counts"].items(), key=lambda x: x[1])
        
        # Most used backend
        if backend_totals:
            trends_analysis["most_used_backend"] = backend_totals.most_common(1)[0]
        
        return {
            "user": user_name,
            "trends_analysis": trends_analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# 9. Feature 7: User Job Analyzer (Researcher Mode)
# ---------------------------
@app.get("/analytics/all-users")
def analyze_all_users():
    """Analyze job activity across all users - Feature 7: User Job Analyzer"""
    try:
        all_users_analysis = {
            "total_users": len(USERS),
            "user_activity": {},
            "summary": {
                "most_active_user": "",
                "total_jobs_all_users": 0,
                "average_jobs_per_user": 0
            }
        }
        
        user_job_counts = {}
        total_jobs = 0
        
        for user in USERS:
            try:
                service = get_service(user)
                jobs = service.jobs(limit=50)
                
                user_stats = {
                    "total_jobs": 0,
                    "status_distribution": Counter(),
                    "backend_usage": Counter(),
                    "recent_activity": []
                }
                
                for job in jobs:
                    job_data = extract_job_data(job)
                    user_stats["total_jobs"] += 1
                    user_stats["status_distribution"][job_data["status"]] += 1
                    user_stats["backend_usage"][job_data["backend"]] += 1
                    
                    if len(user_stats["recent_activity"]) < 5:
                        user_stats["recent_activity"].append({
                            "job_id": job_data["job_id"],
                            "status": job_data["status"],
                            "backend": job_data["backend"],
                            "date": job_data["creation_date"]
                        })
                
                user_stats["status_distribution"] = dict(user_stats["status_distribution"])
                user_stats["backend_usage"] = dict(user_stats["backend_usage"])
                user_stats["success_rate"] = (user_stats["status_distribution"].get("DONE", 0) / user_stats["total_jobs"] * 100) if user_stats["total_jobs"] > 0 else 0
                
                all_users_analysis["user_activity"][user["name"]] = user_stats
                user_job_counts[user["name"]] = user_stats["total_jobs"]
                total_jobs += user_stats["total_jobs"]
                
            except Exception as user_error:
                all_users_analysis["user_activity"][user["name"]] = {
                    "error": str(user_error)
                }
        
        # Calculate summary
        all_users_analysis["summary"]["total_jobs_all_users"] = total_jobs
        all_users_analysis["summary"]["average_jobs_per_user"] = total_jobs / len(USERS) if len(USERS) > 0 else 0
        
        if user_job_counts:
            most_active = max(user_job_counts.items(), key=lambda x: x[1])
            all_users_analysis["summary"]["most_active_user"] = {
                "name": most_active[0],
                "job_count": most_active[1]
            }
        
        return all_users_analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# 10. Feature 8: Backend Usage Monitor
# ---------------------------
@app.get("/analytics/backend-usage/{user_name}")
def monitor_backend_usage(user_name: str):
    """Monitor backend usage patterns - Feature 8: Backend Usage Monitor"""
    user = next((u for u in USERS if u["name"].lower() == user_name.lower()), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        service = get_service(user)
        jobs = service.jobs(limit=100)
        
        backend_monitor = {
            "backend_usage_stats": defaultdict(lambda: {
                "job_count": 0,
                "success_count": 0,
                "total_quantum_seconds": 0,
                "avg_execution_time": 0
            }),
            "usage_summary": {
                "total_backends_used": 0,
                "most_used_backend": "",
                "least_used_backend": "",
                "recommendation": ""
            }
        }
        
        backend_job_counts = Counter()
        execution_times_by_backend = defaultdict(list)
        
        for job in jobs:
            job_data = extract_job_data(job)
            backend = job_data["backend"]
            
            backend_monitor["backend_usage_stats"][backend]["job_count"] += 1
            backend_job_counts[backend] += 1
            
            if job_data["status"] == "DONE":
                backend_monitor["backend_usage_stats"][backend]["success_count"] += 1
            
            if job_data["usage"].get("quantum_seconds"):
                q_seconds = job_data["usage"]["quantum_seconds"]
                backend_monitor["backend_usage_stats"][backend]["total_quantum_seconds"] += q_seconds
            
            if job_data["usage"].get("seconds"):
                execution_times_by_backend[backend].append(job_data["usage"]["seconds"])
        
        # Calculate averages and success rates
        for backend, stats in backend_monitor["backend_usage_stats"].items():
            if stats["job_count"] > 0:
                stats["success_rate"] = (stats["success_count"] / stats["job_count"]) * 100
                
                if execution_times_by_backend[backend]:
                    stats["avg_execution_time"] = sum(execution_times_by_backend[backend]) / len(execution_times_by_backend[backend])
        
        # Summary statistics
        backend_monitor["usage_summary"]["total_backends_used"] = len(backend_monitor["backend_usage_stats"])
        
        if backend_job_counts:
            most_used = backend_job_counts.most_common(1)[0]
            least_used = backend_job_counts.most_common()[-1]
            
            backend_monitor["usage_summary"]["most_used_backend"] = {
                "name": most_used[0],
                "job_count": most_used[1]
            }
            backend_monitor["usage_summary"]["least_used_backend"] = {
                "name": least_used[0],
                "job_count": least_used[1]
            }
        
        # Convert defaultdict to regular dict
        backend_monitor["backend_usage_stats"] = dict(backend_monitor["backend_usage_stats"])
        
        return {
            "user": user_name,
            "backend_monitor": backend_monitor
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# 11. Feature 9: Job Failure Insights
# ---------------------------
@app.get("/analytics/failures/{user_name}")
def analyze_job_failures(user_name: str):
    """Analyze job failure patterns - Feature 9: Job Failure Insights"""
    user = next((u for u in USERS if u["name"].lower() == user_name.lower()), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        service = get_service(user)
        jobs = service.jobs(limit=150)
        
        failure_analysis = {
            "total_jobs_analyzed": 0,
            "failed_jobs": [],
            "failure_patterns": {
                "by_backend": defaultdict(int),
                "by_error_type": Counter(),
                "by_time_pattern": defaultdict(int)
            },
            "failure_insights": {
                "most_unreliable_backend": "",
                "common_failure_reasons": [],
                "failure_rate_trend": []
            }
        }
        
        for job in jobs:
            job_data = extract_job_data(job)
            failure_analysis["total_jobs_analyzed"] += 1
            
            if job_data["status"] in ["ERROR", "CANCELLED", "FAILED"]:
                failure_info = {
                    "job_id": job_data["job_id"],
                    "backend": job_data["backend"],
                    "status": job_data["status"],
                    "error_message": job_data["error_message"],
                    "creation_date": job_data["creation_date"]
                }
                
                failure_analysis["failed_jobs"].append(failure_info)
                failure_analysis["failure_patterns"]["by_backend"][job_data["backend"]] += 1
                
                if job_data["error_message"]:
                    failure_analysis["failure_patterns"]["by_error_type"][job_data["error_message"]] += 1
                
                # Time pattern analysis
                if job_data["creation_date"] and job_data["creation_date"] != "Unknown":
                    try:
                        job_date = datetime.fromisoformat(job_data["creation_date"].replace('Z', '+00:00'))
                        hour = job_date.hour
                        failure_analysis["failure_patterns"]["by_time_pattern"][f"hour_{hour}"] += 1
                    except:
                        pass
        
        # Generate insights
        if failure_analysis["failure_patterns"]["by_backend"]:
            most_unreliable = max(failure_analysis["failure_patterns"]["by_backend"].items(), key=lambda x: x[1])
            failure_analysis["failure_insights"]["most_unreliable_backend"] = {
                "name": most_unreliable[0],
                "failure_count": most_unreliable[1]
            }
        
        failure_analysis["failure_insights"]["common_failure_reasons"] = failure_analysis["failure_patterns"]["by_error_type"].most_common(5)
        
        # Convert defaultdicts to regular dicts
        failure_analysis["failure_patterns"]["by_backend"] = dict(failure_analysis["failure_patterns"]["by_backend"])
        failure_analysis["failure_patterns"]["by_error_type"] = dict(failure_analysis["failure_patterns"]["by_error_type"])
        failure_analysis["failure_patterns"]["by_time_pattern"] = dict(failure_analysis["failure_patterns"]["by_time_pattern"])
        
        # Calculate overall failure rate
        failure_count = len(failure_analysis["failed_jobs"])
        total_jobs = failure_analysis["total_jobs_analyzed"]
        failure_rate = (failure_count / total_jobs * 100) if total_jobs > 0 else 0
        
        failure_analysis["overall_failure_rate"] = failure_rate
        
        return {
            "user": user_name,
            "failure_analysis": failure_analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# 12. Feature 10: Smart Scheduler Recommendation
# ---------------------------
@app.get("/recommendations/smart-scheduler")
def smart_scheduler_recommendation():
    """Get smart backend recommendations - Feature 10: Smart Scheduler Recommendation"""
    try:
        # Use first user's service to get backend info
        service = get_service(USERS[0])
        backends = service.backends()
        
        recommendations = {
            "recommended_backends": [],
            "analysis_timestamp": datetime.now().isoformat(),
            "recommendation_criteria": {
                "operational_status": "Must be operational",
                "queue_length": "Lower is better",
                "reliability": "Based on historical data"
            }
        }
        
        backend_scores = []
        
        for backend in backends:
            try:
                backend_name = backend.name
                status = backend.status()
                
                # Base score calculation
                score = 0
                operational = getattr(status, 'operational', False)
                pending_jobs = getattr(status, 'pending_jobs', 0)
                
                if operational:
                    score += 50  # Base points for being operational
                    
                    # Queue score (fewer pending jobs = higher score)
                    if pending_jobs == 0:
                        score += 30
                    elif pending_jobs < 5:
                        score += 20
                    elif pending_jobs < 10:
                        score += 10
                    else:
                        score += 5
                    
                    # Additional points for backend properties
                    try:
                        properties = backend.properties()
                        if properties:
                            score += 10  # Bonus for having properties available
                    except:
                        pass
                    
                    backend_info = {
                        "backend_name": backend_name,
                        "operational": operational,
                        "pending_jobs": pending_jobs,
                        "recommendation_score": score,
                        "status_message": getattr(status, 'status_msg', 'No message'),
                        "recommendation": "Recommended" if score >= 60 else "Available" if score >= 50 else "Not recommended"
                    }
                    
                    backend_scores.append(backend_info)
                    
            except Exception as backend_error:
                continue
        
        # Sort by recommendation score (highest first)
        backend_scores.sort(key=lambda x: x["recommendation_score"], reverse=True)
        
        recommendations["recommended_backends"] = backend_scores[:5]  # Top 5 recommendations
        recommendations["total_backends_analyzed"] = len(backend_scores)
        
        # Best recommendation
        if backend_scores:
            recommendations["best_choice"] = backend_scores[0]
        
        return recommendations

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# Additional Utility Endpoints
# ---------------------------

@app.get("/users")
def get_all_users():
    """Get list of all available users"""
    return {
        "total_users": len(USERS),
        "users": [user["name"] for user in USERS]
    }

@app.get("/health")
def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "version": "2.0",
        "features_available": 10,
        "total_users": len(USERS),
        "timestamp": datetime.now().isoformat()
    }
import os
from datetime import datetime, date
import pymongo
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "student_placement_nosql")

_client = None
_db = None
_is_real_mongo = False


# Initial sample datasets matching mongodb_student_placement.js
INITIAL_STUDENTS = [
    {
        "student_id": 101,
        "student_name": "Ananya Rao",
        "department": "CSE",
        "graduation_year": 2029,
        "cgpa": 9.20,
        "skills": [
            {"name": "Python", "proficiency": "Advanced"},
            {"name": "SQL", "proficiency": "Advanced"},
            {"name": "MongoDB", "proficiency": "Intermediate"}
        ],
        "placement_status": "Placed"
    },
    {
        "student_id": 102,
        "student_name": "Rahul Kumar",
        "department": "ISE",
        "graduation_year": 2029,
        "cgpa": 8.10,
        "skills": [
            {"name": "Java", "proficiency": "Intermediate"},
            {"name": "SQL", "proficiency": "Advanced"}
        ],
        "placement_status": "Not Placed"
    },
    {
        "student_id": 103,
        "student_name": "Meera Nair",
        "department": "ECE",
        "graduation_year": 2029,
        "cgpa": 7.40,
        "skills": [
            {"name": "Python", "proficiency": "Intermediate"},
            {"name": "Data Analysis", "proficiency": "Beginner"}
        ],
        "placement_status": "Not Placed"
    },
    {
        "student_id": 104,
        "student_name": "Arjun Shetty",
        "department": "CSE",
        "graduation_year": 2029,
        "cgpa": 8.80,
        "skills": [
            {"name": "Java", "proficiency": "Advanced"},
            {"name": "C", "proficiency": "Advanced"}
        ],
        "placement_status": "Not Placed"
    },
    {
        "student_id": 105,
        "student_name": "Pooja Das",
        "department": "AIML",
        "graduation_year": 2029,
        "cgpa": 6.90,
        "skills": [
            {"name": "Python", "proficiency": "Beginner"},
            {"name": "SQL", "proficiency": "Intermediate"}
        ],
        "placement_status": "Not Placed"
    }
]

INITIAL_COMPANIES = [
    {"company_id": 1, "company_name": "TCS", "industry": "IT Services"},
    {"company_id": 2, "company_name": "Infosys", "industry": "IT Services"},
    {"company_id": 3, "company_name": "Accenture", "industry": "Consulting and IT"},
    {"company_id": 4, "company_name": "Microsoft", "industry": "Technology"},
    {"company_id": 5, "company_name": "Deloitte", "industry": "Consulting"},
    {"company_id": 6, "company_name": "Wipro", "industry": "IT Services"},
    {"company_id": 7, "company_name": "Amazon", "industry": "E-commerce and Technology"},
    {"company_id": 8, "company_name": "IBM", "industry": "Technology"}
]

INITIAL_APPLICATIONS = [
    {
        "application_id": 1,
        "student_id": 101,
        "student_name": "Ananya Rao",
        "company_name": "TCS",
        "job_role": "Graduate Trainee",
        "application_date": datetime(2026, 11, 8),
        "status": "Selected",
        "package_lpa": 3.5
    },
    {
        "application_id": 2,
        "student_id": 102,
        "student_name": "Rahul Kumar",
        "company_name": "Infosys",
        "job_role": "Systems Engineer",
        "application_date": datetime(2026, 11, 8),
        "status": "Applied",
        "package_lpa": 4.0
    },
    {
        "application_id": 3,
        "student_id": 103,
        "student_name": "Meera Nair",
        "company_name": "IBM",
        "job_role": "Data Science Intern",
        "application_date": datetime(2026, 11, 8),
        "status": "Applied",
        "stipend_monthly": 20000
    },
    {
        "application_id": 4,
        "student_id": 104,
        "student_name": "Arjun Shetty",
        "company_name": "Microsoft",
        "job_role": "Software Engineer",
        "application_date": datetime(2026, 11, 8),
        "status": "Applied",
        "package_lpa": 18.0
    }
]


def init_mongo():
    """Initializes MongoDB client, either real MongoDB or mongomock fallback."""
    global _client, _db, _is_real_mongo
    if _db is not None:
        return _db

    real_client = None
    try:
        real_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500)
        # Force a quick server check
        real_client.admin.command("ping")
        _client = real_client
        _db = _client[MONGO_DB_NAME]
        _is_real_mongo = True
        print(f"[MongoDB] Successfully connected to live MongoDB server at {MONGO_URI}")
    except Exception as e:
        if real_client is not None:
            try:
                real_client.close()
            except Exception:
                pass
        import mongomock
        print(f"[MongoDB] Live server not available ({e}). Initializing high-fidelity in-memory mongomock engine.")
        _client = mongomock.MongoClient()
        _db = _client[MONGO_DB_NAME]
        _is_real_mongo = False

    seed_mongo_collections(_db)
    return _db


def seed_mongo_collections(db):
    """Creates indexes and seeds initial collections if empty."""
    try:
        # Students
        if db.students.count_documents({}) == 0:
            db.students.insert_many([dict(doc) for doc in INITIAL_STUDENTS])
            try:
                db.students.create_index("student_id", unique=True)
            except Exception:
                pass

        # Companies
        if db.companies.count_documents({}) == 0:
            db.companies.insert_many([dict(doc) for doc in INITIAL_COMPANIES])
            try:
                db.companies.create_index("company_id", unique=True)
            except Exception:
                pass

        # Applications
        if db.applications.count_documents({}) == 0:
            db.applications.insert_many([dict(doc) for doc in INITIAL_APPLICATIONS])
            try:
                db.applications.create_index("application_id", unique=True)
                db.applications.create_index("student_id")
            except Exception:
                pass
    except Exception as e:
        print(f"[MongoDB] Seeding error: {e}")


def get_mongo_db():
    """Returns initialized MongoDB database instance."""
    global _db
    if _db is None:
        return init_mongo()
    return _db


def check_mongo_health():
    """Returns MongoDB health and collection statistics."""
    db = get_mongo_db()
    collections = db.list_collection_names()
    counts = {col: db[col].count_documents({}) for col in collections}
    mode = "Live MongoDB Server" if _is_real_mongo else "Embedded mongomock Engine (Live NoSQL)"
    return {
        "status": "connected",
        "mode": mode,
        "is_real_mongo": _is_real_mongo,
        "database": MONGO_DB_NAME,
        "collections": collections,
        "document_counts": counts
    }


def clean_doc(doc):
    """Converts ObjectId and date objects to JSON-serializable types."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [clean_doc(d) for d in doc]
    if isinstance(doc, dict):
        cleaned = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                cleaned[k] = str(v)
            elif isinstance(v, (datetime, date)):
                cleaned[k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                cleaned[k] = clean_doc(v)
            else:
                cleaned[k] = v
        return cleaned
    return doc


def sync_student_doc(student_id, student_name, dept, year, cgpa, skills, placement_status="Not Placed"):
    """Syncs a student document to MongoDB."""
    db = get_mongo_db()
    skills_formatted = []
    for s in skills:
        if isinstance(s, dict):
            skills_formatted.append({"name": s.get("name", ""), "proficiency": s.get("proficiency", "Beginner")})
        else:
            skills_formatted.append({"name": str(s), "proficiency": "Intermediate"})

    doc = {
        "student_id": int(student_id),
        "student_name": student_name,
        "department": dept,
        "graduation_year": int(year),
        "cgpa": float(cgpa),
        "skills": skills_formatted,
        "placement_status": placement_status
    }
    db.students.update_one({"student_id": int(student_id)}, {"$set": doc}, upsert=True)


def sync_company_doc(company_id, company_name, industry):
    """Syncs a company document to MongoDB."""
    db = get_mongo_db()
    doc = {
        "company_id": int(company_id),
        "company_name": company_name,
        "industry": industry
    }
    db.companies.update_one({"company_id": int(company_id)}, {"$set": doc}, upsert=True)


def sync_application_doc(application_id, student_id, student_name, company_name, job_role, app_date, status, package_lpa=None, stipend=None):
    """Syncs an application document to MongoDB."""
    db = get_mongo_db()
    if isinstance(app_date, str):
        try:
            app_date = datetime.strptime(app_date[:10], "%Y-%m-%d")
        except Exception:
            app_date = datetime.now()
    elif isinstance(app_date, date) and not isinstance(app_date, datetime):
        app_date = datetime.combine(app_date, datetime.min.time())

    doc = {
        "application_id": int(application_id),
        "student_id": int(student_id),
        "student_name": student_name,
        "company_name": company_name,
        "job_role": job_role,
        "application_date": app_date,
        "status": status
    }
    if package_lpa is not None:
        doc["package_lpa"] = float(package_lpa)
    if stipend is not None:
        doc["stipend_monthly"] = float(stipend)

    db.applications.update_one({"application_id": int(application_id)}, {"$set": doc}, upsert=True)


def update_mongo_application_status(application_id, new_status):
    """Updates status of application document and updates student if Selected."""
    db = get_mongo_db()
    db.applications.update_one({"application_id": int(application_id)}, {"$set": {"status": new_status}})
    app = db.applications.find_one({"application_id": int(application_id)})
    if app and new_status == "Selected":
        db.students.update_one({"student_id": app["student_id"]}, {"$set": {"placement_status": "Placed"}})


def delete_student_doc(student_id):
    """Deletes student from MongoDB."""
    db = get_mongo_db()
    db.students.delete_one({"student_id": int(student_id)})
    db.applications.delete_many({"student_id": int(student_id)})


def delete_company_doc(company_id):
    """Deletes company from MongoDB."""
    db = get_mongo_db()
    db.companies.delete_one({"company_id": int(company_id)})

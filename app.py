import os
import re
from datetime import datetime, date
from decimal import Decimal
from flask import Flask, jsonify, request, send_from_directory, render_template_string
from flask_cors import CORS
from dotenv import load_dotenv
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash

from db_mysql import (
    get_connection,
    query_all,
    query_one,
    execute_sql,
    check_mysql_health,
    MYSQL_DB
)
from db_mongo import (
    get_mongo_db,
    check_mongo_health,
    sync_student_doc,
    sync_company_doc,
    sync_application_doc,
    update_mongo_application_status,
    delete_student_doc,
    delete_company_doc,
    clean_doc
)

load_dotenv()

# Setup Flask app to serve the existing frontend from Student_Placement_Frontend directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "Student_Placement_Frontend")

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path=""
)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "placewise_placement_portal_secret_key_2026")
CORS(app)


def serialize_item(obj):
    """Recursively converts Decimals and dates to JSON-serializable types."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: serialize_item(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_item(v) for v in obj]
    return obj


# Helper branding map for companies (matches frontend design)
COMPANY_STYLES = {
    "TCS": {"initial": "T", "color": ""},
    "Infosys": {"initial": "I", "color": "blue-logo"},
    "Accenture": {"initial": "A", "color": "orange-logo"},
    "Microsoft": {"initial": "M", "color": "blue-logo"},
    "Deloitte": {"initial": "D", "color": "green-logo"},
    "Wipro": {"initial": "W", "color": ""},
    "Amazon": {"initial": "a", "color": "orange-logo"},
    "IBM": {"initial": "IBM", "color": "blue-logo"}
}

def get_company_style(name):
    if not name:
        return {"initial": "C", "color": ""}
    return COMPANY_STYLES.get(name, {"initial": name[:2].upper(), "color": ""})


# ---------------------------------------------------------------------------
# FRONTEND ROUTES
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serves the PlaceWise index.html page."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    """Serves frontend static assets (styles.css, app.js, images)."""
    return send_from_directory(FRONTEND_DIR, filename)


# ---------------------------------------------------------------------------
# HEALTH & SYSTEM STATUS
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health_check():
    """Returns connectivity and statistics for both MySQL and MongoDB."""
    mysql_info = check_mysql_health()
    mongo_info = check_mongo_health()
    return jsonify({
        "status": "healthy" if mysql_info.get("status") == "connected" else "degraded",
        "mysql": mysql_info,
        "mongodb": mongo_info,
        "timestamp": datetime.now().isoformat()
    })


# ---------------------------------------------------------------------------
# AUTHENTICATION & STUDENT DASHBOARD API
# ---------------------------------------------------------------------------

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Registers a new student user, creates student record and user credentials."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    phone = data.get("phone", "").strip() or None
    dept = data.get("dept", "CSE").strip()
    year = data.get("year", 2029)
    cgpa = data.get("cgpa", 8.0)
    skills = data.get("skills", ["Python", "SQL"])

    if not name:
        return jsonify({"error": "Full name is required."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "Valid email address is required."}), 400
    if not password or len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters."}), 400

    try:
        cgpa = float(cgpa)
        year = int(year)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid CGPA or graduation year."}), 400

    # Check if email exists in User_Account or Student
    existing_user = query_one("SELECT * FROM User_Account WHERE LOWER(email) = LOWER(%s);", (email,))
    existing_student = query_one("SELECT * FROM Student WHERE LOWER(email) = LOWER(%s);", (email,))
    if existing_user or existing_student:
        return jsonify({"error": "An account with this email already exists. Please log in."}), 400

    # Auto-generate next student ID
    max_row = query_one("SELECT MAX(student_id) AS max_id FROM Student;")
    new_student_id = (max_row["max_id"] or 100) + 1

    try:
        # Insert Student
        execute_sql("""
            INSERT INTO Student (student_id, student_name, email, phone, department, graduation_year, cgpa, placement_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Not Placed');
        """, (new_student_id, name, email, phone, dept, year, cgpa))

        # Insert User_Account
        pw_hash = generate_password_hash(password)
        res_acc = execute_sql("""
            INSERT INTO User_Account (student_id, email, password_hash, full_name, role)
            VALUES (%s, %s, %s, %s, 'Student');
        """, (new_student_id, email, pw_hash, name))

        # Insert Skills
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        for s in skills:
            skill_name = s.get("name") if isinstance(s, dict) else str(s).strip()
            proficiency = s.get("proficiency", "Intermediate") if isinstance(s, dict) else "Intermediate"
            if not skill_name:
                continue
            skill_row = query_one("SELECT skill_id FROM Skill WHERE LOWER(skill_name) = LOWER(%s);", (skill_name,))
            if not skill_row:
                r = execute_sql("INSERT INTO Skill (skill_name) VALUES (%s);", (skill_name,))
                skill_id = r["last_insert_id"]
            else:
                skill_id = skill_row["skill_id"]
            execute_sql("""
                INSERT INTO Student_Skill (student_id, skill_id, proficiency)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE proficiency = VALUES(proficiency);
            """, (new_student_id, skill_id, proficiency))

        # Sync to MongoDB
        sync_student_doc(
            student_id=new_student_id,
            student_name=name,
            dept=dept,
            year=year,
            cgpa=cgpa,
            skills=skills,
            placement_status="Not Placed"
        )

        user_info = {
            "account_id": res_acc["last_insert_id"],
            "student_id": new_student_id,
            "name": name,
            "email": email,
            "dept": dept,
            "cgpa": cgpa,
            "role": "Student"
        }
        return jsonify({"message": "Registration successful!", "user": user_info}), 201
    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticates user with email and password."""
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    account = query_one("SELECT * FROM User_Account WHERE LOWER(email) = LOWER(%s);", (email,))
    if not account:
        return jsonify({"error": "Invalid email or password."}), 401

    if not check_password_hash(account["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    user_info = {
        "account_id": account["account_id"],
        "student_id": account["student_id"],
        "name": account["full_name"],
        "email": account["email"],
        "role": account["role"]
    }

    # If student, attach student details
    if account["student_id"]:
        student = query_one("SELECT * FROM Student WHERE student_id = %s;", (account["student_id"],))
        if student:
            user_info["student"] = serialize_item(student)

    return jsonify({"message": "Login successful!", "user": user_info})


@app.route("/api/auth/accounts", methods=["GET"])
def get_demo_accounts():
    """Returns available accounts for quick switcher."""
    accounts = query_all("""
        SELECT a.account_id, a.student_id, a.email, a.full_name AS name, a.role,
               s.department AS dept, s.cgpa, s.placement_status
        FROM User_Account a
        LEFT JOIN Student s ON a.student_id = s.student_id
        ORDER BY a.role DESC, a.account_id ASC;
    """)
    return jsonify(serialize_item(accounts))


@app.route("/api/student/dashboard/<int:student_id>", methods=["GET"])
def get_student_dashboard(student_id):
    """Returns personalized student dashboard data."""
    student = query_one("SELECT * FROM Student WHERE student_id = %s;", (student_id,))
    if not student:
        return jsonify({"error": "Student not found."}), 404

    # Skills
    skills = query_all("""
        SELECT sk.skill_name AS name, ss.proficiency
        FROM Student_Skill ss
        JOIN Skill sk ON ss.skill_id = sk.skill_id
        WHERE ss.student_id = %s;
    """, (student_id,))

    # My applications
    applications = query_all("""
        SELECT a.application_id AS id, a.status, a.application_date AS date,
               COALESCE(cd.company_name, ci.company_name) AS company,
               COALESCE(d.job_role, i.internship_role) AS role,
               d.package_lpa AS package, i.stipend_monthly AS stipend
        FROM Application a
        LEFT JOIN Placement_Drive d ON a.drive_id = d.drive_id
        LEFT JOIN Company cd ON d.company_id = cd.company_id
        LEFT JOIN Internship i ON a.internship_id = i.internship_id
        LEFT JOIN Company ci ON i.company_id = ci.company_id
        WHERE a.student_id = %s
        ORDER BY a.application_id DESC;
    """, (student_id,))

    # Check eligibility for all drives
    all_drives = query_all("""
        SELECT d.drive_id AS id, d.drive_name AS name, d.job_role AS role,
               d.min_cgpa AS min_cgpa, d.package_lpa AS package, d.drive_date AS date,
               c.company_name AS company
        FROM Placement_Drive d
        JOIN Company c ON d.company_id = c.company_id;
    """)

    eligible_drives = []
    ineligible_drives = []
    student_cgpa = float(student["cgpa"])
    for d in all_drives:
        d_min = float(d["min_cgpa"])
        if student_cgpa >= d_min:
            eligible_drives.append(d)
        else:
            ineligible_drives.append(d)

    # Placement offer if placed
    placement = query_one("""
        SELECT p.placement_id, p.package_lpa, p.offer_date,
               c.company_name, COALESCE(d.job_role, i.internship_role) AS role
        FROM Placement p
        JOIN Company c ON p.company_id = c.company_id
        LEFT JOIN Placement_Drive d ON p.drive_id = d.drive_id
        LEFT JOIN Internship i ON p.internship_id = i.internship_id
        WHERE p.student_id = %s;
    """, (student_id,))

    return jsonify(serialize_item({
        "student": student,
        "skills": skills,
        "applications": applications,
        "eligible_drives_count": len(eligible_drives),
        "ineligible_drives_count": len(ineligible_drives),
        "eligible_drives": eligible_drives,
        "placement": placement
    }))


# ---------------------------------------------------------------------------
# DASHBOARD OVERVIEW API
# ---------------------------------------------------------------------------

@app.route("/api/overview", methods=["GET"])
def get_overview():
    """Returns all aggregate metrics, upcoming opportunities, and recent activity."""
    try:
        # Student count and placed count
        total_students = query_one("SELECT COUNT(*) AS c FROM Student;")["c"]
        placed_students = query_one("SELECT COUNT(*) AS c FROM Student WHERE placement_status = 'Placed';")["c"]
        not_placed_students = total_students - placed_students

        # Drives & Internships
        total_drives = query_one("SELECT COUNT(*) AS c FROM Placement_Drive;")["c"]
        total_internships = query_one("SELECT COUNT(*) AS c FROM Internship;")["c"]
        active_opportunities = total_drives + total_internships

        # Applications
        total_applications = query_one("SELECT COUNT(*) AS c FROM Application;")["c"]
        status_rows = query_all("SELECT status, COUNT(*) AS count FROM Application GROUP BY status;")
        status_counts = {r["status"]: r["count"] for r in status_rows}

        rate = round((placed_students / total_students * 100), 1) if total_students > 0 else 0.0

        # Featured upcoming drives
        featured_drives = query_all("""
            SELECT d.drive_id AS id, d.drive_name AS name, d.job_role AS role,
                   d.package_lpa AS package, d.drive_date AS date,
                   c.company_name AS company
            FROM Placement_Drive d
            JOIN Company c ON d.company_id = c.company_id
            ORDER BY d.drive_date ASC
            LIMIT 5;
        """)
        for d in featured_drives:
            style = get_company_style(d["company"])
            d["initial"] = style["initial"]
            d["color"] = style["color"]

        # Recent activity from Application_Audit or Application
        recent_activity = query_all("""
            SELECT a.audit_id, a.application_id, a.old_status, a.new_status, a.changed_at,
                   s.student_name,
                   COALESCE(cd.company_name, ci.company_name) AS company_name
            FROM Application_Audit a
            JOIN Application app ON a.application_id = app.application_id
            JOIN Student s ON app.student_id = s.student_id
            LEFT JOIN Placement_Drive d ON app.drive_id = d.drive_id
            LEFT JOIN Company cd ON d.company_id = cd.company_id
            LEFT JOIN Internship i ON app.internship_id = i.internship_id
            LEFT JOIN Company ci ON i.company_id = ci.company_id
            ORDER BY a.changed_at DESC
            LIMIT 5;
        """)

        return jsonify(serialize_item({
            "total_students": total_students,
            "placed_students": placed_students,
            "not_placed_students": not_placed_students,
            "placement_rate": rate,
            "total_drives": total_drives,
            "total_internships": total_internships,
            "active_opportunities": active_opportunities,
            "total_applications": total_applications,
            "status_counts": status_counts,
            "featured_drives": featured_drives,
            "recent_activity": recent_activity
        }))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# STUDENT MANAGEMENT API
# ---------------------------------------------------------------------------

@app.route("/api/students", methods=["GET"])
def get_students():
    """Lists students with skills, optional search and filtering."""
    search = request.args.get("search", "").strip().lower()
    dept = request.args.get("dept", "").strip()
    status = request.args.get("status", "").strip()

    sql = """
        SELECT s.student_id AS id, s.student_name AS name, s.email, s.phone,
               s.department AS dept, s.graduation_year AS year, s.cgpa,
               s.placement_status AS status
        FROM Student s
        WHERE 1=1
    """
    params = []
    if dept:
        sql += " AND s.department = %s"
        params.append(dept)
    if status:
        sql += " AND s.placement_status = %s"
        params.append(status)
    if search:
        sql += " AND (LOWER(s.student_name) LIKE %s OR LOWER(s.email) LIKE %s OR LOWER(s.department) LIKE %s)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term])

    sql += " ORDER BY s.student_id ASC;"
    rows = query_all(sql, params)

    # Attach skills for each student
    for s in rows:
        skills = query_all("""
            SELECT sk.skill_name AS name, ss.proficiency
            FROM Student_Skill ss
            JOIN Skill sk ON ss.skill_id = sk.skill_id
            WHERE ss.student_id = %s;
        """, (s["id"],))
        s["skills"] = [sk["name"] for sk in skills]
        s["skills_detail"] = skills

    return jsonify(serialize_item(rows))


@app.route("/api/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    """Gets complete details for a single student."""
    student = query_one("""
        SELECT student_id AS id, student_name AS name, email, phone,
               department AS dept, graduation_year AS year, cgpa,
               placement_status AS status
        FROM Student
        WHERE student_id = %s;
    """, (student_id,))
    if not student:
        return jsonify({"error": "Student not found"}), 404

    skills = query_all("""
        SELECT sk.skill_name AS name, ss.proficiency
        FROM Student_Skill ss
        JOIN Skill sk ON ss.skill_id = sk.skill_id
        WHERE ss.student_id = %s;
    """, (student_id,))
    student["skills"] = [sk["name"] for sk in skills]
    student["skills_detail"] = skills

    applications = query_all("""
        SELECT a.application_id AS id, a.status, a.application_date AS date,
               COALESCE(cd.company_name, ci.company_name) AS company,
               COALESCE(d.job_role, i.internship_role) AS role,
               d.package_lpa AS package, i.stipend_monthly AS stipend
        FROM Application a
        LEFT JOIN Placement_Drive d ON a.drive_id = d.drive_id
        LEFT JOIN Company cd ON d.company_id = cd.company_id
        LEFT JOIN Internship i ON a.internship_id = i.internship_id
        LEFT JOIN Company ci ON i.company_id = ci.company_id
        WHERE a.student_id = %s
        ORDER BY a.application_id DESC;
    """, (student_id,))
    student["applications"] = applications

    return jsonify(serialize_item(student))


@app.route("/api/students", methods=["POST"])
def add_student():
    """Adds a new student to MySQL and syncs to MongoDB."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip() or None
    dept = data.get("dept", "").strip()
    year = data.get("year", 2029)
    cgpa = data.get("cgpa")
    skills = data.get("skills", [])

    # Validation
    if not name:
        return jsonify({"error": "Student name is required."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "Valid email address is required."}), 400
    if not dept:
        return jsonify({"error": "Department is required."}), 400
    try:
        cgpa = float(cgpa)
        if not (0.0 <= cgpa <= 10.0):
            return jsonify({"error": "CGPA must be between 0.00 and 10.00."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid CGPA format."}), 400

    try:
        year = int(year)
        if year < 2020:
            return jsonify({"error": "Graduation year must be 2020 or later."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid graduation year."}), 400

    # Auto-generate or parse student_id
    student_id = data.get("id")
    if not student_id:
        max_row = query_one("SELECT MAX(student_id) AS max_id FROM Student;")
        student_id = (max_row["max_id"] or 100) + 1
    else:
        student_id = int(student_id)

    # Insert into MySQL
    try:
        execute_sql("""
            INSERT INTO Student (student_id, student_name, email, phone, department, graduation_year, cgpa, placement_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Not Placed');
        """, (student_id, name, email, phone, dept, year, cgpa))
    except pymysql.err.IntegrityError as e:
        err_msg = str(e)
        if "Duplicate entry" in err_msg and "email" in err_msg:
            return jsonify({"error": "A student with this email address already exists."}), 400
        if "Duplicate entry" in err_msg and "PRIMARY" in err_msg:
            return jsonify({"error": "A student with this ID already exists."}), 400
        return jsonify({"error": f"Database constraint violation: {err_msg}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Insert skills into Skill and Student_Skill
    skill_names_list = []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    for s in skills:
        skill_name = s.get("name") if isinstance(s, dict) else str(s).strip()
        proficiency = s.get("proficiency", "Intermediate") if isinstance(s, dict) else "Intermediate"
        if not skill_name:
            continue
        skill_names_list.append(skill_name)
        # Ensure Skill exists
        skill_row = query_one("SELECT skill_id FROM Skill WHERE LOWER(skill_name) = LOWER(%s);", (skill_name,))
        if not skill_row:
            res = execute_sql("INSERT INTO Skill (skill_name) VALUES (%s);", (skill_name,))
            skill_id = res["last_insert_id"]
        else:
            skill_id = skill_row["skill_id"]
        # Link in Student_Skill
        try:
            execute_sql("""
                INSERT INTO Student_Skill (student_id, skill_id, proficiency)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE proficiency = VALUES(proficiency);
            """, (student_id, skill_id, proficiency))
        except Exception:
            pass

    # Sync to MongoDB
    try:
        sync_student_doc(
            student_id=student_id,
            student_name=name,
            dept=dept,
            year=year,
            cgpa=cgpa,
            skills=skills,
            placement_status="Not Placed"
        )
    except Exception as e:
        print(f"[MongoDB Sync Warning] {e}")

    return jsonify({
        "message": "Student created successfully.",
        "student": {
            "id": student_id,
            "name": name,
            "email": email,
            "phone": phone,
            "dept": dept,
            "year": year,
            "cgpa": cgpa,
            "status": "Not Placed",
            "skills": skill_names_list
        }
    }), 201


@app.route("/api/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    """Updates an existing student in MySQL and syncs to MongoDB."""
    student = query_one("SELECT * FROM Student WHERE student_id = %s;", (student_id,))
    if not student:
        return jsonify({"error": "Student not found."}), 404

    data = request.get_json() or {}
    name = data.get("name", student["student_name"]).strip()
    email = data.get("email", student["email"]).strip()
    phone = data.get("phone", student["phone"])
    dept = data.get("dept", student["department"]).strip()
    year = int(data.get("year", student["graduation_year"]))
    cgpa = float(data.get("cgpa", student["cgpa"]))
    status = data.get("status", student["placement_status"]).strip()
    skills = data.get("skills")

    try:
        execute_sql("""
            UPDATE Student
            SET student_name = %s, email = %s, phone = %s, department = %s,
                graduation_year = %s, cgpa = %s, placement_status = %s
            WHERE student_id = %s;
        """, (name, email, phone, dept, year, cgpa, status, student_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if skills is not None:
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        # Reset existing skills
        execute_sql("DELETE FROM Student_Skill WHERE student_id = %s;", (student_id,))
        for s in skills:
            skill_name = s.get("name") if isinstance(s, dict) else str(s).strip()
            proficiency = s.get("proficiency", "Intermediate") if isinstance(s, dict) else "Intermediate"
            if not skill_name:
                continue
            skill_row = query_one("SELECT skill_id FROM Skill WHERE LOWER(skill_name) = LOWER(%s);", (skill_name,))
            if not skill_row:
                res = execute_sql("INSERT INTO Skill (skill_name) VALUES (%s);", (skill_name,))
                skill_id = res["last_insert_id"]
            else:
                skill_id = skill_row["skill_id"]
            execute_sql("""
                INSERT INTO Student_Skill (student_id, skill_id, proficiency)
                VALUES (%s, %s, %s);
            """, (student_id, skill_id, proficiency))

    # Sync to MongoDB
    try:
        sync_student_doc(
            student_id=student_id,
            student_name=name,
            dept=dept,
            year=year,
            cgpa=cgpa,
            skills=skills or [],
            placement_status=status
        )
    except Exception as e:
        print(f"[MongoDB Sync Warning] {e}")

    return jsonify({"message": "Student updated successfully."})


@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    """Deletes a student from MySQL and MongoDB."""
    student = query_one("SELECT * FROM Student WHERE student_id = %s;", (student_id,))
    if not student:
        return jsonify({"error": "Student not found."}), 404

    try:
        # Delete dependent placement and application records safely
        execute_sql("DELETE FROM Placement WHERE student_id = %s;", (student_id,))
        apps = query_all("SELECT application_id FROM Application WHERE student_id = %s;", (student_id,))
        for a in apps:
            execute_sql("DELETE FROM Application_Audit WHERE application_id = %s;", (a["application_id"],))
        execute_sql("DELETE FROM Application WHERE student_id = %s;", (student_id,))
        execute_sql("DELETE FROM Student WHERE student_id = %s;", (student_id,))
        # MongoDB deletion
        delete_student_doc(student_id)
        return jsonify({"message": f"Student #{student_id} deleted successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# COMPANY DIRECTORY API
# ---------------------------------------------------------------------------

@app.route("/api/companies", methods=["GET"])
def get_companies():
    """Returns list of companies with role counts and visual styles."""
    search = request.args.get("search", "").strip().lower()
    sql = """
        SELECT c.company_id AS id, c.company_name AS name, c.website, c.industry,
               (SELECT COUNT(*) FROM Placement_Drive d WHERE d.company_id = c.company_id) AS drive_count,
               (SELECT COUNT(*) FROM Internship i WHERE i.company_id = c.company_id) AS internship_count
        FROM Company c
        WHERE 1=1
    """
    params = []
    if search:
        sql += " AND (LOWER(c.company_name) LIKE %s OR LOWER(c.industry) LIKE %s)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term])

    sql += " ORDER BY c.company_id ASC;"
    companies = query_all(sql, params)

    for c in companies:
        c["total_roles"] = c["drive_count"] + c["internship_count"]
        style = get_company_style(c["name"])
        c["initial"] = style["initial"]
        c["color"] = style["color"]

    return jsonify(serialize_item(companies))


@app.route("/api/companies", methods=["POST"])
def add_company():
    """Adds a new company to MySQL and syncs to MongoDB."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    website = data.get("website", "").strip() or None
    industry = data.get("industry", "").strip()

    if not name:
        return jsonify({"error": "Company name is required."}), 400
    if not industry:
        return jsonify({"error": "Industry is required."}), 400

    try:
        res = execute_sql("""
            INSERT INTO Company (company_name, website, industry)
            VALUES (%s, %s, %s);
        """, (name, website, industry))
        company_id = res["last_insert_id"]
        sync_company_doc(company_id, name, industry)
        return jsonify({
            "message": "Company created successfully.",
            "company": {"id": company_id, "name": name, "website": website, "industry": industry}
        }), 201
    except pymysql.err.IntegrityError as e:
        return jsonify({"error": "A company with this name or website already exists."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/companies/<int:company_id>", methods=["PUT"])
def update_company(company_id):
    """Updates company details in MySQL and MongoDB."""
    company = query_one("SELECT * FROM Company WHERE company_id = %s;", (company_id,))
    if not company:
        return jsonify({"error": "Company not found."}), 404

    data = request.get_json() or {}
    name = data.get("name", company["company_name"]).strip()
    website = data.get("website", company["website"])
    industry = data.get("industry", company["industry"]).strip()

    try:
        execute_sql("""
            UPDATE Company
            SET company_name = %s, website = %s, industry = %s
            WHERE company_id = %s;
        """, (name, website, industry, company_id))
        sync_company_doc(company_id, name, industry)
        return jsonify({"message": "Company updated successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/companies/<int:company_id>", methods=["DELETE"])
def delete_company(company_id):
    """Deletes a company from MySQL and MongoDB if no drives/internships exist."""
    company = query_one("SELECT * FROM Company WHERE company_id = %s;", (company_id,))
    if not company:
        return jsonify({"error": "Company not found."}), 404

    drives = query_one("SELECT COUNT(*) AS c FROM Placement_Drive WHERE company_id = %s;", (company_id,))["c"]
    interns = query_one("SELECT COUNT(*) AS c FROM Internship WHERE company_id = %s;", (company_id,))["c"]
    if drives > 0 or interns > 0:
        return jsonify({"error": f"Cannot delete '{company['company_name']}' because it has active placement drives or internships."}), 400

    try:
        execute_sql("DELETE FROM Company WHERE company_id = %s;", (company_id,))
        delete_company_doc(company_id)
        return jsonify({"message": "Company deleted successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# PLACEMENT DRIVES API
# ---------------------------------------------------------------------------

@app.route("/api/drives", methods=["GET"])
def get_drives():
    """Lists all placement drives with company info and eligibility."""
    search = request.args.get("search", "").strip().lower()
    sort_by = request.args.get("sort", "date")

    sql = """
        SELECT d.drive_id AS id, d.drive_name AS name, d.job_role AS role,
               d.min_cgpa AS cgpa, d.package_lpa AS package, d.drive_date AS date,
               c.company_id, c.company_name AS company, c.website
        FROM Placement_Drive d
        JOIN Company c ON d.company_id = c.company_id
        WHERE 1=1
    """
    params = []
    if search:
        sql += " AND (LOWER(d.drive_name) LIKE %s OR LOWER(d.job_role) LIKE %s OR LOWER(c.company_name) LIKE %s)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term])

    if sort_by == "package":
        sql += " ORDER BY d.package_lpa DESC, d.drive_date ASC;"
    else:
        sql += " ORDER BY d.drive_date ASC;"

    drives = query_all(sql, params)
    for d in drives:
        style = get_company_style(d["company"])
        d["initial"] = style["initial"]
        d["color"] = style["color"]

    return jsonify(serialize_item(drives))


@app.route("/api/drives", methods=["POST"])
def add_drive():
    """Creates a new placement drive."""
    data = request.get_json() or {}
    company_id = data.get("company_id")
    drive_name = data.get("name", "").strip()
    role = data.get("role", "").strip()
    min_cgpa = data.get("cgpa", 0.0)
    package = data.get("package")
    drive_date = data.get("date")

    if not company_id or not drive_name or not role or package is None or not drive_date:
        return jsonify({"error": "All drive fields (company, name, role, package, date) are required."}), 400

    try:
        min_cgpa = float(min_cgpa)
        package = float(package)
        if package <= 0:
            return jsonify({"error": "Package LPA must be greater than 0."}), 400
        if not (0.0 <= min_cgpa <= 10.0):
            return jsonify({"error": "Minimum CGPA must be between 0 and 10."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numerical values for CGPA or package."}), 400

    try:
        res = execute_sql("""
            INSERT INTO Placement_Drive (company_id, drive_name, job_role, min_cgpa, package_lpa, drive_date)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (company_id, drive_name, role, min_cgpa, package, drive_date))
        return jsonify({"message": "Placement drive created successfully.", "drive_id": res["last_insert_id"]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/drives/<int:drive_id>", methods=["PUT"])
def update_drive(drive_id):
    """Updates a placement drive."""
    drive = query_one("SELECT * FROM Placement_Drive WHERE drive_id = %s;", (drive_id,))
    if not drive:
        return jsonify({"error": "Placement drive not found."}), 404

    data = request.get_json() or {}
    name = data.get("name", drive["drive_name"]).strip()
    role = data.get("role", drive["job_role"]).strip()
    cgpa = float(data.get("cgpa", drive["min_cgpa"]))
    package = float(data.get("package", drive["package_lpa"]))
    drive_date = data.get("date", str(drive["drive_date"]))

    try:
        execute_sql("""
            UPDATE Placement_Drive
            SET drive_name = %s, job_role = %s, min_cgpa = %s, package_lpa = %s, drive_date = %s
            WHERE drive_id = %s;
        """, (name, role, cgpa, package, drive_date, drive_id))
        return jsonify({"message": "Drive updated successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/drives/<int:drive_id>", methods=["DELETE"])
def delete_drive(drive_id):
    """Deletes a placement drive."""
    drive = query_one("SELECT * FROM Placement_Drive WHERE drive_id = %s;", (drive_id,))
    if not drive:
        return jsonify({"error": "Placement drive not found."}), 404

    try:
        # Check if there are applications
        apps = query_all("SELECT application_id FROM Application WHERE drive_id = %s;", (drive_id,))
        for a in apps:
            execute_sql("DELETE FROM Placement WHERE application_id = %s;", (a["application_id"],))
            execute_sql("DELETE FROM Application_Audit WHERE application_id = %s;", (a["application_id"],))
        execute_sql("DELETE FROM Application WHERE drive_id = %s;", (drive_id,))
        execute_sql("DELETE FROM Placement_Drive WHERE drive_id = %s;", (drive_id,))
        return jsonify({"message": "Placement drive deleted successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# INTERNSHIPS API
# ---------------------------------------------------------------------------

@app.route("/api/internships", methods=["GET"])
def get_internships():
    """Lists all internship opportunities."""
    sql = """
        SELECT i.internship_id AS id, i.internship_role AS role, i.min_cgpa AS cgpa,
               i.stipend_monthly AS stipend, i.start_date AS date,
               c.company_id, c.company_name AS company, c.website
        FROM Internship i
        JOIN Company c ON i.company_id = c.company_id
        ORDER BY i.start_date ASC;
    """
    internships = query_all(sql)
    for item in internships:
        style = get_company_style(item["company"])
        item["initial"] = style["initial"]
        item["color"] = style["color"]

    return jsonify(serialize_item(internships))


@app.route("/api/internships", methods=["POST"])
def add_internship():
    """Creates a new internship opportunity."""
    data = request.get_json() or {}
    company_id = data.get("company_id")
    role = data.get("role", "").strip()
    min_cgpa = data.get("cgpa", 0.0)
    stipend = data.get("stipend", 0.0)
    start_date = data.get("date")

    if not company_id or not role or not start_date:
        return jsonify({"error": "Company, role, and start date are required."}), 400

    try:
        min_cgpa = float(min_cgpa)
        stipend = float(stipend)
        if stipend < 0 or not (0.0 <= min_cgpa <= 10.0):
            return jsonify({"error": "Invalid stipend or minimum CGPA."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numerical values."}), 400

    try:
        res = execute_sql("""
            INSERT INTO Internship (company_id, internship_role, min_cgpa, stipend_monthly, start_date)
            VALUES (%s, %s, %s, %s, %s);
        """, (company_id, role, min_cgpa, stipend, start_date))
        return jsonify({"message": "Internship created successfully.", "internship_id": res["last_insert_id"]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/internships/<int:internship_id>", methods=["PUT"])
def update_internship(internship_id):
    """Updates an internship."""
    internship = query_one("SELECT * FROM Internship WHERE internship_id = %s;", (internship_id,))
    if not internship:
        return jsonify({"error": "Internship not found."}), 404

    data = request.get_json() or {}
    role = data.get("role", internship["internship_role"]).strip()
    cgpa = float(data.get("cgpa", internship["min_cgpa"]))
    stipend = float(data.get("stipend", internship["stipend_monthly"]))
    start_date = data.get("date", str(internship["start_date"]))

    try:
        execute_sql("""
            UPDATE Internship
            SET internship_role = %s, min_cgpa = %s, stipend_monthly = %s, start_date = %s
            WHERE internship_id = %s;
        """, (role, cgpa, stipend, start_date, internship_id))
        return jsonify({"message": "Internship updated successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/internships/<int:internship_id>", methods=["DELETE"])
def delete_internship(internship_id):
    """Deletes an internship."""
    internship = query_one("SELECT * FROM Internship WHERE internship_id = %s;", (internship_id,))
    if not internship:
        return jsonify({"error": "Internship not found."}), 404

    try:
        apps = query_all("SELECT application_id FROM Application WHERE internship_id = %s;", (internship_id,))
        for a in apps:
            execute_sql("DELETE FROM Placement WHERE application_id = %s;", (a["application_id"],))
            execute_sql("DELETE FROM Application_Audit WHERE application_id = %s;", (a["application_id"],))
        execute_sql("DELETE FROM Application WHERE internship_id = %s;", (internship_id,))
        execute_sql("DELETE FROM Internship WHERE internship_id = %s;", (internship_id,))
        return jsonify({"message": "Internship deleted successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# APPLICATION TRACKER API (Demonstrates SQL Triggers check_eligibility & track_application_status)
# ---------------------------------------------------------------------------

@app.route("/api/applications", methods=["GET"])
def get_applications():
    """Lists applications with student and company/role information."""
    search = request.args.get("search", "").strip().lower()
    status = request.args.get("status", "").strip()

    sql = """
        SELECT a.application_id AS id, a.student_id AS student, s.student_name, s.email,
               a.status, a.application_date AS date,
               COALESCE(cd.company_name, ci.company_name) AS company,
               COALESCE(d.job_role, i.internship_role) AS role,
               d.package_lpa AS package, i.stipend_monthly AS stipend,
               a.drive_id, a.internship_id
        FROM Application a
        JOIN Student s ON a.student_id = s.student_id
        LEFT JOIN Placement_Drive d ON a.drive_id = d.drive_id
        LEFT JOIN Company cd ON d.company_id = cd.company_id
        LEFT JOIN Internship i ON a.internship_id = i.internship_id
        LEFT JOIN Company ci ON i.company_id = ci.company_id
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND a.status = %s"
        params.append(status)
    if search:
        sql += " AND (LOWER(s.student_name) LIKE %s OR LOWER(COALESCE(cd.company_name, ci.company_name)) LIKE %s OR LOWER(COALESCE(d.job_role, i.internship_role)) LIKE %s)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term])

    sql += " ORDER BY a.application_id DESC;"
    rows = query_all(sql, params)

    # Format dates nicely as "08 Nov 2026"
    for r in rows:
        if r.get("date"):
            try:
                r["date_display"] = r["date"].strftime("%d %b %Y")
            except Exception:
                r["date_display"] = str(r["date"])

    return jsonify(serialize_item(rows))


@app.route("/api/applications", methods=["POST"])
def submit_application():
    """
    Submits a new application.
    Executes INSERT on Application table in MySQL.
    NOTE: MySQL Trigger 'check_eligibility' automatically verifies if student CGPA >= min_cgpa.
    If not, MySQL throws SQLSTATE 45000: 'Student is not eligible due to low CGPA'.
    """
    data = request.get_json() or {}
    student_id = data.get("student_id")
    drive_id = data.get("drive_id")
    internship_id = data.get("internship_id")

    if not student_id:
        return jsonify({"error": "Student ID is required."}), 400
    if not drive_id and not internship_id:
        return jsonify({"error": "Must apply to either a placement drive or an internship."}), 400
    if drive_id and internship_id:
        return jsonify({"error": "Cannot apply to both a drive and an internship in one application."}), 400

    student = query_one("SELECT * FROM Student WHERE student_id = %s;", (student_id,))
    if not student:
        return jsonify({"error": "Student not found."}), 404

    # Execute insert in MySQL (Triggers check_eligibility and unique index uq_student_drive/internship)
    try:
        res = execute_sql("""
            INSERT INTO Application (student_id, drive_id, internship_id, application_date, status)
            VALUES (%s, %s, %s, CURDATE(), 'Applied');
        """, (student_id, drive_id or None, internship_id or None))
        app_id = res["last_insert_id"]
    except pymysql.err.OperationalError as e:
        err_msg = str(e)
        if "Student is not eligible due to low CGPA" in err_msg:
            return jsonify({"error": "Trigger validation failed: Student is not eligible due to low CGPA."}), 400
        return jsonify({"error": f"Database error: {err_msg}"}), 400
    except pymysql.err.IntegrityError as e:
        err_msg = str(e)
        if "uq_student_drive" in err_msg or "uq_student_internship" in err_msg or "Duplicate entry" in err_msg:
            return jsonify({"error": "This student has already applied for this opportunity."}), 400
        return jsonify({"error": f"Constraint error: {err_msg}"}), 400
    except Exception as e:
        err_msg = str(e)
        if "Student is not eligible due to low CGPA" in err_msg:
            return jsonify({"error": "Trigger validation failed: Student is not eligible due to low CGPA."}), 400
        return jsonify({"error": err_msg}), 500

    # Sync to MongoDB
    try:
        if drive_id:
            drive_info = query_one("""
                SELECT d.job_role, d.package_lpa, c.company_name
                FROM Placement_Drive d
                JOIN Company c ON d.company_id = c.company_id
                WHERE d.drive_id = %s;
            """, (drive_id,))
            sync_application_doc(
                application_id=app_id,
                student_id=student_id,
                student_name=student["student_name"],
                company_name=drive_info["company_name"],
                job_role=drive_info["job_role"],
                app_date=date.today(),
                status="Applied",
                package_lpa=drive_info["package_lpa"]
            )
        else:
            intern_info = query_one("""
                SELECT i.internship_role, i.stipend_monthly, c.company_name
                FROM Internship i
                JOIN Company c ON i.company_id = c.company_id
                WHERE i.internship_id = %s;
            """, (internship_id,))
            sync_application_doc(
                application_id=app_id,
                student_id=student_id,
                student_name=student["student_name"],
                company_name=intern_info["company_name"],
                job_role=intern_info["internship_role"],
                app_date=date.today(),
                status="Applied",
                stipend=intern_info["stipend_monthly"]
            )
    except Exception as e:
        print(f"[MongoDB Sync Warning] {e}")

    return jsonify({"message": "Application submitted successfully.", "application_id": app_id}), 201


@app.route("/api/applications/<int:application_id>/status", methods=["PUT"])
def update_application_status(application_id):
    """
    Updates the application status.
    NOTE: MySQL Triggers:
    1. 'track_application_status' fires and inserts into Application_Audit automatically!
    2. 'create_placement' fires if new status is 'Selected', creating a row in Placement
       and updating Student placement_status to 'Placed'!
    """
    data = request.get_json() or {}
    new_status = data.get("status")
    allowed_statuses = ["Applied", "Shortlisted", "Selected", "Rejected"]

    if new_status not in allowed_statuses:
        return jsonify({"error": f"Invalid status. Allowed values: {', '.join(allowed_statuses)}"}), 400

    app_row = query_one("SELECT * FROM Application WHERE application_id = %s;", (application_id,))
    if not app_row:
        return jsonify({"error": "Application not found."}), 404

    try:
        execute_sql("""
            UPDATE Application
            SET status = %s
            WHERE application_id = %s;
        """, (new_status, application_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Sync to MongoDB
    try:
        update_mongo_application_status(application_id, new_status)
    except Exception as e:
        print(f"[MongoDB Sync Warning] {e}")

    return jsonify({
        "message": f"Application status updated to '{new_status}'. SQL triggers executed successfully.",
        "application_id": application_id,
        "new_status": new_status
    })


@app.route("/api/applications/audit", methods=["GET"])
def get_audit_trail():
    """Returns the entire audit log created by MySQL Trigger 'track_application_status'."""
    rows = query_all("""
        SELECT a.audit_id, a.application_id, a.old_status, a.new_status, a.changed_at,
               s.student_name, s.student_id,
               COALESCE(cd.company_name, ci.company_name) AS company_name,
               COALESCE(d.job_role, i.internship_role) AS role
        FROM Application_Audit a
        JOIN Application app ON a.application_id = app.application_id
        JOIN Student s ON app.student_id = s.student_id
        LEFT JOIN Placement_Drive d ON app.drive_id = d.drive_id
        LEFT JOIN Company cd ON d.company_id = cd.company_id
        LEFT JOIN Internship i ON app.internship_id = i.internship_id
        LEFT JOIN Company ci ON i.company_id = ci.company_id
        ORDER BY a.changed_at DESC;
    """)
    return jsonify(serialize_item(rows))


# ---------------------------------------------------------------------------
# PLACEMENTS API
# ---------------------------------------------------------------------------

@app.route("/api/placements", methods=["GET"])
def get_placements():
    """Lists all confirmed placements from Placement table."""
    placements = query_all("""
        SELECT p.placement_id AS id, p.application_id, p.student_id,
               s.student_name, s.department AS dept, s.cgpa,
               c.company_name AS company,
               COALESCE(d.job_role, i.internship_role) AS role,
               p.package_lpa AS package, p.offer_date AS date
        FROM Placement p
        JOIN Student s ON p.student_id = s.student_id
        JOIN Company c ON p.company_id = c.company_id
        LEFT JOIN Placement_Drive d ON p.drive_id = d.drive_id
        LEFT JOIN Internship i ON p.internship_id = i.internship_id
        ORDER BY p.offer_date DESC;
    """)
    for item in placements:
        if item.get("date"):
            try:
                item["date_display"] = item["date"].strftime("%d %b %Y")
            except Exception:
                item["date_display"] = str(item["date"])

    return jsonify(serialize_item(placements))


# ---------------------------------------------------------------------------
# DBMS ACADEMIC SHOWCASE API (MySQL 15 Queries & MongoDB Aggregations)
# ---------------------------------------------------------------------------

SQL_QUERIES_METADATA = [
    {"id": "q1", "title": "Q1. Display all students", "sql": "SELECT * FROM Student;"},
    {"id": "q2", "title": "Q2. Display students with CGPA > 8.00", "sql": "SELECT student_id, student_name, cgpa FROM Student WHERE cgpa > 8.00;"},
    {"id": "q3", "title": "Q3. Display all companies", "sql": "SELECT * FROM Company;"},
    {"id": "q4", "title": "Q4. Placement drives with company names", "sql": "SELECT d.drive_id, d.drive_name, c.company_name, d.job_role, d.min_cgpa, d.package_lpa FROM Placement_Drive d JOIN Company c ON d.company_id = c.company_id;"},
    {"id": "q5", "title": "Q5. Student applications and statuses", "sql": "SELECT a.application_id, s.student_name, a.status, a.application_date FROM Application a JOIN Student s ON a.student_id = s.student_id;"},
    {"id": "q6", "title": "Q6. Count students in each department", "sql": "SELECT department, COUNT(*) AS total_students FROM Student GROUP BY department;"},
    {"id": "q7", "title": "Q7. Find average CGPA across all students", "sql": "SELECT AVG(cgpa) AS average_cgpa FROM Student;"},
    {"id": "q8", "title": "Q8. Find highest package offered in drives", "sql": "SELECT MAX(package_lpa) AS highest_package FROM Placement_Drive;"},
    {"id": "q9", "title": "Q9. Display students who know SQL", "sql": "SELECT s.student_id, s.student_name FROM Student s JOIN Student_Skill ss ON s.student_id = ss.student_id JOIN Skill sk ON ss.skill_id = sk.skill_id WHERE sk.skill_name = 'SQL';"},
    {"id": "q10", "title": "Q10. Count applications for each status", "sql": "SELECT status, COUNT(*) AS total_applications FROM Application GROUP BY status;"},
    {"id": "q11", "title": "Q11. Display selected students & placement details", "sql": "SELECT s.student_name, c.company_name, p.package_lpa, p.offer_date FROM Placement p JOIN Student s ON p.student_id = s.student_id JOIN Company c ON p.company_id = c.company_id;"},
    {"id": "q12", "title": "Q12. Students with CGPA above overall average (Subquery)", "sql": "SELECT student_name, cgpa FROM Student WHERE cgpa > (SELECT AVG(cgpa) FROM Student);"},
    {"id": "q13", "title": "Q13. Display application audit change history", "sql": "SELECT * FROM Application_Audit ORDER BY changed_at DESC;"},
    {"id": "q14", "title": "Q14. Placement drives offering > 5 LPA, highest first", "sql": "SELECT drive_name, job_role, package_lpa FROM Placement_Drive WHERE package_lpa > 5 ORDER BY package_lpa DESC;"},
    {"id": "q15", "title": "Q15. Display students who have not yet been placed", "sql": "SELECT student_id, student_name FROM Student WHERE placement_status = 'Not Placed';"}
]

@app.route("/api/dbms/sql-queries", methods=["GET"])
def run_academic_sql_queries():
    """Runs all 15 academic SQL queries from mysql_student_placement.sql and returns live results."""
    results = []
    for q in SQL_QUERIES_METADATA:
        try:
            data = query_all(q["sql"])
            results.append({
                "id": q["id"],
                "title": q["title"],
                "sql": q["sql"],
                "status": "success",
                "row_count": len(data),
                "data": serialize_item(data)
            })
        except Exception as e:
            results.append({
                "id": q["id"],
                "title": q["title"],
                "sql": q["sql"],
                "status": "error",
                "error": str(e)
            })
    return jsonify(results)


@app.route("/api/dbms/mongo-queries", methods=["GET"])
def run_academic_mongo_queries():
    """Executes the exact MongoDB CRUD and Aggregation operations from mongodb_student_placement.js."""
    db = get_mongo_db()
    results = []

    try:
        # 1. Display all students
        r1 = list(db.students.find({}, {"_id": 0}))
        results.append({
            "id": "m1",
            "title": "1. db.students.find()",
            "type": "find",
            "description": "Display all student documents",
            "data": clean_doc(r1)
        })

        # 2. Find students with CGPA > 8
        r2 = list(db.students.find({"cgpa": {"$gt": 8}}, {"_id": 0}))
        results.append({
            "id": "m2",
            "title": "2. db.students.find({ cgpa: { $gt: 8 } })",
            "type": "find",
            "description": "Find students with CGPA greater than 8",
            "data": clean_doc(r2)
        })

        # 3. Find students from CSE department
        r3 = list(db.students.find({"department": "CSE"}, {"_id": 0}))
        results.append({
            "id": "m3",
            "title": "3. db.students.find({ department: 'CSE' })",
            "type": "find",
            "description": "Find students from CSE department",
            "data": clean_doc(r3)
        })

        # 4. Find students who know SQL
        r4 = list(db.students.find({"skills.name": "SQL"}, {"_id": 0}))
        results.append({
            "id": "m4",
            "title": "4. db.students.find({ 'skills.name': 'SQL' })",
            "type": "find",
            "description": "Find students who know SQL",
            "data": clean_doc(r4)
        })

        # 5. Aggregation: Count students in each department
        r5 = list(db.students.aggregate([
            {"$group": {"_id": "$department", "total_students": {"$sum": 1}}},
            {"$sort": {"total_students": -1}}
        ]))
        results.append({
            "id": "m5",
            "title": "8. db.students.aggregate([{ $group: { _id: '$department', total_students: { $sum: 1 } } }])",
            "type": "aggregation",
            "description": "Count students in each department",
            "data": clean_doc(r5)
        })

        # 6. Aggregation: Average CGPA by department
        r6 = list(db.students.aggregate([
            {"$group": {"_id": "$department", "average_cgpa": {"$avg": "$cgpa"}}}
        ]))
        results.append({
            "id": "m6",
            "title": "9. db.students.aggregate([{ $group: { _id: '$department', average_cgpa: { $avg: '$cgpa' } } }])",
            "type": "aggregation",
            "description": "Find average CGPA by department",
            "data": clean_doc(r6)
        })

        # 7. Aggregation: Count applications by status
        r7 = list(db.applications.aggregate([
            {"$group": {"_id": "$status", "total": {"$sum": 1}}}
        ]))
        results.append({
            "id": "m7",
            "title": "10. db.applications.aggregate([{ $group: { _id: '$status', total: { $sum: 1 } } }])",
            "type": "aggregation",
            "description": "Count applications by status",
            "data": clean_doc(r7)
        })

        # 8. Find applications with package > 4 LPA
        r8 = list(db.applications.find({"package_lpa": {"$gt": 4}}, {"_id": 0}))
        results.append({
            "id": "m8",
            "title": "11. db.applications.find({ package_lpa: { $gt: 4 } })",
            "type": "find",
            "description": "Applications with package greater than 4 LPA",
            "data": clean_doc(r8)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(results)


# ---------------------------------------------------------------------------
# APPLICATION ENTRYPOINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    print(f"\n=======================================================")
    print(f"  PLACEWISE - Student Placement Management System")
    print(f"  Starting Flask server on http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)

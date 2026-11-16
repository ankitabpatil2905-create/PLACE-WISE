// PLACEWISE — STUDENT PLACEMENT MANAGEMENT SYSTEM
// Full Database-Driven Frontend integrated with Flask (MySQL & MongoDB)

const API_BASE = "https://place-wise.onrender.com";

let state = {
  students: [],
  companies: [],
  drives: [],
  internships: [],
  applications: [],
  placements: [],
  overview: null,
  dbmsSql: [],
  dbmsMongo: [],
  auditLogs: [],
  accounts: []
};

// Current active session / profile
let currentUser = JSON.parse(localStorage.getItem("placewise_user") || "null") || {
  student_id: 101,
  name: "Ananya Rao",
  email: "ananya@example.com",
  role: "Student",
  dept: "CSE",
  cgpa: 9.20
};

const $ = s => document.querySelector(s);
const initials = name => name ? name.split(" ").map(x => x[0]).join("").slice(0, 2).toUpperCase() : "PW";
const dateFmt = d => {
  if (!d) return "—";
  try {
    const dt = new Date(d.includes("T") ? d : d + "T00:00:00");
    return dt.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch (e) {
    return d;
  }
};

function statusPill(status) {
  const st = (status || "applied").toLowerCase();
  return `<span class="status ${st}">${status}</span>`;
}

function companyLogo(name, color = "", initial = "") {
  const init = initial || (name ? name[0] : "C");
  return `<div class="company-logo ${color}">${init}</div>`;
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2800);
}

function openModal(html) {
  $("#modalContent").innerHTML = html;
  $("#modalBackdrop").classList.add("show");
}

function closeModal() {
  $("#modalBackdrop").classList.remove("show");
}

// ---------------------------------------------------------------------------
// USER SESSION & AUTHENTICATION
// ---------------------------------------------------------------------------

function renderUserSession() {
  const init = initials(currentUser.name);
  if ($("#sidebarAvatar")) $("#sidebarAvatar").textContent = init;
  if ($("#sidebarName")) $("#sidebarName").textContent = currentUser.name;
  if ($("#sidebarRole")) $("#sidebarRole").textContent = currentUser.role === "Admin" ? "Placement Officer" : `${currentUser.dept || "Student"} account`;
  if ($("#topAvatar")) $("#topAvatar").textContent = init;
  if ($("#topAuthBtn")) $("#topAuthBtn").textContent = currentUser ? "Switch / Sign Out" : "Sign In";

  if ($("#welcomeHeading")) {
    const firstName = currentUser.name.split(" ")[0];
    $("#welcomeHeading").innerHTML = `Good afternoon, ${firstName} <span>✦</span>`;
  }
}

async function fetchAccounts() {
  try {
    const data = await apiRequest("/api/auth/accounts");
    state.accounts = data;
  } catch (e) {}
}

function openAuthModal() {
  openModal(`
    <h2>Account Sign In & Switcher</h2>
    <p>Sign in with your email or select any student profile to test the application modules.</p>
    
    <div style="margin:16px 0;">
      <label style="display:block;font-size:10px;font-weight:700;color:#666a7a;margin-bottom:8px;">QUICK SWITCH DEMO PROFILES</label>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;" id="quickProfilesGrid">
        <button class="outline-btn" style="text-align:left;padding:8px;" onclick="quickLogin('ananya@example.com', 'student123')">
          <b>Ananya Rao (101)</b><br><small style="color:#1c9b70;">Placed · 9.20 CGPA (CSE)</small>
        </button>
        <button class="outline-btn" style="text-align:left;padding:8px;" onclick="quickLogin('rahul@example.com', 'student123')">
          <b>Rahul Kumar (102)</b><br><small style="color:#85899a;">Not Placed · 8.10 CGPA (ISE)</small>
        </button>
        <button class="outline-btn" style="text-align:left;padding:8px;" onclick="quickLogin('meera@example.com', 'student123')">
          <b>Meera Nair (103)</b><br><small style="color:#85899a;">Not Placed · 7.40 CGPA (ECE)</small>
        </button>
        <button class="outline-btn" style="text-align:left;padding:8px;" onclick="quickLogin('pooja@example.com', 'student123')">
          <b>Pooja Das (105)</b><br><small style="color:#e9946c;">Not Placed · 6.90 CGPA (AIML)</small>
        </button>
        <button class="outline-btn" style="text-align:left;padding:8px;grid-column:span 2;" onclick="quickLogin('admin@placewise.com', 'admin123')">
          <b>Placement Officer (Admin)</b><br><small style="color:#6657df;">Full administrative access</small>
        </button>
      </div>
    </div>

    <hr style="border:0;border-top:1px solid #f0f0f4;margin:18px 0;" />

    <div style="display:flex;gap:10px;margin-bottom:12px;">
      <button class="sub-tab-btn active" id="authTabLogin" style="flex:1;">Sign In</button>
      <button class="sub-tab-btn" id="authTabRegister" style="flex:1;">Register Student</button>
    </div>

    <div id="authLoginForm">
      <div class="form-row">
        <label>Email Address</label>
        <input id="loginEmail" type="email" placeholder="name@example.com" value="${currentUser ? currentUser.email : ''}" />
      </div>
      <div class="form-row">
        <label>Password</label>
        <input id="loginPassword" type="password" placeholder="••••••••" value="student123" />
      </div>
      <button class="primary-btn" id="submitLoginBtn" style="margin-top:10px;">Sign In <span>→</span></button>
    </div>

    <div id="authRegisterForm" style="display:none;">
      <div class="form-row">
        <label>Full Name</label>
        <input id="regName" placeholder="e.g. Shruti Sharma" />
      </div>
      <div class="form-grid-2">
        <div class="form-row">
          <label>Email</label>
          <input id="regEmail" type="email" placeholder="shruti@example.com" />
        </div>
        <div class="form-row">
          <label>Password</label>
          <input id="regPassword" type="password" placeholder="Min 4 chars" value="student123" />
        </div>
      </div>
      <div class="form-grid-2">
        <div class="form-row">
          <label>Department</label>
          <select id="regDept">
            <option>CSE</option>
            <option>ISE</option>
            <option>ECE</option>
            <option>AIML</option>
          </select>
        </div>
        <div class="form-row">
          <label>CGPA</label>
          <input id="regCgpa" type="number" step="0.01" min="0" max="10" value="8.50" />
        </div>
      </div>
      <div class="form-row">
        <label>Technical Skills</label>
        <input id="regSkills" value="Python, SQL" />
      </div>
      <button class="primary-btn" id="submitRegisterBtn" style="margin-top:10px;">Create Account <span>→</span></button>
    </div>
  `);

  $("#authTabLogin").onclick = () => {
    $("#authTabLogin").classList.add("active");
    $("#authTabRegister").classList.remove("active");
    $("#authLoginForm").style.display = "block";
    $("#authRegisterForm").style.display = "none";
  };

  $("#authTabRegister").onclick = () => {
    $("#authTabRegister").classList.add("active");
    $("#authTabLogin").classList.remove("active");
    $("#authRegisterForm").style.display = "block";
    $("#authLoginForm").style.display = "none";
  };

  $("#submitLoginBtn").onclick = async () => {
    const email = $("#loginEmail").value.trim();
    const password = $("#loginPassword").value.trim();
    if (!email || !password) {
      toast("Please enter your email and password.");
      return;
    }
    await loginUser(email, password);
  };

  $("#submitRegisterBtn").onclick = async () => {
    const name = $("#regName").value.trim();
    const email = $("#regEmail").value.trim();
    const password = $("#regPassword").value.trim();
    const dept = $("#regDept").value;
    const cgpa = Number($("#regCgpa").value);
    const skillsRaw = $("#regSkills").value.trim();
    const skills = skillsRaw.split(",").map(x => x.trim()).filter(Boolean);

    if (!name || !email || !password) {
      toast("Please fill in required fields.");
      return;
    }

    try {
      const res = await apiRequest("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ name, email, password, dept, cgpa, skills })
      });
      toast("Account registered successfully!");
      currentUser = res.user;
      localStorage.setItem("placewise_user", JSON.stringify(currentUser));
      closeModal();
      renderUserSession();
      await loadAllData();
      showPage("student-dashboard");
    } catch (e) {
      toast(e.message);
    }
  };
}

async function quickLogin(email, password) {
  await loginUser(email, password);
}

async function loginUser(email, password) {
  try {
    const res = await apiRequest("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    currentUser = res.user;
    if (res.user.student) {
      currentUser.student_id = res.user.student.student_id;
      currentUser.dept = res.user.student.department;
      currentUser.cgpa = res.user.student.cgpa;
      currentUser.placement_status = res.user.student.placement_status;
    }
    localStorage.setItem("placewise_user", JSON.stringify(currentUser));
    toast(`Signed in as ${currentUser.name}`);
    closeModal();
    renderUserSession();
    await loadAllData();
    if (currentUser.role === "Student") {
      showPage("student-dashboard");
    } else {
      showPage("overview");
    }
  } catch (e) {
    toast(e.message);
  }
}

// ---------------------------------------------------------------------------
// DATA FETCHING & SYNCHRONIZATION
// ---------------------------------------------------------------------------

async function apiRequest(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || `HTTP error ${res.status}`);
    }
    return data;
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

async function loadAllData() {
  try {
    checkHealth();
    await Promise.all([
      fetchOverview(),
      fetchStudents(),
      fetchDrives(),
      fetchInternships(),
      fetchApplications(),
      fetchPlacements(),
      fetchCompanies(),
      fetchAccounts()
    ]);
    renderUserSession();
  } catch (err) {
    console.error("Initialization error:", err);
  }
}

async function checkHealth() {
  try {
    const data = await apiRequest("/api/health");
    const badge = $("#dbStatusBadge");
    const dot = $("#dbStatusDot");
    const text = $("#dbStatusText");
    if (data.status === "healthy" || data.mysql?.status === "connected") {
      dot.className = "dot green-dot";
      text.textContent = "MySQL & Mongo Live";
      badge.title = `MySQL: ${data.mysql.database} | Mongo: ${data.mongodb.mode}`;
    } else {
      dot.className = "dot gray-dot";
      text.textContent = "Database Offline";
    }
  } catch (e) {
    $("#dbStatusDot").className = "dot gray-dot";
    $("#dbStatusText").textContent = "API Offline";
  }
}

// ---------------------------------------------------------------------------
// OVERVIEW SCREEN
// ---------------------------------------------------------------------------

async function fetchOverview() {
  try {
    const data = await apiRequest("/api/overview");
    state.overview = data;
    renderOverview();
  } catch (e) {}
}

function renderOverview() {
  if (!state.overview) return;
  const o = state.overview;

  $("#statTotalStudents").textContent = o.total_students;
  $("#statActiveOpps").textContent = o.active_opportunities;
  $("#statDrivesSub").textContent = `${o.total_drives} drives`;
  $("#statInternsSub").textContent = `${o.total_internships} internships`;
  $("#statTotalApps").textContent = o.total_applications;
  $("#statShortlistedSub").textContent = `${o.status_counts["Shortlisted"] || 0} shortlisted`;
  $("#statPlacedStudents").textContent = o.placed_students;
  $("#statPlacementRate").textContent = `${o.placement_rate}%`;

  $("#snapshotRate").textContent = `${o.placement_rate}%`;
  $("#snapshotRatio").textContent = `${o.placed_students} of ${o.total_students}`;
  $("#snapshotBar").style.width = `${Math.min(o.placement_rate, 100)}%`;
  $("#snapshotPlacedCount").textContent = o.placed_students;
  $("#snapshotNotPlacedCount").textContent = o.not_placed_students;

  // Featured drives
  const drivesList = o.featured_drives || [];
  $("#featuredDrives").innerHTML = drivesList.length
    ? drivesList.map(d => `
        <div class="opportunity">
          ${companyLogo(d.company, d.color, d.initial)}
          <div class="opp-main">
            <b>${d.role}</b>
            <small>${d.company} · ${dateFmt(d.date)}</small>
          </div>
          <div class="opp-meta">
            <b>${Number(d.package).toFixed(2)} LPA</b>
            <small>Package</small>
          </div>
        </div>
      `).join("")
    : `<div class="empty">No upcoming placement drives.</div>`;

  // Recent activity
  const activityList = o.recent_activity || [];
  $("#recentActivity").innerHTML = activityList.length
    ? activityList.map(a => `
        <div class="activity">
          <i class="activity-dot"></i>
          <div style="flex:1">
            <b>${a.student_name} · ${a.company_name}</b>
            <small>Status changed from <em>${a.old_status}</em> to <b>${a.new_status}</b> <span style="float:right">${dateFmt(a.changed_at)}</span></small>
            <div style="margin-top:7px">${statusPill(a.new_status)}</div>
          </div>
        </div>
      `).join("")
    : `<div class="activity"><i class="activity-dot"></i><div><b>No status changes recorded yet.</b><small>Updates will appear here via MySQL triggers.</small></div></div>`;
}

// ---------------------------------------------------------------------------
// PERSONALIZED STUDENT DASHBOARD
// ---------------------------------------------------------------------------

async function loadStudentDashboard() {
  const studentId = currentUser.student_id || 101;
  try {
    const data = await apiRequest(`/api/student/dashboard/${studentId}`);
    renderStudentDashboard(data);
  } catch (e) {
    toast("Failed to load student dashboard.");
  }
}

function renderStudentDashboard(data) {
  const s = data.student;
  $("#sdHeading").textContent = `${s.student_name}’s Dashboard`;
  $("#sdCgpa").textContent = Number(s.cgpa).toFixed(2);
  $("#sdDept").textContent = s.department;
  $("#sdYear").textContent = s.graduation_year;
  $("#sdStatus").textContent = s.placement_status;
  $("#sdStatusSub").textContent = s.placement_status === "Placed" ? "Confirmed Offer" : "Actively Applying";

  $("#sdAppsCount").textContent = data.applications.length;
  $("#sdEligibleCount").textContent = data.eligible_drives_count;

  // Placement Offer Highlight
  const banner = $("#sdPlacementBanner");
  if (s.placement_status === "Placed" && data.placement) {
    banner.style.display = "flex";
    $("#sdOfferCompany").textContent = `${data.placement.company_name} – ${data.placement.role || "Software Engineer"}`;
    $("#sdOfferPackage").textContent = `Annual Package: ${data.placement.package_lpa ? Number(data.placement.package_lpa).toFixed(2) + " LPA" : "Confirmed"} · Offer Date: ${dateFmt(data.placement.offer_date)}`;
  } else {
    banner.style.display = "none";
  }

  // Profile info
  $("#sdProfileId").textContent = s.student_id;
  $("#sdProfileEmail").textContent = s.email;
  $("#sdProfilePhone").textContent = s.phone || "Not specified";
  $("#sdProfileDept").textContent = `${s.department} (Batch ${s.graduation_year})`;

  // Skills chips
  const skillsContainer = $("#sdSkillsChips");
  skillsContainer.innerHTML = (data.skills || []).map(sk => `
    <span class="skill-chip" style="font-size:10px;padding:5px 8px;">
      ${sk.name} <small style="color:#6657df;font-weight:700;">(${sk.proficiency})</small>
    </span>
  `).join("") || `<span style="color:#aaa;">No skills added yet.</span>`;

  // Applications list
  const appsList = $("#sdApplicationsList");
  appsList.innerHTML = data.applications.length
    ? data.applications.map(a => `
        <div class="opportunity">
          <div class="opp-main">
            <b>${a.company} – ${a.role}</b>
            <small>Applied on ${dateFmt(a.date)}</small>
          </div>
          <div class="opp-meta">
            ${statusPill(a.status)}
            <small style="display:block;margin-top:4px;">${a.package ? a.package + " LPA" : a.stipend ? "₹" + a.stipend : "—"}</small>
          </div>
        </div>
      `).join("")
    : `<div class="empty">You have not submitted any applications yet.</div>`;

  // Eligible drives
  const eligibleGrid = $("#sdEligibleGrid");
  eligibleGrid.innerHTML = data.eligible_drives.length
    ? data.eligible_drives.slice(0, 3).map(d => `
        <article class="drive-card">
          <div class="drive-card-top">
            ${companyLogo(d.company)}
            <span class="soft-pill">Eligible</span>
          </div>
          <h3>${d.name}</h3>
          <div class="company-name">${d.company}</div>
          <div class="role-name">${d.role}</div>
          <div class="drive-info">
            <div><span>Package</span><b>${Number(d.package).toFixed(2)} LPA</b></div>
            <div><span>Min CGPA</span><b>${Number(d.min_cgpa).toFixed(2)}</b></div>
            <div><span>Drive Date</span><b>${dateFmt(d.date)}</b></div>
            <div><span>Eligible</span><b style="color:#1c9b70;">✓ CGPA ${Number(s.cgpa).toFixed(2)}</b></div>
          </div>
          <div class="card-actions" style="margin-top:12px;">
            <button class="apply-btn" style="width:100%;" onclick="openApplyModal('drive', ${d.id})">Apply now</button>
          </div>
        </article>
      `).join("")
    : `<div class="empty">No matching drives for your CGPA right now.</div>`;
}

// ---------------------------------------------------------------------------
// STUDENTS MANAGEMENT
// ---------------------------------------------------------------------------

async function fetchStudents() {
  const q = ($("#studentSearch")?.value || "").trim();
  const dept = $("#departmentFilter")?.value || "";
  const status = $("#statusFilter")?.value || "";
  const params = new URLSearchParams();
  if (q) params.set("search", q);
  if (dept) params.set("dept", dept);
  if (status) params.set("status", status);

  try {
    const data = await apiRequest(`/api/students?${params.toString()}`);
    state.students = data;
    renderStudents();
  } catch (e) {
    toast("Failed to load students.");
  }
}

function renderStudents() {
  const rows = state.students;
  $("#studentCount").textContent = rows.length;

  $("#studentsTable").innerHTML = rows.length
    ? rows.map(s => `
        <tr>
          <td>
            <div class="student-cell">
              <div class="avatar">${initials(s.name)}</div>
              <div>
                <b>${s.name}</b>
                <small>${s.email} ${s.phone ? `· ${s.phone}` : ""}</small>
              </div>
            </div>
          </td>
          <td>${s.dept}</td>
          <td><b>${Number(s.cgpa).toFixed(2)}</b></td>
          <td>${s.year}</td>
          <td>${(s.skills || []).map(x => `<span class="skill-chip">${x}</span>`).join("")}</td>
          <td>${statusPill(s.status)}</td>
          <td>
            <div class="action-group">
              <button class="action-btn" onclick="openEditStudentModal(${s.id})">Edit</button>
              <button class="action-btn danger" onclick="confirmDeleteStudent(${s.id}, '${s.name}')">Delete</button>
            </div>
          </td>
        </tr>
      `).join("")
    : `<tr><td colspan="7" class="empty">No students match your query.</td></tr>`;
}

function openAddStudentModal() {
  openModal(`
    <h2>Add a student</h2>
    <p>Student record will be stored in MySQL relational tables and synced to MongoDB.</p>
    <div class="form-row">
      <label>Full Name</label>
      <input id="newName" placeholder="e.g. Pooja Das" required />
    </div>
    <div class="form-grid-2">
      <div class="form-row">
        <label>Email Address</label>
        <input id="newEmail" type="email" placeholder="pooja@example.com" required />
      </div>
      <div class="form-row">
        <label>Phone Number</label>
        <input id="newPhone" placeholder="9876543214" />
      </div>
    </div>
    <div class="form-grid-2">
      <div class="form-row">
        <label>Department</label>
        <select id="newDept">
          <option>CSE</option>
          <option>ISE</option>
          <option>ECE</option>
          <option>AIML</option>
        </select>
      </div>
      <div class="form-row">
        <label>Graduation Year</label>
        <input id="newYear" type="number" value="2029" min="2020" max="2035" />
      </div>
    </div>
    <div class="form-row">
      <label>CGPA (0.00 – 10.00)</label>
      <input id="newCgpa" type="number" min="0" max="10" step="0.01" placeholder="e.g. 8.50" required />
    </div>
    <div class="form-row">
      <label>Technical Skills (comma separated)</label>
      <input id="newSkills" placeholder="Python, SQL, MongoDB" value="Python, SQL" />
      <div class="form-hint">Stored in MySQL Skill/Student_Skill & MongoDB skills array</div>
    </div>
    <button class="primary-btn" id="saveStudentBtn">Save to Database <span>→</span></button>
  `);

  $("#saveStudentBtn").onclick = async () => {
    const name = $("#newName").value.trim();
    const email = $("#newEmail").value.trim();
    const phone = $("#newPhone").value.trim();
    const dept = $("#newDept").value;
    const year = Number($("#newYear").value);
    const cgpa = Number($("#newCgpa").value);
    const skillsRaw = $("#newSkills").value.trim();
    const skills = skillsRaw ? skillsRaw.split(",").map(x => x.trim()).filter(Boolean) : [];

    if (!name || !email || !email.includes("@")) {
      toast("Please enter a valid name and email address.");
      return;
    }
    if (isNaN(cgpa) || cgpa < 0 || cgpa > 10) {
      toast("CGPA must be between 0.00 and 10.00.");
      return;
    }

    try {
      await apiRequest("/api/students", {
        method: "POST",
        body: JSON.stringify({ name, email, phone, dept, year, cgpa, skills })
      });
      closeModal();
      toast("Student added to database successfully!");
      await fetchStudents();
      fetchOverview();
    } catch (e) {
      toast(e.message);
    }
  };
}

function openEditStudentModal(id) {
  const s = state.students.find(x => x.id === id);
  if (!s) return;

  openModal(`
    <h2>Edit student details</h2>
    <p>Updating student #${s.id} in MySQL and MongoDB collections.</p>
    <div class="form-row">
      <label>Student Name</label>
      <input id="editName" value="${s.name}" required />
    </div>
    <div class="form-grid-2">
      <div class="form-row">
        <label>Email</label>
        <input id="editEmail" value="${s.email}" required />
      </div>
      <div class="form-row">
        <label>Phone</label>
        <input id="editPhone" value="${s.phone || ""}" />
      </div>
    </div>
    <div class="form-grid-2">
      <div class="form-row">
        <label>Department</label>
        <select id="editDept">
          <option ${s.dept === "CSE" ? "selected" : ""}>CSE</option>
          <option ${s.dept === "ISE" ? "selected" : ""}>ISE</option>
          <option ${s.dept === "ECE" ? "selected" : ""}>ECE</option>
          <option ${s.dept === "AIML" ? "selected" : ""}>AIML</option>
        </select>
      </div>
      <div class="form-row">
        <label>CGPA</label>
        <input id="editCgpa" type="number" min="0" max="10" step="0.01" value="${s.cgpa}" />
      </div>
    </div>
    <div class="form-row">
      <label>Placement Status</label>
      <select id="editStatus">
        <option ${s.status === "Not Placed" ? "selected" : ""}>Not Placed</option>
        <option ${s.status === "Placed" ? "selected" : ""}>Placed</option>
      </select>
    </div>
    <div class="form-row">
      <label>Skills (comma separated)</label>
      <input id="editSkills" value="${(s.skills || []).join(", ")}" />
    </div>
    <button class="primary-btn" id="updateStudentBtn">Update Student <span>→</span></button>
  `);

  $("#updateStudentBtn").onclick = async () => {
    const name = $("#editName").value.trim();
    const email = $("#editEmail").value.trim();
    const phone = $("#editPhone").value.trim();
    const dept = $("#editDept").value;
    const cgpa = Number($("#editCgpa").value);
    const status = $("#editStatus").value;
    const skills = $("#editSkills").value.split(",").map(x => x.trim()).filter(Boolean);

    try {
      await apiRequest(`/api/students/${id}`, {
        method: "PUT",
        body: JSON.stringify({ name, email, phone, dept, cgpa, status, skills })
      });
      closeModal();
      toast("Student updated successfully.");
      await fetchStudents();
      fetchOverview();
    } catch (e) {
      toast(e.message);
    }
  };
}

function confirmDeleteStudent(id, name) {
  openModal(`
    <h2>Delete student</h2>
    <p>Are you sure you want to delete <b>${name}</b> (#${id})? This will remove records from both MySQL and MongoDB.</p>
    <div style="display:flex;gap:10px;margin-top:20px;">
      <button class="outline-btn" style="flex:1" onclick="closeModal()">Cancel</button>
      <button class="primary-btn" style="flex:1;background:#d56c6c" id="deleteConfirmBtn">Yes, Delete</button>
    </div>
  `);

  $("#deleteConfirmBtn").onclick = async () => {
    try {
      await apiRequest(`/api/students/${id}`, { method: "DELETE" });
      closeModal();
      toast("Student deleted successfully.");
      await fetchStudents();
      fetchOverview();
    } catch (e) {
      toast(e.message);
    }
  };
}

// ---------------------------------------------------------------------------
// PLACEMENT DRIVES
// ---------------------------------------------------------------------------

async function fetchDrives() {
  const q = ($("#driveSearch")?.value || "").trim();
  const sort = $("#driveSort")?.value || "date";
  try {
    const data = await apiRequest(`/api/drives?search=${encodeURIComponent(q)}&sort=${sort}`);
    state.drives = data;
    renderDrives();
  } catch (e) {
    toast("Failed to load placement drives.");
  }
}

function renderDrives() {
  $("#driveCount").textContent = state.drives.length;
  $("#driveGrid").innerHTML = state.drives.length
    ? state.drives.map(d => `
        <article class="drive-card">
          <div class="drive-card-top">
            ${companyLogo(d.company, d.color, d.initial)}
            <span class="soft-pill">Placement drive</span>
          </div>
          <h3>${d.name}</h3>
          <div class="company-name">${d.company}</div>
          <div class="role-name">${d.role}</div>
          <div class="drive-info">
            <div><span>Package</span><b>${Number(d.package).toFixed(2)} LPA</b></div>
            <div><span>Minimum CGPA</span><b>${Number(d.cgpa).toFixed(2)}</b></div>
            <div><span>Drive date</span><b>${dateFmt(d.date)}</b></div>
            <div><span>Job type</span><b>Full time</b></div>
          </div>
          <div class="eligibility">✓ Minimum CGPA enforced by MySQL Trigger: ${Number(d.cgpa).toFixed(2)}</div>
          <div class="card-actions">
            <button class="card-link" onclick="viewDriveDetails(${d.id})">View details ↗</button>
            <button class="apply-btn" onclick="openApplyModal('drive', ${d.id})">Apply now</button>
          </div>
          <div class="card-actions-row">
            <button class="action-btn" onclick="openEditDriveModal(${d.id})">Edit</button>
            <button class="action-btn danger" onclick="confirmDeleteDrive(${d.id}, '${d.name}')">Delete</button>
          </div>
        </article>
      `).join("")
    : `<div class="empty">No placement drives found.</div>`;
}

function openAddDriveModal() {
  if (!state.companies.length) {
    toast("Please add at least one company first.");
    return;
  }
  openModal(`
    <h2>Create placement drive</h2>
    <p>Stores a new recruitment drive in MySQL Placement_Drive table.</p>
    <div class="form-row">
      <label>Company</label>
      <select id="driveCompany">
        ${state.companies.map(c => `<option value="${c.id}">${c.name}</option>`).join("")}
      </select>
    </div>
    <div class="form-row">
      <label>Drive Name</label>
      <input id="driveName" placeholder="e.g. TCS Ninja 2026" required />
    </div>
    <div class="form-row">
      <label>Job Role</label>
      <input id="driveRole" placeholder="e.g. Graduate Trainee" required />
    </div>
    <div class="form-grid-2">
      <div class="form-row">
        <label>Package (LPA)</label>
        <input id="drivePackage" type="number" step="0.1" placeholder="e.g. 5.5" required />
      </div>
      <div class="form-row">
        <label>Minimum CGPA</label>
        <input id="driveMinCgpa" type="number" min="0" max="10" step="0.1" value="7.0" required />
      </div>
    </div>
    <div class="form-row">
      <label>Drive Date</label>
      <input id="driveDate" type="date" value="2026-11-25" required />
    </div>
    <button class="primary-btn" id="saveDriveBtn">Create Drive <span>→</span></button>
  `);

  $("#saveDriveBtn").onclick = async () => {
    const company_id = Number($("#driveCompany").value);
    const name = $("#driveName").value.trim();
    const role = $("#driveRole").value.trim();
    const packageVal = Number($("#drivePackage").value);
    const cgpa = Number($("#driveMinCgpa").value);
    const dateVal = $("#driveDate").value;

    if (!name || !role || !dateVal || isNaN(packageVal)) {
      toast("Please fill in all drive details.");
      return;
    }

    try {
      await apiRequest("/api/drives", {
        method: "POST",
        body: JSON.stringify({ company_id, name, role, package: packageVal, cgpa, date: dateVal })
      });
      closeModal();
      toast("Placement drive created successfully.");
      await fetchDrives();
      fetchOverview();
    } catch (e) {
      toast(e.message);
    }
  };
}

function openEditDriveModal(id) {
  const d = state.drives.find(x => x.id === id);
  if (!d) return;

  openModal(`
    <h2>Edit placement drive</h2>
    <p>Update drive details for #${d.id} (${d.name}).</p>
    <div class="form-row">
      <label>Drive Name</label>
      <input id="editDriveName" value="${d.name}" required />
    </div>
    <div class="form-row">
      <label>Job Role</label>
      <input id="editDriveRole" value="${d.role}" required />
    </div>
    <div class="form-grid-2">
      <div class="form-row">
        <label>Package (LPA)</label>
        <input id="editDrivePackage" type="number" step="0.1" value="${d.package}" required />
      </div>
      <div class="form-row">
        <label>Minimum CGPA</label>
        <input id="editDriveMinCgpa" type="number" step="0.1" value="${d.cgpa}" required />
      </div>
    </div>
    <div class="form-row">
      <label>Drive Date</label>
      <input id="editDriveDate" type="date" value="${(d.date || "").slice(0, 10)}" required />
    </div>
    <button class="primary-btn" id="updateDriveBtn">Update Drive <span>→</span></button>
  `);

  $("#updateDriveBtn").onclick = async () => {
    const name = $("#editDriveName").value.trim();
    const role = $("#editDriveRole").value.trim();
    const packageVal = Number($("#editDrivePackage").value);
    const cgpa = Number($("#editDriveMinCgpa").value);
    const dateVal = $("#editDriveDate").value;

    try {
      await apiRequest(`/api/drives/${id}`, {
        method: "PUT",
        body: JSON.stringify({ name, role, package: packageVal, cgpa, date: dateVal })
      });
      closeModal();
      toast("Drive updated successfully.");
      await fetchDrives();
      fetchOverview();
    } catch (e) {
      toast(e.message);
    }
  };
}

function confirmDeleteDrive(id, name) {
  openModal(`
    <h2>Delete placement drive</h2>
    <p>Are you sure you want to delete <b>${name}</b>? Any linked applications will also be removed.</p>
    <div style="display:flex;gap:10px;margin-top:20px;">
      <button class="outline-btn" style="flex:1" onclick="closeModal()">Cancel</button>
      <button class="primary-btn" style="flex:1;background:#d56c6c" id="deleteDriveConfirmBtn">Yes, Delete</button>
    </div>
  `);

  $("#deleteDriveConfirmBtn").onclick = async () => {
    try {
      await apiRequest(`/api/drives/${id}`, { method: "DELETE" });
      closeModal();
      toast("Placement drive deleted.");
      await fetchDrives();
      fetchOverview();
    } catch (e) {
      toast(e.message);
    }
  };
}

function viewDriveDetails(id) {
  const d = state.drives.find(x => x.id === id);
  if (!d) return;

  openModal(`
    <h2>${d.name}</h2>
    <p><b>${d.company}</b> · Full-time Campus Placement Drive</p>
    <div class="drive-info">
      <div><span>Role</span><b>${d.role}</b></div>
      <div><span>Minimum CGPA</span><b>${Number(d.cgpa).toFixed(2)}</b></div>
      <div><span>Package</span><b>${Number(d.package).toFixed(2)} LPA</b></div>
      <div><span>Drive Date</span><b>${dateFmt(d.date)}</b></div>
    </div>
    <p style="margin-top:14px"><b>Relational Rules:</b> This opportunity enforces MySQL Trigger <code>check_eligibility</code> before insertion, and table unique index <code>uq_student_drive</code>.</p>
    <button class="primary-btn" onclick="openApplyModal('drive', ${d.id})">Apply now →</button>
  `);
}

// ---------------------------------------------------------------------------
// INTERNSHIPS
// ---------------------------------------------------------------------------

async function fetchInternships() {
  try {
    const data = await apiRequest("/api/internships");
    state.internships = data;
    renderInternships();
  } catch (e) {
    toast("Failed to load internships.");
  }
}

function renderInternships() {
  $("#internshipCount").textContent = state.internships.length;
  $("#internshipGrid").innerHTML = state.internships.length
    ? state.internships.map(item => `
        <article class="drive-card">
          <div class="drive-card-top">
            ${companyLogo(item.company, item.color, item.initial)}
            <span class="soft-pill">Internship</span>
          </div>
          <h3>${item.role}</h3>
          <div class="company-name">${item.company}</div>
          <div class="role-name">Hands-on industry experience</div>
          <div class="drive-info">
            <div><span>Monthly stipend</span><b>₹${Number(item.stipend).toLocaleString("en-IN")}</b></div>
            <div><span>Minimum CGPA</span><b>${Number(item.cgpa).toFixed(2)}</b></div>
            <div><span>Start date</span><b>${dateFmt(item.date)}</b></div>
            <div><span>Duration</span><b>As per company</b></div>
          </div>
          <div class="eligibility">✓ Minimum CGPA check enforced: ${Number(item.cgpa).toFixed(2)}</div>
          <div class="card-actions">
            <button class="card-link" onclick="viewInternshipDetails(${item.id})">View details ↗</button>
            <button class="apply-btn" onclick="openApplyModal('intern', ${item.id})">Apply now</button>
          </div>
          <div class="card-actions-row">
            <button class="action-btn" onclick="openEditInternshipModal(${item.id})">Edit</button>
            <button class="action-btn danger" onclick="confirmDeleteInternship(${item.id}, '${item.role}')">Delete</button>
          </div>
        </article>
      `).join("")
    : `<div class="empty">No internships found.</div>`;
}

function openAddInternshipModal() {
  if (!state.companies.length) {
    toast("Please add at least one company first.");
    return;
  }
  openModal(`
    <h2>Create internship opportunity</h2>
    <p>Stores a new internship record in MySQL Internship table.</p>
    <div class="form-row">
      <label>Company</label>
      <select id="internCompany">
        ${state.companies.map(c => `<option value="${c.id}">${c.name}</option>`).join("")}
      </select>
    </div>
    <div class="form-row">
      <label>Internship Role</label>
      <input id="internRole" placeholder="e.g. Cloud Intern" required />
    </div>
    <div class="form-grid-2">
      <div class="form-row">
        <label>Monthly Stipend (₹)</label>
        <input id="internStipend" type="number" placeholder="25000" required />
      </div>
      <div class="form-row">
        <label>Minimum CGPA</label>
        <input id="internMinCgpa" type="number" min="0" max="10" step="0.1" value="7.0" required />
      </div>
    </div>
    <div class="form-row">
      <label>Start Date</label>
      <input id="internDate" type="date" value="2027-02-01" required />
    </div>
    <button class="primary-btn" id="saveInternshipBtn">Create Internship <span>→</span></button>
  `);

  $("#saveInternshipBtn").onclick = async () => {
    const company_id = Number($("#internCompany").value);
    const role = $("#internRole").value.trim();
    const stipend = Number($("#internStipend").value);
    const cgpa = Number($("#internMinCgpa").value);
    const dateVal = $("#internDate").value;

    if (!role || !dateVal || isNaN(stipend)) {
      toast("Please fill in all internship details.");
      return;
    }

    try {
      await apiRequest("/api/internships", {
        method: "POST",
        body: JSON.stringify({ company_id, role, stipend, cgpa, date: dateVal })
      });
      closeModal();
      toast("Internship created successfully.");
      await fetchInternships();
      fetchOverview();
    } catch (e) {
      toast(e.message);
    }
  };
}

function openEditInternshipModal(id) {
  const item = state.internships.find(x => x.id === id);
  if (!item) return;

  openModal(`
    <h2>Edit internship</h2>
    <p>Update internship details for #${item.id}.</p>
    <div class="form-row">
      <label>Internship Role</label>
      <input id="editInternRole" value="${item.role}" required />
    </div>
    <div class="form-grid-2">
      <div class="form-row">
        <label>Monthly Stipend (₹)</label>
        <input id="editInternStipend" type="number" value="${item.stipend}" required />
      </div>
      <div class="form-row">
        <label>Minimum CGPA</label>
        <input id="editInternMinCgpa" type="number" step="0.1" value="${item.cgpa}" required />
      </div>
    </div>
    <div class="form-row">
      <label>Start Date</label>
      <input id="editInternDate" type="date" value="${(item.date || "").slice(0, 10)}" required />
    </div>
    <button class="primary-btn" id="updateInternshipBtn">Update Internship <span>→</span></button>
  `);

  $("#updateInternshipBtn").onclick = async () => {
    const role = $("#editInternRole").value.trim();
    const stipend = Number($("#editInternStipend").value);
    const cgpa = Number($("#editInternMinCgpa").value);
    const dateVal = $("#editInternDate").value;

    try {
      await apiRequest(`/api/internships/${id}`, {
        method: "PUT",
        body: JSON.stringify({ role, stipend, cgpa, date: dateVal })
      });
      closeModal();
      toast("Internship updated successfully.");
      await fetchInternships();
      fetchOverview();
    } catch (e) {
      toast(e.message);
    }
  };
}

function confirmDeleteInternship(id, role) {
  openModal(`
    <h2>Delete internship</h2>
    <p>Are you sure you want to delete <b>${role}</b>? Any linked applications will also be removed.</p>
    <div style="display:flex;gap:10px;margin-top:20px;">
      <button class="outline-btn" style="flex:1" onclick="closeModal()">Cancel</button>
      <button class="primary-btn" style="flex:1;background:#d56c6c" id="deleteInternConfirmBtn">Yes, Delete</button>
    </div>
  `);

  $("#deleteInternConfirmBtn").onclick = async () => {
    try {
      await apiRequest(`/api/internships/${id}`, { method: "DELETE" });
      closeModal();
      toast("Internship deleted.");
      await fetchInternships();
      fetchOverview();
    } catch (e) {
      toast(e.message);
    }
  };
}

function viewInternshipDetails(id) {
  const item = state.internships.find(x => x.id === id);
  if (!item) return;

  openModal(`
    <h2>${item.role}</h2>
    <p><b>${item.company}</b> · Practical Industry Internship</p>
    <div class="drive-info">
      <div><span>Role</span><b>${item.role}</b></div>
      <div><span>Minimum CGPA</span><b>${Number(item.cgpa).toFixed(2)}</b></div>
      <div><span>Monthly Stipend</span><b>₹${Number(item.stipend).toLocaleString("en-IN")}</b></div>
      <div><span>Start Date</span><b>${dateFmt(item.date)}</b></div>
    </div>
    <p style="margin-top:14px"><b>Academic DBMS Integration:</b> Applications to internships are validated against MySQL Trigger <code>check_eligibility</code> and stored in MongoDB applications collection.</p>
    <button class="primary-btn" onclick="openApplyModal('intern', ${item.id})">Apply now →</button>
  `);
}

// ---------------------------------------------------------------------------
// APPLICATIONS & APPLICATION TRACKER
// ---------------------------------------------------------------------------

async function fetchApplications() {
  const q = ($("#applicationSearch")?.value || "").trim();
  const status = $("#applicationFilter")?.value || "";
  const params = new URLSearchParams();
  if (q) params.set("search", q);
  if (status) params.set("status", status);

  try {
    const data = await apiRequest(`/api/applications?${params.toString()}`);
    state.applications = data;
    renderApplications();
  } catch (e) {
    toast("Failed to load applications.");
  }
}

function renderApplications() {
  const list = state.applications;

  // Mini stats
  const total = list.length;
  const applied = list.filter(a => a.status === "Applied").length;
  const selected = list.filter(a => a.status === "Selected").length;
  const shortlisted = list.filter(a => a.status === "Shortlisted").length;

  $("#miniAllApps").textContent = total;
  $("#miniApplied").textContent = applied;
  $("#miniSelected").textContent = selected;
  $("#miniShortlisted").textContent = shortlisted;

  $("#applicationsTable").innerHTML = list.length
    ? list.map(a => `
        <tr>
          <td>#APP-${String(a.id).padStart(4, "0")}</td>
          <td>
            <b>${a.student_name}</b><br>
            <small style="color:#9295a5">ID: ${a.student}</small>
          </td>
          <td>
            <b>${a.company}</b><br>
            <small style="color:#9295a5">${a.role}</small>
          </td>
          <td>${a.date_display || dateFmt(a.date)}</td>
          <td>${a.package ? `${Number(a.package).toFixed(2)} LPA` : a.stipend ? `₹${Number(a.stipend).toLocaleString("en-IN")}/mo` : "—"}</td>
          <td>${statusPill(a.status)}</td>
          <td>
            <div class="action-group">
              <button class="action-btn" onclick="openStatusModal(${a.id}, '${a.status}', '${a.student_name}', '${a.company}')">Update status</button>
              <button class="action-btn" onclick="viewAuditForApplication(${a.id})">Audit log</button>
            </div>
          </td>
        </tr>
      `).join("")
    : `<tr><td colspan="7" class="empty">No applications found.</td></tr>`;
}

function openApplyModal(kind, id) {
  const item = kind === "drive" ? state.drives.find(x => x.id === id) : state.internships.find(x => x.id === id);
  if (!item) return;

  const opportunityTitle = kind === "drive" ? item.name : `${item.role} (${item.company})`;
  const minCgpa = item.cgpa;
  const activeStudentId = currentUser.student_id || 101;

  openModal(`
    <h2>Apply for this opportunity</h2>
    <p>Submitting for <b>${opportunityTitle}</b> at <b>${item.company}</b>.</p>
    <div class="form-row">
      <label>Select Applicant Student</label>
      <select id="applyStudentSelect">
        ${state.students.map(s => `
          <option value="${s.id}" ${s.id === activeStudentId ? "selected" : ""}>
            ${s.id} · ${s.name} (CGPA: ${Number(s.cgpa).toFixed(2)} - ${s.dept})
          </option>
        `).join("")}
      </select>
      <div class="form-hint">Enforced by MySQL Trigger: CGPA must be ≥ ${Number(minCgpa).toFixed(2)}</div>
    </div>
    <div class="form-row">
      <label>Opportunity</label>
      <input value="${opportunityTitle}" disabled />
    </div>
    <button class="primary-btn" id="confirmApplyBtn">Submit Application <span>→</span></button>
  `);

  $("#confirmApplyBtn").onclick = async () => {
    const student_id = Number($("#applyStudentSelect").value);
    const body = {
      student_id,
      drive_id: kind === "drive" ? id : null,
      internship_id: kind === "intern" ? id : null
    };

    try {
      await apiRequest("/api/applications", {
        method: "POST",
        body: JSON.stringify(body)
      });
      closeModal();
      toast("Application submitted successfully!");
      await fetchApplications();
      fetchOverview();
      if (student_id === currentUser.student_id) {
        loadStudentDashboard();
      }
    } catch (e) {
      toast(e.message);
    }
  };
}

function openStatusModal(appId, currentStatus, studentName, companyName) {
  openModal(`
    <h2>Update application status</h2>
    <p>Application #APP-${String(appId).padStart(4, "0")} for <b>${studentName}</b> at <b>${companyName}</b>.</p>
    <div class="form-row">
      <label>New Application Status</label>
      <select id="newStatusSelect">
        <option ${currentStatus === "Applied" ? "selected" : ""}>Applied</option>
        <option ${currentStatus === "Shortlisted" ? "selected" : ""}>Shortlisted</option>
        <option ${currentStatus === "Selected" ? "selected" : ""}>Selected</option>
        <option ${currentStatus === "Rejected" ? "selected" : ""}>Rejected</option>
      </select>
    </div>
    <div class="panel" style="background:#fcfbff;padding:12px;margin:12px 0;font-size:10px;line-height:1.5;color:#6b6794;border:1px solid #eeecff">
      ⚡ <b>Triggers that execute on change:</b><br>
      • <code>track_application_status</code>: Writes change to <code>Application_Audit</code>.<br>
      • <code>create_placement</code>: When changed to <b>Selected</b>, automatically inserts into <code>Placement</code> table and sets Student status to <b>Placed</b>!
    </div>
    <button class="primary-btn" id="confirmStatusBtn">Apply Status Change <span>→</span></button>
  `);

  $("#confirmStatusBtn").onclick = async () => {
    const newStatus = $("#newStatusSelect").value;
    try {
      const res = await apiRequest(`/api/applications/${appId}/status`, {
        method: "PUT",
        body: JSON.stringify({ status: newStatus })
      });
      closeModal();
      toast(res.message || "Status updated.");
      await Promise.all([
        fetchApplications(),
        fetchStudents(),
        fetchPlacements(),
        fetchOverview()
      ]);
      if (document.querySelector("#page-student-dashboard.active")) {
        loadStudentDashboard();
      }
    } catch (e) {
      toast(e.message);
    }
  };
}

async function viewAuditForApplication(appId) {
  try {
    const logs = await apiRequest("/api/applications/audit");
    const appLogs = logs.filter(l => l.application_id === appId);

    openModal(`
      <h2>Application audit history</h2>
      <p>Status change logs recorded by MySQL trigger <code>track_application_status</code> for #APP-${String(appId).padStart(4, "0")}.</p>
      ${appLogs.length ? `
        <div class="result-table-wrap">
          <table>
            <thead>
              <tr><th>AUDIT ID</th><th>OLD STATUS</th><th>NEW STATUS</th><th>TIMESTAMP</th></tr>
            </thead>
            <tbody>
              ${appLogs.map(l => `
                <tr>
                  <td>#${l.audit_id}</td>
                  <td>${l.old_status || "None"}</td>
                  <td>${statusPill(l.new_status)}</td>
                  <td>${l.changed_at}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : `<div class="empty">No status changes recorded yet for this application.</div>`}
      <button class="primary-btn" style="margin-top:15px" onclick="closeModal()">Close</button>
    `);
  } catch (e) {
    toast("Failed to load audit history.");
  }
}

// ---------------------------------------------------------------------------
// PLACEMENTS
// ---------------------------------------------------------------------------

async function fetchPlacements() {
  try {
    const data = await apiRequest("/api/placements");
    state.placements = data;
    renderPlacements();
  } catch (e) {
    toast("Failed to load placements.");
  }
}

function renderPlacements() {
  const list = state.placements;
  $("#placementsTable").innerHTML = list.length
    ? list.map(p => `
        <tr>
          <td>
            <div class="student-cell">
              <div class="avatar">${initials(p.student_name)}</div>
              <div>
                <b>${p.student_name}</b>
                <small>ID: ${p.student_id} · ${p.dept} (CGPA: ${Number(p.cgpa).toFixed(2)})</small>
              </div>
            </div>
          </td>
          <td><b>${p.company}</b></td>
          <td>${p.role}</td>
          <td>${p.package ? `${Number(p.package).toFixed(2)} LPA` : "Confirmed Offer"}</td>
          <td>${p.date_display || dateFmt(p.date)}</td>
        </tr>
      `).join("")
    : `<tr><td colspan="5" class="empty">No confirmed placements yet.</td></tr>`;
}

// ---------------------------------------------------------------------------
// COMPANIES DIRECTORY
// ---------------------------------------------------------------------------

async function fetchCompanies() {
  const q = ($("#companySearch")?.value || "").trim();
  try {
    const data = await apiRequest(`/api/companies?search=${encodeURIComponent(q)}`);
    state.companies = data;
    renderCompanies();
  } catch (e) {
    toast("Failed to load companies.");
  }
}

function renderCompanies() {
  const list = state.companies;
  $("#companyGrid").innerHTML = list.length
    ? list.map(c => `
        <article class="company-card" style="position:relative;flex-direction:column;align-items:stretch;">
          <div style="display:flex;align-items:center;gap:12px;">
            ${companyLogo(c.name, c.color, c.initial)}
            <div>
              <h3>${c.name}</h3>
              <p>${c.industry}</p>
              ${c.website ? `<small style="color:#7771ad">${c.website.replace("https://", "")}</small>` : ""}
            </div>
            <div class="company-count" style="margin-left:auto">${c.total_roles}<br>roles</div>
          </div>
          <div class="card-actions-row">
            <button class="action-btn" onclick="openEditCompanyModal(${c.id})">Edit</button>
            <button class="action-btn danger" onclick="confirmDeleteCompany(${c.id}, '${c.name}')">Delete</button>
          </div>
        </article>
      `).join("")
    : `<div class="empty">No companies found.</div>`;
}

function openAddCompanyModal() {
  openModal(`
    <h2>Add a company</h2>
    <p>Stores the organization in MySQL Company table and MongoDB companies collection.</p>
    <div class="form-row">
      <label>Company Name</label>
      <input id="newCompanyName" placeholder="e.g. Google" required />
    </div>
    <div class="form-row">
      <label>Website</label>
      <input id="newCompanyWeb" placeholder="https://www.google.com" />
    </div>
    <div class="form-row">
      <label>Industry</label>
      <input id="newCompanyIndustry" placeholder="Technology / Consulting" required />
    </div>
    <button class="primary-btn" id="saveCompanyBtn">Save Company <span>→</span></button>
  `);

  $("#saveCompanyBtn").onclick = async () => {
    const name = $("#newCompanyName").value.trim();
    const website = $("#newCompanyWeb").value.trim();
    const industry = $("#newCompanyIndustry").value.trim();

    if (!name || !industry) {
      toast("Company name and industry are required.");
      return;
    }

    try {
      await apiRequest("/api/companies", {
        method: "POST",
        body: JSON.stringify({ name, website, industry })
      });
      closeModal();
      toast("Company added successfully!");
      await fetchCompanies();
    } catch (e) {
      toast(e.message);
    }
  };
}

function openEditCompanyModal(id) {
  const c = state.companies.find(x => x.id === id);
  if (!c) return;

  openModal(`
    <h2>Edit company</h2>
    <p>Updating details for #${c.id} (${c.name}).</p>
    <div class="form-row">
      <label>Company Name</label>
      <input id="editCompanyName" value="${c.name}" required />
    </div>
    <div class="form-row">
      <label>Website</label>
      <input id="editCompanyWeb" value="${c.website || ""}" />
    </div>
    <div class="form-row">
      <label>Industry</label>
      <input id="editCompanyIndustry" value="${c.industry}" required />
    </div>
    <button class="primary-btn" id="updateCompanyBtn">Update Company <span>→</span></button>
  `);

  $("#updateCompanyBtn").onclick = async () => {
    const name = $("#editCompanyName").value.trim();
    const website = $("#editCompanyWeb").value.trim();
    const industry = $("#editCompanyIndustry").value.trim();

    try {
      await apiRequest(`/api/companies/${id}`, {
        method: "PUT",
        body: JSON.stringify({ name, website, industry })
      });
      closeModal();
      toast("Company updated successfully.");
      await fetchCompanies();
    } catch (e) {
      toast(e.message);
    }
  };
}

function confirmDeleteCompany(id, name) {
  openModal(`
    <h2>Delete company</h2>
    <p>Are you sure you want to delete <b>${name}</b>?</p>
    <div style="display:flex;gap:10px;margin-top:20px;">
      <button class="outline-btn" style="flex:1" onclick="closeModal()">Cancel</button>
      <button class="primary-btn" style="flex:1;background:#d56c6c" id="deleteCompanyConfirmBtn">Yes, Delete</button>
    </div>
  `);

  $("#deleteCompanyConfirmBtn").onclick = async () => {
    try {
      await apiRequest(`/api/companies/${id}`, { method: "DELETE" });
      closeModal();
      toast("Company deleted.");
      await fetchCompanies();
      fetchOverview();
    } catch (e) {
      toast(e.message);
    }
  };
}

// ---------------------------------------------------------------------------
// DBMS ACADEMIC CONSOLE (MySQL Q1–Q15, MongoDB CRUD/Aggregations, Triggers)
// ---------------------------------------------------------------------------

async function fetchDbmsData() {
  try {
    const [health, sqlQueries, mongoQueries, auditLogs] = await Promise.all([
      apiRequest("/api/health"),
      apiRequest("/api/dbms/sql-queries"),
      apiRequest("/api/dbms/mongo-queries"),
      apiRequest("/api/applications/audit")
    ]);

    state.dbmsSql = sqlQueries;
    state.dbmsMongo = mongoQueries;
    state.auditLogs = auditLogs;

    // Header stats
    $("#dbmsMysqlStatus").textContent = health.mysql.status === "connected" ? "Connected" : "Error";
    $("#dbmsMysqlTables").textContent = `${health.mysql.table_count || 9} tables · 3 triggers`;
    $("#dbmsMongoStatus").textContent = health.mongodb.status === "connected" ? "Connected" : "Error";
    $("#dbmsMongoCols").textContent = `${health.mongodb.collections?.length || 3} collections active`;
    $("#dbmsAuditCount").textContent = auditLogs.length;

    renderSqlQueries();
    renderMongoQueries();
    renderAuditLogs();
  } catch (e) {
    console.error("DBMS Data Load Error:", e);
  }
}

function renderSqlQueries() {
  const container = $("#sqlQueriesContainer");
  if (!state.dbmsSql.length) {
    container.innerHTML = `<div class="empty">No SQL queries loaded.</div>`;
    return;
  }

  container.innerHTML = state.dbmsSql.map((q, idx) => `
    <div class="query-card">
      <div class="query-header">
        <div class="query-title">${q.title}</div>
        <span class="soft-pill">${q.row_count} rows returned</span>
      </div>
      <div class="sql-code">${q.sql}</div>
      ${renderQueryTable(q.data)}
    </div>
  `).join("");
}

function renderQueryTable(data) {
  if (!data || !data.length) {
    return `<div style="font-size:10px;color:#a0a2ae;padding:6px 0;">(0 rows returned)</div>`;
  }
  const headers = Object.keys(data[0]);
  return `
    <div class="result-table-wrap">
      <table>
        <thead>
          <tr>${headers.map(h => `<th>${h.toUpperCase()}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${data.map(row => `
            <tr>
              ${headers.map(h => `<td>${row[h] !== null && row[h] !== undefined ? row[h] : "NULL"}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderMongoQueries() {
  const container = $("#mongoQueriesContainer");
  if (!state.dbmsMongo.length) {
    container.innerHTML = `<div class="empty">No MongoDB queries loaded.</div>`;
    return;
  }

  container.innerHTML = state.dbmsMongo.map(m => `
    <div class="query-card">
      <div class="query-header">
        <div class="query-title">${m.title}</div>
        <span class="badge-pill mongo">${m.type.toUpperCase()}</span>
      </div>
      <p style="font-size:10px;color:#898d9d;margin:2px 0 8px;">${m.description}</p>
      <div class="json-view">${JSON.stringify(m.data, null, 2)}</div>
    </div>
  `).join("");
}

function renderAuditLogs() {
  const tbody = $("#auditTableBody");
  if (!state.auditLogs.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">No audit logs recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = state.auditLogs.map(l => `
    <tr>
      <td>#${l.audit_id}</td>
      <td>#APP-${String(l.application_id).padStart(4, "0")}</td>
      <td>${l.student_name} <small style="color:#999">(${l.student_id})</small></td>
      <td><b>${l.company_name}</b> · ${l.role}</td>
      <td>${l.old_status || "None"}</td>
      <td>${statusPill(l.new_status)}</td>
      <td>${l.changed_at}</td>
    </tr>
  `).join("");
}

// ---------------------------------------------------------------------------
// NAVIGATION & PAGE ROUTING
// ---------------------------------------------------------------------------

function showPage(name) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  $("#page-" + name)?.classList.add("active");
  document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.page === name));

  const labels = {
    overview: "Overview",
    "student-dashboard": "Student Dashboard",
    students: "Students",
    drives: "Placement drives",
    internships: "Internships",
    applications: "Applications",
    placements: "Placements",
    companies: "Companies",
    dbms: "DBMS Console"
  };
  $("#crumbTitle").textContent = labels[name] || "Overview";
  $("#sidebar").classList.remove("open");
  window.scrollTo(0, 0);

  if (name === "dbms") {
    fetchDbmsData();
  } else if (name === "student-dashboard") {
    loadStudentDashboard();
  }
}

// ---------------------------------------------------------------------------
// CSV EXPORT
// ---------------------------------------------------------------------------

function csvDownload(filename, rows) {
  const csv = rows.map(r => r.map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8;" }));
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---------------------------------------------------------------------------
// EVENT LISTENERS & INITIALIZATION
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  // Navigation
  document.addEventListener("click", e => {
    const nav = e.target.closest("[data-page]");
    if (nav) showPage(nav.dataset.page);

    const go = e.target.closest("[data-goto]");
    if (go) showPage(go.dataset.goto);

    const subtab = e.target.closest("[data-subtab]");
    if (subtab) {
      const tab = subtab.dataset.subtab;
      document.querySelectorAll(".sub-tab-btn").forEach(b => b.classList.toggle("active", b === subtab));
      $("#dbmsTabSql").style.display = tab === "sql" ? "block" : "none";
      $("#dbmsTabMongo").style.display = tab === "mongo" ? "block" : "none";
      $("#dbmsTabAudit").style.display = tab === "audit" ? "block" : "none";
    }
  });

  // Search & Filter input bindings
  $("#studentSearch")?.addEventListener("input", renderStudents);
  $("#departmentFilter")?.addEventListener("change", fetchStudents);
  $("#statusFilter")?.addEventListener("change", fetchStudents);

  $("#driveSearch")?.addEventListener("input", renderDrives);
  $("#driveSort")?.addEventListener("change", fetchDrives);

  $("#applicationSearch")?.addEventListener("input", renderApplications);
  $("#applicationFilter")?.addEventListener("change", fetchApplications);

  $("#companySearch")?.addEventListener("input", renderCompanies);

  // Buttons
  $("#addStudentBtn").onclick = openAddStudentModal;
  $("#addDriveBtn").onclick = openAddDriveModal;
  $("#addInternshipBtn").onclick = openAddInternshipModal;
  $("#addCompanyBtn").onclick = openAddCompanyModal;

  $("#topAuthBtn").onclick = openAuthModal;
  $("#sidebarProfile").onclick = openAuthModal;
  $("#topAvatar").onclick = openAuthModal;
  $("#sdSwitchUserBtn")?.addEventListener("click", openAuthModal);

  $("#refreshDbmsBtn").onclick = () => {
    fetchDbmsData();
    toast("DBMS data refreshed.");
  };

  $("#runAllSqlBtn").onclick = () => {
    fetchDbmsData();
    toast("Executing all 15 SQL queries against MySQL...");
  };

  $("#dbStatusBadge").onclick = () => showPage("dbms");

  $("#modalClose").onclick = closeModal;
  $("#modalBackdrop").addEventListener("click", e => {
    if (e.target.id === "modalBackdrop") closeModal();
  });

  $("#menuBtn").onclick = () => $("#sidebar").classList.toggle("open");
  $("#notificationBtn").onclick = () => toast("You're all caught up!");
  $("#helpBtn").onclick = () => {
    openModal(`
      <h2>Welcome to PlaceWise</h2>
      <p>PlaceWise is a comprehensive academic Student Placement Management System connected to MySQL (Relational) and MongoDB (NoSQL).</p>
      <div style="margin-top:14px;font-size:11px;line-height:1.6;color:#555">
        <b>Key Features:</b><br>
        • Live MySQL relational schema with 9 tables, constraints, and triggers.<br>
        • Automatic eligibility checking via MySQL Trigger <code>check_eligibility</code>.<br>
        • Automated placement generation & audit logging via <code>create_placement</code> and <code>track_application_status</code>.<br>
        • MongoDB NoSQL collections for student skill profiles and aggregation analytics.<br>
        • Click <b>DBMS Console</b> in the sidebar to inspect all 15 academic SQL queries and MongoDB aggregations!
      </div>
      <button class="primary-btn" style="margin-top:15px" onclick="closeModal()">Got it</button>
    `);
  };

  // CSV Exports
  $("#exportStudents").onclick = () => {
    csvDownload("placewise_students.csv", [
      ["ID", "Name", "Email", "Phone", "Department", "CGPA", "Graduation Year", "Status", "Skills"],
      ...state.students.map(s => [s.id, s.name, s.email, s.phone || "", s.dept, s.cgpa, s.year, s.status, (s.skills || []).join("; ")])
    ]);
  };

  $("#exportApplications").onclick = () => {
    csvDownload("placewise_applications.csv", [
      ["Application ID", "Student ID", "Student Name", "Company", "Role", "Applied Date", "Package/Stipend", "Status"],
      ...state.applications.map(a => [
        a.id, a.student, a.student_name, a.company, a.role, a.date_display || a.date,
        a.package ? `${a.package} LPA` : a.stipend ? `₹${a.stipend}` : "",
        a.status
      ])
    ]);
  };

  // Initial load
  loadAllData();
});

from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import PyPDF2

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.close()

init_db()

# ---------------- REGISTER ----------------
@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Already Registered! Please Login.", "info")
            conn.close()
            return redirect(url_for("login"))
        else:
            cursor.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                           (name, email, password))
            conn.commit()
            conn.close()
            flash("Registration Successful! Please Login.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = user[1]
            return redirect(url_for("upload"))
        else:
            flash("Invalid Email or Password", "danger")

    return render_template("login.html")

# ---------------- UPLOAD PAGE ----------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        file = request.files["resume"]
        if file.filename == "":
            flash("Please select a file!", "danger")
            return redirect(url_for("upload"))

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(filepath)

        text = extract_text(filepath)
        (score, strengths, weaknesses, suggestions, improvements, skills_needed, job_recommendations) = analyze_resume(text)

        return render_template("result.html",
                       score=score,
                       strengths=strengths,
                       weaknesses=weaknesses,
                       suggestions=suggestions,
                       improvements=improvements,
                       skills_needed=skills_needed,
                       jobs=job_recommendations)

    return render_template("upload.html")

# ---------------- EXTRACT TEXT ----------------
def extract_text(filepath):
    text = ""
    if filepath.endswith(".pdf"):
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    text += content
    return text

# ---------------- ANALYSIS LOGIC ----------------
def analyze_resume(text):
    text = text.lower()

    score = 0
    strengths = []
    weaknesses = []
    suggestions = []
    improvements = []
    skills_needed = []
    job_recommendations = []

    # Skill categories
    tech_skills = ["python", "java", "sql", "html", "css", "javascript",
                   "machine learning", "data science", "flask"]
    soft_skills = ["communication", "leadership", "teamwork", "problem solving"]

    # Detect skills
    detected_skills = [skill for skill in tech_skills if skill in text]
    detected_soft = [skill for skill in soft_skills if skill in text]

    # --- SCORING ---
    if len(detected_skills) >= 3:
        score += 40
        strengths.append("Strong technical skill set.")
    else:
        weaknesses.append("Limited technical skills mentioned.")
        suggestions.append("Add more relevant technical skills.")
        skills_needed.extend(["Python", "SQL", "Data Analysis"])

    if len(detected_soft) >= 2:
        score += 20
        strengths.append("Good soft skills presence.")
    else:
        weaknesses.append("Soft skills not clearly highlighted.")
        suggestions.append("Include communication and teamwork skills.")
        skills_needed.append("Communication Skills")

    if "experience" in text or "project" in text:
        score += 20
        strengths.append("Experience section included.")
    else:
        weaknesses.append("Experience section missing.")
        suggestions.append("Add internship or project experience.")
        improvements.append("Gain practical project experience.")

    if len(text.split()) > 250:
        score += 20
    else:
        weaknesses.append("Resume content too short.")
        suggestions.append("Add measurable achievements.")
        improvements.append("Expand resume with quantified results.")

    score = min(score, 100)

    # --- JOB RECOMMENDATION BASED ON SKILLS ---
    if "python" in detected_skills:
        job_recommendations.append("Python Developer")
        job_recommendations.append("Backend Developer")

    if "machine learning" in detected_skills:
        job_recommendations.append("Machine Learning Engineer")
        job_recommendations.append("Data Scientist")

    if "html" in detected_skills or "css" in detected_skills:
        job_recommendations.append("Frontend Developer")

    if "sql" in detected_skills:
        job_recommendations.append("Database Administrator")

    if not job_recommendations:
        job_recommendations.append("Software Developer")
        job_recommendations.append("IT Support Specialist")

    return (score, strengths, weaknesses,
            suggestions, improvements,
            skills_needed, job_recommendations)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
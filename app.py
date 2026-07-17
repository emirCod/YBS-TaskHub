from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db, init_app


app = Flask(__name__)
app.config["SECRET_KEY"] = "ybs-taskhub-gizli-anahtar"

init_app(app)


PRIORITY_OPTIONS = ["Düşük", "Orta", "Yüksek"]
STATUS_OPTIONS = ["Yapılacak", "Devam Ediyor", "Tamamlandı"]


# -------------------------------------------------
# Yardımcı fonksiyonlar
# -------------------------------------------------

def login_required():
    if "user_id" not in session:
        flash("Bu sayfaya erişmek için önce giriş yapmalısınız.", "warning")
        return False

    return True


def calculate_progress(completed_count, total_count):
    if total_count == 0:
        return 0

    return int((completed_count * 100) / total_count)


def get_user_project(project_id):
    db = get_db()

    return db.execute(
        """
        SELECT *
        FROM projects
        WHERE id = ? AND user_id = ?
        """,
        (project_id, session["user_id"])
    ).fetchone()


def get_user_task(task_id):
    db = get_db()

    return db.execute(
        """
        SELECT t.*
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.id = ? AND p.user_id = ?
        """,
        (task_id, session["user_id"])
    ).fetchone()


def get_due_info(due_date, status):
    if not due_date:
        return {
            "has_due_date": False,
            "due_label": "",
            "is_overdue": False,
            "is_due_soon": False,
            "days_remaining": None
        }

    try:
        due = datetime.strptime(due_date, "%Y-%m-%d").date()
    except ValueError:
        return {
            "has_due_date": False,
            "due_label": "",
            "is_overdue": False,
            "is_due_soon": False,
            "days_remaining": None
        }

    today = date.today()
    days_remaining = (due - today).days

    is_overdue = status != "Tamamlandı" and days_remaining < 0
    is_due_soon = status != "Tamamlandı" and 0 <= days_remaining <= 7

    if is_overdue:
        due_label = f"{abs(days_remaining)} gün gecikti"
    elif days_remaining == 0:
        due_label = "Bugün"
    elif days_remaining == 1:
        due_label = "Yarın"
    else:
        due_label = f"{days_remaining} gün kaldı"

    return {
        "has_due_date": True,
        "due_label": due_label,
        "is_overdue": is_overdue,
        "is_due_soon": is_due_soon,
        "days_remaining": days_remaining
    }


def build_task_dict(task):
    due_info = get_due_info(task["due_date"], task["status"])

    task_data = {
        "id": task["id"],
        "project_id": task["project_id"],
        "title": task["title"],
        "description": task["description"],
        "priority": task["priority"],
        "status": task["status"],
        "due_date": task["due_date"],
        "created_at": task["created_at"]
    }

    if "project_title" in task.keys():
        task_data["project_title"] = task["project_title"]

    task_data.update(due_info)
    return task_data


def get_dashboard_projects(user_id):
    db = get_db()

    project_rows = db.execute(
        """
        SELECT
            p.id,
            p.title,
            p.description,
            p.created_at,
            COUNT(t.id) AS task_count,
            SUM(CASE WHEN t.status = 'Tamamlandı' THEN 1 ELSE 0 END) AS completed_task_count
        FROM projects p
        LEFT JOIN tasks t ON p.id = t.project_id
        WHERE p.user_id = ?
        GROUP BY p.id
        ORDER BY p.created_at DESC
        """,
        (user_id,)
    ).fetchall()

    projects = []

    for project in project_rows:
        task_count = project["task_count"]
        completed_count = project["completed_task_count"] or 0

        projects.append({
            "id": project["id"],
            "title": project["title"],
            "description": project["description"],
            "created_at": project["created_at"],
            "task_count": task_count,
            "completed_task_count": completed_count,
            "progress": calculate_progress(completed_count, task_count)
        })

    return projects


def get_dashboard_stats(user_id):
    db = get_db()

    total_tasks = db.execute(
        """
        SELECT COUNT(t.id)
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE p.user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    completed_tasks = db.execute(
        """
        SELECT COUNT(t.id)
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE p.user_id = ? AND t.status = 'Tamamlandı'
        """,
        (user_id,)
    ).fetchone()[0]

    total_progress = calculate_progress(completed_tasks, total_tasks)

    return total_tasks, completed_tasks, total_progress


def get_upcoming_tasks(user_id):
    db = get_db()

    upcoming_rows = db.execute(
        """
        SELECT
            t.*,
            p.title AS project_title
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE
            p.user_id = ?
            AND t.status != 'Tamamlandı'
            AND t.due_date IS NOT NULL
            AND t.due_date != ''
        ORDER BY t.due_date ASC
        """,
        (user_id,)
    ).fetchall()

    upcoming_tasks = []

    for task in upcoming_rows:
        task_data = build_task_dict(task)

        if task_data["is_overdue"] or task_data["is_due_soon"]:
            upcoming_tasks.append(task_data)

    return upcoming_tasks[:6]


def get_project_tasks(project_id):
    db = get_db()

    task_rows = db.execute(
        """
        SELECT *
        FROM tasks
        WHERE project_id = ?
        ORDER BY created_at DESC
        """,
        (project_id,)
    ).fetchall()

    columns = {
        "Yapılacak": [],
        "Devam Ediyor": [],
        "Tamamlandı": []
    }

    for task in task_rows:
        task_data = build_task_dict(task)

        if task_data["status"] in columns:
            columns[task_data["status"]].append(task_data)

    return task_rows, columns


def clean_project_form():
    return {
        "title": request.form["title"].strip(),
        "description": request.form["description"].strip()
    }


def clean_task_form():
    title = request.form["title"].strip()
    description = request.form["description"].strip()
    priority = request.form["priority"]
    status = request.form["status"]
    due_date = request.form["due_date"]

    if priority not in PRIORITY_OPTIONS:
        priority = "Orta"

    if status not in STATUS_OPTIONS:
        status = "Yapılacak"

    return {
        "title": title,
        "description": description,
        "priority": priority,
        "status": status,
        "due_date": due_date
    }


# -------------------------------------------------
# Ana sayfa
# -------------------------------------------------

@app.route("/")
def home():
    return render_template("home.html")


# -------------------------------------------------
# Kullanıcı işlemleri
# -------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        username = request.form["username"].strip().lower()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        password_confirm = request.form["password_confirm"]

        if not full_name or not username or not email or not password:
            flash("Lütfen tüm alanları doldurun.", "danger")
            return redirect(url_for("register"))

        if " " in username:
            flash("Kullanıcı adı boşluk içeremez.", "danger")
            return redirect(url_for("register"))

        if len(username) < 3:
            flash("Kullanıcı adı en az 3 karakter olmalıdır.", "danger")
            return redirect(url_for("register"))

        if password != password_confirm:
            flash("Şifreler birbiriyle eşleşmiyor.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Şifre en az 6 karakter olmalıdır.", "danger")
            return redirect(url_for("register"))

        db = get_db()

        existing_email = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_email:
            flash("Bu e-posta adresiyle kayıtlı bir kullanıcı zaten var.", "warning")
            return redirect(url_for("register"))

        existing_username = db.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing_username:
            flash("Bu kullanıcı adı zaten kullanılıyor.", "warning")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        db.execute(
            """
            INSERT INTO users (full_name, username, email, password_hash)
            VALUES (?, ?, ?, ?)
            """,
            (full_name, username, email, password_hash)
        )
        db.commit()

        flash("Kayıt başarılı. Şimdi giriş yapabilirsiniz.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["identifier"].strip().lower()
        password = request.form["password"]

        db = get_db()

        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE email = ? OR username = ?
            """,
            (identifier, identifier)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("E-posta, kullanıcı adı veya şifre hatalı.", "danger")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["full_name"] = user["full_name"]
        session["username"] = user["username"]

        flash("Giriş başarılı. Hoş geldiniz.", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Oturum kapatıldı.", "info")
    return redirect(url_for("home"))


# -------------------------------------------------
# Dashboard
# -------------------------------------------------

@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    projects = get_dashboard_projects(user_id)
    total_tasks, completed_tasks, total_progress = get_dashboard_stats(user_id)
    upcoming_tasks = get_upcoming_tasks(user_id)

    return render_template(
        "dashboard.html",
        projects=projects,
        total_projects=len(projects),
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        total_progress=total_progress,
        upcoming_tasks=upcoming_tasks
    )


# -------------------------------------------------
# Proje işlemleri
# -------------------------------------------------

@app.route("/projects/new", methods=["GET", "POST"])
def create_project():
    if not login_required():
        return redirect(url_for("login"))

    if request.method == "POST":
        form_data = clean_project_form()

        if not form_data["title"]:
            flash("Proje adı boş bırakılamaz.", "danger")
            return redirect(url_for("create_project"))

        db = get_db()

        db.execute(
            """
            INSERT INTO projects (user_id, title, description)
            VALUES (?, ?, ?)
            """,
            (
                session["user_id"],
                form_data["title"],
                form_data["description"]
            )
        )
        db.commit()

        flash("Proje başarıyla oluşturuldu.", "success")
        return redirect(url_for("dashboard"))

    return render_template(
        "project_form.html",
        project=None,
        form_mode="create"
    )


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    if not login_required():
        return redirect(url_for("login"))

    project = get_user_project(project_id)

    if project is None:
        flash("Proje bulunamadı veya bu projeye erişim yetkiniz yok.", "danger")
        return redirect(url_for("dashboard"))

    task_rows, columns = get_project_tasks(project_id)

    total_tasks = len(task_rows)
    completed_tasks = len(columns["Tamamlandı"])
    progress = calculate_progress(completed_tasks, total_tasks)

    return render_template(
        "project_detail.html",
        project=project,
        columns=columns,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        progress=progress
    )


@app.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
def edit_project(project_id):
    if not login_required():
        return redirect(url_for("login"))

    project = get_user_project(project_id)

    if project is None:
        flash("Proje bulunamadı veya bu projeye erişim yetkiniz yok.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        form_data = clean_project_form()

        if not form_data["title"]:
            flash("Proje adı boş bırakılamaz.", "danger")
            return redirect(url_for("edit_project", project_id=project_id))

        db = get_db()

        db.execute(
            """
            UPDATE projects
            SET title = ?, description = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                form_data["title"],
                form_data["description"],
                project_id,
                session["user_id"]
            )
        )
        db.commit()

        flash("Proje başarıyla güncellendi.", "success")
        return redirect(url_for("dashboard"))

    return render_template(
        "project_form.html",
        project=project,
        form_mode="edit"
    )


@app.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id):
    if not login_required():
        return redirect(url_for("login"))

    project = get_user_project(project_id)

    if project is None:
        flash("Proje bulunamadı veya bu projeye erişim yetkiniz yok.", "danger")
        return redirect(url_for("dashboard"))

    db = get_db()

    db.execute(
        """
        DELETE FROM projects
        WHERE id = ? AND user_id = ?
        """,
        (project_id, session["user_id"])
    )
    db.commit()

    flash("Proje ve projeye bağlı görevler silindi.", "info")
    return redirect(url_for("dashboard"))


# -------------------------------------------------
# Görev işlemleri
# -------------------------------------------------

@app.route("/projects/<int:project_id>/tasks/new", methods=["GET", "POST"])
def create_task(project_id):
    if not login_required():
        return redirect(url_for("login"))

    project = get_user_project(project_id)

    if project is None:
        flash("Proje bulunamadı veya bu projeye erişim yetkiniz yok.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        form_data = clean_task_form()

        if not form_data["title"]:
            flash("Görev adı boş bırakılamaz.", "danger")
            return redirect(url_for("create_task", project_id=project_id))

        db = get_db()

        db.execute(
            """
            INSERT INTO tasks (project_id, title, description, priority, status, due_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                form_data["title"],
                form_data["description"],
                form_data["priority"],
                form_data["status"],
                form_data["due_date"]
            )
        )
        db.commit()

        flash("Görev başarıyla eklendi.", "success")
        return redirect(url_for("project_detail", project_id=project_id))

    return render_template(
        "task_form.html",
        project=project,
        task=None,
        priority_options=PRIORITY_OPTIONS,
        status_options=STATUS_OPTIONS,
        form_mode="create"
    )


@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
def edit_task(task_id):
    if not login_required():
        return redirect(url_for("login"))

    task = get_user_task(task_id)

    if task is None:
        flash("Görev bulunamadı veya bu göreve erişim yetkiniz yok.", "danger")
        return redirect(url_for("dashboard"))

    project = get_user_project(task["project_id"])

    if request.method == "POST":
        form_data = clean_task_form()

        if not form_data["title"]:
            flash("Görev adı boş bırakılamaz.", "danger")
            return redirect(url_for("edit_task", task_id=task_id))

        db = get_db()

        db.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, priority = ?, status = ?, due_date = ?
            WHERE id = ?
            """,
            (
                form_data["title"],
                form_data["description"],
                form_data["priority"],
                form_data["status"],
                form_data["due_date"],
                task_id
            )
        )
        db.commit()

        flash("Görev başarıyla güncellendi.", "success")
        return redirect(url_for("project_detail", project_id=task["project_id"]))

    return render_template(
        "task_form.html",
        project=project,
        task=task,
        priority_options=PRIORITY_OPTIONS,
        status_options=STATUS_OPTIONS,
        form_mode="edit"
    )


@app.route("/tasks/<int:task_id>/status", methods=["POST"])
def update_task_status(task_id):
    if not login_required():
        return redirect(url_for("login"))

    new_status = request.form["status"]

    if new_status not in STATUS_OPTIONS:
        flash("Geçersiz görev durumu seçildi.", "danger")
        return redirect(url_for("dashboard"))

    task = get_user_task(task_id)

    if task is None:
        flash("Görev bulunamadı veya bu göreve erişim yetkiniz yok.", "danger")
        return redirect(url_for("dashboard"))

    db = get_db()

    db.execute(
        """
        UPDATE tasks
        SET status = ?
        WHERE id = ?
        """,
        (new_status, task_id)
    )
    db.commit()

    flash("Görev durumu güncellendi.", "success")
    return redirect(url_for("project_detail", project_id=task["project_id"]))


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    if not login_required():
        return redirect(url_for("login"))

    task = get_user_task(task_id)

    if task is None:
        flash("Görev bulunamadı veya bu göreve erişim yetkiniz yok.", "danger")
        return redirect(url_for("dashboard"))

    db = get_db()

    db.execute(
        """
        DELETE FROM tasks
        WHERE id = ?
        """,
        (task_id,)
    )
    db.commit()

    flash("Görev silindi.", "info")
    return redirect(url_for("project_detail", project_id=task["project_id"]))


if __name__ == "__main__":
    app.run(debug=True)
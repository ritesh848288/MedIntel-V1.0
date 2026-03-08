from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from langchain.prompts import PromptTemplate
from langchain.llms import LlamaCpp
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from src.helper import download_hugging_face_embeddings
from src.prompt import *
from models import db, User, ChatHistory
import os

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-to-a-random-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///medical_assistant.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# Role decorators
# ---------------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != "admin":
            flash("Access denied. Admins only.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


def doctor_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != "doctor":
            flash("Access denied. Doctors only.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Load AI components
# ---------------------------------------------------------------------------
print("Loading embeddings...")
embeddings = download_hugging_face_embeddings()

print("Loading FAISS index...")
docsearch = FAISS.load_local("faiss_index", embeddings)

PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)
chain_type_kwargs = {"prompt": PROMPT}

print("Loading LLM...")
llm = LlamaCpp(
    model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    temperature=0.0,
    max_tokens=300,
    n_ctx=2048,
    n_threads=4,
    n_batch=128,
    verbose=False
)

retriever = docsearch.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3}
)

qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs=chain_type_kwargs
)


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_redirect"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("dashboard_redirect"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_redirect"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([full_name, username, email, password]):
            flash("All fields are required.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
        else:
            user = User(full_name=full_name, username=username, email=email, role="doctor")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard_redirect():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("doctor_dashboard"))


# ---------------------------------------------------------------------------
# Doctor routes
# ---------------------------------------------------------------------------
@app.route("/doctor/dashboard")
@doctor_required
def doctor_dashboard():
    total_chats = ChatHistory.query.filter_by(user_id=current_user.id).count()
    recent_chats = (ChatHistory.query
                    .filter_by(user_id=current_user.id)
                    .order_by(ChatHistory.created_at.desc())
                    .limit(5)
                    .all())
    return render_template("doctor/dashboard.html",
                           total_chats=total_chats,
                           recent_chats=recent_chats)


@app.route("/chat")
@doctor_required
def chat_page():
    return render_template("doctor/chat.html")


@app.route("/get", methods=["POST"])
@login_required
def get_response():
    msg = request.form.get("msg", "").strip()
    if not msg:
        return jsonify({"error": "Empty message"}), 400

    result = qa({"query": msg})
    answer = str(result["result"])

    # Save to database
    chat = ChatHistory(user_id=current_user.id, question=msg, response=answer)
    db.session.add(chat)
    db.session.commit()

    return answer


@app.route("/doctor/history")
@doctor_required
def doctor_history():
    chats = (ChatHistory.query
             .filter_by(user_id=current_user.id)
             .order_by(ChatHistory.created_at.desc())
             .all())
    return render_template("doctor/history.html", chats=chats)


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    total_users = db.session.query(User).count()
    total_doctors = db.session.query(User).filter_by(role="doctor").count()
    total_chats = db.session.query(ChatHistory).count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_chats = (ChatHistory.query
                    .order_by(ChatHistory.created_at.desc())
                    .limit(10)
                    .all())
    return render_template("admin/dashboard.html",
                           total_users=total_users,
                           total_doctors=total_doctors,
                           total_chats=total_chats,
                           recent_users=recent_users,
                           recent_chats=recent_chats)


@app.route("/admin/users")
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete yourself.", "danger")
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f"User '{user.username}' deleted.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/chats")
@admin_required
def admin_chats():
    chats = (ChatHistory.query
             .order_by(ChatHistory.created_at.desc())
             .all())
    return render_template("admin/chats.html", chats=chats)


# ---------------------------------------------------------------------------
# Print routes
# ---------------------------------------------------------------------------
@app.route("/print/chat/<int:chat_id>")
@login_required
def print_single_chat(chat_id):
    chat = ChatHistory.query.get_or_404(chat_id)
    if not current_user.is_admin and chat.user_id != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for("index"))
    return render_template("print_chat.html", chats=[chat], title="Chat Prediction")


@app.route("/print/history")
@login_required
def print_history():
    if current_user.is_admin:
        chats = ChatHistory.query.order_by(ChatHistory.created_at.desc()).all()
        title = "All Chat Predictions"
    else:
        chats = (ChatHistory.query
                 .filter_by(user_id=current_user.id)
                 .order_by(ChatHistory.created_at.desc())
                 .all())
        title = "My Chat Predictions"
    return render_template("print_chat.html", chats=chats, title=title)


# ---------------------------------------------------------------------------
# Seed default admin & start
# ---------------------------------------------------------------------------
def seed_admin():
    if not User.query.filter_by(username="admin").first():
        admin = User(
            full_name="Administrator",
            username="admin",
            email="admin@doctorai.com",
            role="admin"
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Default admin created (admin / admin123)")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_admin()
    app.run(debug=False, use_reloader=False)

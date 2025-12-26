import os
from flask import Flask, render_template, request, redirect, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import OperationalError
from collections import defaultdict
from sqlalchemy import func, case
import json
from sqlalchemy import desc

app = Flask(__name__)

# -------------------------
# SECRET_KEY（必須）
# -------------------------
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY is not set")

# -------------------------
# DATABASE_URL（必須）
# -------------------------
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL is not set")

# Render/Heroku 系で postgres:// の場合の補正（重要）
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ============================================================
# Models
# ============================================================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

class Progress(db.Model):
    __tablename__ = "progress"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    exercise = db.Column(db.String(100), primary_key=True)
    done = db.Column(db.Boolean, nullable=False, default=False)

class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_id = db.Column(db.String(50), nullable=False)
    attempt_no = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    answers = db.relationship("QuizAnswer", backref="attempt", cascade="all, delete-orphan")

class QuizAnswer(db.Model):
    __tablename__ = "quiz_answers"
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = db.Column(db.String(50), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)

    # 追加：ユーザーの回答（複数選択を想定してJSON文字列にする）
    selected = db.Column(db.Text, nullable=False, default="[]")  # 例: '["A","C"]'



def admin_required():
    if "user" not in session:
        return False
    user = User.query.filter_by(username=session["user"]).first()
    return user and user.is_admin

EXERCISE_CATEGORY = {
    "exercise1": "Login-based SQLi",
    "exercise2": "Search SQLi",
    "exercise3": "URL Parameter SQLi",
    "exercise4": "Error-based SQLi",
    "exercise5": "Blind SQLi",
    "exercise6": "Static Analysis",
    "exercise7": "Dynamic Analysis",
    "exercise8": "Defense (Prepared Statements)",
    "exercise9": "Comprehension Quiz",
}

# ============================================================
# Routes
# ============================================================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("ユーザー名とパスワードを入力してください")
            return redirect("/signup")

        if User.query.filter_by(username=username).first():
            flash("このユーザー名はすでに使用されています")
            return redirect("/signup")

        user = User(username=username, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()

        flash("登録が完了しました！ログインしてください。")
        return redirect("/login")

    return render_template("signup.html")

@app.route("/")
def index():
    if "user" in session:
        return redirect("/home")
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()
        if not user:
            flash("ユーザー名が存在しません")
            return redirect("/login")

        if not check_password_hash(user.password, password):
            flash("パスワードが違います")
            return redirect("/login")

        session.clear()
        session["user"] = user.username
        return redirect("/home")

    return render_template("login.html")

@app.route("/admin")
def admin_dashboard():
    if not admin_required():
        abort(403)

    users = User.query.order_by(User.username).all()
    progresses = Progress.query.all()

    # user_id → { exercise: done }
    progress_map = {}
    for p in progresses:
        progress_map.setdefault(p.user_id, {})[p.exercise] = p.done

    # 管理画面用データ
    user_rows = []
    for u in users:
        user_rows.append({
            "username": u.username,
            "progress": progress_map.get(u.id, {})
        })

    exercises = sorted(EXERCISE_CATEGORY.keys())

    return render_template(
        "admin.html",
        users=user_rows,
        exercises=exercises,
        exercise_labels=EXERCISE_CATEGORY
    )

@app.context_processor
def inject_is_admin():
    is_admin = False
    if "user" in session:
        user = User.query.filter_by(username=session["user"]).first()
        if user and user.is_admin:
            is_admin = True
    return dict(is_admin=is_admin)

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect("/login")

    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        session.clear()
        flash("ユーザー情報が見つかりません。")
        return redirect("/login")

    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        new_password = request.form.get("new_password", "").strip()

        if not new_username:
            flash("ユーザー名を入力してください")
            return redirect("/profile")

        # username 更新（重複チェック）
        if new_username != user.username and User.query.filter_by(username=new_username).first():
            flash("このユーザー名はすでに使用されています")
            return redirect("/profile")

        user.username = new_username

        if new_password:
            user.password = generate_password_hash(new_password)

        db.session.commit()

        session["user"] = user.username
        flash("ユーザー情報を更新しました")
        return redirect("/profile")

    return render_template("profile.html", user=(user.id, user.username, user.password))

@app.route("/delete_user", methods=["POST"])
def delete_user():
    if "user" not in session:
        return redirect("/login")

    user = User.query.filter_by(username=session["user"]).first()
    if user:
        db.session.delete(user)
        db.session.commit()

    session.clear()
    flash("アカウントを削除しました")
    return redirect("/login")

@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/login")

    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        session.clear()
        return redirect("/login")

    done_list = {p.exercise for p in Progress.query.filter_by(user_id=user.id, done=True).all()}

    intro_cards = [
        {"id": "intro_sql", "title": "SQLインジェクションとは？", "desc": "SQLi攻撃の基礎と仕組みを知る", "link": "/intro_sql"},
        {"id": "intro_importance", "title": "なぜセキュリティが重要なのか", "desc": "攻撃により生じる被害やリスクを理解する", "link": "/intro_importance"},
        {"id": "intro_learning", "title": "このアプリで学べること", "desc": "学習内容とゴールを確認する", "link": "/intro_learning"},
        {"id": "intro_notice", "title": "学習上の注意", "desc": "実際のサービスへの攻撃は絶対禁止です", "link": "/intro_notice"},
        {"id": "intro_quiz", "title": "インジェクション理解度チェック", "desc": "SQLインジェクションの理解度を確認する", "link": "/intro_quiz"},
    ]

    exercise_cards = [
        {"title": "演習1：ログインSQLi体験", "desc": "OR '1'='1' による不正ログインを学ぶ", "link": "/exercise1"},
        {"title": "演習2：検索フォームSQLi", "desc": "LIKE検索に対するSQLiを体験", "link": "/exercise2"},
        {"title": "演習3：URLパラメータSQLi", "desc": "id=1 OR 1=1 の攻撃を試す", "link": "/exercise3"},
        {"title": "演習4：エラーベースSQLi", "desc": "エラー文から情報が漏れる仕組み", "link": "/exercise4"},
        {"title": "演習5：ブラインドSQLi", "desc": "結果が表示されないSQLi攻撃とは", "link": "/exercise5"},
        {"title": "演習6：脆弱コードの静的解析", "desc": "危険な行を赤色でハイライト", "link": "/exercise6"},
        {"title": "演習7：動的解析デモ", "desc": "payload自動テストを使って診断", "link": "/exercise7"},
        {"title": "演習8：安全なSQL（防御版）", "desc": "パラメトリクエリを体験", "link": "/exercise8"},
        {"title": "演習9：理解チェッククイズ", "desc": "SQLi理解度テスト", "link": "/exercise9"},
    ]

    return render_template("home.html", intro_cards=intro_cards, exercise_cards=exercise_cards, done_list=done_list)

@app.route("/set_achievement/<exercise>", methods=["POST"])
def set_achievement(exercise):
    if "user" not in session:
        return {"status": "error", "message": "not logged in"}, 403

    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return {"status": "error", "message": "user not found"}, 404

    p = Progress.query.filter_by(user_id=user.id, exercise=exercise).first()
    if p:
        p.done = True
    else:
        db.session.add(Progress(user_id=user.id, exercise=exercise, done=True))

    db.session.commit()
    return {"status": "ok"}


@app.route("/quiz/submit", methods=["POST"])
def submit_quiz():
    if "user" not in session:
        abort(403)

    user = User.query.filter_by(username=session["user"]).first_or_404()
    quiz_id = "quiz_sql_basics"

    attempt_no = QuizAttempt.query.filter_by(user_id=user.id, quiz_id=quiz_id).count() + 1

    score = 0
    attempt = QuizAttempt(user_id=user.id, quiz_id=quiz_id, attempt_no=attempt_no, score=0)
    db.session.add(attempt)
    db.session.flush()  # attempt.id 確定

    for qid, correct_answers in QUIZ_ANSWER_KEY.items():
        user_ans = request.form.getlist(qid)  # 複数選択対応
        is_correct = set(user_ans) == set(correct_answers)
        if is_correct:
            score += 1

        db.session.add(QuizAnswer(
            attempt_id=attempt.id,
            question_id=qid,
            is_correct=is_correct,
            selected=json.dumps(user_ans, ensure_ascii=False)
        ))

    attempt.score = score
    db.session.commit()


@app.route("/admin/user/<username>")
def admin_user_detail(username):
    if not admin_required():
        abort(403)

    user = User.query.filter_by(username=username).first_or_404()

    # 試行の概要
    attempt_summary = (
        db.session.query(
            func.count(QuizAttempt.id).label("attempts"),
            func.avg(QuizAttempt.score).label("avg_score"),
            func.max(QuizAttempt.score).label("best_score"),
        )
        .filter(QuizAttempt.user_id == user.id)
        .first()
    )

    attempts = (QuizAttempt.query
        .filter_by(user_id=user.id)
        .order_by(QuizAttempt.created_at.desc())
        .all()
    )

    # 誤答ログ（選択肢もDBにある前提）
    wrong_rows = (
        db.session.query(QuizAnswer.question_id, QuizAnswer.selected, QuizAttempt.attempt_no, QuizAttempt.created_at)
        .join(QuizAttempt, QuizAttempt.id == QuizAnswer.attempt_id)
        .filter(QuizAttempt.user_id == user.id, QuizAnswer.is_correct == False)
        .order_by(QuizAttempt.created_at.desc())
        .all()
    )

    # question_id ごとに「何を選んで間違えたか」を集計
    wrong_by_q = defaultdict(lambda: {"wrong_count": 0, "selected_counts": defaultdict(int), "examples": []})

    for qid, selected_json, attempt_no, created_at in wrong_rows:
        wrong_by_q[qid]["wrong_count"] += 1

        try:
            selected_list = json.loads(selected_json)
        except Exception:
            selected_list = []

        key = ",".join(selected_list) if selected_list else "(未選択)"
        wrong_by_q[qid]["selected_counts"][key] += 1

        # 直近の例を少し残す（任意）
        if len(wrong_by_q[qid]["examples"]) < 5:
            wrong_by_q[qid]["examples"].append({
                "attempt_no": attempt_no,
                "selected": selected_list,
                "created_at": created_at,
            })

    # テンプレートで扱いやすい形へ
    wrong_stats = []
    for qid, v in wrong_by_q.items():
        selected_counts_sorted = sorted(v["selected_counts"].items(), key=lambda x: x[1], reverse=True)
        wrong_stats.append({
            "question_id": qid,
            "wrong_count": v["wrong_count"],
            "selected_counts": selected_counts_sorted,
            "examples": v["examples"],
        })
    wrong_stats.sort(key=lambda x: x["wrong_count"], reverse=True)

    progress = Progress.query.filter_by(user_id=user.id).all()

    return render_template(
        "admin_user_detail.html",
        user=user,
        progress=progress,
        attempts=attempts,
        attempt_summary=attempt_summary,
        wrong_stats=wrong_stats
    )

# --- intro pages ---
@app.route("/intro_sql")
def intro_sql():
    return render_template("intro_sql.html")

@app.route("/intro_importance")
def intro_importance():
    return render_template("intro_importance.html")

@app.route("/intro_learning")
def intro_learning():
    return render_template("intro_learning.html")

@app.route("/intro_notice")
def intro_notice():
    return render_template("intro_notice.html")

@app.route("/intro_quiz")
def intro_quiz():
    return render_template("intro_quiz.html")

# --- exercise pages ---
@app.route("/exercise1")
def exercise1():
    return render_template("exercise1.html")

@app.route("/exercise2")
def exercise2():
    return render_template("exercise2.html")

@app.route("/exercise3")
def exercise3():
    return render_template("exercise3.html")

@app.route("/exercise4")
def exercise4():
    return render_template("exercise4.html")

@app.route("/exercise5")
def exercise5():
    return render_template("exercise5.html")

@app.route("/exercise6")
def exercise6():
    return render_template("exercise6.html")

@app.route("/exercise7")
def exercise7():
    return render_template("exercise7.html")

@app.route("/exercise8")
def exercise8():
    return render_template("exercise8.html")

@app.route("/exercise9")
def exercise9():
    return render_template("exercise9.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.context_processor
def inject_admin_username():
    return dict(ADMIN_USERNAME=os.environ.get("ADMIN_USERNAME"))

if __name__ == "__main__":
    app.run()

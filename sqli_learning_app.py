import os
from flask import Flask, render_template, request, redirect, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import OperationalError

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

def admin_required():
    if "user" not in session:
        return False
    user = User.query.filter_by(username=session["user"]).first()
    return user and user.is_admin


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

    users = User.query.all()
    data = []

    for u in users:
        done = Progress.query.filter_by(user_id=u.id, done=True).count()
        total = Progress.query.filter_by(user_id=u.id).count()

        data.append({
            "username": u.username,
            "done": done,
            "total": total
        })

    data.sort(key=lambda x: x["username"].lower())
    return render_template("admin.html", data=data)


@app.route("/admin/promote", methods=["POST"])
def promote_admin():
    if "user" not in session:
        abort(403)

    admin_username = os.environ.get("ADMIN_USERNAME")
    if not admin_username or session["user"] != admin_username:
        abort(403)

    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        abort(404)

    if not user.is_admin:
        user.is_admin = True
        db.session.commit()

    flash("管理者に昇格しました")
    return redirect("/admin")

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

if __name__ == "__main__":
    app.run()
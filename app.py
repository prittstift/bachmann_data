from flask_session import Session
from flask import Flask, redirect, render_template, request, session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, prepare_preresults
from woerter import woerter
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/",  methods=["GET", "POST"])
# @login_required
def index():
    if request.method == "POST":

        # Ensure username was submitted
        if request.form.get("year"):

            # Query database for username
            rows = db.execute("SELECT * FROM autorinnen WHERE teilnahmejahr = :year", {
                              "year": str(request.form.get("year"))}).fetchall()

            return prepare_preresults(rows)

        # Ensure username was submitted
        elif request.form.get("title"):

            # Query database for username
            rows = db.execute("SELECT * FROM autorinnen WHERE titel ILIKE CONCAT ('%', :title, '%')",
                              {"title": request.form.get("title")}).fetchall()

            return prepare_preresults(rows)

        elif request.form.get("author"):

            # Query database for username
            rows = db.execute("SELECT * FROM autorinnen WHERE autorinnenname ILIKE CONCAT ('%', :author, '%')",
                              {"author": request.form.get("author")}).fetchall()

            return prepare_preresults(rows)

        elif request.form.get("invited_by"):

            # Query database for username
            rows = db.execute("SELECT * FROM autorinnen WHERE eingeladen_von ILIKE CONCAT ('%', :invited_by, '%')",
                              {"invited_by": request.form.get("invited_by")}).fetchall()

            return prepare_preresults(rows)

        else:
            return apology("must provide input for year, title, author or invited_by", 400)
    else:
        return render_template("index.html")


@app.route("/search",  methods=["GET", "POST"])
# @login_required
def search():
    if request.method == "POST":
        return render_template("text.html")
    else:
        return render_template("search.html")


@app.route("/text/<int:search_result>",  methods=["GET"])
# @login_required
def text(search_result):
    rows = db.execute("SELECT * FROM autorinnen WHERE autorinnen.id = :text_id",
                      {"text_id": search_result}).fetchall()

    class FoundText:
        def __init__(self, rows, i):
            self.autorinnenname = rows[i]["autorinnenname"]
            self.titel = rows[i]["titel"]
            self.eingeladen_von = rows[i]["eingeladen_von"]
            self.teilnahmejahr = rows[i]["teilnahmejahr"]
            self.id = rows[i]["id"]
            self.land = rows[i]["land"]
            self.wohnort = rows[i]["wohnort"]
            self.geburtsjahr = rows[i]["geburtsjahr"]
            if rows[i]["preis_gewonnen"] == "True":
                rows_prices = db.execute("SELECT preistitel FROM preise WHERE autorinnenname = :name",
                                         {"name": rows[i]["autorinnenname"]}).fetchall()
                self.preis = ""
                for j in range(len(rows_prices)):
                    self.preis += rows_prices[j]["preistitel"]
                    if (j >= 0) and (j < (len(rows_prices) - 1)):
                        self.preis += ", "
            else:
                self.preis = "Fehlanzeige"

    results = []
    for i in range(len(rows)):
        results.append(FoundText(rows, i))

    dict = woerter

    labels = []
    values = []
    for key in dict[rows[i]["id"]].keys():
        labels.append(key)
    for value in dict[rows[i]["id"]].values():
        values.append(value)

    high = values[0]
    i = 0
    for i in range(10):
        if high % 10 == 0:
            max = high
            break
        else:
            high += 1
            i += 1

    return render_template("text2.html", results=results, labels=labels, values=values, max=max)


@app.route("/woerterchart", methods=["GET"])
def woerterchart():
    """Show chart of words"""

    dict = woerter

    labels = []
    values = []
    for key in dict[0].keys():
        labels.append(key)
    for value in dict[0].values():
        values.append(value)

    high = values[0]
    i = 0
    for i in range(10):
        if high % 10 == 0:
            max = high
            break
        else:
            high += 1
            i += 1

    return render_template("woerter.html", labels=labels, values=values, max=max)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username;",
                          {"username": request.form.get("username")}).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/landchart")
def landchart():
    """Show chart of countries"""

    return render_template("landchart.html")


@app.route("/ortchart")
def ortchart():
    """Show chart of cities"""

    return render_template("ortchart.html")


@app.route("/alterchart")
def alterchart():
    """Show chart of ages"""

    return render_template("alterchart.html")


@app.route("/kritchart")
def kritchart():
    """Show chart of critics"""

    return render_template("kritchart.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Missing username!", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Missing password!", 400)

        # Ensure password was submitted second time
        elif not request.form.get("confirmation"):
            return apology("Confirm password!", 400)

        # Ensure password was correctly confirmed
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Confirm password!", 400)

        # Generate hash
        hash = generate_password_hash(request.form.get("password"))
        username = request.form.get("username")

        # db.execute failure?
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", {
                            "username": username, "hash": hash})
        db.commit()
        if not result:
            return apology("Username already taken!", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": username}).fetchall()

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

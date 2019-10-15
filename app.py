from flask_session import Session
from flask import Flask, redirect, render_template, request, session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, prepare_preresults, prepare_chartdata, prepare_age, prepare_year
from woerter import woerter
import os
import collections
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
            if request.form.get("year") == "2019":
                temp = "3006"
            if request.form.get("year") == "2018":
                temp = "0807"
            if request.form.get("year") == "2017":
                temp = "0907"
            if request.form.get("year") == "2016":
                temp = "0307"
            if request.form.get("year") == "2015":
                temp = "0507"
            if request.form.get("year") == "2014":
                temp = "0607"

            # Query database for username
            rows = db.execute("SELECT * FROM autorinnen WHERE teilnahmejahr = :year", {
                              "year": (temp + str(request.form.get("year")))}).fetchall()

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

        elif request.form.get("price"):

            # Query database for username

            rows = db.execute("SELECT autorinnen.id, autorinnen.autorinnenname, autorinnen.titel, autorinnen.eingeladen_von, autorinnen.teilnahmejahr FROM autorinnen JOIN preise ON autorinnen.id = preise.autorinnen_id AND preistitel = :preis", {
                              "preis": request.form.get("price")}).fetchall()

            return prepare_preresults(rows)

        elif request.form.get("word"):

            ids = []
            for i in range(1, len(woerter)):
                for key in woerter[i].keys():
                    if key == request.form.get("word").lower():
                        ids.append(i)
            t = tuple(ids)

            if ids == []:
                return apology("must provide exact word OR word does not appear in texts", 400)
            else:
                # Query database for username
                rows = db.execute("SELECT * FROM autorinnen WHERE id IN :id",
                                  {"id": t}).fetchall()

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
            self.teilnahmejahr = prepare_year(rows[i]["teilnahmejahr"])
            self.id = rows[i]["id"]
            self.land = rows[i]["land"]
            self.wohnort = rows[i]["wohnort"]
            self.geburtsjahr = prepare_year(rows[i]["geburtsjahr"])
            self.link = rows[i]["webseite"]
            if rows[i]["preis_gewonnen"] == "True":
                rows_prices = db.execute("SELECT preistitel FROM preise WHERE autorinnen_id = :name",
                                         {"name": rows[i]["id"]}).fetchall()
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


@app.route("/kritikerinnen", methods=["GET"])
def kritikerinnen():
    """Show chart of critics"""

    rows = db.execute("SELECT * FROM autorinnen").fetchall()

    class FoundText:
        def __init__(self, rows, i):
            self.autorinnenname = rows[i]["autorinnenname"]
            self.titel = rows[i]["titel"]
            self.eingeladen_von = rows[i]["eingeladen_von"]
            self.teilnahmejahr = prepare_year(rows[i]["teilnahmejahr"])
            self.id = rows[i]["id"]
            self.land = rows[i]["land"]
            self.wohnort = rows[i]["wohnort"]
            self.geburtsjahr = prepare_year(rows[i]["geburtsjahr"])
            if rows[i]["preis_gewonnen"] == "True":
                rows_prices = db.execute("SELECT preistitel FROM preise WHERE autorinnen_id = :name",
                                         {"name": rows[i]["id"]}).fetchall()
                self.preis = ""
                for j in range(len(rows_prices)):
                    self.preis += rows_prices[j]["preistitel"]
                    if (j >= 0) and (j < (len(rows_prices) - 1)):
                        self.preis += ", "
                    if rows_prices[j]["preistitel"] == "Ingeborg-Bachmann-Preis":
                        self.bachmann = True
                    else:
                        self.bachmann = False
            else:
                self.preis = "Fehlanzeige"

    results = []
    for i in range(len(rows)):
        results.append(FoundText(rows, i))

    rows_preis = db.execute("SELECT * FROM kritikerpreis ORDER BY total DESC").fetchall()

    rows_preis_percent = db.execute("SELECT * FROM kritikerpreis ORDER BY percent DESC").fetchall()

    labels = []
    values_priceless = []
    values_price = []
    labels_percent = []
    values_percent = []
    values_bachmann = []
    for k in range(len(rows_preis)):
        labels.append(rows_preis[k]["kritikerin"])
        values_priceless.append(rows_preis[k]["preis_false"])
        bachmann = rows_preis[k]["bachmann_preis"]
        if bachmann != 0:
            values_price.append((rows_preis[k]["preis_true"] - bachmann))
        else:
            values_price.append(rows_preis[k]["preis_true"])
        values_bachmann.append(bachmann)
        labels_percent.append(rows_preis_percent[k]["kritikerin"])
        values_percent.append(round(rows_preis_percent[k]["percent"], 2))

    return render_template("kritikerinnen.html", results=results, labels=labels, values_priceless=values_priceless, values_price=values_price, values_bachmann=values_bachmann, labels_percent=labels_percent, values_percent=values_percent)


@app.route("/laender", methods=["GET"])
def laender():
    """Show chart of countries"""

    rows = db.execute("SELECT * FROM autorinnen").fetchall()

    class FoundText:
        def __init__(self, rows, i):
            self.autorinnenname = rows[i]["autorinnenname"]
            self.titel = rows[i]["titel"]
            self.eingeladen_von = rows[i]["eingeladen_von"]
            self.teilnahmejahr = prepare_year(rows[i]["teilnahmejahr"])
            self.id = rows[i]["id"]
            self.land = rows[i]["land"]
            self.wohnort = rows[i]["wohnort"]
            self.geburtsjahr = prepare_year(rows[i]["geburtsjahr"])
            if rows[i]["preis_gewonnen"] == "True":
                rows_prices = db.execute("SELECT preistitel FROM preise WHERE autorinnen_id = :name",
                                         {"name": rows[i]["id"]}).fetchall()
                self.preis = ""
                for j in range(len(rows_prices)):
                    self.preis += rows_prices[j]["preistitel"]
                    if (j >= 0) and (j < (len(rows_prices) - 1)):
                        self.preis += ", "
                    if rows_prices[j]["preistitel"] == "Ingeborg-Bachmann-Preis":
                        self.bachmann = True
                    else:
                        self.bachmann = False
            else:
                self.preis = "Fehlanzeige"

    results = []
    for i in range(len(rows)):
        results.append(FoundText(rows, i))

    rows_preis = db.execute("SELECT * FROM landpreis ORDER BY total DESC").fetchall()

    rows_preis_percent = db.execute("SELECT * FROM landpreis ORDER BY percent DESC").fetchall()

    labels = []
    values_priceless = []
    values_price = []
    labels_percent = []
    values_percent = []
    values_bachmann = []
    temp_percent = []
    for k in range(len(rows_preis)):
        labels.append(rows_preis[k]["land"])
        values_priceless.append(rows_preis[k]["preis_false"])
        bachmann = rows_preis[k]["bachmann_preis"]
        if bachmann != 0:
            values_price.append((rows_preis[k]["preis_true"] - bachmann))
        else:
            values_price.append(rows_preis[k]["preis_true"])
        values_bachmann.append(bachmann)
        if rows_preis_percent[k]["id"] not in range(1, 4):
            temp_percent.append(round(rows_preis_percent[k]["percent"], 2))
        else:
            labels_percent.append(rows_preis_percent[k]["land"])
            values_percent.append(round(rows_preis_percent[k]["percent"], 2))
    temp_avg = 0
    for percent in temp_percent:
        temp_avg += percent
        average_percent_other_countries = temp_avg / len(temp_percent)
    labels_percent.append("andere Länder")
    values_percent.append(round(average_percent_other_countries, 2))

    return render_template("laender.html", results=results, labels=labels, values_priceless=values_priceless, values_price=values_price, values_bachmann=values_bachmann, labels_percent=labels_percent, values_percent=values_percent)


@app.route("/orte", methods=["GET"])
def orte():
    """Show chart of cities"""

    rows = db.execute("SELECT * FROM autorinnen").fetchall()

    class FoundText:
        def __init__(self, rows, i):
            self.autorinnenname = rows[i]["autorinnenname"]
            self.titel = rows[i]["titel"]
            self.eingeladen_von = rows[i]["eingeladen_von"]
            self.teilnahmejahr = prepare_year(rows[i]["teilnahmejahr"])
            self.id = rows[i]["id"]
            self.land = rows[i]["land"]
            self.wohnort = rows[i]["wohnort"]
            self.geburtsjahr = prepare_year(rows[i]["geburtsjahr"])
            if rows[i]["preis_gewonnen"] == "True":
                rows_prices = db.execute("SELECT preistitel FROM preise WHERE autorinnen_id = :name",
                                         {"name": rows[i]["id"]}).fetchall()
                self.preis = ""
                for j in range(len(rows_prices)):
                    self.preis += rows_prices[j]["preistitel"]
                    if (j >= 0) and (j < (len(rows_prices) - 1)):
                        self.preis += ", "
                    if rows_prices[j]["preistitel"] == "Ingeborg-Bachmann-Preis":
                        self.bachmann = True
                    else:
                        self.bachmann = False
            else:
                self.preis = "Fehlanzeige"

    results = []
    for i in range(len(rows)):
        results.append(FoundText(rows, i))

    rows_preis = db.execute("SELECT * FROM ortpreis ORDER BY total DESC").fetchall()

    rows_preis_percent = db.execute("SELECT * FROM ortpreis ORDER BY percent DESC").fetchall()

    labels = []
    values_priceless = []
    values_price = []
    labels_percent = []
    values_percent = []
    values_bachmann = []
    temp_percent = []
    for k in range(len(rows_preis)):
        if rows_preis[k]["total"] > 1:
            labels.append(rows_preis[k]["ort"])
            values_priceless.append(rows_preis[k]["preis_false"])
            bachmann = rows_preis[k]["bachmann_preis"]
            if bachmann != 0:
                values_price.append((rows_preis[k]["preis_true"] - bachmann))
            else:
                values_price.append(rows_preis[k]["preis_true"])
            values_bachmann.append(bachmann)
        if rows_preis_percent[k]["total"] > 1:
            labels_percent.append(rows_preis_percent[k]["ort"])
            values_percent.append(round(rows_preis_percent[k]["percent"], 2))
        else:
            temp_percent.append(round(rows_preis_percent[k]["percent"], 2))
    temp_avg = 0
    for percent in temp_percent:
        temp_avg += percent
        average_percent_other_countries = temp_avg / len(temp_percent)
    labels_percent.append("andere Orte")
    values_percent.append(round(average_percent_other_countries, 2))

    return render_template("orte.html", results=results, labels=labels, values_priceless=values_priceless, values_price=values_price, values_bachmann=values_bachmann, labels_percent=labels_percent, values_percent=values_percent)


@app.route("/alter", methods=["GET"])
def alter():
    """Show chart of ages"""

    rows = db.execute("SELECT * FROM autorinnen").fetchall()

    class FoundText:
        def __init__(self, rows, i):
            self.autorinnenname = rows[i]["autorinnenname"]
            self.titel = rows[i]["titel"]
            self.eingeladen_von = rows[i]["eingeladen_von"]
            self.teilnahmejahr = prepare_year(rows[i]["teilnahmejahr"])
            self.id = rows[i]["id"]
            self.land = rows[i]["land"]
            self.wohnort = rows[i]["wohnort"]
            self.geburtsjahr = prepare_year(rows[i]["geburtsjahr"])
            self.alter = prepare_age(rows[i]["geburtsjahr"], rows[i]["teilnahmejahr"])
            if rows[i]["preis_gewonnen"] == "True":
                rows_prices = db.execute("SELECT preistitel FROM preise WHERE autorinnen_id = :name",
                                         {"name": rows[i]["id"]}).fetchall()
                self.preis = ""
                for j in range(len(rows_prices)):
                    self.preis += rows_prices[j]["preistitel"]
                    if (j >= 0) and (j < (len(rows_prices) - 1)):
                        self.preis += ", "
                    if rows_prices[j]["preistitel"] == "Ingeborg-Bachmann-Preis":
                        self.bachmann = True
                    else:
                        self.bachmann = False
                    if rows_prices[j]["preistitel"] == "BKS Bank-Publikumspreis":
                        self.publikum = True
                    else:
                        self.publikum = False
            else:
                self.preis = "Fehlanzeige"
                self.bachmann = False

    results = []
    for i in range(len(rows)):
        results.append(FoundText(rows, i))

    kein_Preis = []
    bachmannpreis = []
    andere_Preise = []
    preise = []
    alter = []
    publikum_temp = []
    publikum_avg = 0
    for result in results:
        dict = {}
        dict[True] = result.teilnahmejahr
        dict[False] = result.alter
        alter.append(dict)
        if result.preis == "Fehlanzeige":
            dict = {}
            dict[True] = result.teilnahmejahr
            dict[False] = result.alter
            kein_Preis.append(dict)
        if result.preis != "Fehlanzeige":
            dict = {}
            dict[True] = result.teilnahmejahr
            dict[False] = result.alter
            preise.append(dict)
            if result.publikum == True:
                publikum_temp.append(result.alter)
                publikum_avg += result.alter
            if result.bachmann == True:
                dict = {}
                dict[True] = result.teilnahmejahr
                dict[False] = result.alter
                bachmannpreis.append(dict)
            else:
                dict = {}
                dict[True] = result.teilnahmejahr
                dict[False] = result.alter
                andere_Preise.append(dict)

    publikum = list(reversed(publikum_temp))
    publikum_avg = round((publikum_avg / len(publikum)), 2)

    return render_template("alter.html", results=results, kein_Preis=kein_Preis, bachmannpreis=bachmannpreis, andere_Preise=andere_Preise, preise=preise, alter=alter, publikum=publikum, publikum_avg=publikum_avg)


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

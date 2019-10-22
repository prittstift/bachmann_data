from flask_session import Session
from flask import Flask, redirect, render_template, request, session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, get_search_data, prepare_preresults, prepare_chartdata, prepare_age, prepare_year
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

        criteria = ["year", "title", "author", "invited_by", "price", "word"]

        for criterion in criteria:
            # Search by criterion
            if request.form.get(criterion):

                search_term = request.form.get(criterion)

                return redirect("/search/q={}&criterion={}".format(str(search_term), str(criterion)))
        # Incorrect search
        else:
            return apology("must provide input for year, title, author or invited_by", 400)

    # request method "GET"
    else:
        return render_template("index.html")


@app.route("/search/q=<string:search_term>&criterion=<string:criterion>",  methods=["GET"])
# @login_required
def search(search_term, criterion):

    rows = get_search_data(search_term, criterion)

    results = prepare_preresults(rows)

    return render_template("search.html", results=results, criterion=criterion, search_term=search_term)


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

    autorin_id = rows[0]["id"]

    rows_fazit = db.execute("SELECT fazit FROM juryfazit WHERE autorin_id = :id",
                            {"id": int(autorin_id)}).fetchall()
    fazit = rows_fazit[0]["fazit"]

    if autorin_id in range(1, 15):
        rows_short = db.execute("SELECT kritikerin, shortlist_kritiker, eingeladen FROM shortlist WHERE autorin_id = :id",
                                {"id": int(autorin_id)}).fetchall()

        class ShortList:
            def __init__(self, rows_short):
                self.vote = []
                for j in range(len(rows_short)):
                    if rows_short[j]["shortlist_kritiker"] == "True":
                        self.vote.append("true")
                    if rows_short[j]["shortlist_kritiker"] == "False":
                        if rows_short[j]["eingeladen"] == "True":
                            self.vote.append(0)
                        else:
                            self.vote.append("false")
                    else:
                        pass

        shortlist = ShortList(rows_short)

        return render_template("text2.html", search_result=search_result, results=results, labels=labels, values=values, max=max, fazit=fazit, shortlist=shortlist)
    else:
        return render_template("text2.html", search_result=search_result, results=results, labels=labels, values=values, max=max, fazit=fazit)


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


@app.route("/pie", methods=["GET", "POST"])
def pie():
    if request.method == "GET":
        return render_template("pie.html")


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

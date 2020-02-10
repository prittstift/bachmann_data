from flask_session import Session
from flask import Flask, redirect, render_template, request, session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, get_search_data, prepare_results, prepare_barchart, prepare_age, prepare_year, prepare_woerterchart, prepare_publications, prepare_autorin_link
from woerter import woerter
import os
import math
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

# index page
@app.route("/",  methods=["GET", "POST"])
def index():
    if request.method == "POST":

        criteria = ["year", "title", "author", "invited_by", "price", "word"]
        # String  of inputs that have been searched for
        search_term = ""
        # String of criteria that have been searched by
        mult_crit = ""
        
        for criterion in criteria:
            # Search by criterion
            temp = request.form.get(criterion)
            if temp != None and temp != "":
                search_term += str(temp) + "+"
                mult_crit += criterion + "+"
        if search_term == "":
            # Incorrect search
            return apology("must provide input", 404)
        if "+" == search_term[-1]:
            search_term = search_term[:-1]
        if "+" == mult_crit[-1]:
            mult_crit = mult_crit[:-1]

        return redirect("search/q={}&criterion={}".format(str(search_term), str(mult_crit)))

    # request method "GET"
    else:
        return render_template("index.html")

# search page
@app.route("/search/q=<string:search_term>&criterion=<string:criterion>",  methods=["GET"])
def search(search_term, criterion):
    # Query database
    rows = get_search_data(search_term, criterion)
    # Error if word has been searched for that doesn't appear in table
    if rows == False:
        return apology("word is not part of the 20 most frequent words in any text", 400)
    # Prepare results in results object
    results = prepare_results(rows, "search", None)

    return render_template("search_cards.html", results=results, criterion=criterion, search_term=search_term)

# text overview page
@app.route("/text/<int:search_result>",  methods=["GET"])
def text(search_result):
    if search_result not in range(1,829):
        return apology("Page Not Found", 404)
    # Query database
    rows = db.execute("SELECT * FROM autorinnen WHERE autorinnen.id = :text_id",
                      {"text_id": search_result}).fetchall()
    # Prepare results in results object
    results = prepare_results(rows, "text", None)

    autorin_id = rows[0]["id"]
    labels = []
    values = []
    max = 0
    # Prepare data for chart
    if autorin_id <= 139:
        labels, values, max = prepare_woerterchart(woerter, search_result)

    
    if autorin_id <= 304:
        # Query database for quotation
        rows_fazit = db.execute("SELECT fazit FROM juryfazit WHERE autorin_id = :id",
                                {"id": int(autorin_id)}).fetchall()
        fazit = rows_fazit[0]["fazit"]
        fazit = fazit.strip()
        
        # Query database for publications
        autorin_name = rows[0]["autorinnenname"]
        autorin_link = prepare_autorin_link(autorin_name)
        
        rows_publ = db.execute("SELECT * FROM perlentaucher_publikationen WHERE autorinnen_id = :text_id",
                      {"text_id": autorin_id}).fetchall()
        
        publications = prepare_publications(rows_publ)
        sum_publications = len(publications)
        if rows_publ[0][2] == "None":
            sum_publications = 0
        
    else:
        fazit = ""
        publications = []
        sum_publications = 0
        autorin_link = ""

    # Define column width for grid system, if no doughnut chart on the right
    infotable_col_width = 12

    # if year == 2019, add doughnut chart with final voting results
    if autorin_id in range(1, 15):
        infotable_col_width = 6
        # Query database for voting results by jury member
        rows_short = db.execute("SELECT kritikerin, shortlist_kritiker, eingeladen FROM shortlist WHERE autorin_id = :id",
                                {"id": int(autorin_id)}).fetchall()
        # Create results object

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
    else:
        shortlist = []

    return render_template("text_overview.html", search_result=int(search_result), results=results, publications=publications, sum_publications=sum_publications, autorin_link=autorin_link, labels=labels, values=values, max=max, fazit=fazit, shortlist=shortlist, infotable_col_width=infotable_col_width)
    

# page with chart on most common words in all texts
@app.route("/woerterchart", methods=["GET"])
def woerterchart():
    """Show chart of words"""

    alles_id = 0
    # Get data for chart
    labels, values, max = prepare_woerterchart(woerter, alles_id)

    return render_template("woerter.html", labels=labels, values=values, max=max)

# logic for pages with charts about depency between won prices and various criteria
@app.route("/charts/<string:criterion>", methods=["GET"])
def kritikerinnen(criterion):
    """Show charts by criterion"""
    criteria = ["kritikerinnen", "laender", "orte", "wochentage", "w-m"]
    if criterion not in criteria:
        return apology("Page Not Found",404)
    # Query database (table with individual infos on authors not yet implemented)
    rows = db.execute("SELECT * FROM autorinnen WHERE id <= 304").fetchall()
    # Safe results in results object
    results = prepare_results(rows, "chart", None)
    # Adjust charts for different criteria
    percent_chart_height = 60
    header_time = "(2010-2019)"
    if criterion == "kritikerinnen":
        table = "kritikerpreis"
        col = "kritikerin"
        max_bar = 20
    elif criterion == "laender":
        criterion = "länder"
        table = "landpreis"
        col = "land"
        max_bar = 500
        percent_chart_height = 20
        header_time = "(1977-2019)"
    elif criterion == "orte":
        table = "ortpreis"
        col = "ort"
        max_bar = 350
        header_time = "(1977-2019)"
    elif criterion == "wochentage":
        table = "vortragspreis"
        col = "vorgetragen_am"
        max_bar = 130
        percent_chart_height = 20
        header_time = "(1998-2019)"
    elif criterion == "w-m":
        table = "geschlechtpreis"
        col = "geschlecht"
        max_bar = 600
        percent_chart_height = 20
        header_time = "(1977-2019)"
    # Query chart table
    rows_preis = db.execute("SELECT * FROM {} ORDER BY total DESC".format(table)).fetchall()
    # Query chart table
    rows_preis_percent = db.execute(
        "SELECT * FROM {} ORDER BY percent DESC".format(table)).fetchall()
    # Safe results in object with all chart data
    chartdata = prepare_barchart(col, rows_preis, rows_preis_percent)

    return render_template("barcharts.html", criterion=criterion.title(), max_bar=max_bar, percent_chart_height=percent_chart_height, results=results, chartdata=chartdata, header_time=header_time)

# page with chart on age
@app.route("/alter", methods=["GET"])
def alter():
    """Show chart of ages"""
    # Query database
    rows = db.execute("SELECT * FROM autorinnen WHERE id != 181").fetchall()
    # Safe results in object
    results = prepare_results(rows, "chart", "alter")
    # Prepare data for scatterplot and line chart
    kein_Preis = []
    bachmannpreis = []
    andere_Preise = []
    for result in results:
        if result.preis == "Fehlanzeige":
            dict = {}
            dict[True] = result.teilnahmejahr
            dict[False] = result.alter
            kein_Preis.append(dict)
        if result.preis != "Fehlanzeige":
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
    
    rows_alter = db.execute("SELECT * FROM alterpreis").fetchall()

    class Result_alter:
            def __init__(self, rows_alter, i):
                self.jahr = rows_alter[i]["jahr"]
                self.gruppe = rows_alter[i]["gruppe"]
                if math.isnan(rows_alter[i]["alter"]) == True:
                    self.alter = ""
                else:
                    self.alter = rows_alter[i]["alter"]

    results_alter = []
    for i in range(len(rows_alter)):
            results_alter.append(Result_alter(rows_alter, i))

    for result in results_alter:
        if result.jahr == "abs" and result.gruppe == "absolut":
            alter_absolut = result.alter
        if result.jahr == "abs" and result.gruppe == "preis_gewonnen":
            alter_preis_gewonnen = result.alter
        if result.jahr == "abs" and result.gruppe == "bachmann":
            alter_bachmann = result.alter
        if result.jahr == "abs" and result.gruppe == "publikum":
            alter_publikum = result.alter

    return render_template("alter.html", results=results, kein_Preis=kein_Preis, bachmannpreis=bachmannpreis, andere_Preise=andere_Preise, alter_absolut=alter_absolut, alter_preis_gewonnen=alter_preis_gewonnen, alter_bachmann=alter_bachmann, alter_publikum=alter_publikum, results_alter=results_alter)

# logic for login page (if implemented in the future)
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


@app.route("/about")
def about():

    return render_template("about.html")


# logic for logout (if implemented)
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

# logic for registration (if implemented)
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


# Prevent site crashing
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

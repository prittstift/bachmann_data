import datetime
from datetime import date
from flask import redirect, render_template, request, session
from functools import wraps
from woerter import woerter
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Logic for form on index.html


def get_search_data(search_term, criterion):

    if criterion == "year":
        # Day and month of competition to match data in database
        days = {2019: "3006", 2018: "0807", 2017: "0907",
                2016: "0307", 2015: "0507", 2014: "0607", 2013: "0707", 2012: "0807", 2011: "1007", 2010: "2706"}
        # Query database for year of competition
        rows = db.execute("SELECT * FROM autorinnen WHERE teilnahmejahr = :year", {
                          "year": (days[int(search_term)] + str(search_term))}).fetchall()
        return rows

    elif criterion == "word":
        ids = []
        for i in range(1, len(woerter)):
            for key in woerter[i].keys():
                if key == search_term.lower():
                    ids.append(i)
        t = tuple(ids)

        if ids == []:
            # Incorrect search
            return apology("must provide exact word OR word does not appear in texts", 400)
        else:
            # Query database
            rows = db.execute("SELECT * FROM autorinnen WHERE id IN :id",
                              {"id": t}).fetchall()
            return rows
    elif criterion == "price":
        # Query database
        rows = db.execute("SELECT autorinnen.id, autorinnen.autorinnenname, autorinnen.titel, autorinnen.eingeladen_von, autorinnen.teilnahmejahr FROM autorinnen JOIN preise ON autorinnen.id = preise.autorinnen_id AND preistitel = :price", {
                          "price": search_term}).fetchall()
        return rows
    else:
        if criterion == "title":
            sql_comparison = "titel ILIKE CONCAT ('%', :title, '%')"
        elif criterion == "author":
            sql_comparison = "autorinnenname ILIKE CONCAT ('%', :author, '%')"
        elif criterion == "invited_by":
            sql_comparison = "eingeladen_von = :invited_by"
        # Query database
        rows = db.execute("SELECT * FROM autorinnen WHERE {}".format(sql_comparison), {
                          "{}".format(criterion): search_term}).fetchall()
        return rows

# Return year from datetime string


def prepare_year(data):

    year = datetime.datetime.strptime(data, '%d%m%Y').date().year
    return year

# Return age from datetime strings


def prepare_age(birthday, year):

    date_temp = datetime.datetime.strptime(birthday, '%d%m%Y').date()
    year_temp = datetime.datetime.strptime(year, '%d%m%Y').date()
    age_temp = year_temp - date_temp
    age = float(age_temp.days) / 365.25
    age = round(age, 2)
    return age

# Safe results from query in object


def prepare_results(rows, site, special):

    class Result:
        def __init__(self, rows, i):
            self.autorinnenname = rows[i]["autorinnenname"]
            self.titel = rows[i]["titel"]
            self.eingeladen_von = rows[i]["eingeladen_von"]
            self.teilnahmejahr = prepare_year(rows[i]["teilnahmejahr"])
            self.id = rows[i]["id"]

            if (site == "text") or (site == "chart"):
                self.land = rows[i]["land"]
                self.wohnort = rows[i]["wohnort"]
                self.geburtsjahr = prepare_year(rows[i]["geburtsjahr"])
                self.vorgetragen_am = rows[i]["vorgetragen_am"]
                self.link = rows[i]["webseite"]
                if special == "alter":
                    self.alter = prepare_age(rows[i]["geburtsjahr"], rows[i]["teilnahmejahr"])
                if rows[i]["preis_gewonnen"] == "True":
                    rows_prices = db.execute("SELECT preistitel FROM preise WHERE autorinnen_id = :name",
                                             {"name": rows[i]["id"]}).fetchall()
                    self.preis = ""
                    for j in range(len(rows_prices)):
                        self.preis += rows_prices[j]["preistitel"]
                        if (j >= 0) and (j < (len(rows_prices) - 1)):
                            self.preis += ", "
                        if site == "chart":
                            if rows_prices[j]["preistitel"] == "Ingeborg-Bachmann-Preis":
                                self.bachmann = True
                            else:
                                self.bachmann = False
                            if special == "alter":
                                if rows_prices[j]["preistitel"] == "BKS Bank-Publikumspreis":
                                    self.publikum = True
                                else:
                                    self.publikum = False
                else:
                    self.preis = "Fehlanzeige"

    results = []
    for i in range(len(rows)):
        results.append(Result(rows, i))

    return results

# Logic for chart with most common words


def prepare_woerterchart(woerter, current_id):
    labels = []
    values = []
    for key in woerter[current_id].keys():
        labels.append(key)
    for value in woerter[current_id].values():
        values.append(value)
    # Define max value of chart
    high = values[0]
    i = 0
    for i in range(10):
        if high % 10 == 0:
            max = high
            break
        else:
            high += 1
            i += 1

    return labels, values, max

# Prepare data for barcharts


def prepare_barchart(col, rows_preis, rows_preis_percent):

    class Chartdata:
        def __init__(self, col, rows_preis, rows_preis_percent):
            self.labels = []
            self.values_priceless = []
            self.values_price = []
            self.labels_percent = []
            self.values_percent = []
            self.values_bachmann = []

            # Define which labels are shown individually by setting min number of value
            relevance_border_bar = 0
            if col == "ort":
                relevance_border_bar = 2
            if col == "land":
                relevance_border_bar = 5
            if col == "kritikerin":
                relevance_border_bar = 5

            relevance_border_percent = 0
            if col == "land":
                relevance_border_percent = 3
            if col == "ort":
                relevance_border_percent = 1

            if relevance_border_bar != 0:
                temp_values_priceless = 0
                temp_values_price = 0
                temp_values_bachmann = 0

            if relevance_border_percent != 0:
                temp_percent = []

            # Safe labels and values for stacked bar chart
            for k in range(len(rows_preis)):
                if rows_preis[k]["total"] > relevance_border_bar:
                    self.labels.append(rows_preis[k][col])
                    self.values_priceless.append(rows_preis[k]["preis_false"])
                    bachmann = rows_preis[k]["bachmann_preis"]
                    if bachmann != 0:
                        self.values_price.append((rows_preis[k]["preis_true"] - bachmann))
                    else:
                        self.values_price.append(rows_preis[k]["preis_true"])
                    self.values_bachmann.append(bachmann)
                else:
                    temp_values_priceless += rows_preis[k]["preis_false"]
                    bachmann = rows_preis[k]["bachmann_preis"]
                    if bachmann != 0:
                        temp_values_price += (rows_preis[k]["preis_true"] - bachmann)
                    else:
                        temp_values_price += rows_preis[k]["preis_true"]
                    temp_values_bachmann += bachmann
                # Safe labels and values for horizontal bar chart
                if relevance_border_percent != 0:
                    if rows_preis_percent[k]["total"] > relevance_border_percent:
                        self.labels_percent.append(rows_preis_percent[k][col])
                        self.values_percent.append(round(rows_preis_percent[k]["percent"], 2))
                    else:
                        temp_percent.append(round(rows_preis_percent[k]["percent"], 2))
                else:
                    self.labels_percent.append(rows_preis_percent[k][col])
                    self.values_percent.append(round(rows_preis_percent[k]["percent"], 2))

            if relevance_border_bar != 0:
                if col == "ort":
                    other_label = "Orte"
                if col == "land":
                    other_label = "Länder"
                if col == "kritikerin":
                    other_label = "Kritikerinnen"
                self.labels.append("andere {}".format(other_label))
                self.values_price.append(temp_values_price)
                self.values_priceless.append(temp_values_priceless)
                self.values_bachmann.append(temp_values_bachmann)

            if relevance_border_percent != 0:
                if col == "land":
                    other_label = "Länder"
                if col == "ort":
                    other_label = "Orte"
                temp_avg = 0
                for percent in temp_percent:
                    temp_avg += percent
                    average_percent_other = temp_avg / len(temp_percent)
                self.labels_percent.append("andere {}".format(other_label))
                self.values_percent.append(round(average_percent_other, 2))

    chartdata = Chartdata(col, rows_preis, rows_preis_percent)
    return chartdata

# render apology page


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

# Logic for internal sites


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

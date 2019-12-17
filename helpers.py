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


def get_search_data(search_term, criterion):
    # Logic for form on index.html (mulitple criteria search)

    # Create map to access all criteria and all search_terms for query
    term_list = search_term.split("+")
    criterion_list = criterion.split("+")
    crit_term_map = {}
    for i in range(len(criterion_list)):
        crit_term_map[criterion_list[i]] = term_list[i]

    # Create dictionnary for query
    sql_explain = {}

    # Create beginning of query command
    select = "SELECT autorinnen.id, autorinnen.autorinnenname, autorinnen.titel, autorinnen.eingeladen_von, autorinnen.teilnahmejahr FROM autorinnen JOIN preise_new ON autorinnen.id = preise_new.autorinnen_id AND "

    # Count, if condition for query command was added
    crit_counter = 0

    if "year" in criterion_list:
        # Day and month of competition to match data in database
        days = {2019: "3006", 2018: "0807", 2017: "0907",
                2016: "0307", 2015: "0507", 2014: "0607", 2013: "0707", 2012: "0807", 2011: "1007", 2010: "2706", 2009: "2806", 2008: "2806", 2007: "0107", 2006: "2506", 2005: "2606", 2004: "2706", 2003: "2906", 2002: "3006", 2001: "0107", 2000: "0207"}

        # Add condition to query command
        select += "autorinnen.teilnahmejahr = :year"
        # Add element to query dictionnary
        sql_explain["year"] = (days[int(crit_term_map["year"])] + str(crit_term_map["year"]))
        # New condition was added
        crit_counter += 1

    if "word" in criterion_list:
        # Find all id's where search term matches any of 20 most common words in text
        ids = []
        for i in range(1, len(woerter)):
            for key in woerter[i].keys():
                if crit_term_map["word"].lower() in key:
                    ids.append(i)
        t = tuple(ids)

        if ids == []:
            # Incorrect search
            return False
        else:
            if crit_counter == 1:
                select += " AND "
                crit_counter = 0
            select += "autorinnen.id IN :id"
            sql_explain["id"] = t
            crit_counter += 1

    # Preparation for query if criterion is price, title, author or invited_by
    dict = {"price": "preistitel", "title": "titel",
            "author": "autorinnenname", "invited_by": "eingeladen_von"}
    for element in dict:
        if element in criterion_list:
            if crit_counter == 1:
                select += " AND "
                crit_counter = 0
            if element == "invited_by":
                select += "eingeladen_von = :invited_by"
            else:
                select += "{} ILIKE CONCAT ('%', :{}, '%')".format(dict[element], element)
            sql_explain["{}".format(element)] = crit_term_map["{}".format(element)]
            crit_counter += 1

    # Query database
    rows = db.execute(select, sql_explain).fetchall()
    return rows


def prepare_year(data):
    # Return year from datetime string
    year = datetime.datetime.strptime(data, '%d%m%Y').date().year
    return year


def prepare_age(birthday, year):
    # Return age from datetime strings
    date_temp = datetime.datetime.strptime(birthday, '%d%m%Y').date()
    year_temp = datetime.datetime.strptime(year, '%d%m%Y').date()
    age_temp = year_temp - date_temp
    age = float(age_temp.days) / 365.25
    age = round(age, 2)
    return age


def prepare_results(rows, site, special):
    # Safe results from query in object
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
                if self.id == 181:
                    self.geburtsjahr = "im letzten Drittel des 20. Jahrhunderts"
                else:
                    self.geburtsjahr = prepare_year(rows[i]["geburtsjahr"])
                self.vorgetragen_am = rows[i]["vorgetragen_am"]
                self.link = rows[i]["webseite"]
                if special == "alter":
                    self.alter = prepare_age(rows[i]["geburtsjahr"], rows[i]["teilnahmejahr"])
                if rows[i]["preis_gewonnen"] == "True":
                    rows_prices = db.execute("SELECT preistitel FROM preise_new WHERE autorinnen_id = :name",
                                             {"name": rows[i]["id"]}).fetchall()
                    self.preis = rows_prices[0]["preistitel"]
                    if site == "chart":
                        if "Ingeborg-Bachmann-Preis" in rows_prices[0]["preistitel"]:
                            self.bachmann = True
                        else:
                            self.bachmann = False
                        if special == "alter":
                            if "Publikumspreis" in rows_prices[0]["preistitel"]:
                                self.publikum = True
                            else:
                                self.publikum = False
                else:
                    self.preis = "Fehlanzeige"

    results = []
    for i in range(len(rows)):
        results.append(Result(rows, i))

    return results


def prepare_woerterchart(woerter, current_id):
    # Logic for chart with most common words
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


def prepare_barchart(col, rows_preis, rows_preis_percent):
    # Prepare data for barcharts
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


def apology(message, code=400):
    # render apology page
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


def login_required(f):
    # Logic for internal sites
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

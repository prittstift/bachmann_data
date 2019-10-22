import requests
import urllib.parse
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

    if criterion == "year":
        days = {2019: "3006", 2018: "0807", 2017: "0907",
                2016: "0307", 2015: "0507", 2014: "0607"}

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

        rows = db.execute("SELECT * FROM autorinnen WHERE {}".format(sql_comparison), {
                          "{}".format(criterion): search_term}).fetchall()

        return rows


def prepare_year(data):

    year = datetime.datetime.strptime(data, '%d%m%Y').date().year
    return year


def prepare_age(birthday, year):

    date_temp = datetime.datetime.strptime(birthday, '%d%m%Y').date()
    year_temp = datetime.datetime.strptime(year, '%d%m%Y').date()
    age_temp = year_temp - date_temp
    age = float(age_temp.days) / 365.25
    age = round(age, 2)
    return age


def prepare_preresults(rows):

    class Preresult:
        def __init__(self, rows, i):
            self.autorinnenname = rows[i]["autorinnenname"]
            self.titel = rows[i]["titel"]
            self.eingeladen_von = rows[i]["eingeladen_von"]
            self.teilnahmejahr = prepare_year(rows[i]["teilnahmejahr"])
            self.id = rows[i]["id"]

    results = []
    for i in range(len(rows)):
        results.append(Preresult(rows, i))

    return results


def prepare_chartdata(rows_preis, rows_preis_percent):

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

    return labels, values_priceless, values_price, labels_percent, values_percent, values_bachmann


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

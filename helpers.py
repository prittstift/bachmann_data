import requests
import urllib.parse
import datetime
from datetime import date
from flask import redirect, render_template, request, session
from functools import wraps


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

    return render_template("search.html", results=results)


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

import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Choose name for new table and column to get data from: geschlechtpreis - geschlecht - geschlecht / vortragspreis - vorgetragen_am - vorgetragen_am
tablename = "geschlechtpreis"
criterion = "geschlecht"
col = "geschlecht"

# Create table
db.execute("CREATE TABLE {} (id SERIAL PRIMARY KEY, {} VARCHAR(40) NOT NULL, preis_true INTEGER NOT NULL, preis_false INTEGER NOT NULL, total INTEGER NOT NULL, percent FLOAT NOT NULL, bachmann_preis INTEGER NOT NULL)".format(tablename, criterion))
db.commit()


def main():
    rows = db.execute("SELECT * FROM autorinnen").fetchall()

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

            self.col = rows[i][col]

            if rows[i]["preis_gewonnen"] == "True":
                rows_prices = db.execute("SELECT preistitel FROM preise_new WHERE autorinnen_id = :name",
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

    labels = []
    for result in results:
        if result.col not in labels:
            labels.append(result.col)
    values_priceless = []
    values_price = []
    values_bachmann = []
    for label in labels:
        i = 0
        j = 0
        k = 0
        for result in results:
            if result.col == label:
                if result.preis == "Fehlanzeige":
                    i += 1
                if result.preis != "Fehlanzeige":
                    j += 1
                    if "Ingeborg-Bachmann-Preis" in result.preis:
                        k += 1
        values_priceless.append(i)
        values_price.append(j)
        values_bachmann.append(k)
    print(labels)
    print(values_priceless)
    print(values_price)
    print(values_bachmann)

    for l in range(len(labels)):
        db.execute("INSERT INTO {} ({}, preis_true, preis_false, total, percent, bachmann_preis) VALUES (:{}, :preis_true, :preis_false, :total, :percent, :bachmann_preis)".format(tablename, criterion, criterion), {
                   "{}".format(criterion): labels[l], "preis_true": values_price[l], "preis_false": values_priceless[l], "total": (values_price[l] + values_priceless[l]), "percent": ((values_price[l] / (values_price[l] + values_priceless[l])) * 100), "bachmann_preis": values_bachmann[l]})
        db.commit()


if __name__ == "__main__":
    main()

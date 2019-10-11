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

# Create table books
db.execute("CREATE TABLE landpreis (id SERIAL PRIMARY KEY, land VARCHAR(40) NOT NULL, preis_true INTEGER NOT NULL, preis_false INTEGER NOT NULL, total INTEGER NOT NULL, percent FLOAT NOT NULL, bachmann_preis INTEGER NOT NULL)")
db.commit()

# Import data from csv file


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

    labels = []
    for result in results:
        if result.land not in labels:
            if ", " in result.land:
                split_land = result.land.split(", ")
                if split_land[0] not in labels:
                    labels.append(split_land[0])
                if split_land[1] not in labels:
                    labels.append(split_land[1])
            else:
                labels.append(result.land)
    print(labels)
    values_priceless = []
    values_price = []
    values_bachmann = []

    for label in labels:
        i = 0
        j = 0
        k = 0
        for result in results:
            if label in result.land:
                if result.preis == "Fehlanzeige":
                    i += 1
                if result.preis != "Fehlanzeige":
                    j += 1
                    if result.preis == "Ingeborg-Bachmann-Preis":
                        k += 1
        values_priceless.append(i)
        values_price.append(j)
        values_bachmann.append(k)
    print(labels)
    print(values_priceless)
    print(values_price)
    print(values_bachmann)

    for l in range(len(labels)):
        db.execute("INSERT INTO landpreis (land, preis_true, preis_false, total, percent, bachmann_preis) VALUES (:land, :preis_true, :preis_false, :total, :percent, :bachmann_preis)", {
                   "land": labels[l], "preis_true": values_price[l], "preis_false": values_priceless[l], "total": (values_price[l] + values_priceless[l]), "percent": ((values_price[l] / (values_price[l] + values_priceless[l])) * 100), "bachmann_preis": values_bachmann[l]})
        db.commit()


if __name__ == "__main__":
    main()

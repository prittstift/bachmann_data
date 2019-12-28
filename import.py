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
db.execute("CREATE TABLE autorinnen (id SERIAL PRIMARY KEY, autorinnenname VARCHAR(100) NOT NULL, land VARCHAR(100), wohnort VARCHAR(100), titel VARCHAR(200), eingeladen_von VARCHAR(100), teilnahmejahr VARCHAR(20) NOT NULL, geburtsjahr VARCHAR(50) NOT NULL, geschlecht VARCHAR(20) NOT NULL, vorgetragen_am VARCHAR(20), preis_gewonnen VARCHAR(20) NOT NULL, wikipedia VARCHAR(20) NOT NULL, webseite VARCHAR(100))")
db.commit()


# Import data from csv file
def main():
    with open('autorinnen_complete.csv', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        for autorinnenname, land, wohnort, titel, eingeladen_von, teilnahmejahr, geburtsjahr, geschlecht, vorgetragen_am, preis_gewonnen, wikipedia, webseite in reader:
            db.execute("INSERT INTO autorinnen (autorinnenname, land, wohnort, titel, eingeladen_von, teilnahmejahr, geburtsjahr, geschlecht, vorgetragen_am, preis_gewonnen, wikipedia, webseite) VALUES (:autorinnenname, :land, :wohnort, :titel, :eingeladen_von, :teilnahmejahr, :geburtsjahr, :geschlecht, :vorgetragen_am, :preis_gewonnen, :wikipedia, :webseite)", {
                       "autorinnenname": autorinnenname, "land": land, "wohnort": wohnort, "titel": titel, "eingeladen_von": eingeladen_von, "teilnahmejahr": teilnahmejahr, "geburtsjahr": geburtsjahr, "geschlecht": geschlecht, "vorgetragen_am": vorgetragen_am, "preis_gewonnen": preis_gewonnen, "wikipedia": wikipedia, "webseite": webseite})
        db.commit()


if __name__ == "__main__":
    main()

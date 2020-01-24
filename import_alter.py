import pandas as pd
import numpy as np
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


# Query database

data_stream = pd.read_sql("SELECT autorinnen.id, autorinnen.teilnahmejahr, autorinnen.geburtsjahr, autorinnen.preis_gewonnen, preise_new.preistitel FROM autorinnen JOIN preise_new ON autorinnen.id = preise_new.autorinnen_id", con=engine, index_col='id')

# rows = db.execute("SELECT autorinnen.id, autorinnen.autorinnenname, autorinnen.titel, autorinnen.eingeladen_von, autorinnen.teilnahmejahr FROM autorinnen JOIN preise_new ON autorinnen.id = preise_new.autorinnen_id").fetchall()

temp = data_stream[data_stream['geburtsjahr'].map(lambda x: str(x)!="geburtsjahr")]

data = temp[temp['geburtsjahr'].map(lambda x: str(x)!="im letzten Drittel des 20. Jahrhunderts")]

data['geburtsjahr'] = pd.to_datetime(data['geburtsjahr'], format='%d%m%Y')

data['teilnahmejahr'] = pd.to_datetime(data['teilnahmejahr'], format='%d%m%Y')

data["alter"] = data.apply(
    lambda row: row["teilnahmejahr"] - row["geburtsjahr"], axis=1)

data.drop(['geburtsjahr'], axis=1)

data["alter"] = data["alter"] / np.timedelta64(1, 'Y')

data["alter"] = round(data["alter"], 2)

data['teilnahmejahr'] = data['teilnahmejahr'].dt.year

# Create table
db.execute("CREATE TABLE alterpreis (id SERIAL PRIMARY KEY, jahr VARCHAR(40) NOT NULL, gruppe VARCHAR(100), alter FLOAT NOT NULL)")
db.commit()

temp_preis = data[data['preis_gewonnen'].map(lambda x: str(x)=="True")]
temp_bachmann = data[data['preistitel'].map(lambda x: "Ingeborg-Bachmann-Preis" in str(x))]
temp_publikum = data[data['preistitel'].map(lambda x: "Publikumspreis" in str(x))]

mean_preis = round(temp_preis["alter"].mean(), 2)
mean_bachmann = round(temp_bachmann["alter"].mean(), 2)
mean_publikum = round(temp_publikum["alter"].mean(), 2)

mean_abs = round(data["alter"].mean(), 2)

gruppen_abs = {"absolut": mean_abs, "preis_gewonnen": mean_preis, "bachmann": mean_bachmann, "publikum": mean_publikum}

for gruppe in gruppen_abs.keys():
    db.execute("INSERT INTO alterpreis (jahr, gruppe, alter) VALUES (:jahr, :gruppe, :alter)", {"jahr": "abs", "gruppe": gruppe, "alter": gruppen_abs[gruppe]})
    db.commit()

print(data)

print("Absoluter Durchschnitt: " + str(mean_abs))
print("Absoluter Durchschnitt (Preis gewonnen): " + str(mean_preis))
print("Absoluter Durchschnitt (Bachmannpreis): " + str(mean_bachmann))
print("Absoluter Durchschnitt (Publikumspreis): " + str(mean_publikum))

for year in range(1977,2020):
    temp = data[data['teilnahmejahr'].map(lambda x: int(x)==year)]
    temp_preis = temp[temp['preis_gewonnen'].map(lambda x: str(x)=="True")]
    temp_bachmann = temp_preis[temp_preis['preistitel'].map(lambda x: "Ingeborg-Bachmann-Preis" in str(x))]
    temp_publikum = temp_preis[temp_preis['preistitel'].map(lambda x: "Publikumspreis" in str(x))]
    mean_temp = round(temp["alter"].mean(), 2)
    mean_temp_preis = round(temp_preis["alter"].mean(), 2)
    age_temp_bachmann = round(temp_bachmann["alter"].mean(), 2)
    age_temp_publikum = round(temp_publikum["alter"].mean(), 2)
    gruppen = {"absolut": mean_temp, "preis_gewonnen": mean_temp_preis, "bachmann": age_temp_bachmann, "publikum": age_temp_publikum}
    
    for gruppe in gruppen.keys():
        db.execute("INSERT INTO alterpreis (jahr, gruppe, alter) VALUES (:jahr, :gruppe, :alter)", {"jahr": year, "gruppe": gruppe, "alter": gruppen[gruppe]})
        db.commit()

    print("Durchschnitt ({}): ".format(year) + str(mean_temp))
    print("Durchschnitt ({})(Preis gewonnen): ".format(year) + str(mean_temp_preis))
    print("Durchschnitt ({})(Bachmannpreis): ".format(year) + str(age_temp_bachmann))
    print("Durchschnitt ({})(Publikumspreis): ".format(year) + str(age_temp_publikum))


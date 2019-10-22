import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

kritikerinnen = ["Gmünder", "Gomringer", "Kastberger", "Keller", "Wiederstein",
                 "Wilke", "Winkels", "Kegel", "Feßmann", "Steiner", "Dusini", "Strigl", "Spinnen"]

for i in range(len(kritikerinnen)):

    rows = db.execute("SELECT saetze FROM sentiment WHERE kritikerin = :kritikerin", {
                      "kritikerin": "{}".format(kritikerinnen[i])}).fetchall()

    if kritikerinnen[i] == "Gmünder":
        k = "gmuender"
    elif kritikerinnen[i] == "Feßmann":
        k = "fessmann"
    else:
        k = kritikerinnen[i].lower()

    with open("kritikerinnen/{}.txt".format(k), "w", encoding="utf-8") as f1:
        for i in range(len(rows)):
            f1.write(rows[i]["saetze"])

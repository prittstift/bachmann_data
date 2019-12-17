from spacy_sentiws import spaCySentiWS
import spacy
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
db.execute("CREATE TABLE juryfazit (autorin_id INTEGER NOT NULL PRIMARY KEY, fazit TEXT NOT NULL)")
db.commit()

nlp = spacy.load('de_core_news_sm')

for p in range(1, 305):
    with open("jurydiskussionen/clean/jury_fazit.txt", "a", encoding="utf-8") as f1:
        jury = open("jurydiskussionen/clean/{}.txt".format(p), encoding="utf-8").read()
        doc = nlp(jury)
        absatz_counter = 0
        for sentence in doc.sents:
            if (("Jury" in sentence.text) and (absatz_counter == 0)):
                absatz_counter += 1
                fazit = sentence.text
            elif (("\n" in sentence.text) and (absatz_counter == 0)):
                absatz_counter += 1
                fazit = sentence.text

        fazit.strip()
        if "“" in fazit:
            fazit = fazit.replace("“", "'")
        if "„" in fazit:
            fazit = fazit.replace("„", "‚")
        if "\"" in fazit:
            fazit = fazit.replace("\"", "\'")

    db.execute("INSERT INTO juryfazit ( autorin_id, fazit) VALUES (:autorin_id, :fazit)", {
               "autorin_id": p, "fazit": fazit})
    db.commit()

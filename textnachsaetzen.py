import spacy

autoren = ["albig", "baar", "beyer", "birkhan", "birnbacher", "bjerg", "clavadetscher", "dinic", "dorian", "dündar", "dürr", "edelbauer", "falkner", "federer", "fischer", "flor", "fritsch", "ganzoni", "gardi", "gericke", "gerster", "goetsch", "gomringer", "grigorcea", "groetzner", "groß", "halter", "heier", "heitzler", "jost", "klein", "klemm", "krohn", "kummer", "lange", "lehn", "lohse", "loß", "macht", "maljartschuk", "mannhart", "marchel",
           "markovic", "meschik", "fehr", "molinari", "neft", "nickel", "nolte", "obexer", "othmann", "otoo", "oezdogan", "peschka", "petz", "poelzl", "poladjan", "praeauer", "preiwuss", "recker", "roenne", "rubinowitz",  "sargnagel", "schenk", "schmalz", "schneider_b", "schneider_n", "schultens", "schwitter", "sievers", "snela", "sommer", "sozio", "stern", "thomae", "treber", "truschner", "tschui", "varatharajah", "wipauer", "wolf", "wray", "zwicky"]

nlp = spacy.load('de_core_news_sm')

for autor in autoren:
    with open("C:/Users/D/Desktop/CS/bachmann/Texte/txt_voyant/clean/{}.pdf.txt".format(autor), "w", encoding="utf-8") as f1:
        jury = open(
            "C:/Users/D/Desktop/CS/bachmann/Texte/txt_voyant/{}.pdf.txt".format(autor), encoding="utf-8").read()
        doc = nlp(jury)
        for sentence in doc.sents:
            f1.write(sentence.text)
            f1.write("\n")

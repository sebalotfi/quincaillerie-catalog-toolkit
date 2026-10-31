"""Parcours de l'écran : import, résumé, tableaux et téléchargements."""

import io
from pathlib import Path

import openpyxl
from streamlit.testing.v1 import AppTest

RACINE = Path(__file__).resolve().parents[1]


def lancer() -> AppTest:
    application = AppTest.from_file(str(RACINE / "app.py"), default_timeout=30)
    application.run()
    assert not application.exception, application.exception
    return application


def test_ecran_d_accueil():
    application = lancer()
    assert application.info
    assert "Importez un fichier" in application.info[0].value
    assert application.title[0].value == "Quincaillerie Catalog Toolkit"


def test_import_exemple_resume_tableaux_et_telechargements():
    application = lancer()
    exemple = (RACINE / "exemples" / "catalogue_exemple.csv").read_bytes()
    application.file_uploader[0].upload("catalogue_exemple.csv", exemple, "text/csv")
    application.run()
    assert not application.exception, application.exception

    metriques = {metrique.label: metrique.value for metrique in application.metric}
    assert metriques == {
        "Produits analysés": "10",
        "Lignes conformes": "2",
        "Lignes avec problème": "8",
        "Problèmes détectés": "10",
    }
    assert any("8 lignes" in message.value for message in application.warning)
    assert len(application.dataframe) >= 2
    assert [bouton.label for bouton in application.download_button] == [
        "Télécharger le rapport des erreurs (CSV)",
        "Télécharger les données importées (CSV)",
    ]


def test_messages_fichier_vide_format_incorrect_et_excel():
    vide = lancer()
    vide.file_uploader[0].upload("vide.csv", b"", "text/csv")
    vide.run()
    assert not vide.exception, vide.exception
    assert vide.error and "vide" in vide.error[0].value

    mauvais_format = lancer()
    mauvais_format.file_uploader[0].upload("notes.txt", b"bonjour", "text/plain")
    mauvais_format.run()
    assert not mauvais_format.exception, mauvais_format.exception
    assert mauvais_format.error and "Format incorrect" in mauvais_format.error[0].value

    classeur = openpyxl.Workbook()
    classeur.active.append(["nom", "reference", "prix", "quantite"])
    classeur.active.append(["Vis", "V-1", 2, 4])
    tampon = io.BytesIO()
    classeur.save(tampon)
    excel = lancer()
    excel.file_uploader[0].upload(
        "ok.xlsx",
        tampon.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    excel.run()
    assert not excel.exception, excel.exception
    metriques = {metrique.label: metrique.value for metrique in excel.metric}
    assert metriques["Produits analysés"] == "1"
    assert metriques["Problèmes détectés"] == "0"
    assert excel.success

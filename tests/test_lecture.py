"""Lecture CSV et Excel, et export sans modification du fichier d'origine."""

import io

import openpyxl

from lecture_catalogue import ErreurFichier, identifier_colonnes, lire_catalogue, vers_csv


def test_csv_virgule_et_excel_conservent_les_lignes_du_fichier():
    catalogue = lire_catalogue(
        "nom,référence,prix,quantité\nVis,V-1,1.5,3\n".encode(),
        "simple.csv",
    )
    assert list(catalogue.donnees.columns) == ["nom", "référence", "prix", "quantité"]
    assert list(catalogue.lignes_fichier) == [2]
    identifier_colonnes(catalogue.donnees.columns)

    classeur = openpyxl.Workbook()
    feuille = classeur.active
    feuille.append(["Nom du produit", "Référence", "Prix (€)", "Quantité"])
    feuille.append(["Tournevis", "TOU-1", 12.5, 4])
    feuille.append([None, None, None, None])
    feuille.append(["Clou", "CLO-9", 1, 2])
    tampon = io.BytesIO()
    classeur.save(tampon)

    excel = lire_catalogue(tampon.getvalue(), "catalogue.xlsx")
    assert list(excel.lignes_fichier) == [2, 4]
    assert excel.donnees.loc[0, "Nom du produit"] == "Tournevis"


def test_export_csv_cite_les_decimales_et_omet_la_colonne_de_controle():
    catalogue = lire_catalogue(
        "nom;référence;prix;quantité\nVis à bois;VIS-001;2,50;100\n".encode(),
        "catalogue.csv",
    )
    copie = vers_csv(catalogue.donnees)
    texte = copie.decode("utf-8-sig")

    assert copie.startswith(b"\xef\xbb\xbf")
    assert "2,50" in texte
    assert "Vis à bois" in texte
    assert "Contrôle" not in texte


def test_fichiers_refusés():
    cas = [
        (b"", "vide.csv", "vide"),
        (b"   \n", "blanc.csv", "vide"),
        (b"nom;reference;prix;quantite\n", "entetes.csv", "aucun produit"),
        (b"notes", "notes.txt", "Format incorrect"),
        (b"ancien", "ancien.xls", "Format incorrect"),
        (b"nom\x00prix", "binaire.csv", "illisible"),
        (b"ceci n'est pas un classeur", "faux.xlsx", "illisible"),
        ("nom;référence;prix\nVis;A;1,50\n".encode(), "manque.csv", "Colonnes absentes"),
        (
            "nom,reference,ref,prix,quantite\nA,B,C,1,2\n".encode(),
            "doublons.csv",
            "Plusieurs colonnes",
        ),
        (
            "nom,reference,prix,quantite\nA,B,1,2,extra\n".encode(),
            "irregulier.csv",
            "mal formé",
        ),
    ]
    for contenu, nom, extrait in cas:
        try:
            catalogue = lire_catalogue(contenu, nom)
            identifier_colonnes(catalogue.donnees.columns)
        except ErreurFichier as erreur:
            assert extrait in str(erreur), (nom, erreur)
        else:
            raise AssertionError(f"devait échouer : {nom}")

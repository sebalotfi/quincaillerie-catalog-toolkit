"""Contrôles des références, prix, quantités et catégories."""

from pathlib import Path

from lecture_catalogue import identifier_colonnes, lire_catalogue
from validation_catalogue import analyser_catalogue

RACINE = Path(__file__).resolve().parents[1]


def controler(texte: str, nom: str = "catalogue.csv"):
    catalogue = lire_catalogue(texte.encode("utf-8"), nom)
    colonnes = identifier_colonnes(catalogue.donnees.columns)
    avant = catalogue.donnees.copy()
    resultat = analyser_catalogue(
        catalogue.donnees,
        catalogue.lignes_fichier,
        colonnes,
    )
    assert catalogue.donnees.equals(avant)
    return resultat


def problemes(resultat) -> set[tuple[int, str]]:
    return set(zip(resultat.problemes["Ligne"], resultat.problemes["Problème"]))


def test_exemple_signale_les_erreurs_volontaires():
    contenu = (RACINE / "exemples" / "catalogue_exemple.csv").read_bytes()
    avant = contenu
    catalogue = lire_catalogue(contenu, "catalogue_exemple.csv")
    resultat = analyser_catalogue(
        catalogue.donnees,
        catalogue.lignes_fichier,
        identifier_colonnes(catalogue.donnees.columns),
    )

    assert resultat.produits_analyses == 10
    assert resultat.lignes_conformes == 2
    assert resultat.lignes_en_erreur == 8
    assert len(resultat.problemes) == 10
    assert problemes(resultat) == {
        (2, "Référence en double."),
        (3, "Référence en double."),
        (4, "Référence manquante."),
        (5, "Prix non numérique."),
        (6, "Prix négatif."),
        (6, "Quantité négative."),
        (7, "Quantité non valide. Indiquez un nombre entier positif ou nul."),
        (8, "Catégorie manquante."),
        (9, "Référence manquante."),
        (9, "Quantité manquante."),
    }
    assert (RACINE / "exemples" / "catalogue_exemple.csv").read_bytes() == avant


def test_prix_et_quantite_a_zero_sont_acceptes():
    resultat = controler("nom,reference,prix,quantite\nVis,V-1,0,0\n")
    assert resultat.problemes.empty
    assert resultat.lignes_conformes == 1


def test_reference_en_double_ignore_casse_et_espaces():
    resultat = controler(
        "nom,reference,prix,quantite\nVis,vis-1,2,3\nEcrou, VIS-1 ,2,3\n"
    )
    assert list(resultat.problemes["Problème"]) == [
        "Référence en double.",
        "Référence en double.",
    ]


def test_champs_essentiels_manquants():
    resultat = controler(
        "nom;reference;prix;quantite;categorie\n;;;;Visserie\n"
    )
    assert problemes(resultat) == {
        (2, "Nom du produit manquant."),
        (2, "Référence manquante."),
        (2, "Prix manquant."),
        (2, "Quantité manquante."),
    }


def test_prix_non_numerique_et_quantite_decimale():
    resultat = controler("nom,reference,prix,quantite\nVis,V-1,abc,2.5\n")
    assert problemes(resultat) == {
        (2, "Prix non numérique."),
        (2, "Quantité non valide. Indiquez un nombre entier positif ou nul."),
    }


def test_virgule_decimale_et_milliers_sont_lus():
    resultat = controler(
        "nom;reference;prix;quantite\nVis;V-1;1.234,56;10,0\n"
    )
    assert resultat.problemes.empty


def test_categorie_vide_uniquement_si_la_colonne_existe():
    avec_colonne = controler(
        "designation,code,tarif,stock,famille\nVis,A,2,3,\n"
    )
    assert list(avec_colonne.problemes["Problème"]) == ["Catégorie manquante."]

    sans_colonne = controler("nom,reference,prix,quantite\nVis,A,2,3\n")
    assert sans_colonne.problemes.empty

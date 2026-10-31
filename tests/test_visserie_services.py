"""Tests pour la détection des services et la règle visserie (1 diamètre = 1 fiche)."""

import pandas as pd
import pytest

from classification_catalogue import (
    classifier_et_regrouper,
    est_un_service,
    charger_regles,
)


@pytest.fixture
def regles():
    return charger_regles()


def test_detection_services(regles):
    config_serv = regles["services"]
    assert est_un_service("LIVRAISON", config_serv) is True
    assert est_un_service("TRANSPORT", config_serv) is True
    assert est_un_service("MAIN D'EUVRE", config_serv) is True
    assert est_un_service("XV2/B4/ BOULON (T.P) 4*12", config_serv) is False


def test_separation_diametres_visserie(regles):
    """Vérifie que Ø4 et Ø5 génèrent 2 fiches différentes sans mélanger les longueurs."""
    lignes = [
        {"code": "1001", "nom": "XV2/B4/ BOULON (T.P) 4*12", "prix": 4, "stock": 50},
        {"code": "1002", "nom": "XV2/B4/ BOULON (T.P) 4*20", "prix": 4, "stock": 30},
        {"code": "1003", "nom": "XV2/B4/ BOULON (T.P) 4*40", "prix": 6, "stock": 10},
        {"code": "2001", "nom": "XV2/B5/ BOULON (T.F) 5*30", "prix": 6, "stock": 20},
        {"code": "2002", "nom": "XV2/B5/ BOULON (T.F) 5*50", "prix": 9, "stock": 15},
        {"code": "9001", "nom": "LIVRAISON", "prix": 1, "stock": 0},
    ]
    df = pd.DataFrame(lignes)
    lignes_fichier = pd.Series([2, 3, 4, 5, 6, 7], index=df.index)

    df_qualifie, fiches = classifier_et_regrouper(
        donnees=df,
        lignes_fichier=lignes_fichier,
        colonne_nom="nom",
        colonne_ref="code",
        colonne_prix="prix",
        colonne_quantite="stock",
        config=regles,
    )

    # 1. Vérification services
    assert (df_qualifie["Type Ligne"] == "Service / Frais").sum() == 1
    assert "LIVRAISON" in df_qualifie["nom"].values

    # 2. Vérification des fiches visserie : 2 fiches séparées
    assert len(fiches) == 2

    fiche_diam_4 = next(f for f in fiches if f.diametre == "4")
    fiche_diam_5 = next(f for f in fiches if f.diametre == "5")

    longueurs_4 = fiche_diam_4.longueurs_disponibles
    longueurs_5 = fiche_diam_5.longueurs_disponibles

    assert set(longueurs_4) == {"12", "20", "40"}
    assert set(longueurs_5) == {"30", "50"}
    assert "50" not in longueurs_4
    assert "12" not in longueurs_5

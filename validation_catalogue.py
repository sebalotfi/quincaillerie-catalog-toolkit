"""Contrôles d'un catalogue de quincaillerie déjà chargé."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import pandas as pd

from lecture_catalogue import LIBELLES_CHAMPS

COLONNES_RAPPORT = ["Ligne", "Champ", "Valeur", "Problème"]

MESSAGES_MANQUANTS = {
    "nom": "Nom du produit manquant.",
    "reference": "Référence manquante.",
    "prix": "Prix manquant.",
    "quantite": "Quantité manquante.",
    "categorie": "Catégorie manquante.",
}
MESSAGE_REFERENCE_DOUBLE = "Référence en double."
MESSAGE_PRIX_NON_NUMERIQUE = "Prix non numérique."
MESSAGE_PRIX_NEGATIF = "Prix négatif."
MESSAGE_QUANTITE_INVALIDE = (
    "Quantité non valide. Indiquez un nombre entier positif ou nul."
)
MESSAGE_QUANTITE_NEGATIVE = "Quantité négative."


@dataclass(frozen=True)
class ResultatAnalyse:
    """Bilan d'un contrôle, avec une ligne de rapport par problème."""

    produits_analyses: int
    lignes_conformes: int
    lignes_en_erreur: int
    problemes: pd.DataFrame


def analyser_catalogue(
    donnees: pd.DataFrame,
    lignes_fichier: pd.Series,
    colonnes: dict[str, str],
) -> ResultatAnalyse:
    """Repère les doublons, les champs vides et les nombres inutilisables.

    Le tableau d'entrée n'est pas modifié.
    """
    problemes: list[dict[str, object]] = []
    lignes_touchees: set[int] = set()
    references = [
        None if _est_vide(valeur) else str(valeur).strip().casefold()
        for valeur in donnees[colonnes["reference"]]
    ]
    compteur: dict[str, int] = {}
    for reference in references:
        if reference is not None:
            compteur[reference] = compteur.get(reference, 0) + 1
    references_en_double = {
        reference for reference, nombre in compteur.items() if nombre > 1
    }

    for position, idx in enumerate(donnees.index):
        numero_ligne = int(lignes_fichier.loc[idx])

        def signaler(champ: str, valeur: object, message: str) -> None:
            problemes.append(
                {
                    "Ligne": numero_ligne,
                    "Champ": LIBELLES_CHAMPS[champ],
                    "Valeur": "" if _est_vide(valeur) else str(valeur).strip(),
                    "Problème": message,
                }
            )
            lignes_touchees.add(numero_ligne)

        for champ in ("nom", "reference", "prix", "quantite"):
            valeur = donnees.at[idx, colonnes[champ]]
            if _est_vide(valeur):
                signaler(champ, valeur, MESSAGES_MANQUANTS[champ])
            elif champ == "prix":
                _controler_prix(valeur, signaler)
            elif champ == "quantite":
                _controler_quantite(valeur, signaler)

        if "categorie" in colonnes:
            categorie = donnees.at[idx, colonnes["categorie"]]
            if _est_vide(categorie):
                signaler("categorie", categorie, MESSAGES_MANQUANTS["categorie"])

        reference_comparable = references[position]
        if reference_comparable in references_en_double:
            signaler(
                "reference",
                donnees.at[idx, colonnes["reference"]],
                MESSAGE_REFERENCE_DOUBLE,
            )

    rapport = pd.DataFrame(problemes, columns=COLONNES_RAPPORT)
    if not rapport.empty:
        rapport = rapport.sort_values("Ligne", kind="mergesort").reset_index(drop=True)

    produits_analyses = int(len(donnees))
    lignes_en_erreur = len(lignes_touchees)
    return ResultatAnalyse(
        produits_analyses=produits_analyses,
        lignes_conformes=produits_analyses - lignes_en_erreur,
        lignes_en_erreur=lignes_en_erreur,
        problemes=rapport,
    )


def repartition_problemes(problemes: pd.DataFrame) -> pd.DataFrame:
    """Compte combien de fois chaque problème apparaît."""
    if problemes.empty:
        return pd.DataFrame(columns=["Problème", "Nombre"])
    return (
        problemes["Problème"]
        .value_counts()
        .rename_axis("Problème")
        .reset_index(name="Nombre")
    )


def _controler_prix(valeur: object, signaler) -> None:
    nombre = _lire_nombre(valeur)
    if nombre is None:
        signaler("prix", valeur, MESSAGE_PRIX_NON_NUMERIQUE)
        return
    if nombre < 0:
        signaler("prix", valeur, MESSAGE_PRIX_NEGATIF)


def _controler_quantite(valeur: object, signaler) -> None:
    nombre = _lire_nombre(valeur)
    if nombre is None or not nombre.is_integer():
        signaler("quantite", valeur, MESSAGE_QUANTITE_INVALIDE)
        return
    if nombre < 0:
        signaler("quantite", valeur, MESSAGE_QUANTITE_NEGATIVE)


def _lire_nombre(valeur: object) -> float | None:
    """Lit un prix ou une quantité, avec virgule ou point décimal."""
    if isinstance(valeur, bool) or valeur is None:
        return None
    if isinstance(valeur, (int, float)):
        if isinstance(valeur, float) and math.isnan(valeur):
            return None
        return float(valeur)

    texte = str(valeur).strip().replace("\u00a0", "").replace(" ", "")
    texte = texte.replace("€", "").replace("EUR", "").replace("eur", "")
    texte = texte.replace("−", "-").replace("–", "-")
    if not texte:
        return None
    if "," in texte and "." in texte:
        if texte.rfind(",") > texte.rfind("."):
            texte = texte.replace(".", "").replace(",", ".")
        else:
            texte = texte.replace(",", "")
    elif "," in texte:
        texte = texte.replace(",", ".")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", texte):
        return None
    return float(texte)


def _est_vide(valeur: object) -> bool:
    if valeur is None:
        return True
    if isinstance(valeur, float) and math.isnan(valeur):
        return True
    return str(valeur).strip() == ""

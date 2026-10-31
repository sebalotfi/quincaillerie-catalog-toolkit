"""Lecture d'un catalogue produits CSV ou Excel."""

from __future__ import annotations

import io
import math
import re
import unicodedata
import warnings
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

CHAMPS_ESSENTIELS = ("nom", "reference", "prix", "quantite")

LIBELLES_CHAMPS = {
    "nom": "Nom du produit",
    "reference": "Référence",
    "prix": "Prix",
    "quantite": "Quantité",
    "categorie": "Catégorie",
}

ALIAS_COLONNES = {
    "nom": {
        "nom",
        "nom_produit",
        "nom_du_produit",
        "produit",
        "designation",
        "libelle",
        "libelle_produit",
        "article",
        "intitule",
    },
    "reference": {
        "reference",
        "reference_produit",
        "reference_article",
        "ref",
        "ref_produit",
        "sku",
        "code",
        "code_produit",
        "code_article",
    },
    "prix": {
        "prix",
        "prix_unitaire",
        "prix_ht",
        "prix_ttc",
        "prix_euro",
        "prix_eur",
        "pu",
        "pu_ht",
        "price",
        "tarif",
    },
    "quantite": {
        "quantite",
        "quantite_stock",
        "qte",
        "qte_stock",
        "stock",
        "qty",
        "quantity",
    },
    "categorie": {
        "categorie",
        "famille",
        "rayon",
        "sous_famille",
        "category",
    },
}

EXTENSIONS_ACCEPTEES = {".csv", ".xlsx"}


class ErreurFichier(Exception):
    """Erreur de lecture expliquée à la personne qui importe le catalogue."""


class _LignesIrregulieres(Exception):
    """Le séparateur essayé ne donne pas le même nombre de colonnes sur chaque ligne."""


@dataclass(frozen=True)
class CatalogueImporte:
    """Tableau lu tel quel, avec le numéro de ligne d'origine de chaque produit."""

    donnees: pd.DataFrame
    lignes_fichier: pd.Series


def normaliser_entete(valeur: object) -> str:
    """Ramène un en-tête à une forme comparable, sans accent ni ponctuation."""
    texte = str(valeur).strip().lower().replace("€", "")
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(caractere for caractere in texte if not unicodedata.combining(caractere))
    texte = re.sub(r"[^a-z0-9]+", "_", texte)
    return texte.strip("_")


def identifier_colonnes(colonnes: list[str] | pd.Index) -> dict[str, str]:
    """Associe chaque champ contrôlé au nom réel de sa colonne.

    Lève ErreurFichier si un champ obligatoire est absent, ou si deux colonnes
    visent le même champ.
    """
    correspondance: dict[str, str] = {}
    for colonne in colonnes:
        cle = normaliser_entete(colonne)
        for champ, alias in ALIAS_COLONNES.items():
            if cle not in alias:
                continue
            if champ in correspondance:
                raise ErreurFichier(
                    "Plusieurs colonnes correspondent au champ "
                    f"« {LIBELLES_CHAMPS[champ]} » : « {correspondance[champ]} » et "
                    f"« {colonne} ». Conservez une seule de ces colonnes."
                )
            correspondance[champ] = str(colonne)

    manquants = [
        LIBELLES_CHAMPS[champ]
        for champ in CHAMPS_ESSENTIELS
        if champ not in correspondance
    ]
    if manquants:
        raise ErreurFichier(
            "Colonnes absentes : "
            + ", ".join(manquants)
            + ". Le fichier doit contenir le nom du produit, la référence, le prix "
            "et la quantité. Exemples d'en-têtes : nom, référence, prix, quantité."
        )
    return correspondance


def lire_catalogue(contenu: bytes, nom_fichier: str) -> CatalogueImporte:
    """Lit un CSV ou un Excel .xlsx et refuse les fichiers inutilisables."""
    if contenu is None or len(contenu.strip()) == 0:
        raise ErreurFichier("Le fichier est vide.")

    extension = Path(nom_fichier or "").suffix.lower()
    if extension == ".xls":
        raise ErreurFichier(
            "Format incorrect. L'ancien format Excel .xls n'est pas accepté. "
            "Enregistrez le classeur en .xlsx, ou exportez-le en CSV."
        )
    if extension not in EXTENSIONS_ACCEPTEES:
        raise ErreurFichier(
            "Format incorrect. Importez un fichier CSV (.csv) ou Excel (.xlsx)."
        )

    if extension == ".csv":
        table = _lire_csv(contenu)
    else:
        table = _lire_xlsx(contenu)
    return _preparer_table(table)


def vers_csv(donnees: pd.DataFrame) -> bytes:
    """Convertit un tableau en CSV UTF-8, sans changer le tableau en mémoire."""
    return donnees.to_csv(index=False).encode("utf-8-sig")


def _lire_csv(contenu: bytes) -> pd.DataFrame:
    if b"\x00" in contenu:
        raise ErreurFichier(
            "Le fichier est illisible. Le contenu ne ressemble pas à un CSV texte."
        )
    if contenu.startswith(b"PK"):
        raise ErreurFichier(
            "Format incorrect. Ce fichier ressemble à un classeur Excel. "
            "Importez-le avec l'extension .xlsx."
        )

    texte = _decoder_texte(contenu)
    if not texte.strip():
        raise ErreurFichier("Le fichier est vide.")

    lectures: list[pd.DataFrame] = []
    lignes_irregulieres = False
    for separateur in (";", ",", "\t", None):
        try:
            lectures.append(_lire_csv_texte(texte, separateur))
        except _LignesIrregulieres:
            lignes_irregulieres = True
        except pd.errors.ParserError:
            continue
        except UnicodeError as exc:
            raise ErreurFichier(
                "Le fichier est illisible. Vérifiez qu'il s'agit bien d'un CSV."
            ) from exc
        except Exception as exc:
            raise ErreurFichier(
                "Le fichier CSV est illisible ou mal formé."
            ) from exc

    tables_larges = [table for table in lectures if table.shape[1] >= 2]
    if tables_larges:
        return max(tables_larges, key=lambda table: table.shape[1])
    if lignes_irregulieres:
        raise ErreurFichier(
            "Le fichier CSV est mal formé : certaines lignes n'ont pas "
            "le même nombre de colonnes que la ligne d'en-têtes. "
            "Si une valeur contient le séparateur, entourez-la de guillemets."
        )
    if lectures:
        return lectures[0]
    raise ErreurFichier(
        "Le fichier CSV est illisible ou mal formé. "
        "Utilisez un séparateur virgule, point-virgule ou tabulation, "
        "et placez les en-têtes sur la première ligne."
    )


def _lire_csv_texte(texte: str, separateur: str | None) -> pd.DataFrame:
    arguments = {
        "dtype": str,
        "keep_default_na": False,
        "engine": "python",
        "index_col": False,
    }
    with warnings.catch_warnings(record=True) as alertes:
        warnings.simplefilter("always")
        if separateur is None:
            table = pd.read_csv(io.StringIO(texte), sep=None, **arguments)
        else:
            table = pd.read_csv(io.StringIO(texte), sep=separateur, **arguments)
    for alerte in alertes:
        if "does not match length" in str(alerte.message):
            raise _LignesIrregulieres(str(alerte.message))
    return table.map(_texte_ou_vide)


def _lire_xlsx(contenu: bytes) -> pd.DataFrame:
    if not contenu.startswith(b"PK"):
        raise ErreurFichier(
            "Le fichier est illisible. Un fichier .xlsx doit être un classeur Excel valide."
        )
    try:
        return pd.read_excel(
            io.BytesIO(contenu),
            dtype=str,
            keep_default_na=False,
            engine="openpyxl",
        )
    except ErreurFichier:
        raise
    except Exception as exc:
        raise ErreurFichier(
            "Le fichier Excel est illisible. Vérifiez qu'il n'est pas corrompu "
            "et qu'il n'est pas protégé par un mot de passe."
        ) from exc


def _cellule_vide(valeur: object) -> bool:
    return str(valeur).strip() == ""


def _colonne_vide(colonne: pd.Series) -> bool:
    return all(_cellule_vide(valeur) for valeur in colonne.tolist())


def _masque_lignes_vides(table: pd.DataFrame) -> pd.Series:
    masque = pd.Series(True, index=table.index, dtype=bool)
    for colonne in table.columns:
        vide = pd.Series(
            (_cellule_vide(valeur) for valeur in table[colonne].tolist()),
            index=table.index,
            dtype=bool,
        )
        masque = masque & vide
    return masque


def _texte_ou_vide(valeur: object) -> str:
    if valeur is None:
        return ""
    if isinstance(valeur, float) and math.isnan(valeur):
        return ""
    return str(valeur)


def _decoder_texte(contenu: bytes) -> str:
    for encodage in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return contenu.decode(encodage)
        except UnicodeDecodeError:
            continue
    raise ErreurFichier(
        "Le fichier est illisible. L'encodage du texte n'est pas reconnu."
    )


def _preparer_table(table: pd.DataFrame) -> CatalogueImporte:
    table = table.copy().map(_texte_ou_vide)
    table.columns = [str(colonne).strip() for colonne in table.columns]
    if table.shape[1] == 0:
        raise ErreurFichier("Le fichier est vide.")

    colonnes_sans_nom = [
        colonne
        for colonne in table.columns
        if normaliser_entete(colonne).startswith("unnamed")
        and _colonne_vide(table[colonne])
    ]
    if colonnes_sans_nom:
        table = table.drop(columns=colonnes_sans_nom)

    numeros = pd.Series(range(2, len(table) + 2), index=table.index)
    lignes_vides = _masque_lignes_vides(table)

    donnees = table.loc[~lignes_vides].reset_index(drop=True)
    lignes_fichier = numeros.loc[~lignes_vides].reset_index(drop=True)
    lignes_fichier.name = "ligne_fichier"

    if donnees.shape[1] == 0:
        raise ErreurFichier("Le fichier est vide.")
    if donnees.empty:
        raise ErreurFichier(
            "Le fichier ne contient aucun produit. La ligne d'en-têtes est présente, "
            "mais aucune donnée n'a été trouvée."
        )
    return CatalogueImporte(donnees=donnees, lignes_fichier=lignes_fichier)

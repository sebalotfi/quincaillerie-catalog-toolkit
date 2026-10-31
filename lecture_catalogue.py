"""Module de lecture et détection des colonnes du catalogue."""

from __future__ import annotations

import io
from dataclasses import dataclass
import pandas as pd


class ErreurFichier(Exception):
    """Exception levée en cas d'erreur de lecture du fichier."""


@dataclass
class CatalogueImporte:
    donnees: pd.DataFrame
    lignes_fichier: pd.Series
    nom_fichier: str


CHAMPS_ESSENTIELS = ["nom", "reference", "prix", "quantite"]

LIBELLES_CHAMPS = {
    "nom": "Désignation",
    "reference": "Référence / Code-barres",
    "prix": "Prix de vente",
    "quantite": "Stock / Quantité",
    "categorie": "Famille / Catégorie",
}

ALIAS_CHAMPS = {
    "nom": [
        "designation du produit",
        "désignation du produit",
        "designation",
        "désignation",
        "nom",
        "produit",
        "libelle",
        "libellé",
        "article",
        "description",
    ],
    "reference": [
        "code a barre",
        "code à barre",
        "code barre",
        "code-barres",
        "code_barre",
        "reference",
        "référence",
        "code",
        "sku",
        "barcode",
        "ean",
        "ean13",
    ],
    "prix": [
        "prix de vente 1",
        "prix vente 1",
        "prix de vente",
        "prix initial",
        "prix",
        "tarif",
        "price",
        "pu_ttc",
        "pv_ttc",
    ],
    "quantite": [
        "stock",
        "quantite",
        "quantité",
        "qte",
        "qté",
        "qty",
        "inventaire",
        "disponible",
    ],
    "categorie": [
        "famille",
        "categorie",
        "catégorie",
        "rayon",
    ],
}


def normaliser(texte: str) -> str:
    t = str(texte).lower().replace("à", "a").replace("é", "e").replace("è", "e").replace("ê", "e")
    return "".join(c for c in t if c.isalnum() or c.isspace()).strip()


def lire_excel(contenu: bytes) -> tuple[pd.DataFrame, pd.Series]:
    try:
        df_raw = pd.read_excel(io.BytesIO(contenu), header=None, nrows=15)
    except Exception as err:
        raise ErreurFichier(f"Erreur lecture Excel : {err}") from err

    header_idx = 0
    for i in range(min(len(df_raw), 15)):
        ligne = " ".join(df_raw.iloc[i].dropna().astype(str).tolist())
        ligne_norm = normaliser(ligne)
        if "designation" in ligne_norm or "code a barre" in ligne_norm or "code barre" in ligne_norm:
            header_idx = i
            break

    df = pd.read_excel(io.BytesIO(contenu), header=header_idx)
    lignes_fichier = pd.Series(df.index + header_idx + 2, index=df.index)
    return df, lignes_fichier


def lire_csv(contenu: bytes) -> tuple[pd.DataFrame, pd.Series]:
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        for sep in [";", ",", "\t"]:
            try:
                df = pd.read_csv(io.BytesIO(contenu), sep=sep, encoding=enc)
                if df.shape[1] > 1:
                    return df, pd.Series(df.index + 2, index=df.index)
            except Exception:
                continue
    raise ErreurFichier("Format CSV non reconnu.")


def lire_catalogue(contenu: bytes, nom_fichier: str) -> CatalogueImporte:
    if nom_fichier.lower().endswith((".xlsx", ".xls")):
        donnees, lignes_fichier = lire_excel(contenu)
    elif nom_fichier.lower().endswith(".csv"):
        donnees, lignes_fichier = lire_csv(contenu)
    else:
        raise ErreurFichier("Format non supporté (.xlsx ou .csv attendu).")

    donnees.columns = [str(col).strip() for col in donnees.columns]
    return CatalogueImporte(donnees=donnees, lignes_fichier=lignes_fichier, nom_fichier=nom_fichier)


def identifier_colonnes(colonnes_existantes) -> dict[str, str]:
    mapping = {}
    cols_norm = {col: normaliser(str(col)) for col in colonnes_existantes}
    for champ, alias_liste in ALIAS_CHAMPS.items():
        trouve = None
        for alias in alias_liste:
            anorm = normaliser(alias)
            for col_orig, cnorm in cols_norm.items():
                if cnorm == anorm:
                    trouve = col_orig
                    break
            if trouve:
                break
        if trouve:
            mapping[champ] = trouve

    manquants = [c for c in CHAMPS_ESSENTIELS if c not in mapping]
    if manquants:
        libelles = [LIBELLES_CHAMPS[c] for c in manquants]
        raise ErreurFichier(f"Colonnes obligatoires manquantes : {', '.join(libelles)}")
    return mapping


def vers_csv(df: pd.DataFrame) -> bytes:
    tampon = io.StringIO()
    df.to_csv(tampon, index=False, sep=";", encoding="utf-8-sig")
    return tampon.getvalue().encode("utf-8-sig")

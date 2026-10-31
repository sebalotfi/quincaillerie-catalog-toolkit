"""Module de classification des articles, détection des services et regroupement visserie v2."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import pandas as pd


CHEMIN_CONFIG_DEFAUT = Path(__file__).parent / "familles_regles.json"


@dataclass
class DeclinaisonProduit:
    reference: str
    designation_source: str
    longueur: str
    prix: float | str
    stock: float | str
    ligne_fichier: int


@dataclass
class FicheProduit:
    id_fiche: str
    famille: str
    nom_base: str
    diametre: str
    declinaisons: list[DeclinaisonProduit] = field(default_factory=list)

    @property
    def total_stock(self) -> float:
        total = 0.0
        for d in self.declinaisons:
            try:
                total += float(d.stock)
            except (ValueError, TypeError):
                pass
        return total

    @property
    def longueurs_disponibles(self) -> list[str]:
        uniques = sorted(
            {d.longueur for d in self.declinaisons},
            key=lambda x: float(x.replace(",", ".")) if _est_nombre(x) else 9999.0,
        )
        return uniques


def _est_nombre(valeur: str) -> bool:
    try:
        float(valeur.replace(",", "."))
        return True
    except ValueError:
        return False


def charger_regles(chemin_config: Path | str | None = None) -> dict[str, Any]:
    chemin = Path(chemin_config) if chemin_config else CHEMIN_CONFIG_DEFAUT
    if not chemin.exists():
        return {
            "services": {
                "termes_exacts": ["LIVRAISON", "TRANSPORT", "MAIN D'EUVRE", "MAIN D'OEUVRE"],
                "mots_cles": ["LIVRAISON", "TRANSPORT", "MAIN D'EUVRE"],
            },
            "familles": {
                "visserie": {
                    "mots_cles_detection": ["BOULON", "VIS", "TIR-FOND"],
                    "regex_dimensions": [
                        r"(?P<diametre>\d+(?:[.,]\d+)?)\s*[*xX]\s*(?P<longueur>\d+(?:[.,]\d+)?)"
                    ],
                }
            },
        }
    with open(chemin, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def est_un_service(designation: str, config_services: dict[str, Any]) -> bool:
    if not isinstance(designation, str):
        return False
    texte = designation.strip().upper()
    for exact in config_services.get("termes_exacts", []):
        if texte == exact.upper():
            return True
    for mot in config_services.get("mots_cles", []):
        if re.search(rf"\b{re.escape(mot.upper())}\b", texte):
            return True
    return False


def nettoyer_prefixe_designation(designation: str) -> str:
    return re.sub(r"^[A-Z0-9]+/[A-Z0-9._-]+/\s*", "", designation).strip()


def extraire_dimensions_visserie(
    designation: str, regex_liste: list[str]
) -> tuple[str | None, str | None, str]:
    texte = designation.strip()
    for motif in regex_liste:
        correspondance = re.search(motif, texte, flags=re.IGNORECASE)
        if correspondance:
            groupes = correspondance.groupdict()
            diam = groupes.get("diametre") or groupes.get("diametre_m")
            longueur = groupes.get("longueur") or groupes.get("longueur_m")
            nom_base = (texte[: correspondance.start()] + texte[correspondance.end() :]).strip()
            nom_base = re.sub(r"\s+", " ", nom_base)
            return diam, longueur, nom_base
    return None, None, texte


def classifier_et_regrouper(
    donnees: pd.DataFrame,
    lignes_fichier: pd.Series,
    colonne_nom: str,
    colonne_ref: str,
    colonne_prix: str,
    colonne_quantite: str,
    config: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, list[FicheProduit]]:
    if config is None:
        config = charger_regles()

    config_services = config.get("services", {})
    config_visserie = config.get("familles", {}).get("visserie", {})
    mots_cles_visserie = config_visserie.get("mots_cles_detection", ["BOULON", "VIS", "TIR-FOND"])
    regex_dim = config_visserie.get(
        "regex_dimensions",
        [r"(?P<diametre>\d+(?:[.,]\d+)?)\s*[*xX]\s*(?P<longueur>\d+(?:[.,]\d+)?)"],
    )

    types_lignes: list[str] = []
    familles_detectees: list[str] = []
    fiches_dict: dict[str, FicheProduit] = {}

    for idx, row in donnees.iterrows():
        designation = str(row.get(colonne_nom, "")).strip()
        ref = str(row.get(colonne_ref, "")).strip()
        prix = row.get(colonne_prix, 0)
        stock = row.get(colonne_quantite, 0)
        num_ligne = int(lignes_fichier.loc[idx])

        if est_un_service(designation, config_services):
            types_lignes.append("Service / Frais")
            familles_detectees.append("Service")
            continue

        designation_haute = designation.upper()
        est_visserie = any(mot in designation_haute for mot in mots_cles_visserie)

        if est_visserie:
            diam, longueur, nom_base_brut = extraire_dimensions_visserie(designation, regex_dim)
            if diam and longueur:
                nom_base = nettoyer_prefixe_designation(nom_base_brut)
                cle_fiche = f"VISSERIE::{nom_base}::D_{diam}".upper()

                if cle_fiche not in fiches_dict:
                    fiches_dict[cle_fiche] = FicheProduit(
                        id_fiche=cle_fiche,
                        famille="Visserie & Boulonnerie",
                        nom_base=nom_base,
                        diametre=diam,
                    )

                fiches_dict[cle_fiche].declinaisons.append(
                    DeclinaisonProduit(
                        reference=ref,
                        designation_source=designation,
                        longueur=longueur,
                        prix=prix,
                        stock=stock,
                        ligne_fichier=num_ligne,
                    )
                )

                types_lignes.append("Produit réel (Visserie)")
                familles_detectees.append("Visserie & Boulonnerie")
                continue

        types_lignes.append("Produit réel (Standard)")
        familles_detectees.append("À qualifier" if not est_visserie else "Visserie (Sans dim.)")

    donnees_qualifiees = donnees.copy()
    donnees_qualifiees.insert(0, "Type Ligne", types_lignes)
    donnees_qualifiees.insert(1, "Famille Détectée", familles_detectees)

    return donnees_qualifiees, list(fiches_dict.values())


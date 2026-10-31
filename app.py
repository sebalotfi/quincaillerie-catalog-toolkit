"""Interface locale du Quincaillerie Catalog Toolkit v2."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lecture_catalogue import (
    LIBELLES_CHAMPS,
    ErreurFichier,
    identifier_colonnes,
    lire_catalogue,
    vers_csv,
)
from validation_catalogue import analyser_catalogue, repartition_problemes
from classification_catalogue import classifier_et_regrouper, charger_regles


def main() -> None:
    st.set_page_config(
        page_title="Quincaillerie Catalog Toolkit",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        [data-testid="stSkillsNudgeAnchor"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    _afficher_entete()
    fichier = st.file_uploader(
        "Catalogue à contrôler et classifier",
        help="CSV (.csv) ou Excel (.xlsx). Compatible format magasin Nielsen.",
    )
    if fichier is None:
        st.info("Importez un fichier CSV ou Excel pour lancer l'analyse.")
        return

    try:
        catalogue = lire_catalogue(fichier.getvalue(), fichier.name)
        colonnes = identifier_colonnes(catalogue.donnees.columns)
        resultat = analyser_catalogue(
            catalogue.donnees,
            catalogue.lignes_fichier,
            colonnes,
        )
        regles = charger_regles()
        donnees_classifiees, fiches_visserie = classifier_et_regrouper(
            donnees=catalogue.donnees,
            lignes_fichier=catalogue.lignes_fichier,
            colonne_nom=colonnes["nom"],
            colonne_ref=colonnes["reference"],
            colonne_prix=colonnes["prix"],
            colonne_quantite=colonnes["quantite"],
            config=regles,
        )
    except ErreurFichier as erreur:
        st.error(str(erreur))
        return

    onglet_controles, onglet_classification, onglet_visserie = st.tabs([
        "1. Contrôle Qualité (v1)",
        "2. Classification & Services (v2)",
        "3. Fiches Visserie (1 Diamètre = 1 Fiche)",
    ])

    with onglet_controles:
        _afficher_resume(fichier.name, colonnes, resultat)
        _afficher_problemes(resultat.problemes)
        _afficher_donnees(catalogue.donnees, catalogue.lignes_fichier, resultat.problemes)

    with onglet_classification:
        _afficher_onglet_classification(donnees_classifiees)

    with onglet_visserie:
        _afficher_onglet_visserie(fiches_visserie)


def _afficher_entete() -> None:
    st.title("Quincaillerie Catalog Toolkit")
    st.write(
        "Contrôlez, classifiez et structurez votre catalogue quincaillerie "
        "selon vos règles métier locales sans altérer les fichiers sources."
    )
    with st.sidebar:
        st.header("Fonctionnalités v2")
        st.markdown(
            """
- Détection des services (`LIVRAISON`, `TRANSPORT`) sans suppression
- Visserie : **1 diamètre = 1 fiche**, longueurs en déclinaisons
- Support du décalage d'en-tête Nielsen
- Masquage automatique des prix de revient
            """
        )


def _afficher_resume(nom_fichier: str, colonnes: dict[str, str], resultat) -> None:
    st.subheader("Résumé du contrôle initial")
    st.caption(f"Fichier analysé : {nom_fichier}")
    colonnes_utilisees = ", ".join(
        f"{LIBELLES_CHAMPS[champ]} ({colonne})"
        for champ, colonne in colonnes.items()
    )
    st.caption(f"Colonnes identifiées : {colonnes_utilisees}")

    metrique_1, metrique_2, metrique_3, metrique_4 = st.columns(4)
    metrique_1.metric("Produits analysés", resultat.produits_analyses)
    metrique_2.metric("Lignes conformes", resultat.lignes_conformes)
    metrique_3.metric("Lignes avec problème", resultat.lignes_en_erreur)
    metrique_4.metric("Problèmes détectés", len(resultat.problemes))

    if resultat.lignes_en_erreur == 0:
        st.success("Aucun problème détecté sur les champs contrôlés.")
    elif resultat.lignes_en_erreur == 1:
        st.warning("1 ligne contient au moins un problème.")
    else:
        st.warning(f"{resultat.lignes_en_erreur} lignes contiennent au moins un problème.")

    if not resultat.problemes.empty:
        st.dataframe(
            repartition_problemes(resultat.problemes),
            width="stretch",
            hide_index=True,
        )


def _afficher_problemes(problemes: pd.DataFrame) -> None:
    st.subheader("Rapport des erreurs")
    if problemes.empty:
        st.write("Aucune erreur à signaler.")
    else:
        st.dataframe(problemes, width="stretch", hide_index=True)
    st.download_button(
        label="Télécharger le rapport des erreurs (CSV)",
        data=vers_csv(problemes),
        file_name="rapport_erreurs.csv",
        mime="text/csv",
    )


def _afficher_donnees(
    donnees: pd.DataFrame,
    lignes_fichier: pd.Series,
    problemes: pd.DataFrame,
) -> None:
    st.subheader("Données brutes importées")
    affichage = donnees.copy()
    if "Prix de revient" in affichage.columns:
        affichage = affichage.drop(columns=["Prix de revient"])

    lignes_en_erreur = set(problemes["Ligne"].tolist()) if not problemes.empty else set()
    affichage.insert(
        0,
        "Contrôle",
        [
            "À corriger" if int(lignes_fichier.loc[idx]) in lignes_en_erreur else "Conforme"
            for idx in donnees.index
        ],
    )
    st.dataframe(affichage, width="stretch", hide_index=True)


def _afficher_onglet_classification(donnees_classifiees: pd.DataFrame) -> None:
    st.subheader("Classification globale & Détection des Services")
    st.write(
        "Les lignes de frais et services sont étiquetées pour exclusion de l'export boutique, "
        "tout en préservant l'intégrité de la table d'origine."
    )

    donnees_a_afficher = donnees_classifiees.copy()
    if "Prix de revient" in donnees_a_afficher.columns:
        donnees_a_afficher = donnees_a_afficher.drop(columns=["Prix de revient"])

    c1, c2 = st.columns([1, 2])
    with c1:
        repart = donnees_a_afficher["Type Ligne"].value_counts().reset_index()
        repart.columns = ["Type Ligne", "Nombre d'articles"]
        st.dataframe(repart, hide_index=True)
    with c2:
        nb_services = (donnees_a_afficher["Type Ligne"] == "Service / Frais").sum()
        st.metric("Lignes de services / frais détectées", nb_services)
        st.caption("Ces lignes ne seront pas injectées comme fiches articles dans PrestaShop.")

    st.dataframe(donnees_a_afficher, width="stretch", hide_index=True)
    st.download_button(
        label="Télécharger les données classifiées (CSV)",
        data=vers_csv(donnees_a_afficher),
        file_name="catalogue_qualifie.csv",
        mime="text/csv",
    )


def _afficher_onglet_visserie(fiches_visserie: list) -> None:
    st.subheader("Regroupement Visserie : 1 Diamètre = 1 Fiche indépendante")
    st.caption("Règle appliquée : Aucune interversion de longueurs entre diamètres distincts.")

    if not fiches_visserie:
        st.info("Aucun article de visserie n'a été reconnu dans ce fichier.")
        return

    st.metric("Fiches produits Visserie créées", len(fiches_visserie))

    for fiche in fiches_visserie:
        with st.expander(f"📦 {fiche.nom_base} — Ø {fiche.diametre} ({len(fiche.declinaisons)} déclinaisons)", expanded=False):
            st.markdown(f"**Identifiant fiche :** `{fiche.id_fiche}`")
            st.markdown(f"**Longueurs disponibles :** {', '.join(fiche.longueurs_disponibles)} mm")
            st.markdown(f"**Stock cumulé :** {fiche.total_stock}")

            df_decl = pd.DataFrame([
                {
                    "Référence (Code Barre)": d.reference,
                    "Désignation Caisse": d.designation_source,
                    "Déclinaison Longueur": f"{d.longueur} mm",
                    "Prix Vente": d.prix,
                    "Stock": d.stock,
                    "Ligne": d.ligne_fichier,
                }
                for d in fiche.declinaisons
            ])
            st.dataframe(df_decl, hide_index=True, width="stretch")


main()

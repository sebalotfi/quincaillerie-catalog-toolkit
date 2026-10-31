"""Interface locale du Quincaillerie Catalog Toolkit."""

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


def main() -> None:
    st.set_page_config(
        page_title="Quincaillerie Catalog Toolkit",
        layout="wide",
    )
    # Le bandeau « skills » de Streamlit est en anglais et recouvre la page.
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
        "Catalogue à contrôler",
        help="CSV (.csv) ou Excel (.xlsx). La première ligne doit contenir les en-têtes.",
    )
    if fichier is None:
        st.info("Importez un fichier CSV ou Excel pour lancer le contrôle.")
        return

    try:
        catalogue = lire_catalogue(fichier.getvalue(), fichier.name)
        colonnes = identifier_colonnes(catalogue.donnees.columns)
        resultat = analyser_catalogue(
            catalogue.donnees,
            catalogue.lignes_fichier,
            colonnes,
        )
    except ErreurFichier as erreur:
        st.error(str(erreur))
        return

    _afficher_resume(fichier.name, colonnes, resultat)
    _afficher_problemes(resultat.problemes)
    _afficher_donnees(catalogue.donnees, catalogue.lignes_fichier, resultat.problemes)


def _afficher_entete() -> None:
    st.title("Quincaillerie Catalog Toolkit")
    st.write(
        "Contrôlez un catalogue produits sur cet ordinateur, puis téléchargez "
        "le rapport des erreurs et une copie CSV des données lues."
    )
    with st.sidebar:
        st.header("Contrôles effectués")
        st.markdown(
            """
- Références produit en double
- Nom, référence, prix ou quantité manquants
- Prix négatif ou non numérique
- Quantité négative ou non entière
- Catégorie vide, lorsque la colonne est présente
            """
        )
        st.header("Fichier d'origine")
        st.write(
            "Le fichier que vous déposez n'est pas modifié. "
            "Les téléchargements sont de nouvelles copies."
        )


def _afficher_resume(nom_fichier: str, colonnes: dict[str, str], resultat) -> None:
    st.subheader("Résumé")
    st.caption(f"Fichier lu : {nom_fichier}")
    colonnes_utilisees = ", ".join(
        f"{LIBELLES_CHAMPS[champ]} ({colonne})"
        for champ, colonne in colonnes.items()
    )
    st.caption(f"Colonnes utilisées : {colonnes_utilisees}")

    metrique_1, metrique_2, metrique_3, metrique_4 = st.columns(4)
    metrique_1.metric("Produits analysés", resultat.produits_analyses)
    metrique_2.metric("Lignes conformes", resultat.lignes_conformes)
    metrique_3.metric("Lignes avec problème", resultat.lignes_en_erreur)
    metrique_4.metric("Problèmes détectés", len(resultat.problemes))

    if resultat.lignes_en_erreur == 0:
        st.success("Aucun problème détecté sur les champs contrôlés.")
        return
    if resultat.lignes_en_erreur == 1:
        st.warning("1 ligne contient au moins un problème.")
    else:
        st.warning(
            f"{resultat.lignes_en_erreur} lignes contiennent au moins un problème."
        )
    st.dataframe(
        repartition_problemes(resultat.problemes),
        width="stretch",
        hide_index=True,
    )


def _afficher_problemes(problemes: pd.DataFrame) -> None:
    st.subheader("Rapport des erreurs")
    if problemes.empty:
        st.write("Aucune erreur à signaler. Le rapport téléchargé ne contient que les en-têtes.")
    else:
        st.dataframe(problemes, width="stretch", hide_index=True)
    st.download_button(
        label="Télécharger le rapport des erreurs (CSV)",
        data=vers_csv(problemes),
        file_name="rapport_erreurs.csv",
        mime="text/csv",
        on_click="ignore",
    )


def _afficher_donnees(
    donnees: pd.DataFrame,
    lignes_fichier: pd.Series,
    problemes: pd.DataFrame,
) -> None:
    st.subheader("Données importées")
    st.caption(
        "Les autres colonnes du fichier sont conservées. "
        "La colonne Contrôle est ajoutée seulement dans cet aperçu."
    )
    st.dataframe(
        _ajouter_statut(donnees, lignes_fichier, problemes),
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        label="Télécharger les données importées (CSV)",
        data=vers_csv(donnees),
        file_name="catalogue_importe.csv",
        mime="text/csv",
        on_click="ignore",
        help="Copie des données lues, sans la colonne Contrôle et sans écrire dans le fichier d'origine.",
    )


def _ajouter_statut(
    donnees: pd.DataFrame,
    lignes_fichier: pd.Series,
    problemes: pd.DataFrame,
) -> pd.DataFrame:
    lignes_en_erreur = set()
    if not problemes.empty:
        lignes_en_erreur = set(problemes["Ligne"].tolist())
    affichage = donnees.copy()
    affichage.insert(
        0,
        "Contrôle",
        [
            "À corriger" if int(lignes_fichier.loc[idx]) in lignes_en_erreur else "Conforme"
            for idx in donnees.index
        ],
    )
    return affichage


main()

# Quincaillerie Catalog Toolkit

Application locale pour contrôler un catalogue de produits de quincaillerie avant de le réutiliser. Le fichier déposé n'est pas modifié : l'application en lit une copie, signale les problèmes, puis propose deux téléchargements CSV.

Les données restent sur votre ordinateur. Cette version ne comporte ni compte, ni base de données, ni service en ligne.

Licence : [MIT](LICENSE).

## Prérequis

- Windows, macOS ou Linux
- Python 3.12

Les bibliothèques utilisées sont [Streamlit](https://streamlit.io/) (interface), [Pandas](https://pandas.pydata.org/) (tableaux) et [OpenPyXL](https://openpyxl.readthedocs.io/) (fichiers Excel `.xlsx`). Pytest sert uniquement aux tests automatisés.

## Installation

Dans le dossier du projet :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Sous macOS ou Linux :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Si le dossier `.venv` existe déjà, seule la seconde commande est nécessaire.

## Lancement

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

Sous macOS ou Linux :

```bash
.venv/bin/streamlit run app.py
```

Streamlit ouvre l'application dans le navigateur, en général à l'adresse `http://localhost:8501`.

Pour fermer l'application, revenez au terminal et appuyez sur `Ctrl+C`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Sous macOS ou Linux : `.venv/bin/python -m pytest`.

## Fichiers du projet

| Fichier | Rôle |
| --- | --- |
| `app.py` | Écran : import, résumé, tableaux et téléchargements |
| `lecture_catalogue.py` | Lecture CSV et Excel, reconnaissance des colonnes |
| `validation_catalogue.py` | Règles de contrôle |
| `tests/` | Tests automatisés |
| `exemples/catalogue_exemple.csv` | Petit catalogue fictif, avec des erreurs volontaires |
| `requirements.txt` | Bibliothèques à installer |
| `.gitignore` | Fichiers à ne pas publier |
| `LICENSE` | Licence MIT |

## Colonnes attendues

La première ligne du fichier doit contenir les en-têtes. Quatre colonnes sont obligatoires :

| Champ | Exemples d'en-têtes |
| --- | --- |
| Nom du produit | `nom`, `désignation`, `libellé` |
| Référence | `référence`, `ref`, `code` |
| Prix | `prix`, `prix_ht`, `tarif` |
| Quantité | `quantité`, `qté`, `stock` |

La colonne `catégorie` (ou `famille`, `rayon`) est facultative. Si elle est présente, une cellule vide est signalée. Les autres colonnes sont conservées dans l'aperçu et dans le CSV des données importées, sans être contrôlées.

Le séparateur CSV peut être une virgule, un point-virgule ou une tabulation. Les décimales acceptent le point (`2.50`) ou la virgule (`2,50`). Écrivez les prix et les quantités sans séparateur de milliers.

## Contrôles

- référence répétée, sans tenir compte des majuscules ni des espaces autour ;
- nom, référence, prix ou quantité manquant ;
- prix qui n'est pas un nombre, ou prix négatif (zéro reste accepté) ;
- quantité qui n'est pas un nombre entier, ou quantité négative (zéro reste accepté) ;
- catégorie vide, seulement si la colonne existe.

Le résumé indique le nombre de produits analysés, de lignes conformes, de lignes avec au moins un problème, et le nombre total de problèmes. Le numéro de ligne reprend celui du fichier : la ligne 1 est l'en-tête, le premier produit est donc la ligne 2.

## Téléchargements

- **Rapport des erreurs** : une ligne par problème (`Ligne`, `Champ`, `Valeur`, `Problème`).
- **Données importées** : copie CSV de ce qui a été lu, sans la colonne `Contrôle` affichée à l'écran.

Ces fichiers sont de nouveaux CSV, encodés en UTF-8 avec un indicateur d'encodage pour Excel. Le séparateur est la virgule, et les valeurs qui contiennent une virgule sont entourées de guillemets. Le fichier d'origine n'est pas réécrit.

## Essayer avec l'exemple

1. Lancez l'application.
2. Importez `exemples/catalogue_exemple.csv`.
3. Le résumé doit indiquer 10 produits, 2 lignes conformes, 8 lignes avec problème et 10 problèmes.

Ce fichier contient des produits inventés. Ne versionnez pas de catalogue commercial : `.gitignore` écarte les CSV et Excel locaux, sauf cet exemple.

## Messages en cas de fichier inutilisable

| Situation | Ce que l'application affiche |
| --- | --- |
| Fichier vide | Le fichier est vide. |
| En-têtes seuls, sans produit | Le fichier ne contient aucun produit. |
| Colonne obligatoire absente | Colonnes absentes, avec la liste des champs manquants. |
| Extension autre que `.csv` ou `.xlsx` | Format incorrect. |
| Excel illisible, protégé ou corrompu | Le fichier Excel est illisible. |
| CSV binaire ou mal formé | Le fichier est illisible ou mal formé. |

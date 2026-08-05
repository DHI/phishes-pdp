"""
read_hydrus_results.py
--------------
Trois fonctions pour lire les fichiers de sortie HYDRUS-1D sous forme de
DataFrame pandas, quelle que soit la taille du fichier.

Fonctions
---------
read_solute(path)   → DataFrame  (solute1.out  — transfert de masse)
read_tlevel(path)   → DataFrame  (T_Level.out  — transfert d'eau)
read_nod_inf(path)  → DataFrame  (Nod_Inf.out  — profils de profondeur)

Dépendances : pandas
Python : 3.11+
"""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Utilitaires internes
# ---------------------------------------------------------------------------

def _read_text(path: str | Path) -> str:
    """Lit un fichier texte en gérant les fins de ligne Windows (\\r\\n)."""
    return Path(path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def _is_data_line(line: str) -> bool:
    """Renvoie True si la ligne contient exclusivement des valeurs numériques."""
    stripped = line.strip()
    if not stripped:
        return False
    # Une ligne de données commence par un chiffre, un signe ou un point
    if not re.match(r"^[\s\d\+\-\.]", stripped):
        return False
    # Tente une conversion : si au moins le premier token est numérique → données
    try:
        float(stripped.split()[0])
        return True
    except ValueError:
        return False


def _build_obs_colnames(n_fixed: int, n_extra: int) -> list[str]:
    """
    Génère les noms des colonnes supplémentaires (points d'observation)
    présentes dans solute1.out au-delà des colonnes fixes documentées.
    Chaque point d'observation produit deux colonnes : cv(i) et Sum(cv(i)).
    """
    cols: list[str] = []
    for i in range(1, n_extra // 2 + 1):
        cols += [f"cv({i})", f"Sum(cv({i}))"]
    if n_extra % 2 == 1:          # colonne orpheline éventuelle
        cols.append(f"cv({n_extra // 2 + 1})")
    return cols


# ---------------------------------------------------------------------------
# 1. read_solute  —  solute1.out
# ---------------------------------------------------------------------------

# Colonnes fixes documentées dans le manuel HYDRUS-1D pour solute1.out
_SOLUTE_FIXED_COLS = [
    "Time",
    "cvTop", "cvBot",
    "Sum(cvTop)", "Sum(cvBot)",
    "cvCh0", "cvCh1",
    "cTop", "cRoot", "cBot",
    "cvRoot", "Sum(cvRoot)", "Sum(cvNEql)",
    "TLevel",
    "cGWL", "cRunOff", "Sum(cRunOff)",
]

def read_solute(path: str | Path) -> pd.DataFrame:
    """
    Lit le fichier solute1.out de HYDRUS-1D.

    Le fichier contient un en-tête sur 2 lignes (noms + unités) suivi de
    lignes de données numériques. Le nombre de colonnes peut varier selon
    le nombre de points d'observation définis dans la simulation ; les
    colonnes supplémentaires sont nommées cv(i) / Sum(cv(i)).

    Paramètres
    ----------
    path : chemin vers solute1.out.

    Retourne
    --------
    DataFrame avec une ligne par pas de temps.
    """
    text  = _read_text(path)
    lines = text.splitlines()

    # --- Détection de l'en-tête (ligne contenant "Time" et "cvTop") ---
    header_idx = None
    for i, line in enumerate(lines):
        if "Time" in line and "cvTop" in line:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("En-tête 'Time … cvTop' introuvable dans le fichier.")

    # --- Collecte des lignes de données ---
    data_lines: list[str] = []
    for line in lines[header_idx + 2:]:   # +2 : saute la ligne d'unités
        if _is_data_line(line):
            data_lines.append(line)

    if not data_lines:
        raise ValueError("Aucune ligne de données trouvée dans le fichier.")

    # --- Détermination du nombre de colonnes (variable selon les obs.) ---
    n_cols = len(data_lines[0].split())
    n_fixed = len(_SOLUTE_FIXED_COLS)
    n_extra = n_cols - n_fixed
    columns = _SOLUTE_FIXED_COLS + _build_obs_colnames(n_fixed, n_extra)

    # --- Parsing via pandas ---
    df = pd.read_csv(
        StringIO("\n".join(data_lines)),
        sep=r"\s+",
        header=None,
        names=columns,
        engine="python",
    )

    # TLevel est un entier (numéro interne de pas de temps)
    df["TLevel"] = df["TLevel"].astype(int)

    return df


# ---------------------------------------------------------------------------
# 2. read_tlevel  —  T_Level.out
# ---------------------------------------------------------------------------

# Colonnes fixes documentées dans le manuel HYDRUS-1D pour T_Level.out
_TLEVEL_FIXED_COLS = [
    "Time",
    "rTop", "rRoot", "vTop", "vRoot", "vBot",
    "sum(rTop)", "sum(rRoot)", "sum(vTop)", "sum(vRoot)", "sum(vBot)",
    "hTop", "hRoot", "hBot",
    "RunOff", "sum(RunOff)",
    "Volume",
    "sum(Infil)", "sum(Evap)",
    "TLevel",
    "Cum(WTrans)",
    "SnowLayer",
]

def read_tlevel(path: str | Path) -> pd.DataFrame:
    """
    Lit le fichier T_Level.out de HYDRUS-1D.

    Le fichier commence par un bloc d'en-tête programme (lignes *******),
    suivi d'une ligne de noms de colonnes et d'une ligne d'unités, puis
    des données numériques. Les colonnes supplémentaires éventuelles sont
    nommées extra_1, extra_2, …

    Paramètres
    ----------
    path : chemin vers T_Level.out.

    Retourne
    --------
    DataFrame avec une ligne par pas de temps.
    """
    text  = _read_text(path)
    lines = text.splitlines()

    # --- Détection de l'en-tête (ligne contenant "Time" et "rTop") ---
    header_idx = None
    for i, line in enumerate(lines):
        if "Time" in line and "rTop" in line:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("En-tête 'Time … rTop' introuvable dans le fichier.")

    # --- Collecte des lignes de données ---
    data_lines: list[str] = []
    for line in lines[header_idx + 2:]:   # +2 : saute la ligne d'unités
        if _is_data_line(line):
            data_lines.append(line)

    if not data_lines:
        raise ValueError("Aucune ligne de données trouvée dans le fichier.")

    # --- Nommage des colonnes ---
    n_cols  = len(data_lines[0].split())
    n_fixed = len(_TLEVEL_FIXED_COLS)
    n_extra = n_cols - n_fixed
    if n_extra > 0:
        extra_cols = [f"extra_{i}" for i in range(1, n_extra + 1)]
    else:
        extra_cols = []
    columns = _TLEVEL_FIXED_COLS[:n_cols] if n_extra < 0 else _TLEVEL_FIXED_COLS + extra_cols

    # --- Parsing ---
    df = pd.read_csv(
        StringIO("\n".join(data_lines)),
        sep=r"\s+",
        header=None,
        names=columns,
        engine="python",
    )

    df["TLevel"] = df["TLevel"].astype(int)

    return df


# ---------------------------------------------------------------------------
# 3. read_nod_inf  —  Nod_Inf.out
# ---------------------------------------------------------------------------

# Colonnes fixes documentées dans le manuel HYDRUS-1D pour Nod_Inf.out
_NOD_FIXED_COLS = [
    "Node", "Depth", "Head", "Moisture", "K", "C",
    "Flux", "Sink", "Kappa", "v_KsTop", "Temp",
]

def read_nod_inf(path: str | Path) -> pd.DataFrame:
    """
    Lit le fichier Nod_Inf.out de HYDRUS-1D.

    Le fichier est structuré en blocs temporels séparés par « end ».
    Chaque bloc commence par « Time: <valeur> » suivi d'un en-tête de
    colonnes et des données nœud par nœud. La colonne « Time » est ajoutée
    à chaque ligne pour identifier le pas de temps. Les colonnes de
    concentration et de sorption sont nommées Conc(1), Conc(2), … et
    Sorb(1), Sorb(2), …

    Paramètres
    ----------
    path : chemin vers Nod_Inf.out.

    Retourne
    --------
    DataFrame avec une ligne par (temps × nœud).
    La colonne « Time » identifie le bloc temporel.
    """
    text   = _read_text(path)
    lines  = text.splitlines()

    # --- Détection de l'en-tête de colonnes (ligne contenant "Node" et "Depth") ---
    col_header_idx = None
    for i, line in enumerate(lines):
        if "Node" in line and "Depth" in line and "Head" in line:
            col_header_idx = i
            break
    if col_header_idx is None:
        raise ValueError("En-tête 'Node  Depth  Head …' introuvable dans le fichier.")

    # Détermination du nombre de colonnes de concentration/sorption
    # à partir de la première ligne de données du premier bloc
    first_data_idx = col_header_idx + 2   # +2 : saute la ligne d'unités
    while first_data_idx < len(lines) and not _is_data_line(lines[first_data_idx]):
        first_data_idx += 1

    if first_data_idx >= len(lines):
        raise ValueError("Aucune ligne de données trouvée dans le fichier.")

    n_total  = len(lines[first_data_idx].split())
    n_fixed  = len(_NOD_FIXED_COLS)
    n_extra  = n_total - n_fixed          # colonnes Conc + Sorb
    n_conc   = n_extra // 2
    n_sorb   = n_extra - n_conc

    conc_cols = [f"Conc({i})" for i in range(1, n_conc + 1)]
    sorb_cols = [f"Sorb({i})" for i in range(1, n_sorb + 1)]
    columns   = _NOD_FIXED_COLS + conc_cols + sorb_cols

    # --- Parcours des blocs temporels ---
    blocks: list[pd.DataFrame] = []
    current_time: float | None = None
    current_data: list[str]    = []

    def _flush(t: float | None, rows: list[str]) -> None:
        """Parse et stocke un bloc accumulé."""
        if t is None or not rows:
            return
        df_block = pd.read_csv(
            StringIO("\n".join(rows)),
            sep=r"\s+",
            header=None,
            names=columns,
            engine="python",
        )
        df_block.insert(0, "Time", t)
        blocks.append(df_block)

    for line in lines:
        stripped = line.strip()

        # Ligne « Time: <valeur> » → début d'un nouveau bloc
        m = re.match(r"^Time:\s+([\d\.\-\+eE]+)", stripped)
        if m:
            _flush(current_time, current_data)
            current_time = float(m.group(1))
            current_data = []
            continue

        # Ligne « end » → fin du bloc courant
        if stripped.lower() == "end":
            _flush(current_time, current_data)
            current_time = None
            current_data = []
            continue

        # Ligne de données numériques
        if current_time is not None and _is_data_line(line):
            current_data.append(line)

    # Dernier bloc sans "end" final éventuel
    _flush(current_time, current_data)

    if not blocks:
        raise ValueError("Aucun bloc temporel trouvé dans le fichier.")

    df = pd.concat(blocks, ignore_index=True)
    df["Node"] = df["Node"].astype(int)

    return df


# ---------------------------------------------------------------------------
# Exemple d'utilisation
# ---------------------------------------------------------------------------
# if __name__ == "__main__":
#     import sys
#
#     paths = {
#         "solute1.out": "solute1.out",
#         "T_Level.out": "T_Level.out",
#         "Nod_Inf.out": "Nod_Inf.out",
#     }
#
#     print("=== solute1.out ===")
#     df_s = read_solute(paths["solute1.out"])
#     print(df_s.head())
#     print(f"Shape : {df_s.shape}  |  Colonnes : {list(df_s.columns)}\n")
#
#     print("=== T_Level.out ===")
#     df_t = read_tlevel(paths["T_Level.out"])
#     print(df_t.head())
#     print(f"Shape : {df_t.shape}  |  Colonnes : {list(df_t.columns)}\n")
#
#     print("=== Nod_Inf.out ===")
#     df_n = read_nod_inf(paths["Nod_Inf.out"])
#     print(df_n.head())
#     print(f"Shape : {df_n.shape}  |  Colonnes : {list(df_n.columns)}")
#     print(f"Blocs temporels : {df_n['Time'].nunique()}")

"""
generate_atmosph.py
-------------------
Génère un fichier ATMOSPH.IN (format HYDRUS) en remplaçant :
  - la colonne "Prec"  par les valeurs de inf_hydrus.csv        (colonne 'infiltration')
  - la colonne "cTop"  par les valeurs de conc_inf_no3_hydrus.csv (colonne 'concentration')

Les valeurs de Prec et cTop sont :
  - multipliées par leur facteur multiplicatif respectif (prec_factor, ctop_factor)
  - arrondies et écrites sur 6 caractères significatifs maximum afin de garantir
    l'alignement des colonnes dans le fichier à largeur fixe (champ de 12 caractères)

Le nombre de lignes du fichier généré suit toujours la longueur des CSV :
  - CSV plus long  → extension automatique + mise à jour de MaxAL
  - CSV plus court → troncature automatique + mise à jour de MaxAL
  - CSV identique  → remplacement pur, MaxAL inchangé

Dépendances : pandas
Python : 3.11+
"""

from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Indices de colonnes dans les lignes de données (0-based)
#   0:tAtm  1:Prec  2:rSoil  3:rRoot  4:hCritA  5:rB  6:hB  7:ht
#   8:tTop  9:tBot  10:Ampl  11:cTop  12:cBot   (13:RootDepth — optionnel)
# ---------------------------------------------------------------------------
COL_TATM = 0
COL_PREC = 1
COL_CTOP = 11

FIELD_WIDTH     = 12   # largeur totale de chaque champ (identique à l'original)
DECIMAL_PLACES = 6     # nombre de décimales après la virgule pour Prec et cTop


def _format_data_value(value: float) -> str:
    """
    Formate une valeur de données (Prec ou cTop) avec DECIMAL_PLACES décimales
    fixes après la virgule, puis l'aligne à droite dans FIELD_WIDTH caractères.

    Exemples (FIELD_WIDTH=12, DECIMAL_PLACES=6) :
      -0.006667037  →  "   -0.006667"   (6 décimales, arrondi)
      -0.659937162  →  "   -0.659937"   (6 décimales, arrondi)
       39.4513534   →  "   39.451353"   (6 décimales, arrondi)
       0.0          →  "    0.000000"
      -1.0          →  "   -1.000000"
    """
    formatted = f"{value:.{DECIMAL_PLACES}f}"
    return f"{formatted:>{FIELD_WIDTH}}"


def _format_other_value(value: float) -> str:
    """
    Formate une valeur des colonnes non remplacées (rSoil, rRoot, etc.)
    en conservant le style original (entier si possible, sinon 'g').
    """
    if value == int(value) and abs(value) < 1e15:
        return f"{int(value):>{FIELD_WIDTH}}"
    return f"{value:>{FIELD_WIDTH}g}"


def _build_data_line(tokens_template: list[str], row_idx: int,
                     prec: float, ctop: float, eol: str) -> str:
    """
    Construit une ligne de données en partant du gabarit de tokens issu
    de la dernière ligne du template, en remplaçant tAtm, Prec et cTop.
    """
    tokens = tokens_template.copy()
    tokens[COL_TATM] = str(row_idx + 1)
    tokens[COL_PREC] = _format_data_value(prec).strip()
    tokens[COL_CTOP] = _format_data_value(ctop).strip()
    return "".join(f"{tok:>{FIELD_WIDTH}}" for tok in tokens) + " " + eol


def generate_atmosph(
    template_path: str | Path,
    inf_csv_path: str | Path,
    conc_csv_path: str | Path,
    output_path: str | Path,
    prec_factor: float = 1.0,
    ctop_factor: float = 1.0,
    nbdays: float = -1.0
) -> None:
    """
    Génère un fichier ATMOSPH.IN en remplaçant les colonnes Prec et cTop.

    Paramètres
    ----------
    template_path : chemin vers le fichier ATMOSPH.IN original (modèle).
    inf_csv_path  : chemin vers inf_hydrus.csv
                    (doit contenir une colonne 'infiltration').
    conc_csv_path : chemin vers conc_inf_no3_hydrus.csv
                    (doit contenir une colonne 'concentration').
    output_path   : chemin du fichier ATMOSPH.IN généré en sortie.
    prec_factor   : facteur multiplicatif appliqué à chaque valeur de Prec
                    (défaut : 1.0, aucune modification).
    ctop_factor   : facteur multiplicatif appliqué à chaque valeur de cTop
                    (défaut : 1.0, aucune modification).
    """
    template_path = Path(template_path)
    output_path   = Path(output_path)

    # ------------------------------------------------------------------
    # 1. Lecture et validation des CSV
    # ------------------------------------------------------------------
    df_inf  = pd.read_csv(inf_csv_path)
    df_conc = pd.read_csv(conc_csv_path)
    if nbdays > 0:
        df_inf = df_inf[:nbdays]
        df_conc = df_conc[:nbdays]

    # if infiltration = 0, no need to add a concentration in the infiltration (to avoid mass balance errors)
    df_conc[df_inf == 0.0] = 0.0

    if "infiltration" not in df_inf.columns:
        raise ValueError(
            f"Colonne 'infiltration' introuvable dans {inf_csv_path}. "
            f"Colonnes disponibles : {list(df_inf.columns)}"
        )
    if "concentration" not in df_conc.columns:
        raise ValueError(
            f"Colonne 'concentration' introuvable dans {conc_csv_path}. "
            f"Colonnes disponibles : {list(df_conc.columns)}"
        )

    prec_values = (df_inf["infiltration"] * prec_factor).tolist()
    ctop_values = (df_conc["concentration"] * ctop_factor).tolist()
    n_csv = len(prec_values)

    if len(ctop_values) != n_csv:
        raise ValueError(
            f"Les deux CSV n'ont pas le même nombre de lignes : "
            f"inf_hydrus.csv={n_csv}, conc_inf_no3_hydrus.csv={len(ctop_values)}"
        )

    if prec_factor != 1.0:
        print(f"ℹ️  Facteur Prec  : {prec_factor}")
    if ctop_factor != 1.0:
        print(f"ℹ️  Facteur cTop  : {ctop_factor}")

    # ------------------------------------------------------------------
    # 2. Lecture du fichier template
    # ------------------------------------------------------------------
    raw   = template_path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines(keepends=True)

    # Détection du séparateur de fin de ligne dominant
    eol = "\r\n" if raw.count("\r\n") > raw.count("\n") // 2 else "\n"

    # Repérage de la ligne d'en-tête des colonnes ("tAtm … Prec …")
    header_line_idx = None
    for i, line in enumerate(lines):
        if "tAtm" in line and "Prec" in line:
            header_line_idx = i
            break

    if header_line_idx is None:
        raise ValueError(
            "Ligne d'en-tête 'tAtm ... Prec ...' introuvable dans le fichier template."
        )

    data_start_idx = header_line_idx + 1

    # ------------------------------------------------------------------
    # 3. Séparation : avant le bloc de données / données / après
    # ------------------------------------------------------------------
    pre_data   = lines[:data_start_idx]
    data_lines = []
    post_lines = []

    for line in lines[data_start_idx:]:
        stripped = line.strip()
        if stripped.lower().startswith("end") or not stripped:
            post_lines.append(line)
        else:
            if post_lines:
                post_lines.append(line)
            else:
                data_lines.append(line)

    n_template = len(data_lines)

    # Gabarit de tokens issu de la dernière ligne du template
    last_data_tokens = data_lines[-1].strip().split() if data_lines else ["0"] * 13

    # ------------------------------------------------------------------
    # 4. Calcul du nombre de lignes en sortie et messages informatifs
    # ------------------------------------------------------------------
    n_output = n_csv

    if n_csv < n_template:
        print(
            f"ℹ️  Réduction  : CSV={n_csv} lignes < template={n_template} lignes "
            f"→ tronqué à {n_csv} lignes."
        )
    elif n_csv > n_template:
        print(
            f"ℹ️  Extension  : CSV={n_csv} lignes > template={n_template} lignes "
            f"→ étendu à {n_csv} lignes."
        )

    # ------------------------------------------------------------------
    # 5. Construction du nouveau bloc de données
    # ------------------------------------------------------------------
    new_data_lines: list[str] = []

    for row_idx in range(n_output):
        prec = prec_values[row_idx]
        ctop = ctop_values[row_idx]

        if row_idx < n_template:
            # Ligne existante dans le template
            tokens = data_lines[row_idx].strip().split()
            tokens[COL_TATM] = str(row_idx + 1)
            tokens[COL_PREC] = _format_data_value(prec).strip()
            tokens[COL_CTOP] = _format_data_value(ctop).strip()
            new_line = "".join(f"{tok:>{FIELD_WIDTH}}" for tok in tokens) + " " + eol
        else:
            # Ligne supplémentaire (extension au-delà du template)
            new_line = _build_data_line(last_data_tokens, row_idx, prec, ctop, eol)

        new_data_lines.append(new_line)

    # ------------------------------------------------------------------
    # 6. Mise à jour de MaxAL dans l'en-tête si nécessaire
    # ------------------------------------------------------------------
    if n_output != n_template:
        for i, line in enumerate(pre_data):
            if "MaxAL" in line and "number of atmospheric" in line:
                max_al_value_idx = i + 1
                if max_al_value_idx < len(pre_data):
                    old_val_line = pre_data[max_al_value_idx]
                    new_val_line = (
                        old_val_line.rstrip().rstrip("0123456789")
                        + str(n_output)
                        + eol
                    )
                    pre_data[max_al_value_idx] = new_val_line
                    print(f"ℹ️  MaxAL mis à jour : {n_template} → {n_output}")
                break

    # ------------------------------------------------------------------
    # 7. Assemblage et écriture
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(pre_data + new_data_lines + post_lines), encoding="utf-8")

    print(
        f"✅  Fichier généré : {output_path}  "
        f"({n_output} lignes de données, MaxAL={n_output})"
    )


# ---------------------------------------------------------------------------
# Point d'entrée — exemple d'utilisation
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    generate_atmosph(
        template_path="ATMOSPH.IN",
        inf_csv_path="inf_hydrus.csv",
        conc_csv_path="conc_inf_no3_hydrus.csv",
        output_path="ATMOSPH_new.IN",
        prec_factor=1.0,
        ctop_factor=1.0,
    )

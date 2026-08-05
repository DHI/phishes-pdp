"""
generate_atmosph.py
-------------------
Génère un fichier ATMOSPH.IN (format HYDRUS) en remplaçant :
  - la colonne "Prec"  par les valeurs de inf_hydrus.csv        (colonne 'infiltration')
  - la colonne "cTop"  par les valeurs de conc_inf_no3_hydrus.csv (colonne 'concentration')

Si les CSV contiennent plus de lignes que le template :
  - le bloc de données est étendu automatiquement
  - la valeur MaxAL dans l'en-tête est mise à jour en conséquence

Si les CSV contiennent moins de lignes que le template :
  - seules les lignes couvertes par les CSV sont mises à jour
  - un avertissement est émis

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

FIELD_WIDTH = 12   # largeur de champ identique à l'original


def _format_value(value: float) -> str:
    """Formate un flottant en respectant le style du fichier original."""
    if value == int(value) and abs(value) < 1e15:
        return f"{int(value):>{FIELD_WIDTH}}"
    return f"{value:>{FIELD_WIDTH}g}"


def _build_data_line(tokens_template: list[str], row_idx: int,
                     prec: float, ctop: float, eol: str) -> str:
    """
    Construit une ligne de données en partant du gabarit de tokens,
    en remplaçant tAtm (index 0), Prec (index 1) et cTop (index 11).
    """
    tokens = tokens_template.copy()
    tokens[COL_TATM] = str(row_idx + 1)   # tAtm commence à 1
    tokens[COL_PREC] = _format_value(prec).strip()
    tokens[COL_CTOP] = _format_value(ctop).strip()
    return "".join(f"{tok:>{FIELD_WIDTH}}" for tok in tokens) + " " + eol


def generate_atmosph(
    template_path: str | Path,
    inf_csv_path: str | Path,
    conc_csv_path: str | Path,
    output_path: str | Path,
) -> None:
    """
    Génère un fichier ATMOSPH.IN en remplaçant les colonnes Prec et cTop,
    et en étendant automatiquement le nombre de lignes si nécessaire.

    Paramètres
    ----------
    template_path : chemin vers le fichier ATMOSPH.IN original (modèle).
    inf_csv_path  : chemin vers inf_hydrus.csv
                    (doit contenir une colonne 'infiltration').
    conc_csv_path : chemin vers conc_inf_no3_hydrus.csv
                    (doit contenir une colonne 'concentration').
    output_path   : chemin du fichier ATMOSPH.IN généré en sortie.
    """
    template_path = Path(template_path)
    output_path   = Path(output_path)

    # ------------------------------------------------------------------
    # 1. Lecture des CSV
    # ------------------------------------------------------------------
    df_inf  = pd.read_csv(inf_csv_path)
    df_conc = pd.read_csv(conc_csv_path)

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

    prec_values = df_inf["infiltration"].tolist()
    ctop_values = df_conc["concentration"].tolist()
    n_csv = len(prec_values)

    if len(ctop_values) != n_csv:
        raise ValueError(
            f"Les deux CSV n'ont pas le même nombre de lignes : "
            f"inf_hydrus.csv={n_csv}, conc_inf_no3_hydrus.csv={len(ctop_values)}"
        )

    # ------------------------------------------------------------------
    # 2. Lecture du fichier template
    # ------------------------------------------------------------------
    raw = template_path.read_text(encoding="utf-8", errors="replace")
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
    pre_data   = lines[:data_start_idx]      # en-tête HYDRUS + ligne col.
    data_lines = []                           # lignes de données du template
    post_lines = []                           # ligne "end***" et suivantes

    for line in lines[data_start_idx:]:
        stripped = line.strip()
        if stripped.lower().startswith("end") or not stripped:
            post_lines.append(line)
            # toutes les lignes après "end" aussi
        else:
            if post_lines:
                # des lignes de données après un "end" ne devraient pas exister
                post_lines.append(line)
            else:
                data_lines.append(line)

    n_template = len(data_lines)

    # Gabarit de tokens issu de la dernière ligne de données du template
    # (valeurs par défaut pour les colonnes non remplacées : rSoil, rRoot…)
    last_data_tokens = data_lines[-1].strip().split() if data_lines else (
        ["0"] * 13
    )

    # ------------------------------------------------------------------
    # 4. Calcul du nombre de lignes en sortie (= longueur des CSV)
    # ------------------------------------------------------------------
    n_output = n_csv   # le nombre de lignes de sortie suit toujours les CSV

    if n_csv < n_template:
        print(
            f"ℹ️  Réduction : les CSV contiennent {n_csv} lignes, le template "
            f"en avait {n_template}. Le bloc de données sera tronqué à {n_csv} lignes."
        )
    elif n_csv > n_template:
        print(
            f"ℹ️  Extension : les CSV contiennent {n_csv} lignes, le template "
            f"en avait {n_template}. Le bloc de données sera étendu à {n_csv} lignes."
        )

    # ------------------------------------------------------------------
    # 5. Construction du nouveau bloc de données
    # ------------------------------------------------------------------
    new_data_lines: list[str] = []

    for row_idx in range(n_output):
        prec = prec_values[row_idx]
        ctop = ctop_values[row_idx]

        if row_idx < n_template:
            # Ligne existante dans le template → on met à jour Prec et cTop
            tokens = data_lines[row_idx].strip().split()
            tokens[COL_TATM] = str(row_idx + 1)
            tokens[COL_PREC] = _format_value(prec).strip()
            tokens[COL_CTOP] = _format_value(ctop).strip()
            new_line = "".join(f"{tok:>{FIELD_WIDTH}}" for tok in tokens) + " " + eol
        else:
            # Ligne supplémentaire à créer (extension au-delà du template)
            new_line = _build_data_line(
                last_data_tokens, row_idx, prec, ctop, eol
            )

        new_data_lines.append(new_line)

    # ------------------------------------------------------------------
    # 6. Mise à jour de MaxAL dans l'en-tête si nécessaire
    # ------------------------------------------------------------------
    if n_output != n_template:
        # Cherche la ligne qui contient uniquement la valeur numérique de MaxAL
        # (ligne juste après celle qui contient "MaxAL")
        for i, line in enumerate(pre_data):
            if "MaxAL" in line and "number of atmospheric" in line:
                # La valeur est sur la ligne suivante
                max_al_value_idx = i + 1
                if max_al_value_idx < len(pre_data):
                    old_val_line = pre_data[max_al_value_idx]
                    # Remplace le nombre en conservant l'indentation originale
                    new_val_line = old_val_line.rstrip().rstrip("0123456789") + str(n_output) + eol
                    pre_data[max_al_value_idx] = new_val_line
                    print(
                        f"ℹ️  MaxAL mis à jour : {n_template} → {n_output}"
                    )
                break

    # ------------------------------------------------------------------
    # 7. Assemblage et écriture
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    all_lines = pre_data + new_data_lines + post_lines
    output_path.write_text("".join(all_lines), encoding="utf-8")

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
    )

"""
------------------
Utility to update van Genuchten / Mualem soil parameters
(thr, ths, Alfa, n, Ks, l) in a HYDRUS-1D SELECTOR.IN file.

Values are right-aligned to the exact column positions of the original file:
  thr->col 7, ths->col 15, Alfa->col 23, n->col 31, Ks->col 42, l->col 50
"""

import re
from pathlib import Path


# Right-alignment column (1-based end position) for each of the 6 parameters,
# measured directly from the HYDRUS-1D SELECTOR.IN format.
_RIGHT_COLS = [7, 15, 23, 31, 42, 50]
_PARAM_NAMES = ["thr", "ths", "alfa", "n", "ks", "l"]
_LINE_WIDTH = 51          # total line length (without the trailing \r\n)


def _format_value(value: float) -> str:
    """Return a compact string representation of a float (no trailing zeros)."""
    return f"{value:g}"


def _build_values_line(values: list[float]) -> str:
    """
    Build the parameter value line with each value right-aligned to the
    column positions defined in _RIGHT_COLS, matching the original file layout.
    """
    line = [" "] * _LINE_WIDTH
    for col, val in zip(_RIGHT_COLS, values):
        text = _format_value(val)
        start = col - len(text)
        if start < 0:
            raise ValueError(
                f"Value '{text}' is too wide to fit before column {col}."
            )
        for i, ch in enumerate(text):
            line[start + i] = ch
    return "".join(line)


def update_soil_params(
    file_path: str | Path,
    thr:  float | None = None,
    ths:  float | None = None,
    alfa: float | None = None,
    n:    float | None = None,
    ks:   float | None = None,
    l:    float | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """
    Update van Genuchten / Mualem soil parameters in a HYDRUS-1D SELECTOR.IN file.

    Each value is right-aligned to its original column position, preserving
    the exact formatting of the file.

    Parameters
    ----------
    file_path : str or Path
        Path to the SELECTOR.IN file to read.
    thr : float, optional
        Residual water content [cm³/cm³].
    ths : float, optional
        Saturated water content [cm³/cm³].
    alfa : float, optional
        van Genuchten alpha parameter [1/cm].
    n : float, optional
        van Genuchten n shape parameter [-].
    ks : float, optional
        Saturated hydraulic conductivity [cm/day].
    l : float, optional
        Pore connectivity / tortuosity parameter (Mualem) [-].
    output_path : str or Path, optional
        Destination file path. Defaults to overwriting ``file_path`` in-place.

    Returns
    -------
    Path
        The path of the written output file.

    Raises
    ------
    ValueError
        If the parameter header line is not found, or a value is too wide
        for its column.
    """
    file_path = Path(file_path)
    content = file_path.read_text(encoding="utf-8")

    # Detect line ending style (CRLF vs LF) so we preserve it.
    crlf = "\r\n" in content

    # ---------------------------------------------------------------
    # Locate the header + value block.
    # ---------------------------------------------------------------
    header_pattern = re.compile(
        r"([ \t]*thr[ \t]+ths[ \t]+Alfa[ \t]+n[ \t]+Ks[ \t]+l[ \t]*\r?\n)"
        r"([ \t]*\S+[ \t]+\S+[ \t]+\S+[ \t]+\S+[ \t]+\S+[ \t]+\S+[ \t]*\r?\n?)",
        re.IGNORECASE,
    )

    match = header_pattern.search(content)
    if match is None:
        raise ValueError(
            "Could not find the soil-parameter block "
            "(header 'thr  ths  Alfa  n  Ks  l') in the file."
        )

    values_line = match.group(2)

    # Parse existing values as fallback for parameters not supplied.
    tokens = values_line.split()
    if len(tokens) < 6:
        raise ValueError(
            f"Expected 6 values on the soil-parameter line, found: {values_line!r}"
        )

    current = {
        "thr":  float(tokens[0]),
        "ths":  float(tokens[1]),
        "alfa": float(tokens[2]),
        "n":    float(tokens[3]),
        "ks":   float(tokens[4]),
        "l":    float(tokens[5]),
    }

    # Override only the parameters explicitly supplied by the caller.
    if thr  is not None: current["thr"]  = thr
    if ths  is not None: current["ths"]  = ths
    if alfa is not None: current["alfa"] = alfa
    if n    is not None: current["n"]    = n
    if ks   is not None: current["ks"]   = ks
    if l    is not None: current["l"]    = l

    # ---------------------------------------------------------------
    # Rebuild the value line with right-aligned columns.
    # ---------------------------------------------------------------
    new_line_body = _build_values_line([current[p] for p in _PARAM_NAMES])
    line_ending = "\r\n" if crlf else "\n"
    new_values_line = new_line_body + line_ending

    new_content = (
        content[: match.start(2)]
        + new_values_line
        + content[match.end(2):]
    )

    # ---------------------------------------------------------------
    # Write output.
    # ---------------------------------------------------------------
    out_path = Path(output_path) if output_path is not None else file_path
    out_path.write_text(new_content, encoding="utf-8")
    return out_path



"""
hydrus_profile.py
-----------------
Generate a HYDRUS-1D PROFILE.DAT file from two parameters:
  - soil_depth      : total profile depth [cm]  (positive value)
  - vert_resolution : node spacing       [cm]

All values are formatted to exactly match the original HYDRUS column layout
(right-aligned, 3-digit exponents in scientific notation).
"""

import re
import math
from pathlib import Path


# ---------------------------------------------------------------------------
# Low-level formatting helpers
# ---------------------------------------------------------------------------

def _hfmt(value: float) -> str:
    """
    Format a float in HYDRUS scientific notation:
    6 decimal places, sign on mantissa when negative, 3-digit exponent.
    Examples: 0.0 -> '0.000000e+000'   -300.0 -> '-3.000000e+002'
    """
    s = f"{value:.6e}"                                  # Python gives 2-digit exp
    return re.sub(r'e([+-])(\d{2})$', r'e\g<1>0\2', s) # pad to 3 digits


def _place(line: list[str], text: str, end_col: int) -> None:
    """Right-align *text* so its last character lands at *end_col* (1-based)."""
    start = end_col - len(text)
    for i, ch in enumerate(text):
        line[start + i] = ch


# ---------------------------------------------------------------------------
# Line builders  (all column positions measured from the reference file)
# ---------------------------------------------------------------------------

def _boundary_line(idx: int, depth_cm: float) -> str:
    """
    Lines 3 & 4  – boundary node table (50 chars).
    Columns (1-based end): idx→5, depth→20, 1.0→35, 1.0→50.
    Surface node (depth=0) is written as positive zero (no minus sign).
    """
    line = [' '] * 50
    depth_val = 0.0 if depth_cm == 0.0 else -depth_cm   # positive zero at surface
    _place(line, str(idx),          5)
    _place(line, _hfmt(depth_val), 20)
    _place(line, _hfmt(1.0),       35)
    _place(line, _hfmt(1.0),       50)
    return ''.join(line)


def _column_header_line(n_nodes: int) -> str:
    """
    Line 5 – column header (144 chars).
    First token is the total number of nodes.
    """
    line = [' '] * 144
    _place(line, str(n_nodes), 5)
    _place(line, '1',         10)
    _place(line, '1',         15)
    _place(line, '1',         20)
    _place(line, 'x',         22)
    _place(line, 'h',         32)
    _place(line, 'Mat',       41)
    _place(line, 'Lay',       46)
    _place(line, 'Beta',      56)
    _place(line, 'Axz',       70)
    _place(line, 'Bxz',       85)
    _place(line, 'Dxz',      100)
    _place(line, 'Temp',     114)
    _place(line, 'Conc',     128)
    _place(line, 'SConc',    144)
    return ''.join(line)


def _node_line(idx: int, depth_cm: float) -> str:
    """
    One profile node line (135 chars).
    depth_cm is the distance from surface; stored as negative value.
    Surface node uses -0.0 (negative zero), matching the original file.

    Column end positions (1-based):
      idx→5, x→20, h→35, Mat→40, Lay→45,
      Beta→60, Axz→75, Bxz→90, Dxz→105, Temp→120, Conc→135
    """
    line = [' '] * 135
    x = math.copysign(depth_cm, -1.0)    # always negative, including -0.0
    _place(line, str(idx),       5)
    _place(line, _hfmt(x),      20)
    _place(line, _hfmt(0.1),    35)      # initial pressure head h
    _place(line, '1',           40)      # material index
    _place(line, '1',           45)      # layer index
    _place(line, _hfmt(0.0),    60)      # Beta
    _place(line, _hfmt(1.0),    75)      # Axz
    _place(line, _hfmt(1.0),    90)      # Bxz
    _place(line, _hfmt(1.0),   105)      # Dxz
    _place(line, _hfmt(20.0),  120)      # Temp
    _place(line, _hfmt(0.0),   135)      # Conc
    return ''.join(line)


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def generate_profile(
    soil_depth: float,
    vert_resolution: float,
    input_filename: str | Path  = 'PROFILE.DAT',
    output_filename: str | Path = 'PROFILE.DAT',
) -> Path:
    """
    Generate a HYDRUS-1D PROFILE.DAT soil-profile discretisation file.

    Parameters
    ----------
    soil_depth : float
        Total depth of the soil profile [cm].  Must be a positive value.
        Example: 300  →  profile from 0 to -300 cm.
    vert_resolution : float
        Vertical spacing between nodes [cm].
        soil_depth must be exactly divisible by vert_resolution.
        Example: 6  →  nodes at 0, -6, -12, … cm.
    input_filename : str or Path
        Name of the template / source file (kept for symmetry with
        hydrus_selector.py; not read by this function).
        Appears in the function signature as requested.
    output_filename : str or Path
        Path of the PROFILE.DAT file to create.  Will be overwritten
        if it already exists.

    Returns
    -------
    Path
        The path of the written file.

    Raises
    ------
    ValueError
        If soil_depth is not exactly divisible by vert_resolution.
    """
    if soil_depth <= 0:
        raise ValueError(f"soil_depth must be positive, got {soil_depth}")
    if vert_resolution <= 0:
        raise ValueError(f"vert_resolution must be positive, got {vert_resolution}")

    # Check divisibility with a small floating-point tolerance
    n_intervals = soil_depth / vert_resolution
    if abs(n_intervals - round(n_intervals)) > 1e-9:
        raise ValueError(
            f"soil_depth ({soil_depth}) is not exactly divisible "
            f"by vert_resolution ({vert_resolution})."
        )
    n_intervals = round(n_intervals)
    n_nodes = n_intervals + 1   # e.g. 300/6=50 intervals → 51 nodes

    # Build file content line by line
    lines: list[str] = []

    # Line 1 – version tag
    lines.append('Pcp_File_Version=4')

    # Line 2 – number of boundary nodes (always 2: top and bottom)
    lines.append('    2')

    # Lines 3–4 – boundary node table
    lines.append(_boundary_line(1, 0.0))
    lines.append(_boundary_line(2, soil_depth))

    # Line 5 – column header
    lines.append(_column_header_line(n_nodes))

    # Lines 6 … 6+n_nodes-1 – one line per node
    for i in range(n_nodes):
        depth = i * vert_resolution
        lines.append(_node_line(i + 1, depth))

    # Final line
    lines.append('0')

    # Join with '\n' and add a trailing newline to match the reference file
    content = '\n'.join(lines) + '\n'

    out_path = Path(output_filename)
    out_path.write_text(content, encoding='utf-8')
    return out_path
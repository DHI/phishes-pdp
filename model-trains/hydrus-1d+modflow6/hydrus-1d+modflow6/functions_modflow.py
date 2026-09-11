# import
import os
import importlib
import numpy as np
import platform
from contextlib import contextmanager
from time import time
import re
import pandas as pd
from pathlib import Path

@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


class ModFlowSimulation:
    def __init__(self,
                 name,
                 folder,
                 path_mf6dll,
                 ndays,
                 timestep,
                 specific_storage,
                 specific_yield,
                 nlay,
                 nrow,
                 ncol,
                 rowsize,
                 colsize,
                 top,
                 bottom,
                 basin,
                 head,
                 permeability,
                 north_chd,
                 slope,
                 width,
                 verbose=True):

        flopy = importlib.import_module("flopy", package=None)

        self.name = name.upper()  # MODFLOW requires the name to be uppercase
        self.folder = folder
        self.dir_mf6dll = path_mf6dll
        self.nrow = nrow
        self.ncol = ncol
        self.rowsize = rowsize
        self.colsize = colsize
        self.basin = basin
        self.n_active_cells = self.basin.sum()
        self.working_directory = os.path.join('.', '.')
        if not os.path.exists(self.working_directory):
            os.makedirs(self.working_directory)
        self.verbose = verbose

        self.charge_amont_imposee = north_chd
        self.slope = slope
        self.domain_width = width

        print("Creating MODFLOW model")
        sim = flopy.mf6.MFSimulation(sim_name=self.name, version='mf6',
                                     exe_name=os.path.join('modflow', 'mf6'), sim_ws=self.working_directory,
                                     memory_print_option='all')
        # creating tdis package
        tdis = flopy.mf6.ModflowTdis(sim, nper=ndays, perioddata=[(1.0, 1, 1)] * ndays, time_units="DAYS")
        # defining solver settings
        ims = flopy.mf6.ModflowIms(sim, print_option=None, complexity='COMPLEX', #linear_acceleration='BICGSTAB',
                                   #rcloserecord=[0.1 * 24 * 3600 * timestep * self.n_active_cells, 'L2NORM_RCLOSE'],
                                   under_relaxation='SIMPLE', under_relaxation_gamma=0.2, inner_maximum=200, outer_maximum=20,
                                   outer_dvclose=0.001, inner_dvclose=0.0001)
        # creating gwf model
        gwf = flopy.mf6.ModflowGwf(sim, modelname=self.name, newtonoptions='under_relaxation', print_input=False,
                                   print_flows=False)
        # creating discretization package
        dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=self.nrow, ncol=self.ncol,
                                      delr=self.rowsize, delc=self.colsize, top=top,
                                      botm=bottom, idomain=self.basin, nogrb=True)
        # defining initial condition
        ic = flopy.mf6.ModflowGwfic(gwf, strt=head)
        # defining node property flow
        npf = flopy.mf6.ModflowGwfnpf(gwf, save_flows=True, icelltype=1, k=permeability * timestep)
        # defining aquifer storage parameters
        sto = flopy.mf6.ModflowGwfsto(gwf, save_flows=False, iconvert=1,
                                      ss=specific_storage, sy=specific_yield,  # specific yield
                                      steady_state=False, transient=True)
        # defining output control
        oc = flopy.mf6.ModflowGwfoc(gwf,
                                    head_filerecord=f'{self.name}.hds',
                                    budget_filerecord=f'{self.name}.bud',
                                    saverecord=[('HEAD', "LAST")])#, ("BUDGET", "ALL")])

        # Imposed head on the South and North boundaries of the model
        chd_data = []
        for k in range(nlay):
            for ic in range(self.ncol):  # we add an imposed head for each column in the first and last row
                chd_data.append(((0, 0, ic), self.charge_amont_imposee))  # charge imposée amont
                chd_data.append(((0, self.nrow - 1, ic), self.charge_amont_imposee - self.slope * self.rowsize * self.nrow))  # charge imposée aval
        chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data={0: chd_data}, maxbound=len(chd_data), pname="CHD")

        # preparing recharge input, recharge should be > 0 and already given in m/timestep per ModFlow cell
        recharge = np.zeros((self.basin[0].sum(), 4), dtype=np.int32)   # only set recharge in the first layer (=>[0]) where the cell is active
        recharge = np.zeros((self.basin[0].sum(), 5), dtype=np.int32)  # the 5th column is for recharge concentration
        recharge_locations = np.where(self.basin[0] == 1)
        recharge[:, 0] = 0  # layer
        recharge[:, 1] = recharge_locations[0]  # row
        recharge[:, 2] = recharge_locations[1]  # col
        # recharge[:, 4] = 10  # concentration in mg/L
        # We add a source of pollution at y = -200 m and x = 400 m, soit row = 20, et col = 60
        # recharge[100*19+59][4]=10  # concentration in mg/L
        recharge = recharge.tolist()
        # adding recharge package
        recharge = flopy.mf6.ModflowGwfrch(gwf, fixed_cell=False,
                                           print_input=False, print_flows=False,
                                           save_flows=False, boundnames=None,
                                           maxbound=self.basin[0].sum(), stress_period_data=recharge,
                                           pname="rch",
                                           auxiliary=["CONCENTRATION"])


        ## ADDING THE SOLUTE TRANSPORT PART ##

        transport_model_name = self.name + "_T"

        # Instantiating MODFLOW 6 groundwater transport package
        self.gwt = flopy.mf6.MFModel(sim, model_type="gwt6",
                                modelname=transport_model_name,
                                model_nam_file=f"{transport_model_name}.nam")

        # Create iterative model solution and register the gwt model with it
        imsgwt = flopy.mf6.ModflowIms(sim,
                                      print_option="SUMMARY",
                                      outer_dvclose=1e-4,
                                      outer_maximum=100,
                                      under_relaxation="NONE",
                                      inner_maximum=300,
                                      inner_dvclose=1e-4,
                                      rcloserecord=1e-4,
                                      linear_acceleration="BICGSTAB",
                                      scaling_method="NONE",
                                      reordering_method="NONE",
                                      relaxation_factor=1.0,
                                      filename=f"{transport_model_name}.ims")

        sim.register_ims_package(imsgwt, [self.gwt.name])

        # Instantiating MODFLOW 6 transport discretization package
        dis_GWT = flopy.mf6.ModflowGwtdis(self.gwt,
                                          nlay=nlay,
                                          nrow=self.nrow,
                                          ncol=self.ncol,
                                          delr=self.rowsize,
                                          delc=self.colsize,
                                          top=top,
                                          botm=bottom,
                                          idomain=self.basin,
                                          pname="DIS_T",
                                          length_units="METERS",
                                          filename=f"{transport_model_name}.dis")

        # Instantiating MODFLOW 6 transport initial concentrations
        init_conc = self.basin * 0.0
        flopy.mf6.ModflowGwtic(self.gwt, strt=init_conc, filename=f"{transport_model_name}.ic")

        # Instantiating MODFLOW 6 transport advection package
        flopy.mf6.ModflowGwtadv(self.gwt, scheme="TVD", filename=f"{transport_model_name}.adv")

        # Instantiating MODFLOW 6 transport mass storage package (formerly "reaction" package in MT3DMS)
        flopy.mf6.ModflowGwtmst(self.gwt,
                                porosity=specific_yield,
                                first_order_decay=None,  # True,
                                decay=None,  # first_decay_coef,
                                sorption=None,
                                decay_sorbed=None,
                                bulk_density=None,
                                distcoef=None,
                                filename=f"{transport_model_name}.mst")
        # see https://flopy.readthedocs.io/en/3.3.2/source/flopy.mf6.modflow.mfgwtmst.html
        # and https://pubs.usgs.gov/tm/06/a61/tm6a61.pdf

        # Instantiating MODFLOW 6 transport output control package
        flopy.mf6.ModflowGwtoc(self.gwt,
                               concentration_filerecord=f"{transport_model_name}.ucn",
                               saverecord=[("CONCENTRATION", "LAST")])

        # Instantiating MODFLOW 6 transport source-sink mixing package
        # sourcerecarray = [("CHD", "AUX", "CONCENTRATION"), ("RCH", "AUX", "CONCENTRATION")]
        # flopy.mf6.ModflowGwtssm(self.gwt,  # sources=sourcerecarray,
        #                         pname="SSM", filename=f"{model_transport_name}.ssm")
        flopy.mf6.ModflowGwtssm(self.gwt,
                                sources=[("rch", "AUX", "CONCENTRATION")], # ("CHD", "AUX", "CONCENTRATION")],
                                pname="SSM", filename=f"{transport_model_name}.ssm")
            # Use "AUXMIXED" instead of "AUX" if RCH can also act as a sink: sources=[("rch", "AUXMIXED", "CONCENTRATION")]

        # Coupling flow model and solute transport model
        flopy.mf6.ModflowGwfgwt(sim, exgtype="GWF6-GWT6", exgmnamea=self.name, exgmnameb=transport_model_name)

        # writing MODFLOW packages
        sim.write_simulation(silent=True)
        # success, buff = sim.run_simulation()

        self.load_bmi()

    def bmi_return(self, success, model_ws):
        """
        parse libmf6.so and libmf6.dll stdout file
        """
        fpth = os.path.join(model_ws, 'mfsim.stdout')
        return success, open(fpth).readlines()

    def load_bmi(self):
        """Load the Basic Model Interface"""
        success = False

        if platform.system() == 'Windows':
            library_name = 'libmf6.dll'
        elif platform.system() == 'Linux':
            library_name = 'libmf6.so'
        else:
            raise ValueError(f'Platform {platform.system()} not recognized.')

        # modflow requires the real path (no symlinks etc.)
        library_path = os.path.realpath(os.path.join(self.dir_mf6dll, library_name))
        try:
            xmipy = importlib.import_module("xmipy")
            self.mf6 = xmipy.XmiWrapper(library_path)

        except Exception as e:
            print("Failed to load " + library_path)
            print("with message: " + str(e))
            return self.bmi_return(success, self.working_directory)

        with cd(self.working_directory):

            # modflow requires the real path (no symlinks etc.)
            config_file = os.path.realpath('mfsim.nam')
            # print(config_file)
            if not os.path.exists(config_file):
                raise FileNotFoundError(
                    f"Config file {config_file} not found on disk. Did you create the model first (load_from_disk = False)?")

            # initialize the model
            try:
                self.mf6.initialize(config_file)
            except:
                return self.bmi_return(success, self.working_directory)

            if self.verbose:
                print("MODFLOW model initialized")

        self.end_time = self.mf6.get_end_time()

        # recharge_tag = self.mf6.get_var_address("BOUND", self.name, "RCH_0")
        # there seems to be a bug in xmipy where the size of the pointer to RCHA is
        # is the size of the entire modflow area, including basined cells. Only the first
        # part of the array is actually used, when a part of the area is basined. Since
        # numpy returns a view of the array when the array[]-syntax is used, we can simply
        # use the view of the first part of the array up to the number of active
        # (non-basined) cells  => Luca pas compris
        # self.recharge = self.mf6.get_value_ptr(recharge_tag)[:, 0]

        # new part from Luca to get the input concentration within the recharge
        recharge_tag = self.mf6.get_var_address("BOUND", self.name, "RCH")
        conc_rech_tag = self.mf6.get_var_address("AUXVAR", self.name, "RCH")
        self.recharge = self.mf6.get_value_ptr(recharge_tag)
        # print("self.recharge", np.shape(self.recharge))
        self.conc_rech = self.mf6.get_value_ptr(conc_rech_tag)
        # print("self.conc_rech", np.shape(self.conc_rech))

        # print(self.mf6.get_output_var_names())

        head_tag = self.mf6.get_var_address("X", self.name)
        self.head = self.mf6.get_value_ptr(head_tag)

        # drainage_tag = self.mf6.get_var_address("BOUND", self.name, "DRN_0")
        # self.drainage = self.mf6.get_value_ptr(drainage_tag)[:, 0]

        mxit_tag = self.mf6.get_var_address("MXITER", "SLN_1")
        self.max_iter = self.mf6.get_value_ptr(mxit_tag)[0]

        self.prepare_time_step()

    def compress(self, a):
        return np.compress(self.basin, a)

    def decompress(self, a):
        o = np.full(self.basin.shape, np.nan, dtype=a.dtype)
        o[self.basin] = a
        return o

    def prepare_time_step(self):
        dt = self.mf6.get_time_step()
        self.mf6.prepare_time_step(dt)

    def set_recharge(self, recharge):
        """Set recharge, value in m/day"""
        # modif luca to include concentration
        # self.recharge[:] = recharge[self.basin[0] == True]
        self.recharge[:, 0] = recharge[self.basin[0] == True]

    def set_conc_recharge(self, conc_rech):
        """Set recharge, value in m/day"""
        # modif luca to include concentration
        # self.recharge[:] = recharge[self.basin[0] == True]
        self.conc_rech[:, 0] = conc_rech[self.basin[0] == True]

    def step(self, plot=False):
        if self.mf6.get_current_time() > self.end_time:
            raise StopIteration("MODFLOW used all iteration steps. Consider increasing `ndays`")

        t0 = time()
        # loop over subcomponents
        n_solutions = self.mf6.get_subcomponent_count()
        for solution_id in range(1, n_solutions + 1):

            # convergence loop
            kiter = 0
            self.mf6.prepare_solve(solution_id)
            while kiter < self.max_iter:
                has_converged = self.mf6.solve(solution_id)
                kiter += 1

                if has_converged:
                    break

            self.mf6.finalize_solve(solution_id)

        self.mf6.finalize_time_step()

        if self.verbose:
            print(f'MODFLOW timestep {int(self.mf6.get_current_time())} converged in {round(time() - t0, 2)} seconds')

        # If next step exists, prepare timestep. Otherwise the data set through the bmi
        # will be overwritten when preparing the next timestep.
        if self.mf6.get_current_time() < self.end_time:
            self.prepare_time_step()

    def finalize(self):
        self.mf6.finalize()


def parse_volume_budgets(lst_file):
    records = []
    row = None
    current_section = None

    term_pattern = re.compile(r"^\s+([\w][\w\-]*)\s*=\s*([\d\.\-Ee+]+)")

    with open(lst_file, "r") as f:
        for line in f:

            # --- Start of a new budget block ---
            if "VOLUME BUDGET FOR ENTIRE MODEL" in line:
                if row:
                    records.append(row)
                row = {}
                current_section = None
                m = re.search(r"TIME STEP\s+(\d+),\s+STRESS PERIOD\s+(\d+)", line)
                if m:
                    row["stress_period"] = int(m.group(2))
                    row["time_step"]     = int(m.group(1))
                continue

            if row is None:
                continue

            stripped = line.strip()

            # --- Skip empty or decorative lines (---, ===, etc.) ---
            if not stripped or re.match(r"^[-= ]+$", stripped):
                continue

            # --- Detect IN / OUT section headers ---
            # Use "in" because the line is "IN:       ...        IN:"
            if re.match(r"\s+IN:\s*", line):
                current_section = "IN"
                continue
            if re.match(r"\s+OUT:\s*", line):
                current_section = "OUT"
                continue

            # --- Totals and discrepancy ---
            if "TOTAL IN" in line:
                current_section = None
                m = re.search(r"TOTAL IN\s*=\s*([\d\.\-Ee+]+)", line)
                if m:
                    row["TOTAL_IN"] = float(m.group(1))
                continue

            if "TOTAL OUT" in line:
                m = re.search(r"TOTAL OUT\s*=\s*([\d\.\-Ee+]+)", line)
                if m:
                    row["TOTAL_OUT"] = float(m.group(1))
                continue

            if "IN - OUT" in line:
                m = re.search(r"IN - OUT\s*=\s*([\d\.\-Ee+]+)", line)
                if m:
                    row["IN_OUT"] = float(m.group(1))
                continue

            if "PERCENT DISCREPANCY" in line:
                m = re.search(r"PERCENT DISCREPANCY\s*=\s*([\d\.\-Ee+]+)", line)
                if m:
                    row["PERCENT_DISCREPANCY"] = float(m.group(1))
                continue

            # --- Parse package term lines ---
            if current_section:
                m = term_pattern.match(line)
                if m:
                    term  = m.group(1).strip()
                    value = float(m.group(2))
                    col   = f"{term}_{current_section}"
                    if col in row:
                        row[col] += value
                    else:
                        row[col] = value

    # Last block
    if row:
        records.append(row)

    df = pd.DataFrame(records).fillna(0.0)

    # Reorder columns
    meta_cols  = ["stress_period", "time_step"]
    total_cols = ["TOTAL_IN", "TOTAL_OUT", "IN_OUT", "PERCENT_DISCREPANCY"]
    pkg_cols   = [c for c in df.columns if c not in meta_cols + total_cols]
    in_cols    = sorted([c for c in pkg_cols if c.endswith("_IN")])
    out_cols   = sorted([c for c in pkg_cols if c.endswith("_OUT")])
    final_cols = meta_cols + in_cols + ["TOTAL_IN"] + out_cols + ["TOTAL_OUT", "IN_OUT", "PERCENT_DISCREPANCY"]
    df = df[[c for c in final_cols if c in df.columns]]

    return df

def read_modflow_mass_budget(lst_path):
    """
    Parse a MODFLOW .lst file and return the non-cumulative (period) mass
    budget for each stress period / timestep as a tidy pandas DataFrame.

    Parameters
    ----------
    lst_path : str or Path
        Path to the MODFLOW listing (.lst) file.

    Returns
    -------
    pd.DataFrame
        Columns:
            stress_period  – int
            timestep       – int
            term           – str   (e.g. "STORAGE-AQUEOUS", "RCH", "CHD")
            direction      – str   ("IN", "OUT", or "N/A" for PERCENT DISCREPANCY)
            rate           – float (non-cumulative value, model units / time)

    Notes
    -----
    MODFLOW 6 omits the space between "STRESS PERIOD" and the period number
    once the number reaches 1000 (fixed-width Fortran output field overflows
    into the preceding space).  The header regex therefore uses ``\\s*``
    (zero-or-more spaces) instead of ``\\s+`` so that stress periods up to
    99999 are captured correctly.
    """
    lst_path = Path(lst_path)

    # FIX: \s* (zero-or-more spaces) instead of \s+ so that stress periods
    # >= 1000 are matched even when MODFLOW drops the separating space due to
    # the fixed-width Fortran format field overflowing (e.g. "STRESS PERIOD1458").
    re_header = re.compile(
        r"BUDGET FOR ENTIRE MODEL AT END OF TIME STEP\s+(\d+),\s*STRESS PERIOD\s*(\d+)",
        re.IGNORECASE,
    )
    re_block_start = re.compile(r"CUMULATIVE.*RATES FOR THIS TIME STEP", re.IGNORECASE)
    re_block_end   = re.compile(r"TIME SUMMARY AT END OF TIME STEP",     re.IGNORECASE)
    re_direction   = re.compile(r"^\s*(IN|OUT)\s*:",                     re.IGNORECASE)
    re_in_out_line = re.compile(r"IN\s*-\s*OUT",                         re.IGNORECASE)

    # Matches one "TERM_NAME = numeric_value" token anywhere on a line.
    # We collect ALL such tokens; the rightmost value for a given term name
    # is the non-cumulative (rates) column.
    re_kv      = re.compile(r"([\w][\w\s\-]*?)\s*=\s*([\-\d][\d\.Ee+\-]*)")
    re_total   = re.compile(r"TOTAL\s+(IN|OUT)",    re.IGNORECASE)
    re_percent = re.compile(r"PERCENT\s+DISCREPANCY\s*=\s*([\-\d][\d\.Ee+\-]*)", re.IGNORECASE)

    records: list[dict] = []

    with lst_path.open("r", errors="replace") as fh:
        lines = fh.readlines()

    i, n = 0, len(lines)

    while i < n:
        line = lines[i]

        m_hdr = re_header.search(line)
        if not m_hdr:
            i += 1
            continue

        timestep      = int(m_hdr.group(1))
        stress_period = int(m_hdr.group(2))
        i += 1

        # Advance to the side-by-side block header
        in_block = False
        while i < n:
            if re_block_start.search(lines[i]):
                in_block = True
                i += 1
                break
            if re_header.search(lines[i]):
                break
            i += 1

        if not in_block:
            continue

        direction = None  # "IN" or "OUT"

        while i < n:
            l = lines[i]

            # End of block
            if re_block_end.search(l) or re_header.search(l):
                break

            stripped = l.strip()

            # Blank / separator lines
            if not stripped or stripped.startswith("-"):
                i += 1
                continue

            # IN: / OUT: context switch
            m_dir = re_direction.match(l)
            if m_dir:
                direction = m_dir.group(1).upper()
                i += 1
                continue

            # Skip "IN - OUT" lines
            if re_in_out_line.search(l):
                i += 1
                continue

            # PERCENT DISCREPANCY — take the last (rightmost) value
            pct_all = re_percent.findall(l)
            if pct_all:
                records.append({
                    "stress_period": stress_period,
                    "timestep":      timestep,
                    "term":          "PERCENT DISCREPANCY",
                    "direction":     "N/A",
                    "rate":          float(pct_all[-1]),
                })
                i += 1
                continue

            # Lines must contain "=" to carry data
            if "=" not in l:
                i += 1
                continue

            # -- parse all key=value tokens on the line ------------------
            # Separate TOTAL IN/OUT tokens from regular term tokens so we
            # can handle them cleanly without double-counting.

            # Find TOTAL IN / TOTAL OUT occurrences: collect their values,
            # keep only the last (= rates column).
            total_seen: dict[str, list[float]] = {}
            for m in re.finditer(
                r"(TOTAL\s+(?:IN|OUT))\s*=\s*([\-\d][\d\.Ee+\-]*)", l, re.IGNORECASE
            ):
                key = re.sub(r"\s+", " ", m.group(1).strip().upper())
                total_seen.setdefault(key, []).append(float(m.group(2)))

            for term, vals in total_seen.items():
                dir_ = "IN" if term.endswith("IN") else "OUT"
                records.append({
                    "stress_period": stress_period,
                    "timestep":      timestep,
                    "term":          term,
                    "direction":     dir_,
                    "rate":          vals[-1],   # rightmost = rates column
                })

            if total_seen:
                i += 1
                continue

            # Regular term lines — collect all kv pairs, keep last value per name
            kv_pairs = re_kv.findall(l)
            if not kv_pairs:
                i += 1
                continue

            # Build dict: last occurrence wins (= rightmost = rates column)
            term_vals: dict[str, float] = {}
            for raw_name, raw_val in kv_pairs:
                name = raw_name.strip()
                # Skip anything that looks like a TOTAL token (handled above)
                if re_total.search(name):
                    continue
                try :
                    term_vals[name] = float(raw_val)
                except:  # sometimes it does not work (for example for values written like "2.1429-100")
                    term_vals[name] = 0

            for term, val in term_vals.items():
                if direction is None:
                    continue
                records.append({
                    "stress_period": stress_period,
                    "timestep":      timestep,
                    "term":          term,
                    "direction":     direction,
                    "rate":          val,
                })

            i += 1

    if not records:
        raise ValueError(
            "No mass budget blocks found. "
            "Verify this is a MODFLOW listing file with budget output enabled."
        )

    df = (
        pd.DataFrame(records, columns=["stress_period", "timestep", "term", "direction", "rate"])
        .drop_duplicates()
        .reset_index(drop=True)
    )
    return df


def pivot_budget(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot the tidy DataFrame from read_modflow_mass_budget() to wide format.
    Each (term, direction) pair becomes one column: e.g. STORAGE-AQUEOUS_IN.

    Returns
    -------
    pd.DataFrame
        One row per (stress_period, timestep).
    """
    df = df.copy()
    df["col"] = (
        df["term"].str.strip().str.replace(r"\s+", "_", regex=True)
        + "_"
        + df["direction"].str.strip()
    )
    wide = df.pivot_table(
        index=["stress_period", "timestep"],
        columns="col",
        values="rate",
        aggfunc="last",
    ).reset_index()
    wide.columns.name = None
    return wide
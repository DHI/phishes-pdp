from pathlib import Path

import pandas as pd

DAISY_HEADER_PREFIX = "year\tmonth\tmday\thour\t"
DAISY_INTERVAL_TOTAL_COLUMNS = frozenset(
    {
        "Precipitation",
        "Irrigation",
        "Potential evapotranspiration",
        "Actual evapotranspiration",
        "Matrix percolation",
        "Biopore percolation",
        "Matrix drain flow",
        "Biopore drain flow",
        "Runoff",
    }
)


def _find_daisy_header_line(outputFile):
    with open(outputFile, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file):
            if line.startswith(DAISY_HEADER_PREFIX):
                return line_number

    raise ValueError(f"Could not find a DAISY table header in {outputFile}")


def _read_daisy_table(outputFile):
    header_line = _find_daisy_header_line(outputFile)
    columns = pd.read_csv(
        outputFile,
        sep="\t",
        skiprows=header_line,
        nrows=0,
        encoding="utf-8",
    ).columns.tolist()

    return pd.read_csv(
        outputFile,
        sep="\t",
        skiprows=header_line + 2,
        names=columns,
        encoding="utf-8",
    )


def _ensure_datetime_index(df):
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("DAISY result DataFrame must use a DatetimeIndex")


def readDaisyOutput(outputFile):
    df = _read_daisy_table(outputFile)

    for column_name in df.columns:
        df[column_name] = pd.to_numeric(df[column_name], errors="coerce")

    df = df.dropna(subset=["year", "month", "mday", "hour"]).copy()
    df.rename(columns={"mday": "day"}, inplace=True)

    df[["year", "month", "day", "hour"]] = df[["year", "month", "day", "hour"]].astype(
        int
    )
    df["datetime"] = pd.to_datetime(df[["year", "month", "day", "hour"]])
    df.set_index("datetime", inplace=True)
    df.sort_index(inplace=True)

    return df


def requireDaisyColumn(df, colName):
    if colName not in df.columns:
        available_columns = ", ".join(map(str, df.columns))
        raise KeyError(
            f"DAISY output column '{colName}' not found. "
            f"Available columns: {available_columns}"
        )

    return colName


def addIntervalMetadata(df):
    _ensure_datetime_index(df)

    interval_df = df.copy()
    interval_end = interval_df.index.to_series(index=interval_df.index)
    interval_df["interval_end_time"] = interval_end
    interval_df["interval_start_time"] = interval_end.shift(1)
    interval_df["interval_seconds"] = (
        interval_df["interval_end_time"] - interval_df["interval_start_time"]
    ).dt.total_seconds()

    return interval_df


def findIntervalRowInDaisyResult(df, target_time):
    """Return the first DAISY interval row whose end time is at or after target_time.

    This helper assumes the DAISY timestamps denote interval end times, which matches
    the current Phase 0 working assumption for interval-total water-balance columns.
    """

    interval_df = addIntervalMetadata(df)
    target_time = pd.to_datetime(target_time)
    row_position = interval_df.index.searchsorted(target_time, side="left")

    if row_position >= len(interval_df):
        raise KeyError(f"No DAISY interval found at or after {target_time}")

    interval_row = interval_df.iloc[row_position]
    if pd.isna(interval_row["interval_seconds"]):
        raise KeyError(
            "No complete DAISY interval is available for the requested target time"
        )

    return interval_row


def findIntervalValueInDaisyResult(df, target_time, colName):
    requireDaisyColumn(df, colName)
    return findIntervalRowInDaisyResult(df, target_time)[colName]


def findIntervalRateInDaisyResult(df, target_time, colName):
    requireDaisyColumn(df, colName)
    interval_row = findIntervalRowInDaisyResult(df, target_time)
    return (interval_row[colName] / 1000.0) / interval_row["interval_seconds"]


def findValueInDaisyResult(df, target_time, colName):
    """Legacy linear interpolation helper for continuous or state-like values.

    Do not use this helper for interval-total water-balance columns such as runoff,
    matrix percolation, or drain flow.
    """

    requireDaisyColumn(df, colName)
    df = df.reindex(df.index.union([target_time])).sort_index()
    df[colName] = df[colName].interpolate(method="time")

    return df.loc[target_time, colName]


if __name__ == "__main__":
    sample_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "Cernici_060126_Test02_2"
        / "Monthly_FWater.csv"
    )
    daisyResult = readDaisyOutput(sample_path)
    findIntervalValueInDaisyResult(
        daisyResult,
        pd.to_datetime("2024-09-01 00:00"),
        "Matrix percolation",
    )

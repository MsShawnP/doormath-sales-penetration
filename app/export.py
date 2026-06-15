"""CSV export for exception list data."""

import io

import pandas as pd


def export_csv(exception_rows):
    """Export exception rows as CSV string for download.

    Args:
        exception_rows: list of dicts or DataFrame with exception columns.

    Returns:
        CSV string content.
    """
    if isinstance(exception_rows, list):
        df = pd.DataFrame(exception_rows)
    else:
        df = exception_rows

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()

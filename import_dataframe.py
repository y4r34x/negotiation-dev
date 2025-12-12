import pandas as pd

def import_dataframe(filepath: str) -> pd.DataFrame:

  try:
    df = pd.read_csv(filepath, sep='\t')
    return df

  except FileNotFoundError:
    print(f"Error: file not found at {filepath}")
    return pd.DataFrame()
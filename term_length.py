import pandas as pd
from pathlib import Path
# from typing import Optional
# import re
# import json

# data source: CUAD v1. Here's what I did:
#   1. downloaded the ZIP file
#   2. opened the CSV
#   3. cleaned manually (normalized date formatting, corrected typos, etc.)
#   4. save as a TSV and import to the IDE

EXPECTED_COLUMNS = [
  "URL",
  "Document Name",
  "Parties",
  "Agreement Date",
  "Effective Date",
  "Expiration Date",
  "Renewal Term (Days)",
  "Notice Period To Terminate Renewal",
  "Termination For Convenience",
  "Change Of Control",
  "Anti-Assignment",
  "Revenue/Profit Sharing",
  "Ip Ownership Assignment",
  "Joint Ip Ownership",
  "Non-Transferable License",
  "Source Code Escrow",
  "Post-Termination Services",
  "Audit Rights",
  "Uncapped Liability",
  "Cap On Liability",
  "Liquidated Damages",
  "Warranty Duration"
]


def load_data(file_path: str | Path = 'tsv_path') -> pd.DataFrame:
  '''
  In: raw TSV file 
  Out: dataframe
  '''

  # import the tsv as a dataframe

  df = get_lengths(df)

  return df


def get_lengths(df: pd.Dataframe) -> pd.DataFrame:
  '''
  In: dataframe with 'effective_date' and 'expiration_date' cols
  Out: same dataframe with an additional 'term_length' col
  '''
  df = df

  return df
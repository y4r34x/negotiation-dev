import pandas as pd
import numpy as np

def get_average(df: pd.DataFrame) -> float:
  """
  Performs a simple scoring calculation on the dataframe.

  Args:
    df (pd.DataFrame): The DataFrame to be processed.

  Returns:
    float: the calculated score 
  """

  if all(col in df.columns for col in ['id', 'equity', 'vest', 'cliff']):
    #score = e/vc^2
    avg_score = 10**9 * ( df['equity'] / (np.square(df['cliff']) * df['vest'])).mean()
    return avg_score

  else:
    print("Warning: you've got a missing column in the input data!")
    return 0.0
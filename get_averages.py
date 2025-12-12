import pandas as pd
import numpy as np

def get_averages(df: pd.DataFrame) -> np.array:
  """
  Performs a simple scoring calculation on the dataframe.

  Args:
    df (pd.DataFrame): The DataFrame to be processed.

  Returns:
    float: the calculated score 
  """
  avgs = np.zeros(2)

  if all(col in df.columns for col in ['id', 'equity', 'vest', 'cliff']):
    #score = e/vc^2
    avg_score = (df['equity'] / (np.square(df['cliff']) * df['vest'])).mean()
    avg_ratio = (df['cliff'] / df['vest']).mean()

    avgs[0] = avg_score
    avgs[1] = avg_ratio

    return avgs

  else:
    print("Warning: you've got a missing column in the input data!")
    return np.zeros(2)
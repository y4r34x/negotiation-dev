import import_dataframe
import get_averages
import best_offer
from scipy.optimize import fsolve


def main():

  filepath = 'data.tsv'

  # Step 1: Import the Data
  df = import_dataframe.import_dataframe(filepath)

  if df is not None:
    print(df.head(), '\n')
    print(f"Total rows: {len(df)}",'\n', "*" * 40, '\n')
  else:
    print("Seriously? You fucked up loading the data? I'm jk loading the data is a pain")
    return

  # Step 2: Compute the averages
  avgs = get_averages.get_averages(df)

  if avgs is not None:
    print(f"The average score is {avgs[0]} and ratio is {avgs[1]}", '\n', "*" * 40, '\n')
  else:
    print("Bruh you didn't compute the averages")
    return

  # Step 3: Solve the equation to get the score:
  equations = best_offer.equations
  initial_guess = [1,1]
  offer = fsolve(lambda x: equations(x, avgs), initial_guess)

  if offer is not None:
    print(f"Before rounding, if you're to accept the 30% equity ownership offer, you should add a vesting period of {offer[1] / 365} years and a cliff at {offer[0] / 12} months.")
  else:
    print("Uh oh! No offer found...")
    return


if __name__ == "__main__":
  main()
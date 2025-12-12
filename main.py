import import_dataframe
import get_average

def main():

  filepath = 'data.tsv'

  # Step 1: Import the Data
  df = import_dataframe.import_dataframe(filepath)

  if df is not None:
    print("\n Data loaded successfully! \n")
    print(df.head(), '\n')
    print(f"Total rows: {len(df)}")

  else:
    print("Could not load the data")
    return

  print('\n', "*" * 40, '\n')


  #Step 2: Compute the average

  avg = get_average.get_average(df)

  if avg is not None:
    print("Average calculated successfully! \n")
    print(f"The average score is {avg} \n")
  else:
    print("Could not compute average :(")
    return


if __name__ == "__main__":
  main()
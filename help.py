import pandas as pd

def save_csv_with_eof(df, csv_file_path):
    # Save DataFrame to CSV file
    df.to_csv(csv_file_path, index=False)

    # Append EOF text
    with open(csv_file_path, 'a') as file:
        file.write('**EOF**')

# Example
data = {
    'Column1': [1, 2, 3],
    'Column2': ['a', 'b', 'c']
}

df = pd.DataFrame(data)
save_csv_with_eof(df, "data.csv")

print(pd.read_csv('data.csv', skipfooter=1, engine='python'))
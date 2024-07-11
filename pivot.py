import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Sample data
symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']
strategies = ['Strategy_A', 'Strategy_B', 'Strategy_C', 'Strategy_D', 'Strategy_E']

# Generate sample data
data = {
    'ric': np.random.choice(symbols, 100),
    'date': [datetime.now() - timedelta(days=random.randint(0, 6)) for _ in range(100)],
    'strategy': np.random.choice(strategies, 100),
    'qty': np.random.randint(1, 1000, 100)
}

# Create DataFrame
df = pd.DataFrame(data)

# Drop the time part from the date column
df['date'] = df['date'].dt.date

# print(df.head())

df = df.groupby(['ric', 'date', 'strategy'])['qty'].sum().reset_index()
df.reset_index(inplace=True)

dates = df['date'].drop_duplicates().tolist()

df_list = []
for date in dates:
    df2  = df[df['date']==date]
    df3 = df2[['ric', 'strategy', 'qty', 'date']]
    df3.columns = pd.MultiIndex.from_product([[date], ['ric', 'strategy', 'qty', 'date']])
    df3 = df3.drop('date', axis = 1, level = 1)
    # print(df3)
    df_list.append(df3)
    
df_res = df_list[0]
for i in range(len(df_list)-1):
    df_res = pd.concat([df_res, df_list[i+1]], axis=0, ignore_index=True)
    
df_sorted = df_res.copy()
for date in dates:
	df_sorted[date] = df_sorted[date].sort_values(by='ric').reset_index(drop=True)
df_sorted = df_sorted.dropna(axis = 0, how = 'all')
df_sorted = df_sorted.fillna("") 

print(df_sorted)



# Puts the scrollbar next to the DataFrame
from IPython.display import display, HTML
display(HTML( "<div style='height: 200px; overflow: auto; width: fit-content'>" + df_sorted.to_html() + "</div>"))
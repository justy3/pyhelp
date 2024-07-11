import pandas as pd

df = pd.DataFrame({'ric': ['ric1', 'ric2', 'ric3'], 
                    'strat': ['strat1', 'strat2', 'strat3'], 
                    'qty': [27, 21, 21],
                    'date': ['d1', 'd2', 'd2']}) 

df.reset_index(inplace=True)

dates = df['date'].drop_duplicates().tolist()

df_list = []
for date in dates:
    df2  = df[df['date']==date]
    df3 = df2[['ric', 'strat', 'qty', 'date']]
    df3.columns = pd.MultiIndex.from_product([[date], ['ric', 'strat', 'qty', 'date']])
    df3 = df3.drop('date', axis = 1, level = 1)
    # print(df3)
    df_list.append(df3)

df_res = df_list[0]
for i in range(len(df_list)-1):
    df_res = pd.concat([df_res, df_list[i+1]], axis=0, ignore_index=True)
# df_res.fillna("")
df_sorted = df_res.copy()
for date in dates:
	df_sorted[date] = df_sorted[date].sort_values(by='ric').reset_index(drop=True)
df_sorted.fillna("")

print(df_sorted)

from xbrl_parser import *

if __name__=="__main__":
	# EXAMPLE
	mypath = "/home/justy/private/capula/pyhelp/jpy_parser/data_XBRL/"
	xbrlfiles = [f for f in os.listdir(mypath) if f.endswith("_XBRL")]
	# xbrlfiles = ["S100RKD8_XBRL"]

	jpy_parsed = []
	jpy_parsed_df = []
	for xbrl in xbrlfiles:
		print(mypath + xbrl)
		jpy = JPY_shares(mypath + xbrl)
		jpy_parsed.append(jpy)
		jpy_parsed_df.append(jpy.dataframe)
		# print(jpy.dataframe)

	df = pd.concat(jpy_parsed_df)
	df.set_index(['file_name', 'submission_date'], inplace=True)
	print(df)
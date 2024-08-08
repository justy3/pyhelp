from parser import *

if __name__=="__main__":
	# EXAMPLE
	mypath = "/home/justy/private/capula/pyhelp/jpy_parser/data/"
	pdffiles = [f for f in os.listdir(mypath) if f[-1]=="f"]
	# pdffiles = ["S100T9LP.pdf"]

	jpy_parsed = []
	jpy_parsed_df = []
	for pdf in pdffiles:
		jpy = JPY_shares(mypath + pdf)
		jpy_parsed.append(jpy)
		jpy_parsed_df.append(jpy.dataframe)
		# print(jpy.dataframe)

	df = pd.concat(jpy_parsed_df)
	df.set_index(['pdf_name', 'submission_date'], inplace=True)
	print(df)
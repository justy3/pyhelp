import os
import re
import pprint
import logging
import pdfplumber
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from deep_translator import GoogleTranslator

'''
LOGGER
'''
# Set up the basic configuration for logging
logging.basicConfig(level=logging.INFO,
					format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					handlers=[
						logging.StreamHandler()
					])

# Create a logger
logger = logging.getLogger(__name__)

def pattern_in_line(list_of_text, line):
	found = False
	for text in list_of_text:
		if text in line:
			found = True
			break
	return found

def extract_PDF_content(path):
	content = ''
	with pdfplumber.open(path) as pdf:
		for i in range(len(pdf.pages)):
			page = pdf.pages[i]
			page_content = page.extract_text()
			# page_content = '\n'.join(page.extract_text().split('\n')[:-1])
			content = content + page_content
	return content

class JPY_shares:
	
	def __init__(self, path):
		# save path and pdf_name
		logger.info(f"parsing pdf at : {path}")
		self.path = path
		self.pdf_name = os.path.basename(path)

		# retrieve pdf text in Japanese
		logger.info(f"retrieve japenese text")
		self.original_text = extract_PDF_content(path)

		# translate to English (requires Internet)
		logger.info("translating to english")
		self.en_translated = GoogleTranslator(source='auto', target='english').translate(self.original_text)
		self.en_translated = self.en_translated.replace('\u200b', '')
		self.en_translated_lower = self.en_translated.lower()
		self.en_lines = self.en_translated_lower.split("\n")

		# for fixing the space in output from buggy translator module
		self.lines_comma_replaced = re.sub("(\d) ,(\d)", r"\1,\2", self.en_translated_lower).split("\n")
		self.lines_comma_replaced = re.sub("(\d), (\d)", r"\1,\2", self.en_translated_lower).split("\n")

		# populate fields with dummy values
		self.ticker_id = None
		self.submission_date = None
		self.reporting_period_start = None
		self.reporting_period_end = None
		self.company_name = None
		self.disposed_treasury_stocks = None
		self.disposed_treasury_stocks_yen = None
		self.approved_buyback_stocks = None
		self.approved_buyback_stocks_yen = None
		self.shares_issued = None
		self.shares_held = None
		self.acquired_treasury_stock_by_day = None
		self.parsed_fields = [	
								"pdf_name",
								"ticker_id",
								"submission_date",
								"reporting_period_start",
								"reporting_period_end",
								"company_name",
								"shares_issued",
								"shares_held",
								"approved_buyback_stocks",
								"approved_buyback_stocks_yen",
								"acquired_treasury_stock_by_day",
								"disposed_stock_by_day"
								]

		# fill all fields
		self.get_ticker_id()
		self.get_submission_date()
		self.get_reporting_period()
		self.get_company_name()
		self.get_treasury_stocks_disposed()
		self.get_cum_treasury_stock()
		self.get_approved_buyback_shares()
		self.get_shares_issued_and_held()
		self.get_count_treasury_stock()
		self.get_count_disposed_stock()

		# get dataframe
		self.dataframe = None
		self.parsed_fields_to_df()


	def __str__(self):
		repr = ""
		repr += f"path\t\t\t\t:\t{self.path}\n"
		repr += f"pdf_name\t\t\t:\t{self.pdf_name}\n"
		repr += f"ticker_id\t\t\t:\t{self.ticker_id}\n"
		repr += f"submission_date\t\t\t:\t{self.submission_date}\n"
		repr += f"reporting_period\t\t:\t{self.reporting_period_start} to {self.reporting_period_end}\n"
		repr += f"company_name\t\t\t:\t{self.company_name}\n"
		repr += f"disposed_treasury_stocks\t:\t({self.disposed_treasury_stocks}, {self.disposed_treasury_stocks_yen})\n"
		repr += f"approved_buyback_stocks\t\t:\t({self.approved_buyback_stocks}, {self.approved_buyback_stocks_yen})\n"
		repr += f"shares_issued_and_held\t\t:\t({self.shares_issued}, {self.shares_held})\n"
		repr += f"acquired_treasury_stock_by_day\t\t:\t{self.acquired_treasury_stock_by_day}\n"
		return repr

	def show_df(self):
		print(df.fillna(""))

	'''''
	Functions to get each field
	-> latency is not an issue as we have already stored the translated text
	'''''
	def get_ticker_id(self):
		text = self.en_translated
		matches = re.findall(r'E\d{5}', " " + text + " ")
		matches = list(set(matches))

		ticker_id = None
		if len(matches)==0:
			logger.warning("No match found for ticker id")
		elif len(matches)>1:
			logger.warning("Multiple matches found")
			ticker_id = matches[0]
		else:
			ticker_id = matches[0]
		
		self.ticker_id = ticker_id

	def get_submission_date(self):
		for line in self.en_lines:
			if "submitted on" in line:
				sub_date = line.replace("[submitted on] ", "")
				self.submission_date = datetime.strptime(sub_date, "%B %d, %Y").date()
				break


	def get_reporting_period(self):
		for line in self.en_lines:
			if "reporting period" in line:
				dates = line.replace("[reporting period] ", "").replace("from", "").replace("to", "").strip().split(" ")
				sub_date_start = dates[0] + " " + dates[1] + " " + dates[2]
				self.reporting_period_start = datetime.strptime(sub_date_start, "%B %d, %Y").date()
				sub_date_end = dates[4] + " " + dates[5] + " " + dates[6]
				self.reporting_period_end = datetime.strptime(sub_date_end, "%B %d, %Y").date()
				break


	def get_company_name(self):
		for line in self.en_lines:
			if "company name" in line:
				self.company_name = line.replace("[company name] ", "").strip()
				break

	def get_treasury_stocks_disposed(self):
		en_lines = self.en_lines
		shares_disposed = (None, None)
		try:
			for i in range(len(en_lines)):
				line = en_lines[i]
				list_of_keywords = ["disposal of treasury stock", "disposal of treasury stocks", "disposal of treasury share", "disposal of treasury shares"]
				if pattern_in_line(list_of_keywords, line):
					break
			line = en_lines[i+1]
			if "total" in line:
				shares_parsed = re.findall(r'[0-9][0-9,.]+', line)
				# print(line)
				assert len(shares_parsed)==2, "expecting 2 numbers for disposed shares - No of stocks and stocks' value in Yen"
				shares_disposed = (int(shares_parsed[0].replace(",", "")), int(shares_parsed[1].replace(",", "")))
		except Exception as e:
			logger.warning(f"couldnt find disposed shares, error : {e}")
		
		self.disposed_treasury_stocks = shares_disposed[0]
		self.disposed_treasury_stocks_yen = shares_disposed[1]


	def get_approved_buyback_shares(self):
		en_lines = self.en_lines
		shares_approved_for_buyback = (None, None)
		try:
			for i in range(len(en_lines)):
				line = en_lines[i]
				if "board of directors meeting" in line:
						# print(line)
						# we are expecting the numbers to be in next line
						if i+1 != len(en_lines):
							line = en_lines[i+1]
						else:
							line = "" # 
						break
			shares_parsed = re.findall(r'[0-9][0-9,.]+', line)
			# print(line)
			assert len(shares_parsed)==2, "expecting 2 numbers for buyback shares - No of stocks and stocks' value in Yen"
			shares_approved_for_buyback = (int(shares_parsed[0].replace(",", "")), int(shares_parsed[1].replace(",", "")))
		except Exception as e:
			logger.warning(f"couldnt find approved buyback shares, error : {e}")

		# return
		self.approved_buyback_stocks = shares_approved_for_buyback[0]
		self.approved_buyback_stocks_yen = shares_approved_for_buyback[1]


	def get_shares_issued_and_held(self):
		en_lines = self.en_lines
		# text is self.en_lines
		shares_issued = None
		try:
			for line in en_lines:
				list_of_keywords = ["issued shares", "issued share", "issued stock", "issued stocks"]
				if pattern_in_line(list_of_keywords, line):
					shares_issued = int(re.findall(r'[0-9][0-9,.]+', line)[0].replace(",", ""))
					break
		except Exception as e:
			logger.warning(f"couldnt find issued shares, error : {e}")

		shares_held = None
		try:
			for line in en_lines:
				list_of_keywords = ["shares held", "share held", "stocks held", "stock held"]
				if pattern_in_line(list_of_keywords, line): 
					shares_held = int(re.findall(r'[0-9][0-9,.]+', line)[0].replace(",", ""))
					break
		except Exception as e:
			logger.warning(f"couldnt find shares held, error : {e}")
		
		# return
		self.shares_issued = shares_issued
		self.shares_held = shares_held
				
	def get_cum_treasury_stock(self):
		en_lines = self.en_lines
		# text is self.en_lines
		cum_stocks_acquired = (None, None)
		try:
			for i in range(len(en_lines)):
				line = en_lines[i]
				list_of_keywords = ["cumulative treasury stock acquired", "cumulative treasury stocks acquired", "cumulative treasury share acquired", "cumulative treasury shares acquired"]
				if pattern_in_line(list_of_keywords, line):
					break
			shares_parsed = re.findall(r'[0-9][0-9,.]+', line)
			assert 2==len(shares_parsed), f"cumulative treasury stocks not found in {i}th line, len(en_lines) = {len(en_lines)}"
			if 2!=len(shares_parsed):
				shares_parsed = re.findall(r'[0-9][0-9,.]+', en_lines[i+1])
			cum_stocks_acquired = (float(shares_parsed[0].replace(",", "")), float(shares_parsed[1].replace(",", "")))

		except Exception as e:
			logger.warning(f"couldnt find cumulative stocks acquired, error : {e}")

		# return
		self.cumulative_treasury_stocks_acquired = cum_stocks_acquired

	def get_count_treasury_stock(self):
		en_lines = self.lines_comma_replaced
		months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
		acquired_treasury_stock_dict = {}
		total_treasury_stocks_acquired = (None, None)

		try:
			for i in range(len(en_lines)):
				line = en_lines[i]
				list_of_keywords = ["treasury shares in the reporting month", "treasury share in the reporting month", "treasury stock in the reporting month", "treasury stocks in the reporting month"]
				if pattern_in_line(list_of_keywords, line):
					break
			
			monthly_reports = []
			while i < len(en_lines):
				line = en_lines[i]
				# print(f"i = {i}")
				# print(line)
				line = line.strip().split(" ")
				split_line = [x for x in line if x]
				# print(split_line)
				j = 0
				while j < len(split_line):
					# print(f"j = {j}")
					if split_line[j] in months:
						datum = split_line[j:j+4]
						monthly_reports.append(datum)
						# print(f"datum = {datum}")
						j += 4
					else:
						j += 1
				if "total" in line:
					break
				i += 1

			for dat in monthly_reports:
				date_string = dat[0]+ " " + dat[1] + " " + str(self.submission_date.year)
				date_string = date_string.replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")
				date = datetime.strptime(date_string, "%B %d %Y").date()
				# print(f"date_string = {date_string}, date = {date}")
				acquired_treasury_stock_dict[date] = (int(dat[2].replace(",", "")), int(dat[3].replace(",", ""))) # keep it generic string to check the date format across all documents

			if "total" in line:
				total_idx = line.index("total")
				line = " ".join(line[total_idx:])
				shares_parsed = re.findall(r'[0-9][0-9,.]+', line)
				assert len(shares_parsed)==2, "expecting 2 numbers for buyback shares - No of stocks and stocks' value in Yen"
				total_treasury_stocks_acquired = (int(shares_parsed[0].replace(",", "")), int(shares_parsed[1].replace(",", "")))
				# acquired_treasury_stock_dict["total"] = total_treasury_stocks_acquired

				# TODO
				# cross check if the total matches the sum of individual reportings

		except Exception as e:
			logger.warning(f"couldnt find treasury stocks, error : {e}")

		self.acquired_treasury_stock_by_day = acquired_treasury_stock_dict
		self.total_treasury_stocks_acquired = total_treasury_stocks_acquired
	
	def get_count_disposed_stock(self):
		en_lines = self.lines_comma_replaced
		months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
		disposed_stock_dict = {}

		try:
			for i in range(len(en_lines)):
				line = en_lines[i]
				list_of_keywords = ["exercise of shares acquisition rights", "exercise of share acquisition rights", "exercise of stock acquisition rights", "exercise of stocks acquisition rights"]
				if pattern_in_line(list_of_keywords, line):
					break
			
			monthly_reports = []
			while i < len(en_lines):
				line = en_lines[i]
				if "total" in line:
					break
				# print(f"i = {i}")
				# print(line)
				line = line.strip().split(" ")
				split_line = [x for x in line if x]
				# print(split_line)
				j = 0
				while j < len(split_line):
					# print(f"j = {j}")
					if split_line[j] in months:
						datum = split_line[j:j+4]
						monthly_reports.append(datum)
						# print(f"datum = {datum}")
						j += 4
					else:
						j += 1
				i += 1

			for dat in monthly_reports:
				date_string = dat[0]+ " " + dat[1] + " " + str(self.submission_date.year)
				date_string = date_string.replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")
				date = datetime.strptime(date_string, "%B %d %Y").date()
				# print(f"date_string = {date_string}, date = {date}")
				disposed_stock_dict[date] = (int(dat[2].replace(",", "")), int(dat[3].replace(",", ""))) # keep it generic string to check the date format across all documents

			if "total" in line:
				shares_parsed = re.findall(r'[0-9][0-9,.]+', line)
				assert len(shares_parsed)==2, "expecting 2 numbers for buyback shares - No of stocks and stocks' value in Yen"
				stocks_disposed = (int(shares_parsed[0].replace(",", "")), int(shares_parsed[1].replace(",", "")))
				# disposed_stock_dict["total"] = stocks_disposed

				# TODO
				# cross check if the total matches the sum of individual reportings

		except Exception as e:
			logger.warning(f"couldnt find treasury stocks, error : {e}")

		self.disposed_stock_by_day = disposed_stock_dict

	def parsed_fields_to_df(self):
		df_dict = {}

		for k in self.parsed_fields:
			if k not in ["acquired_treasury_stock_by_day", "disposed_stock_by_day"]:
				df_dict[k] = [self.__dict__[k]]

		all_reporting_dates = []
		all_reporting_dates = list(self.acquired_treasury_stock_by_day.keys()) + list(self.disposed_stock_by_day.keys())
		all_reporting_dates = list(set(all_reporting_dates))

		# fill following fields for reporting dates
		treasury_stock, treasury_stock_yen = [], []
		disposed_stock, disposed_stock_yen = [], []

		all_reporting_dates.sort()
		for d in all_reporting_dates:
			if d in self.acquired_treasury_stock_by_day.keys():
				treasury_stock.append(self.acquired_treasury_stock_by_day[d][0])
				treasury_stock_yen.append(self.acquired_treasury_stock_by_day[d][1])
			else:
				treasury_stock.append(None)
				treasury_stock_yen.append(None)

			if d in self.disposed_stock_by_day.keys():
				disposed_stock.append(self.disposed_stock_by_day[d][0])
				disposed_stock_yen.append(self.disposed_stock_by_day[d][1])
			else:
				disposed_stock.append(None)
				disposed_stock_yen.append(None)

		# fill dictionary fields for dataframe
		df_dict['total_treasury_stocks_acquired'] = self.total_treasury_stocks_acquired[0]
		df_dict['total_treasury_stocks_acquired_yen'] = self.total_treasury_stocks_acquired[1]
		df_dict['cumulative_treasury_stocks_acquired'] = self.cumulative_treasury_stocks_acquired[0]
		df_dict['cumulative_treasury_stocks_acquired_yen'] = self.cumulative_treasury_stocks_acquired[1]
		df_dict['reporting_period_date'] = all_reporting_dates
		df_dict['treasury_stock'] = treasury_stock
		df_dict['treasury_stock_yen'] = treasury_stock_yen
		df_dict['disposed_stock'] = disposed_stock
		df_dict['disposed_stock_yen'] = disposed_stock_yen

		self.dataframe = pd.DataFrame(dict([(key, pd.Series(value)) for key, value in df_dict.items()]))
		self.dataframe.to_csv(self.path.replace("pdf", "csv"))

if __name__=="__main__":
	# EXAMPLE
	mypath = "/home/justy/private/capula/pyhelp/jpy_parser/temp_data/"
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
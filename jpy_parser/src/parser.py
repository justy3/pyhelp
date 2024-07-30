import os
import re
import pprint
import logging
import pdfplumber
import numpy as np
import pandas as pd
from pathlib import Path
from deep_translator import GoogleTranslator

'''
LOGGER
'''
# Set up the basic configuration for logging
logging.basicConfig(level=logging.INFO,
					format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					handlers=[
						logging.FileHandler("example.log"),
						logging.StreamHandler()
					])

# Create a logger
logger = logging.getLogger(__name__)


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
		self.en_translated_lower = self.en_translated.lower()
		self.en_lines = self.en_translated_lower.split("\n")

		# populate fields with dummy values
		self.ticker_id = None
		self.submission_date = None
		self.reporting_period = None
		self.company_name = None
		self.treasury_stocks_disposed = None
		self.buyback_stocks_approved = None
		self.shares_issued_and_held = None
		self.treasury_stock_by_day = None

		# fill all fields
		self.get_ticker_id()
		self.get_submission_date()
		self.get_reporting_period()
		self.get_company_name()
		self.get_treasury_stocks_disposed()
		self.get_approved_buyback_shares()
		self.get_shares_issued_and_held()
		self.get_count_treasury_stock()


	def __str__(self):
		fields = ["path", "pdf_name", "ticker_id", "submission_date", "reporting_period", "company_name", "treasury_stocks_disposed", "buyback_stocks_approved", "shares_issued_and_held", "treasury_stock_by_day"]
		repr = ""
		repr += f"path\t\t\t\t:\t{self.path}\n"
		repr += f"pdf_name\t\t\t:\t{self.pdf_name}\n"
		repr += f"ticker_id\t\t\t:\t{self.ticker_id}\n"
		repr += f"submission_date\t\t\t:\t{self.submission_date}\n"
		repr += f"reporting_period\t\t:\t{self.reporting_period}\n"
		repr += f"company_name\t\t\t:\t{self.company_name}\n"
		repr += f"treasury_stocks_disposed\t:\t{self.treasury_stocks_disposed}\n"
		repr += f"buyback_stocks_approved\t\t:\t{self.buyback_stocks_approved}\n"
		repr += f"shares_issued_and_held\t\t:\t{self.shares_issued_and_held}\n"
		repr += f"treasury_stock_by_day\t\t:\t{self.treasury_stock_by_day}\n"
		return repr

	'''''
	Functions to get each field
	-> latency is not an issue as we have already stored the translated text
	'''''
	def get_ticker_id(self):
		text = self.en_translated
		matches = re.findall(r'E\d{4}', " " + text + " ")
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
				self.submission_date = line.replace("[submitted on] ", "")
				break


	def get_reporting_period(self):
		for line in self.en_lines:
			if "reporting period" in line:
				dates = line.replace("[reporting period] ", "").replace("from", "").replace("to", "").strip().split(" ")
				self.reporting_period = (dates[0]+dates[1]+dates[2], dates[4]+dates[5]+dates[6])
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
				if "disposal of treasury stock" in line:
					break
			line = en_lines[i+1]
			if "total" in line:
				shares_parsed = re.findall(r'[0-9][0-9,.]+', line)
				# print(line)
				assert len(shares_parsed)==2, "expecting 2 numbers for disposed shares - No of stocks and stocks' value in Yen"
				shares_disposed = (int(shares_parsed[0].replace(",", "")), int(shares_parsed[1].replace(",", "")))
		except Exception as e:
			logger.warning(f"couldnt find disposed shares, error : {e}")
		
		self.treasury_stocks_disposed = shares_disposed


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
		self.buyback_stocks_approved = shares_approved_for_buyback


	def get_shares_issued_and_held(self):
		en_lines = self.en_lines
		# text is self.en_lines
		shares_issued = None
		try:
			for line in en_lines:
				if "issued shares" in line:
					shares_issued = int(re.findall(r'[0-9][0-9,.]+', line)[0].replace(",", ""))
					break
		except Exception as e:
			logger.warning(f"couldnt find issued shares, error : {e}")

		shares_held = None
		try:
			for line in en_lines:
				if "shares held" in line:
					shares_held = int(re.findall(r'[0-9][0-9,.]+', line)[0].replace(",", ""))
					break
		except Exception as e:
			logger.warning(f"couldnt find shares held, error : {e}")
		
		# return
		self.shares_issued_and_held = (shares_issued, shares_held)
				

	def get_count_treasury_stock(self):
		en_lines = self.en_lines
		months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
		acquired_treasury_stock_dict = {}

		try:
			for i in range(len(en_lines)):
				line = en_lines[i]
				if "treasury stock in the reporting month" in line:
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
				acquired_treasury_stock_dict[dat[0]+ " " + dat[1]] = (dat[2], dat[3]) # keep it generic string to check the date format across all documents

			if "total" in line:
				shares_parsed = re.findall(r'[0-9][0-9,.]+', line)
				assert len(shares_parsed)==2, "expecting 2 numbers for buyback shares - No of stocks and stocks' value in Yen"
				total_treasury_stocks_acquired = (int(shares_parsed[0].replace(",", "")), int(shares_parsed[1].replace(",", "")))
				acquired_treasury_stock_dict["total"] = total_treasury_stocks_acquired

				# cross check if the total matches the 
		except Exception as e:
			logger.warning(f"couldnt find treasury stocks, error : {e}")
		
		self.treasury_stock_by_day = acquired_treasury_stock_dict

# EXAMPLE
mypath = os.getcwd()
pdffiles = [f for f in os.listdir(mypath+"/../data/") if f[-1]=="f"]

jpy_parsed = []
for pdf in pdffiles:
	jpy = JPY_shares("/home/kumarsau/private/capula/pyhelp/jpy_parser/data/" + pdf)
	# print(jpy)
	jpy_parsed.append(jpy)

for parsed_data in jpy_parsed:
	print(parsed_data)
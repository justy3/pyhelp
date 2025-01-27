import os
import re
import json
import pprint
import logging
import xmltodict
import pdfplumber
import numpy as np
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from jeraconv import jeraconv
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

def jp_date_to_py_date(date, j2w=None):
	# 2023年11月30日	-> 2023-11-30
	# western date
	year 	= date[0].split("年")[0]
	nyear 	= date[0].split("年")[1]

	if date[1]!="":
		if j2w == None:
			j2w = jeraconv.J2W()
		year_w 	= j2w.convert(year + "年")
	else:
		year_w = int(year.strip())

	date = nyear.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
	for ch in "年月日":
		date = date.replace(ch, " ")

	date_str = date.split(" ")
	year 	= year_w
	month 	= date_str[0]
	day 	= date_str[1]

	date_fmt = f"{year} {month} {day}"
	date = datetime.strptime(date_fmt, "%Y %m %d").date()
	return date

class JPY_shares:
	# date_regex = "[\d]+年[\d]+月[\d]+日"
	date_regex = "(?:(令和|平成|昭和)?\s*\d{1,2}年\s*\d{1,2}月\s*\d{1,2}日)|(?:\d{4}年\s*\d{1,2}月\s*\d{1,2}日)"
	field_keys = dict = {
		"filing_date" : "jpcrp-sbr_cor:FilingDateCoverPage",
		"reporting_period" : "jpcrp-sbr_cor:ReportingPeriodCoverPage",
		"en_name" : "jpcrp-sbr_cor:CompanyNameInEnglishCoverPage",
		"EDINETCode" : "jpdei_cor:EDINETCodeDEI",
		"shareholder_meeting_acquisition" : "jpcrp-sbr_cor:AcquisitionsByResolutionOfShareholdersMeetingTextBlock",
		"director_meeting_acquisition" : "jpcrp-sbr_cor:AcquisitionsByResolutionOfBoardOfDirectorsMeetingTextBlock",
		"disposal_of_treasury" : "jpcrp-sbr_cor:DisposalsOfTreasurySharesTextBlock",
		"holding_of_tresaury" : "jpcrp-sbr_cor:HoldingOfTreasurySharesTextBlock"
	}


	def __init__(self, path):
		'''
		path        : /home/justy/notebooks/capula/data/S100RIVY_XBRL/
		pdf name    : S100RIVY
		xbrl file   : /home/justy/notebooks/capula/data/S100RIVY_XBRL/XBRL/PublicDoc/jpcrp170000-sbr-001_E05739-000_2023-08-07_01_2023-08-07.xbrl
		'''
		logger.info("reading contents of xbrl file")
		self.path = path
		self.file_name = path.split("/")[-1]
		self.xbrl_file = [(path + "/XBRL/PublicDoc/" + f) for f in os.listdir(path + "/XBRL/PublicDoc/") if f.endswith(".xbrl")][0]
		self.contents = Path(self.xbrl_file).read_text()
		self.translator = GoogleTranslator(source='japanese', target='english')

		# parse xbrl content
		logger.info("parsing contents using xml library")
		self.parsed_dictionary = xmltodict.parse(self.contents)

		# populate fields with dummy values
		self.edinet_id 							= None
		self.submission_date 					= None
		self.reporting_period_start 			= None
		self.reporting_period_end 				= None
		self.company_name 						= None
		self.shares_issued 						= None
		self.shares_held 						= None
		self.resolution_status_shares 			= None
		self.resolution_status_shares_yen 		= None
		self.acquired_shares_daily 			= None
		self.cumulative_shares_acquired 		= None
		self.cumulative_shares_acquired_yen 	= None
		self.total_shares_acquired 				= None
		self.total_shares_acquired_yen 			= None


		self.parsed_fields = [	"file_name",
								"edinet_id",
								"submission_date",
								"reporting_period_start",
								"reporting_period_end",
								"company_name",
								"shares_issued",
								"shares_held"
								]

		# fill all fields
		self.get_edinet_id()
		self.get_submission_date()
		self.get_reporting_period()
		self.get_company_name()
		self.get_shareholder_meeting_acquisition_stocks()
		self.get_disposed_shares()
		self.get_shares_issued_and_held()

		# get dataframe
		self.dataframe = None
		self.parsed_fields_to_df()

	def __str__(self):
		repr = ""
		repr += f"path\t\t\t\t:\t{self.path}\n"
		repr += f"file_name\t\t\t:\t{self.file_name}\n"
		repr += f"edinet_id\t\t\t:\t{self.edinet_id}\n"
		repr += f"submission_date\t\t\t:\t{self.submission_date}\n"
		repr += f"reporting_period\t\t:\t{self.reporting_period_start} to {self.reporting_period_end}\n"
		repr += f"company_name\t\t\t:\t{self.company_name}\n"
		return repr

	def show_df(self):
		print(df.fillna(""))

	'''''
	Functions to get each field
	-> latency is not an issue as we have already stored the translated text
	'''''
	def get_edinet_id(self):
		parsed_dict = self.parsed_dictionary
		self.edinet_id = parsed_dict['xbrli:xbrl']["jpdei_cor:EDINETCodeDEI"]["#text"]


	def get_submission_date(self):
		parsed_dict = self.parsed_dictionary
		date = parsed_dict['xbrli:xbrl']["jpcrp-sbr_cor:FilingDateCoverPage"]["#text"]
		date = datetime.strptime(date, "%Y-%m-%d").date()
		self.submission_date = date


	def get_reporting_period(self):
		parsed_dict = self.parsed_dictionary
		dates_parsed = parsed_dict['xbrli:xbrl']["jpcrp-sbr_cor:ReportingPeriodCoverPage"]["#text"]
		dates_parsed = re.findall(fr'({self.date_regex})', dates_parsed)
		date_from 	= jp_date_to_py_date(dates_parsed[0])
		date_to 	= jp_date_to_py_date(dates_parsed[1])
		self.reporting_period_start = date_from
		self.reporting_period_end 	= date_to


	def get_company_name(self):
		parsed_dict = self.parsed_dictionary
		self.company_name = parsed_dict['xbrli:xbrl']["jpcrp-sbr_cor:CompanyNameInEnglishCoverPage"]["#text"]


	def get_shareholder_meeting_acquisition_stocks(self):
		parsed_dict = self.parsed_dictionary
		html_text = parsed_dict['xbrli:xbrl']["jpcrp-sbr_cor:AcquisitionsByResolutionOfBoardOfDirectorsMeetingTextBlock"]["#text"]
		soup = BeautifulSoup(html_text, 'lxml')
		jp_text = soup.text
		jp_text_lines = list(filter(None, jp_text.split("\n")))
		en_text = self.translator.translate(jp_text).lower()
		en_text_lines = list(filter(None, en_text.split("\n")))

		# resolution status
		try:
			logger.info(f"getting resolution status")
			keywords = [["status"], "resolution", ["board", "boards"], ["directors", "director"], "meeting"] # status of resolution at the board of directors meeting

			resolution_status = (None, None)

			for i in range(len(en_text_lines)):
				line = en_text_lines[i]
				if "resolution" in line:
					# data_parsed = re.findall(r'([0-9][0-9,.]*[0-9])[\s+]([0-9][0-9,.]*[0-9])', "\n".join(en_text_lines[i:]))[0]
					data_parsed = re.findall(r'([0-9][0-9,.]*[0-9])', re.sub(fr'{self.date_regex}', '', "\n".join(jp_text_lines[i:])))
					resolution_status = (data_parsed[0], data_parsed[1])
					break


		except Exception as e:
			logger.warning(f"couldnt find resolution status, error : {e}")


		# resolution data by day
		# import pdb; pdb.set_trace()
		try:
			logger.info(f"getting resolution data by day")
			daily_data = dict()
			last_date = None

			for i in range(len(en_text_lines)):
				line = en_text_lines[i]

				if "reporting month" in line:
					data_parsed = re.findall(fr'([\d]+月[\d]+日)[\s+]([0-9][0-9,.]*[0-9])[\s+]([0-9][0-9,.]*[0-9])', "\n".join(jp_text_lines))

					for dat in data_parsed:
						date_string = dat[0] + " " + str(self.submission_date.year)
						date_string = date_string.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
						date = datetime.strptime(date_string, "%m月%d日  %Y").date()
						daily_data[date] = (int(dat[1].replace(",", "")), int(dat[2].replace(",", "")))

					last_date = data_parsed[-1][0]
					break

		except Exception as e:
			logger.warning(f"couldnt find resolution data by day, error : {e}")

		# accumulated shares
		try:
			logger.info(f"getting accumulated shares")
			cumulative_shares_acquired = (None, None)

			for i in range(len(en_text_lines)):
				line = en_text_lines[i].lower()
				if "accumulate" in line or "cumulative" in line:
					data_parsed = re.findall(r'([0-9][0-9,.]*[0-9])[\s\n]*([0-9][0-9,.]*[0-9])', "\n".join(en_text_lines[i:]))[0]
					cumulative_shares_acquired = (data_parsed[0], data_parsed[1])
					break

		except Exception as e:
			logger.warning(f"couldnt find accumulated shares, error : {e}")


		# total shares acquired
		try:
			logger.info(f"getting total shares acquired")
			total_shares_acquired = (None, None)
			jp_text_lines = list(filter(None, jp_text.split("\n")))

			for i in range(len(jp_text_lines)):
				line = jp_text_lines[i]
				if last_date in line:
					data_parsed = re.findall(r'([0-9][0-9,.]*[0-9])[\s+]([0-9][0-9,.]*[0-9])', "\n".join(jp_text_lines[i:]))[1]
					total_shares_acquired = (data_parsed[0], data_parsed[1])
					break

		except Exception as e:
			logger.warning(f"couldnt find total shares acquired, error : {e}")

		# dates : meeting and buyback period
		try:
			buyback_dates = (None, None, None, None)
			logger.info(f"getting meeting date and buyback period")
			jp_text_lines = list(filter(None, jp_text.split("\n")))
			buyback_dates = re.findall(fr'({self.date_regex})', "\n".join(jp_text_lines))
			assert(3<len(buyback_dates)), "couldnt find enough dates in the text block"
			for i in range(len(buyback_dates)):
				buyback_dates[i] = jp_date_to_py_date(buyback_dates[i])
		except Exception as e:
			logger.warning("couldnt find meeting date and buyback period")

		self.resolution_status_shares 		= resolution_status[0]
		self.resolution_status_shares_yen 	= resolution_status[1]
		self.acquired_shares_daily 		= daily_data
		self.cumulative_shares_acquired 	= cumulative_shares_acquired[0]
		self.cumulative_shares_acquired_yen = cumulative_shares_acquired[1]
		self.total_shares_acquired 			= total_shares_acquired[0]
		self.total_shares_acquired_yen 		= total_shares_acquired[1]
		self.buyback_meeting_date 	= buyback_dates[1]
		self.buyback_period_start 	= buyback_dates[2]
		self.buyback_period_end 	= buyback_dates[3]


	def get_disposed_shares(self):
		try:
			parsed_dict = self.parsed_dictionary
			html_text = parsed_dict['xbrli:xbrl']["jpcrp-sbr_cor:DisposalsOfTreasurySharesTextBlock"]["#text"]
			soup = BeautifulSoup(html_text, 'lxml')
			jp_text = soup.text
			jp_text_lines = list(filter(None, jp_text.split("\n")))
			en_text = self.translator.translate(jp_text).lower()
			en_text_lines = list(filter(None, en_text.split("\n")))
		except Exception as e:
			logger.warning(f"couldnt retrieve field DisposalsOfTreasurySharesTextBlock from xbrl contents")

		# resolution status
		try:
			logger.info(f"getting disposed shares")
			daily_data = dict()
			data_parsed = re.findall(r'([\d]+月[\d]+日)[\s+]([0-9][0-9,.]*[0-9])[\s+]([0-9][0-9,.]*[0-9])', "\n".join(jp_text_lines))

			for dat in data_parsed:
				date_string = dat[0] + " " + str(self.submission_date.year)
				date_string = date_string.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
				date = datetime.strptime(date_string, "%m月%d日  %Y").date()
				daily_data[date] = (int(dat[1].replace(",", "")), int(dat[2].replace(",", "")))

		except Exception as e:
			logger.warning(f"couldnt find disposed shares, error : {e}")

		self.disposed_shares_daily = daily_data



	def get_shares_issued_and_held(self):
		parsed_dict = self.parsed_dictionary
		html_text = parsed_dict['xbrli:xbrl']["jpcrp-sbr_cor:HoldingOfTreasurySharesTextBlock"]["#text"]
		soup = BeautifulSoup(html_text, 'lxml')
		jp_text = soup.text
		en_text = self.translator.translate(jp_text).lower()
		en_text_lines = list(filter(None, en_text.split("\n")))

		# issued shares
		try:
			logger.info(f"issued shares")
			shares_issued = None
			data_parsed = re.findall(r'issued shares[\s\n]+([0-9][0-9,.]*[0-9])', en_text)[0]
			shares_issued = int(data_parsed.replace("," , ""))

		except Exception as e:
			logger.warning(f"couldnt find issued shares, error : {e}")


		# shares held
		try:
			logger.info(f"getting shares held")
			shares_held = None
			data_parsed = re.findall(r'shares held[\s\n]+([0-9][0-9,.]*[0-9])', en_text)[0]
			shares_held = int(data_parsed.replace("," , ""))

		except Exception as e:
			logger.warning(f"couldnt find shares held, error : {e}")

		self.shares_held = shares_held
		self.shares_issued = shares_issued


	def parsed_fields_to_df(self):
		df_dict = {}

		for k in self.parsed_fields:
			df_dict[k] = [self.__dict__[k]]

		all_reporting_dates = []
		all_reporting_dates = list(self.acquired_shares_daily.keys()) + list(self.disposed_shares_daily.keys())
		all_reporting_dates = list(set(all_reporting_dates))

		# fill following fields for reporting dates
		acquired_share, acquired_share_yen = [], []
		disposed_share, disposed_share_yen = [], []

		all_reporting_dates.sort()
		for d in all_reporting_dates:
			if d in self.acquired_shares_daily.keys():
				acquired_share.append(self.acquired_shares_daily[d][0])
				acquired_share_yen.append(self.acquired_shares_daily[d][1])
			else:
				acquired_share.append(None)
				acquired_share_yen.append(None)

			# if False:
			if d in self.disposed_shares_daily.keys():
				disposed_share.append(self.disposed_shares_daily[d][0])
				disposed_share_yen.append(self.disposed_shares_daily[d][1])
			else:
				disposed_share.append(None)
				disposed_share_yen.append(None)

		# fill dictionary fields for dataframe
		df_dict['resolution_status_shares'] 			= self.resolution_status_shares
		df_dict['resolution_status_shares_yen'] 		= self.resolution_status_shares_yen
		df_dict['buyback_meeting_date']					= self.buyback_meeting_date
		df_dict['buyback_period_start']					= self.buyback_period_start
		df_dict['buyback_period_end']					= self.buyback_period_end
		df_dict['total_shares_acquired']				= self.total_shares_acquired
		df_dict['total_shares_acquired_yen']			= self.total_shares_acquired_yen
		df_dict['cumulative_shares_acquired'] 			= self.cumulative_shares_acquired
		df_dict['cumulative_shares_acquired_yen'] 		= self.cumulative_shares_acquired_yen
		df_dict['reporting_period_date'] 				= all_reporting_dates
		df_dict['acquired_shares'] 						= acquired_share
		df_dict['acquired_shares_yen'] 					= acquired_share_yen
		df_dict['disposed_share'] 						= disposed_share
		df_dict['disposed_share_yen'] 					= disposed_share_yen

		self.dataframe = pd.DataFrame(dict([(key, pd.Series(value)) for key, value in df_dict.items()]))

		# save csv file
		csv_dir = os.path.dirname(self.path) + "_csv/"
		if not os.path.isdir(csv_dir):
			logger.info(f"creating directory for csv files : {csv_dir}")
			os.mkdir(csv_dir)

		csv_path = csv_dir + self.file_name.replace("_XBRL", ".csv")
		self.dataframe.to_csv(csv_path)

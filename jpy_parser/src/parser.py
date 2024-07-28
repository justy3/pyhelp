import os
import pdfplumber
from pathlib import Path
from deep_translator import GoogleTranslator

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
		print(f"parsing pdf at : {path}")
		self.path = path
		self.pdf_name = os.path.basename(path)

		# retrieve pdf text in Japanese
		print(f"retrieve japenese text")
		self.original_text = extract_PDF_content(path)

		# translate to English (requires Internet)
		print("translating to english")
		self.en_translated = GoogleTranslator(source='auto', target='english').translate(self.original_text)
		self.en_translated_lower = self.en_translated.lower()


	def __str__(self):
		return f"PATH : {self.path}, PDF_NAME : {self.pdf_name}"

'''''
Functions to get each field
-> latency is not an issue as we have already stored the translated text
'''''
def get_ticker_id(text):
    matches = re.findall(r'E\d{4}', " " + jpy1.en_translated + " ")
    matches = list(set(matches))
    if len(matches)==0:
        logger.INFO("No match found for ticker id")
        return None
    elif len(matches)>1:
        logger.WARN("Multiple matches found")
        return matches[0]
    else:
        return matches[0]

def get_submission_date(text):
    lines = text.split("\n")
    for line in lines:
        if "submitted on" in line:
            return line.replace("[submitted on] ", "")
    return None

def get_reporting_period(text):
    lines = text.split("\n")
    for line in lines:
        if "reporting period" in line:
            dates = line.replace("[reporting period] ", "").replace("from", "").replace("to", "").strip().split(" ")
            (dates[0]+dates[1]+dates[2], dates[4]+dates[5]+dates[6])
    return []

def get_company_name(text):
    lines = text.split("\n")
    for line in lines:
        if "company name" in line:
            return line.replace("[company name] ", "").strip()
    return []



# EXAMPLE
jpy1 = JPY_shares("/home/kumarsau/private/capula/pyhelp/jpy_parser/data/S100TZQ3.pdf")
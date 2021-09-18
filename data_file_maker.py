import configparser
from bs4 import BeautifulSoup
import requests
import pandas as pd
import time

#Constant setup
conf = configparser.ConfigParser()
conf.read('config.ini')

API_KEY = conf['SERVICE_SETTINGS']['api_key']
DATA_FILE_PATH = conf['PATH_SETTINGS']['data_file_path']

#Getting S&P500 company list from wiki
page = requests.get('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
soup = BeautifulSoup(page.text, 'html.parser')

sp500_df = pd.DataFrame(columns = ['Symbol', 'CompanyName', 'Sector', 'Industry'])

table = soup.find('table', {'id': 'constituents'})
tr_list = table.find_all('tr')
for tr in tr_list:
	td_list = tr.find_all('td')
	if (len(td_list) > 0):
		sp500_df = sp500_df.append({'Symbol': td_list[0].text.replace('.','-').replace('\n',''),
									'CompanyName': td_list[1].text.replace('\n',''),
									'Sector': td_list[3].text.replace('\n',''),
									'Industry': td_list[4].text.replace('\n','')}, ignore_index=True)

export_dataframe = pd.DataFrame(columns = [	'Symbol', 'CompanyName', 'Sector_index', 'Sector', 'Industry', 'MCap', 'Shares',
											'dividendYield', 'PayRat', 'PE', 'PEG', 'PS', 'PB', 'EVR', 'EVE', 'DE', 'DEbit',
											'ROE', 'ROA', 'ProfMar', 'OperMar'])

for i in range(len(sp500_df)):
	#Getting ratios and balance sheet data fron alphavantage
	company_overview = requests.get('https://www.alphavantage.co/query?function=OVERVIEW&symbol='+sp500_df['Symbol'].iloc[i]+'&apikey='+API_KEY)
	overview_dict = company_overview.json()
	balance_sheet = requests.get('https://www.alphavantage.co/query?function=BALANCE_SHEET&symbol='+sp500_df['Symbol'].iloc[i]+'&apikey='+API_KEY)
	balance_dict = balance_sheet.json()
	debit = 0
	de = 0
	for quarterly_record in balance_dict['quarterlyReports']:
		if (overview_dict['LatestQuarter'] <= quarterly_record['fiscalDateEnding']):
		#Getting data of the last quarterly report for calculation of debt ratios
			net_debt = float(quarterly_record['shortTermDebt'].replace('None', '0')) + float(quarterly_record['longTermDebt'].replace('None', '0')) - float(quarterly_record['cashAndCashEquivalentsAtCarryingValue'].replace('None', '0'))
			if (overview_dict['EBITDA'] == 'None'):
				debit = ''
			else:
				debit = net_debt / float(overview_dict['EBITDA'])
			if (quarterly_record['totalShareholderEquity'] == 'None'):
				de = ''
			else:
				de = net_debt / float(quarterly_record['totalShareholderEquity'])
	
	export_dataframe = export_dataframe.append({'Symbol': sp500_df['Symbol'].iloc[i],
												'CompanyName': sp500_df['CompanyName'].iloc[i],
												'Sector_index': 'S&P500 ' + sp500_df['Sector'].iloc[i],
												'Sector': overview_dict['Sector'],
												'Industry': overview_dict['Industry'],
												'MCap': overview_dict['MarketCapitalization'],
												'Shares': overview_dict['SharesOutstanding'],
												'dividendYield': overview_dict['DividendYield'].replace('None', ''),
												'PayRat': overview_dict['PayoutRatio'].replace('None', ''),
												'PE': overview_dict['PERatio'].replace('None', ''),
												'PEG': overview_dict['PEGRatio'].replace('None', ''),
												'PS': overview_dict['PriceToSalesRatioTTM'].replace('None', ''),
												'PB': overview_dict['PriceToBookRatio'].replace('None', ''),
												'EVR': overview_dict['EVToRevenue'].replace('None', ''),
												'EVE': overview_dict['EVToEBITDA'].replace('None', ''),
												'DE': de,
												'DEbit': debit,
												'ROE': overview_dict['ReturnOnEquityTTM'].replace('None', ''),
												'ROA': overview_dict['ReturnOnAssetsTTM'].replace('None', ''),
												'ProfMar': overview_dict['ProfitMargin'].replace('None', ''),
												'OperMar': overview_dict['OperatingMarginTTM'].replace('None', '')}, ignore_index=True)

export_dataframe.to_csv(DATA_FILE_PATH, index=False)
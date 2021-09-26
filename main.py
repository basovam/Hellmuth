import configparser
import json
import requests
import datetime
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mpl_dates
from mpl_finance import candlestick_ohlc
from bs4 import BeautifulSoup
from urllib.error import HTTPError
from aiohttp import web

#Constant setup
CONF = configparser.ConfigParser()
CONF.read('config.ini')

HOSTNAME = CONF['SERVER_SETTINGS']['hostname']
SERVERPORT = CONF['SERVER_SETTINGS']['serverport']

BOT_TOKEN = CONF['BOT_SETTINGS']['bot_token']
BOT_REQUEST_URL = 'https://api.telegram.org/bot' + BOT_TOKEN + '/'

LOG_FILE_PATH = CONF['PATH_SETTINGS']['log_file_path']
DATA_FILE_PATH = CONF['PATH_SETTINGS']['data_file_path']
IMAGE_FOLDER = CONF['PATH_SETTINGS']['image_folder']

ratio_title_dict = {	'PE': 'P/E',
						'PEG': 'PEG',
						'PS': 'P/S',
						'PB': 'P/Bv',
						'DE': 'Debt/Equity',
						'DEbit': 'Debt/EBITDA',
						'EVR': 'EV/Revenue',
						'EVE': 'EV/EBITDA',
						'ROE': 'ROE',
						'ROA': 'ROA',
						'dividendYield': 'Дивидендная доходность',
						'PayRat': 'PayOut ratio',
						'ProfMar': 'Profit Margin',
						'OperMar': 'Operating Margin'}

def gen_bars_values(series):
	return [series.mean(), series.max(), series.min()]
	
def draw_numbers(axes, row, column, numbers_list, indent):
	for i,v in enumerate(numbers_list):
		if (v is not None) and (not np.isnan(v)):
			if (v > 0):
				axes[row,column].text(i - 0.15, v + indent, str("%.2f" % v))
			else:
				axes[row,column].text(i - 0.15, indent, str("%.2f" % v))
		else:
			axes[row,column].text(i - 0.15, indent, 'N/a')
	return axes

def empty_space(axes, row, column):
	axes[row,column].get_yaxis().set_visible(False)
	axes[row,column].get_xaxis().set_visible(False)
	axes[row,column].spines['top'].set_visible(False)
	axes[row,column].spines['right'].set_visible(False)
	axes[row,column].spines['bottom'].set_visible(False)
	axes[row,column].spines['left'].set_visible(False)
	return axes

def stocks_infographic(wordlist, chat_id, language):
	ticker_index = wordlist.index('/stock')+1
	#Checking ticker in incomming message
	if (ticker_index < len(wordlist)):
		ticker = wordlist.pop(ticker_index).upper()
		stocks_data = pd.read_csv(DATA_FILE_PATH)
		company_data = stocks_data.loc[stocks_data['Symbol'] == ticker]
		if (company_data.shape[0] > 0):
		#If ticker in S&P500
			response = requests.post(BOT_REQUEST_URL + 'sendMessage', data={'chat_id': chat_id,	'text': CONF[language]['delay_message']})
			img_name = 'stock-'+str(chat_id)+'-'+str(datetime.datetime.now()).replace(' ','_')+'.png'
			#Modify CompanyName string for printing on image
			company_name = company_data.iloc[0].CompanyName
			if (len(company_name) > 12):
				company_name = company_name[:12]+company_name[12:].replace(' ','\n',1)
			if (len(company_name) > 24):
				company_name = company_name[:24]+company_name[24:].replace(' ','\n',2)
			
			sector_index_name = company_data.iloc[0].Sector_index
			sector_data = stocks_data.loc[stocks_data['Sector_index'] == sector_index_name]

			tags_list = [CONF[language]['mean_of_index'],
						CONF[language]['mean_of_sector']+'\n'+sector_index_name[:6]+sector_index_name[6:12].replace(' ','\n',1)+sector_index_name[12:].replace(' ','\n',1),
						CONF[language]['max_of_sector']+'\n'+sector_index_name[:6]+sector_index_name[6:12].replace(' ','\n',1)+sector_index_name[12:].replace(' ','\n',1),
						CONF[language]['min_of_sector']+'\n'+sector_index_name[:6]+sector_index_name[6:12].replace(' ','\n',1)+sector_index_name[12:].replace(' ','\n',1),
						company_name]

			plt.rcParams.update({'font.size': 15})
			fig, ax = plt.subplots(4,4,figsize=(39, 32))
			#Setting main title
			fig.suptitle(company_data.iloc[0].CompanyName, y=0.98, fontsize='xx-large')
			#Setting margins
			fig.subplots_adjust(left=0.025, bottom=0.065, right=0.975, top=0.95, wspace=0.1, hspace=0.35)
				
			for i,ratio_name in enumerate(ratio_title_dict):
				if (ratio_name in ['PB', 'DE', 'DEbit', 'EVR', 'EVE']):
					#Selecting ratios which can be only more than zero
					bars_list = np.array([stocks_data.loc[stocks_data[ratio_name] > 0][ratio_name].dropna().mean()])
					bars_list = np.append(bars_list, gen_bars_values(sector_data.loc[sector_data[ratio_name] > 0][ratio_name].dropna()))
					if (company_data.iloc[0][ratio_name] > 0):
						bars_list = np.append(bars_list, [company_data.iloc[0][ratio_name]])
					else:
						bars_list = np.append(bars_list, [np.nan])
				elif (ratio_name == 'ROE'):
					#Dropping -999999.9 value for ROE (unnormal value)
					bars_list = np.array([stocks_data.loc[stocks_data[ratio_name] > -99999.9][ratio_name].dropna().mean()])
					bars_list = np.append(bars_list, gen_bars_values(sector_data.loc[sector_data[ratio_name] > -99999.9][ratio_name].dropna()))
					if (company_data.iloc[0][ratio_name] > -99999.9):
						bars_list = np.append(bars_list, [company_data.iloc[0][ratio_name]])
					else:
						bars_list = np.append(bars_list, [np.nan])
				else:
					#Default situation
					bars_list = np.array([stocks_data[ratio_name].dropna().mean()])
					bars_list = np.append(bars_list, gen_bars_values(sector_data[ratio_name].dropna()))
					bars_list = np.append(bars_list, [company_data.iloc[0][ratio_name]])
				row = i // 4
				column = i % 4
				if (row == 3):
					column += 1
				ax[row,column].bar(tags_list,np.nan_to_num(bars_list))
				ax[row,column].set_title(ratio_title_dict[ratio_name])
				ax = draw_numbers(ax, row, column, bars_list, max(bars_list[:3])/100)
			#Making axes invisible in empty place on image
			ax = empty_space(ax, 3, 0)
			ax = empty_space(ax, 3, 3)
					
			fig.savefig(IMAGE_FOLDER + img_name)
			return ('', img_name)
		else:
			return (CONF[language]['no_found_message'], '')
	else:
		return (CONF[language]['no_ticker_message'].format('/stock'), '')

def ratios_buttons_message(wordlist, language):
	ticker_index = wordlist.index('/ratio')+1
	#Checking ticker in incomming message
	if ticker_index < len(wordlist):
		ticker = wordlist.pop(ticker_index).upper()
		stocks_data = pd.read_csv(DATA_FILE_PATH)
		if (stocks_data.loc[stocks_data['Symbol'] == ticker].shape[0] > 0):
		#If ticker in S&P500
			buttons_list = [[{'text': 'P/E', 'callback_data': 'PE ' + ticker}, {'text': 'PEG', 'callback_data': 'PEG ' + ticker},
							{'text': 'P/S', 'callback_data': 'PS ' + ticker}, {'text': 'P/B', 'callback_data': 'PB ' + ticker}],
							[{'text': 'Debt/Equity', 'callback_data': 'DE ' + ticker}, {'text': 'Debt/EBITDA', 'callback_data': 'DEbit ' + ticker}],
							[{'text': 'ROE', 'callback_data': 'ROE ' + ticker}, {'text': 'ROA', 'callback_data': 'ROA ' + ticker}],
							[{'text': 'EV/Revenue', 'callback_data': 'EVR ' + ticker}, {'text': 'EV/EBITDA', 'callback_data': 'EVE ' + ticker}],
							[{'text': 'Profit Margin', 'callback_data': 'ProfMar ' + ticker}, {'text': 'Operating Margin', 'callback_data': 'OperMar ' + ticker}],
							[{'text': 'Dividend Yield', 'callback_data': 'dividendYield ' + ticker}, {'text': 'Payout Ratio', 'callback_data': 'PayRat ' + ticker}]]
			return (CONF[language]['ratio_message'], buttons_list)
		else:
			return (CONF[language]['no_found_message'], [])
	else:
		return (CONF[language]['no_ticker_message'].format('/ratio'), [])

def stock_candlestick_chart(wordlist, chat_id, language):
	ticker_index = wordlist.index('/chart')+1
	#Checking ticker in incomming message
	if (ticker_index < len(wordlist)):
		img_name = 'ratio-'+str(chat_id)+'-'+str(datetime.datetime.now()).replace(' ','_')+'.png'
		ticker = wordlist.pop(ticker_index).upper()
		period_index = ticker_index
		if (period_index < len(wordlist)) and (wordlist[period_index] == '5y'):
			response = requests.post(BOT_REQUEST_URL + 'sendMessage', data={'chat_id': chat_id,	'text': CONF[language]['delay_message']})
		
		#Try to get company name 
		if ((ticker.find('.ME') == -1) and (ticker.find('.DE') == -1)):
		#If ticker not from Moscow exchange or German market
			page = requests.get('https://www.tinkoff.ru/invest/stocks/'+ticker+'/')
		elif (ticker.find('.DE') == -1):
		#If ticker from Moscow exchange
			page = requests.get('https://www.tinkoff.ru/invest/stocks/'+ticker[0:-3]+'/')
		else:
		#If ticker from German market
			page = requests.get('https://www.tinkoff.ru/invest/stocks/'+ticker.replace('.','@')+'/')
		soup = BeautifulSoup(page.text, "html.parser")
		elem = soup.find('span', {'class': 'SecurityHeaderPure__showName_250CD'})
		if (elem != None):
			company_name = soup.find('span', {'class': 'SecurityHeaderPure__showName_250CD'}).text
		else:
			company_name = None
		
		#Preparing time value for Yahoo finance query
		#Today value in unix epoch (end of period)
		p2 = str('%.0f' % datetime.datetime(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day, 0, 0).timestamp())
		#(number of days, width of image, height of image)
		periods_dict = {'1mo': (31, 10, 8), '3mo': (92, 12, 8), '6mo': (163, 15, 10), '1y': (366, 20, 13), '5y': (365*5+2, 25, 15)}
		period = ''
		#Checking period value in incomming message
		if (period_index < len(wordlist)):
			period = wordlist.pop(period_index).lower()
		#Setting default value for period
		if (period not in ['1mo', '3mo', '6mo', '1y', '5y']):
			period = '1y'
		period_days = periods_dict[period][0]
		#Start time value
		p1 = str('%.0f' % (int(p2) - 60*60*24*period_days))
		try:
			#	*Note*	fix big try
			#Try get data from Yahoo finance
			#	*Note*	posible better way is did not get data by pd.read_csv and use intermediate request-variable
			history_data = pd.read_csv('https://query1.finance.yahoo.com/v7/finance/download/'+ticker+'?period1='+p1+'&period2='+p2+'&interval=1d&events=history&includeAdjustedClose=true')
			history_data['Date'] = pd.to_datetime(history_data['Date'])
			history_data['Date'] = history_data['Date'].apply(mpl_dates.date2num)
			history_data = history_data.astype(float)
			plot_data = history_data[['Date', 'Open', 'High', 'Low', 'Close']]
			fig, ax = plt.subplots(figsize=(periods_dict[period][1], periods_dict[period][2]))
			candlestick_ohlc(ax, plot_data.values.tolist(), width=0.6, colorup='green', colordown='red', alpha=0.8)
			if (company_name != None):
				ax.set_title(company_name)
			else:
				ax.set_title(ticker)
			date_format = mpl_dates.DateFormatter('%m-%Y')
			ax.xaxis.set_major_formatter(date_format)
			fig.savefig(IMAGE_FOLDER + img_name, bbox_inches='tight')
			return ('', img_name)
		except HTTPError:
			return (CONF[language]['no_found_message'], '')
	else:
		return (CONF[language]['no_ticker_message'].format('/chart'), '')

def ratio_sector_chart(wordlist, chat_id, language):
	img_name = 'ratio-'+str(chat_id)+'-'+str(datetime.datetime.now()).replace(' ','_')+'.png'
	#	*Note*	Add check for incoming data
	ratio = wordlist[0]
	ticker = wordlist[1]
	
	stocks_data = pd.read_csv(DATA_FILE_PATH)
	company_data = stocks_data.loc[stocks_data['Symbol'] == ticker]
	sector_index_name = company_data.iloc[0].Sector_index
	sector_data = stocks_data.loc[stocks_data['Sector_index'] == sector_index_name].dropna(subset=[ratio])
	#Adding mean ratio values for sector
	sector_data = sector_data.append({	'Symbol': '',
										'CompanyName': 'Mean_of_the_sector',
										'Sector_index': sector_index_name,
										'Sector': '',
										'Industry': '',
										'MCap': '',
										'Shares': '',
										'dividendYield': sector_data.loc[sector_data['dividendYield'] > 0].dividendYield.dropna().mean(),
										'PayRat': sector_data.loc[sector_data['PayRat'] > 0].PayRat.dropna().mean(),
										'PE': sector_data.loc[sector_data['PE'] > 0].PE.dropna().mean(),
										'PEG': sector_data.loc[sector_data['PEG'] > 0].PEG.dropna().mean(),
										'PS': sector_data.PS.dropna().mean(),
										'PB': sector_data.PB.dropna().mean(),
										'EVR': sector_data.loc[sector_data['EVR'] > 0].EVR.dropna().mean(),
										'EVE': sector_data.loc[sector_data['EVE'] > 0].EVE.dropna().mean(),
										'DE': sector_data.loc[sector_data['DE'] > 0].DE.dropna().mean(),
										'DEbit': sector_data.loc[sector_data['DEbit'] > 0].DEbit.dropna().mean(),
										'ROE': sector_data.loc[sector_data['ROE'] > -99999.9].ROE.dropna().mean(),
										'ROA': sector_data.ROA.dropna().mean(),
										'ProfMar': sector_data.ProfMar.dropna().mean(),
										'OperMar': sector_data.OperMar.dropna().mean()}, ignore_index=True)
	#Drop unnormal values
	if (ratio in ['PB', 'DE', 'DEbit', 'EVR', 'EVE', 'dividendYield', 'PayRat']):
		sector_data = sector_data.loc[sector_data[ratio] > 0]
	elif (ratio == 'ROE'):
		sector_data = sector_data.loc[sector_data[ratio] > -99999.9]
	
	#If company data was dropped from sector dataframe
	if (sector_data.loc[sector_data['Symbol'] == ticker].shape[0] == 0):
		#Add Nan ratio values
		sector_data = sector_data.append({	'Symbol': company_data.iloc[0].Symbol,
											'CompanyName': company_data.iloc[0].CompanyName,
											'Sector_index': sector_index_name,
											'Sector': company_data.iloc[0].Sector,
											'Industry': company_data.iloc[0].Industry,
											'MCap': company_data.iloc[0].MCap,
											'Shares': company_data.iloc[0].Shares,
											'dividendYield': 0,
											'PayRat': np.nan,
											'PE': np.nan,
											'PEG': np.nan,
											'PS': np.nan,
											'PB': np.nan,
											'EVR': np.nan,
											'EVE': np.nan,
											'DE': np.nan,
											'DEbit': np.nan,
											'ROE': np.nan,
											'ROA': np.nan,
											'ProfMar': np.nan,
											'OperMar': np.nan}, ignore_index=True)
	sector_data = sector_data.sort_values(by=[ratio], na_position='first').reset_index()
			
	fig, ax = plt.subplots(figsize=(20, sector_data.shape[0]/3))
	ax.set_title(ratio_title_dict[ratio] + ' ' + CONF[language]['ratio_title_filler'] + ' ' + sector_index_name)
	barslist = ax.barh(sector_data['CompanyName'], sector_data[ratio])
	barslist[sector_data.loc[sector_data['CompanyName'] == 'Mean_of_the_sector'].index.values[0]].set_color('tab:orange')
	barslist[sector_data.loc[sector_data['Symbol'] == ticker].index.values[0]].set_color('tab:green')
	indent = sector_data[ratio].max()/100
	for i,v in enumerate(sector_data[ratio]):
		if (np.isnan(v)):
			ax.text(indent, i - 0.1, str('N/a'))
		elif (v > 0):
			ax.text(v + indent, i - 0.1, str("%.2f" % v))
		else:
			ax.text(indent, i - 0.1, str("%.2f" % v))
	fig.savefig(IMAGE_FOLDER + img_name, bbox_inches='tight')
	return(img_name)

async def get_handler(request):
	return web.Response()
		
async def post_handler(request):
	request_data = await request.text()
	request_json = {}
	try:
	#Try parsing incoming json, end handler if fail
		request_json = json.loads(request_data)
	except error:
		with open(LOG_FILE_PATH, 'a') as log_file:
			log_file.write(str(datetime.datetime.now()) + ' | ERROR JSON LOAD | ' + error + ' |\n')
		return web.Response()
		
	if ('message' in request_json):
		#Writing log
		with open(LOG_FILE_PATH, 'a') as log_file:
			# Current time | Chat Id | User Name | Message text
			log_str = str(datetime.datetime.now()) + ' | '							# Current time
			log_str += str(request_json['message']['chat']['id']) + ' | '			# Chat id
			log_str += str(request_json['message']['from']['first_name']) + ' | '	# User Name
			if ('text' in request_json['message']):
				log_str += str(request_json['message']['text']) + ' |\n'				# Message text
			else:
				log_str += 'No message text |\n'										# or no-text log
			log_file.write(log_str)
		
		#Make template of response
		response_message = {'chat_id': request_json['message']['chat']['id'],
							'text': ''
							}
		if ('text' in request_json['message']):
		#User send correct message with text
			command_found_in_text = False
			#Checkind for command in text
			msg_txt = request_json['message']['text'].lower()
			if msg_txt.find('/start') + 1:
				if ('language_code' in request_json['message']['from']) and (request_json['message']['from']['language_code'] == 'ru'):
					response_message['text'] = CONF['RUSSIAN_LANGUAGE']['hlp_txt']
				else:
					response_message['text'] = CONF['DEFAULT_LANGUAGE']['hlp_txt']
				response = requests.post(BOT_REQUEST_URL + 'sendMessage', data=response_message)
				command_found_in_text = True
			if msg_txt.find('/help') + 1:
				if ('language_code' in request_json['message']['from']) and (request_json['message']['from']['language_code'] == 'ru'):
					response_message['text'] = CONF['RUSSIAN_LANGUAGE']['hlp_txt']
				else:
					response_message['text'] = CONF['DEFAULT_LANGUAGE']['hlp_txt']
				response = requests.post(BOT_REQUEST_URL + 'sendMessage', data=response_message)
				command_found_in_text = True
			if msg_txt.find('/stock') + 1:
				if ('language_code' in request_json['message']['from']) and (request_json['message']['from']['language_code'] == 'ru'):
					response_message['text'], image_name = stocks_infographic(request_json['message']['text'].split(), response_message['chat_id'], 'RUSSIAN_LANGUAGE')
				else:
					response_message['text'], image_name = stocks_infographic(request_json['message']['text'].split(), response_message['chat_id'], 'DEFAULT_LANGUAGE')
				if (len(image_name) > 0):
					with open(IMAGE_FOLDER + image_name, 'rb') as image_file:
						response = requests.post(BOT_REQUEST_URL + 'sendPhoto', files={'photo': image_file}, data={'chat_id': response_message['chat_id']})
					os.remove(IMAGE_FOLDER + image_name)
				response = requests.post(BOT_REQUEST_URL + 'sendMessage', data=response_message)
				command_found_in_text = True
			if msg_txt.find('/ratio') + 1:
				if ('language_code' in request_json['message']['from']) and (request_json['message']['from']['language_code'] == 'ru'):
					response_message['text'], response_buttons_list = ratios_buttons_message(request_json['message']['text'].split(), 'RUSSIAN_LANGUAGE')
				else:
					response_message['text'], response_buttons_list = ratios_buttons_message(request_json['message']['text'].split(), 'DEFAULT_LANGUAGE')
				if (len(response_buttons_list) > 0):
					response_message['reply_markup'] = json.dumps({'inline_keyboard': response_buttons_list})
				response = requests.post(BOT_REQUEST_URL + 'sendMessage', data=response_message)
				command_found_in_text = True
			if msg_txt.find('/chart') + 1:
				if ('language_code' in request_json['message']['from']) and (request_json['message']['from']['language_code'] == 'ru'):
					response_message['text'], image_name = stock_candlestick_chart(request_json['message']['text'].split(), response_message['chat_id'], 'RUSSIAN_LANGUAGE')
				else:
					response_message['text'], image_name = stock_candlestick_chart(request_json['message']['text'].split(), response_message['chat_id'], 'DEFAULT_LANGUAGE')
				if (len(image_name) > 0):
					with open(IMAGE_FOLDER + image_name, 'rb') as image_file:
						response = requests.post(BOT_REQUEST_URL + 'sendPhoto', files={'photo': image_file}, data={'chat_id': response_message['chat_id']})
					os.remove(IMAGE_FOLDER + image_name)
				response = requests.post(BOT_REQUEST_URL + 'sendMessage', data=response_message)
				command_found_in_text = True
			if (not command_found_in_text):
				if ('language_code' in request_json['message']['from']) and (request_json['message']['from']['language_code'] == 'ru'):
					response_message['text'] = CONF['RUSSIAN_LANGUAGE']['etc_txt']
				else:
					response_message['text'] = CONF['DEFAULT_LANGUAGE']['etc_txt']
				
				response = requests.post(BOT_REQUEST_URL + 'sendMessage', data=response_message)
		else:
		#User can send message without text (like photo or other media). Bot must handle with this type of messages.
			if ('language_code' in request_json['message']['from']) and (request_json['message']['from']['language_code'] == 'ru'):
				response_message['text'] = CONF['RUSSIAN_LANGUAGE']['etc_txt']
			else:
				response_message['text'] = CONF['DEFAULT_LANGUAGE']['etc_txt']
			response = requests.post(BOT_REQUEST_URL + 'sendMessage', data=response_message)
	elif ('callback_query' in request_json):
		#Writing log
		with open(LOG_FILE_PATH, 'a') as log_file:
			log_str = str(datetime.datetime.now()) + ' | '										# Current time
			log_str += str(request_json['callback_query']['from']['id']) + ' | '				# User Id
			log_str += str(request_json['callback_query']['from']['first_name']) + ' | '		# User Name
			if ('data' in request_json['callback_query']):
				log_str += str(request_json['callback_query']['data']) + ' |\n'					# Query data
			else:
				log_str += 'Unexpected  callback_query |\n'										# or log message about unexpected query
			log_file.write(log_str)	 
			 
		if ('data' in request_json['callback_query']):
			if ('language_code' in request_json['callback_query']['from']) and (request_json['callback_query']['from']['language_code'] == 'ru'):
				image_name = ratio_sector_chart(request_json['callback_query']['data'].split(), request_json['callback_query']['from']['id'], 'RUSSIAN_LANGUAGE')
			else:
				image_name = ratio_sector_chart(request_json['callback_query']['data'].split(), request_json['callback_query']['from']['id'], 'DEFAULT_LANGUAGE')
			with open(IMAGE_FOLDER + image_name, 'rb') as image_file:
				response = requests.post(BOT_REQUEST_URL + 'sendPhoto', files={'photo': image_file}, data={'chat_id': request_json['callback_query']['from']['id']})
			os.remove(IMAGE_FOLDER + image_name)
		response = requests.post(BOT_REQUEST_URL + 'answerCallbackQuery', data={'callback_query_id': request_json['callback_query']['id']})
	else:
		with open(LOG_FILE_PATH, 'a') as log_file:
			log_file.write(str(datetime.datetime.now()) + ' | WARNING | Request was not processed |' + str(request_json) + ' |\n')
	return web.Response()

app = web.Application()
app.add_routes([web.post('/', post_handler), web.get('/', get_handler)])

if __name__ == "__main__":
	web.run_app(app, host=HOSTNAME, port=SERVERPORT)
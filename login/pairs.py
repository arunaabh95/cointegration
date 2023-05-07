#stats import
import yfinance as yf
import numpy as np
import pandas as pd

#django imports
from django_cron import CronJobBase, Schedule
from .models import Pair

#util imports
import re
from datetime import date
from datetime import timedelta
from queue import Queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from util import execute_trade

def subtract_years(dt, years):
        try:
            dt = dt.replace(year=dt.year-years)
        except ValueError:
            dt = dt.replace(year=dt.year-years, day=dt.day-1)
        return dt


class PairsCronJob(CronJobBase):
    RUN_EVERY_MINS = 60 * 24
    RETRY_AFTER_FAILURE_MINS = 10
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS, retry_after_failure_mins=RETRY_AFTER_FAILURE_MINS)
    code = 'yfinance'    # a unique code
    base_url = 'https://en.wikipedia.org/wiki/Companies_listed_on_the_New_York_Stock_Exchange_(A)'
    end_date = date.today() - timedelta(days=1)
    start_date = subtract_years(end_date, 1)
    sectors = {}

    def do(self):
        urls = self.prepare_urls()
        tickers = self.fetch_tickers(urls)
        self.fetch_sectors_and_filter(tickers)
        print(self.sectors)
        pairs = self.make_sectorwise_pairs()
        kss_output = pd.DataFrame(columns=["stock1", "stock2", "sector","score"])
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for sector in pairs.keys():
                # calling data in batches to sectors, to avoid issues
                data = self.download_data(self.sectors[sector])
                data.dropna(inplace=True)
                for tickers in pairs[sector]:
                    futures.append(executor.submit(self.run_execute_trade, tickers, sector, data))

            for future in as_completed(futures):
                output = future.result()
                print(f"Trades done for {output[2]}")
                kss_output.loc[len(kss_output.index)] = [output[0], output[1], output[2], np.append(1, np.cumprod(1+output[3]['gross'])).mean()]
                # test update hack
                #kss_output.loc[len(kss_output.index)] = [tickers[0], tickers[1], sector, 5.0]

        print("Sectors: \n", self.sectors)
        print("output: \n", kss_output)
        # updating my model
        self.update_model(kss_output)
        # download 1 years ticker data
        #calculate_pairs(data)
        # 2 cases, either the pair is in the table or it is not
        # if present then continue
        # else add it
        # clean it 


    def prepare_urls(self):
        urls = [self.base_url]
        reg = r'\([\s\S]*\)'
        for i in range(26):
            to = '(' + chr(i + ord('A')) + ')'
            urls.append(re.sub(reg, to, self.base_url))
        return urls

    def fetch_ticker_thread(self, url, results_queue):
        try:
            data_table = pd.read_html(url)
            results_queue.put(data_table[1]['Symbol'].to_list())
        except:
            print(f"Url not found {url}")

    def fetch_tickers(self, urls):
        # Create a queue to hold the results
        results_queue = Queue()
        threads = []
        for url in urls:
            thread = threading.Thread(target=self.fetch_ticker_thread, args=(url, results_queue))
            thread.start()
            threads.append(thread)

            # Wait for all threads to finish
        for thread in threads:
            thread.join()

            # Get all the results from the queue
        results = []
        while not results_queue.empty():
            result = results_queue.get()
            results += result
        return results
        #tickers = []
        #for url in urls:
            
        #return tickers

    def fetch_sectors_and_filter(self, tickers):
        for ticker in tickers:
            ticker_data = yf.Ticker(ticker)
            try:
                ticker_info = ticker_data.info
                if ticker_info['quoteType'] != 'NONE':
                    if ticker_info['sector'] in self.sectors:
                        self.sectors[ticker_info['sector']].append(ticker)
                    else:
                        self.sectors[ticker_info['sector']] = [ticker]
            except:
                print("Error in handling ticker ", ticker)


    def download_data(self, tickers):
        data = yf.download(tickers, end=self.end_date, start=self.start_date)
        return data['Close']

    def make_sectorwise_pairs(self):
        res = {}
        for sector in self.sectors.keys():
            stock_list = self.sectors[sector] 
            if len(stock_list) < 2:
                continue
            if len(stock_list) > 20:
                stock_list = stock_list[0:20]
            res[sector] = [(a, b) for idx, a in enumerate(stock_list) for b in stock_list[idx + 1:]]
        return res

    def update_model(self, df):
        try:
            for index, row in df.iterrows():
                # Try to retrieve a row with the given stock1 and stock2 values
                try:
                    obj = Pair.objects.get(stock1=row['stock1'], stock2=row['stock2'])
                except Pair.DoesNotExist:
                    # If the row doesn't exist, create a new one
                    obj = Pair.objects.create(stock1=row['stock1'], stock2=row['stock2'], sector=row['sector'], score=row['score'])
                else:
                    # If the row already exists, update the score field
                    obj.score = row['score']
                # Save the updated or newly created row
                obj.save()
        except Exception as inst:
            print(inst)

    def run_execute_trade(self, tickers, sector, data):
        return [tickers[0], tickers[1], sector, execute_trade(tickers, data)]


# Test code for sectors
#sectors = {'Communication Services': ['AMC', 'AMX', 'AMOV', 'T', 'ZH']}
#temp = make_sectorwise_pairs(sectors)
#print(temp)

#Test code before download
#urls = prepare_urls()
#tickers = fetch_tickers(urls)
#sectors = dict()
#filtered_tickers = fetch_sectors_and_filter(tickers, sectors)
#download_data(filtered_tickers)
#print(filtered_tickers, sectors)

#tickers = ['AYI', 'AAN']
#end_date = date.today() - timedelta(days=1)
#start_date = subtract_years(end_date, 2)
#raw_data = yf.download(tickers=tickers, end=end_date, start=start_date)
#print(raw_data['Close'])


# Test downloaded data + trade output
#tickers = ['AAPL', 'MSFT']
#data = yf.download(tickers, start="2017-01-01", end="2019-01-01", threads=True, repair=True)
#data = data['Close']
#op = execute_trade(tickers, data)
#print(op)
#for ind in data.index:
#    print(ind, "  ", data['AAPL'][ind], " ", data['MSFT'][ind])


#temp = Temp()
#temp.do()
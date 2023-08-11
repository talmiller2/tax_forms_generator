
import datetime
from selenium import webdriver
from bs4 import BeautifulSoup # makes it work on Google Colab

CPI_ISRAEL_URL = 'https://calculators.hilan.co.il/calc/ConsumerPriceIndexCalculator.aspx'

class cpi_israel_scraper():
    """
    Load the Israeli CPI data from "hilan" website and use it to calculate the cpi for some date
    """
    def __init__(self):
        dates, cpis = self.load_data()
        self.dates = dates
        self.cpis = cpis
        return

    def load_data(self):
        # configure Selenium to use a headless browser
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # ensure GUI is off
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)

        # get the source code for the page
        try:
            driver.get(CPI_ISRAEL_URL)
            source_code = driver.page_source
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            driver.quit()

        # read the lines in the page and retrieve the cpi data
        lines = source_code.split('\n')
        dates = []
        cpis = []
        do_count = False
        for line in lines:
            if '<div class="innerrow ie-fix' in line:
                do_count = True
                cnt = 0
            if do_count == True:
                if cnt == 1:
                    date_string = line.split('<div>')[1].split('</div>')[0]
                    date_format = "%m/%Y"
                    date = datetime.datetime.strptime(date_string, date_format)
                    dates += [date]
                if cnt == 5:
                    cpi = float(line.split('<div>')[1].split('</div>')[0])
                    cpis += [cpi]
                cnt += 1
                if cnt == 6:
                    do_count = False

        # reverse the order so the data is from past to future
        dates.reverse()
        cpis.reverse()

        return dates, cpis

    def get_cpi_value(self, date_input):
        # check input date is within available data
        if date_input.year < self.dates[0].year \
                or (date_input.year == self.dates[0].year and date_input.month < self.dates[0].month):
            raise ValueError('input date', date_input.strftime("%d/%m/%Y"),
                             'is before the oldest available data ', self.dates[0].strftime("%d/%m/%Y"))
        if date_input.year > self.dates[-1].year \
                or (date_input.year == self.dates[-1].year and date_input.month > self.dates[-1].month):
            raise ValueError('input date', date_input.strftime("%d/%m/%Y"),
                             'is after the newest available data ', self.dates[-1].strftime("%d/%m/%Y"))

        # search for the relevant month in the data
        for date, cpi in zip(self.dates, self.cpis):
            if date_input.year == date.year and date_input.month == date.month:
                return cpi
                break

        raise ValueError('cpi was not found for date', date_input.strftime("%d/%m/%Y"))

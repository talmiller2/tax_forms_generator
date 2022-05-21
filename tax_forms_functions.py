import argparse
import copy
import csv
import datetime
import os

import openpyxl
from currency_converter import CurrencyConverter, ECB_URL


def get_date_format(datetime_string):
    """
    datetime comes in different forms in the IB csv output file. Did not recognize the pattern, they come at random.
    """
    if ',' in datetime_string:
        date_format = '%Y-%m-%d, %H:%M:%S'
    else:
        if '/' in datetime_string:
            date_format = '%d/%m/%Y'
        elif '-' in datetime_string:
            date_format = '%Y-%m-%d'
        else:
            raise ValueError('cannot read date properly.')
    return date_format


def extract_data_from_csv(file_dir, csv_file_name, verbosity=0):
    """
    read the csv output file from IB and extract the necessary data for closing transactions and dividends
    """
    csv_file = file_dir + '/' + csv_file_name + '.csv'
    c = CurrencyConverter(ECB_URL, fallback_on_missing_rate=True)  # using the ECB database

    # csv file column definitions
    col_main_type = 0
    col_header = 1
    col_trade_type = 2
    col_asset_category = 3
    col_currency = 4
    col_ticker = 5
    col_datetime = 6
    col_quantity = 8
    col_price = 9
    col_fee = 12

    # open file in read mode
    with open(csv_file, 'r') as read_obj:
        csv_reader = csv.reader(read_obj)

        previous_trade_dict = None
        closed_lots_list = []
        closed_lots_datetime_list = []
        dividends_list = []

        for row in csv_reader:
            if verbosity == 1:
                print(row)

            # skip irrelevant rows
            if row[col_main_type] == 'Trades' and row[col_asset_category] in ['Stocks', 'Equity and Index Options']:
                if row[col_trade_type] in ['Trade', 'ClosedLot']:
                    trade_dict = {}
                    trade_dict['trade_type'] = row[col_trade_type]
                    trade_dict['currency'] = row[col_currency]
                    trade_dict['ticker'] = row[col_ticker]
                    datetime_string = row[col_datetime]
                    date_format = get_date_format(datetime_string)
                    trade_dict['datetime'] = datetime.datetime.strptime(datetime_string, date_format)
                    trade_dict['quantity'] = float(
                        row[col_quantity].replace(',', ''))  # remove comma from strings of quantities
                    trade_dict['price'] = float(row[col_price])
                    if row[col_trade_type] == 'Trade':
                        trade_dict['fee'] = abs(float(row[col_fee]))
                    if trade_dict['trade_type'] == 'Trade':
                        previous_trade_dict = copy.deepcopy(trade_dict)
                    elif trade_dict['trade_type'] == 'ClosedLot':
                        closed_lot_dict = {}
                        closed_lot_dict['currency'] = trade_dict['currency']
                        closed_lot_dict['ticker'] = trade_dict['ticker']
                        closed_lot_dict['close_datetime'] = previous_trade_dict['datetime']
                        closed_lot_dict['close_date'] = closed_lot_dict['close_datetime'].strftime("%d/%m/%Y")
                        closed_lot_dict['open_datetime'] = trade_dict['datetime']
                        closed_lot_dict['open_date'] = closed_lot_dict['open_datetime'].strftime("%d/%m/%Y")
                        closed_lot_dict['quantity'] = trade_dict['quantity']
                        closed_lot_dict['close_price'] = previous_trade_dict['price']
                        closed_lot_dict['open_price'] = trade_dict['price']
                        # for the close_value need to deduct the fee for closing the position
                        # the following works for both long/short positions
                        closed_lot_dict['close_value'] = closed_lot_dict['quantity'] * closed_lot_dict['close_price']
                        closed_lot_dict['close_value'] -= previous_trade_dict['fee']
                        # the open_value already takes into account the fee for opening the position
                        closed_lot_dict['open_value'] = closed_lot_dict['quantity'] * closed_lot_dict['open_price']
                        if row[col_asset_category] == 'Equity and Index Options':
                            # prices written per single stock but option contract are for 100 stock units
                            closed_lot_dict['close_value'] *= 100
                            closed_lot_dict['open_value'] *= 100
                        if trade_dict['quantity'] > 0:
                            closed_lot_dict['position_type'] = 'long'
                        else:
                            closed_lot_dict['position_type'] = 'short'
                        closed_lot_dict['profit'] = closed_lot_dict['close_value'] - closed_lot_dict['open_value']

                        # convert numbers from base currency to ILS and calculate profit and loss according to Israeli regulation
                        closed_lot_dict['open_currency_factor'] = c.convert(1, closed_lot_dict['currency'], 'ILS',
                                                                            date=closed_lot_dict['open_datetime'])
                        closed_lot_dict['close_currency_factor'] = c.convert(1, closed_lot_dict['currency'], 'ILS',
                                                                             date=closed_lot_dict['close_datetime'])
                        closed_lot_dict['currency_factor_ratio'] = closed_lot_dict['close_currency_factor'] / \
                                                                   closed_lot_dict['open_currency_factor']
                        closed_lot_dict['open_value_ILS'] = closed_lot_dict['open_value'] \
                                                            * closed_lot_dict['open_currency_factor']
                        closed_lot_dict['open_value_ILS_adjusted'] = closed_lot_dict['open_value'] \
                                                                     * closed_lot_dict['close_currency_factor']
                        closed_lot_dict['close_value_ILS'] = closed_lot_dict['close_value'] \
                                                             * closed_lot_dict['close_currency_factor']
                        profit_method_1 = closed_lot_dict['close_value_ILS'] \
                                          - closed_lot_dict['open_value_ILS']
                        profit_method_2 = closed_lot_dict['close_value_ILS'] \
                                          - closed_lot_dict['open_value_ILS_adjusted']
                        if closed_lot_dict['profit'] >= 0:
                            closed_lot_dict['profit_ILS'] = max(min(profit_method_1, profit_method_2), 0)
                        elif closed_lot_dict['profit'] < 0:
                            closed_lot_dict['profit_ILS'] = min(max(profit_method_1, profit_method_2), 0)

                        closed_lots_list += [closed_lot_dict]
                        closed_lots_datetime_list += [closed_lot_dict['close_datetime']]

            elif row[col_main_type] in ['Dividends', 'Withholding Tax'] and row[col_header] == 'Data':
                event_dict = {}
                event_dict['currency'] = row[2]
                if 'Total' not in event_dict['currency']:
                    datetime_string = row[3]
                    date_format = get_date_format(datetime_string)
                    event_dict['datetime'] = datetime.datetime.strptime(datetime_string, date_format)
                    event_dict['date'] = event_dict['datetime'].strftime("%d/%m/%Y")
                    event_dict['ticker'] = row[4].split('(')[0]
                    event_dict['amount'] = float(row[5])
                    if row[col_main_type] == 'Dividends':
                        if len(dividends_list) > 0 and dividends_list[-1]['ticker'] == event_dict['ticker'] \
                                and dividends_list[-1]['date'] == event_dict['date']:
                            dividends_list[-1]['amount'] += event_dict['amount']
                        else:
                            event_dict['withholding_tax'] = 0
                            dividends_list += [event_dict]
                    elif row[col_main_type] == 'Withholding Tax':
                        # find correct element in dividends list
                        ind_correct = None
                        for ind, dividend_dict in enumerate(dividends_list):
                            if dividend_dict['ticker'] == event_dict['ticker'] \
                                    and dividend_dict['date'] == event_dict['date']:
                                ind_correct = ind
                                break

                        if ind_correct is not None:
                            dividends_list[ind_correct]['withholding_tax'] += event_dict['amount']

    # some post-processing for the dividends
    for ind, dividend_dict in enumerate(dividends_list):
        dividend_dict['currency_factor'] = c.convert(1, dividend_dict['currency'], 'ILS',
                                                     date=dividend_dict['datetime'])
        dividend_dict['dividend'] = dividend_dict['amount']
        dividend_dict['dividend_ILS'] = dividend_dict['dividend'] * dividend_dict['currency_factor']
        dividend_dict['withholding_tax_ILS'] = dividend_dict['withholding_tax'] * dividend_dict['currency_factor']

    if verbosity == 1:
        for closed_lot_dict in closed_lots_list:
            output_string = ''
            output_string += 'ticker ' + closed_lot_dict['ticker'] + ': '
            output_string += 'open_date ' + closed_lot_dict['open_date'] + ', '
            output_string += 'close_date ' + closed_lot_dict['close_date'] + ', '
            output_string += 'position_type: ' + closed_lot_dict['position_type'] + ', '
            output_string += 'quantity=' + str(closed_lot_dict['quantity']) + ', '
            output_string += 'open_value=' + str(closed_lot_dict['open_value']) + ', '
            output_string += 'close_value=' + str(closed_lot_dict['close_value']) + ', '
            output_string += 'profit=' + str(closed_lot_dict['profit']) + ', '
            rate_open = c.convert(1, closed_lot_dict['currency'], 'ILS', date=closed_lot_dict['open_datetime'])
            rate_close = c.convert(1, closed_lot_dict['currency'], 'ILS', date=closed_lot_dict['close_datetime'])
            output_string += 'rate open=' + str(rate_open) + ', rate_close=' + str(rate_close)
            print(output_string)

    # sort closed-lots by closing date, as required in form 1325
    inds_sorted_close_dates = [i[0] for i in sorted(enumerate(closed_lots_datetime_list), key=lambda x: x[1])]

    return closed_lots_list, inds_sorted_close_dates, dividends_list


def write_tax_form_files(file_dir, csv_file_name, closed_lots_list, inds_sorted_close_dates, dividends_list):
    """
    write an Excel file with summary of transactions in the correct format of form 1325,
    and dividends + withohlding tax table and summary for forms 1322 + 1324.
    """

    template_file = os.path.dirname(os.path.abspath(__file__)) + '/tax_forms_template.xlsx'
    xfile = openpyxl.load_workbook(template_file)

    sheet = xfile.get_sheet_by_name('CapitalGains')
    total_profit_and_loss_ILS = 0
    total_sell_amount_ILS = 0
    for ind_line, ind_sort in enumerate(inds_sorted_close_dates):
        closed_lot_dict = closed_lots_list[ind_sort]
        num_row = ind_line + 6
        sheet['B' + str(num_row)] = ind_line + 1
        sheet['C' + str(num_row)] = closed_lot_dict['ticker']
        sheet['M' + str(num_row)] = closed_lot_dict['close_date']
        sheet['F' + str(num_row)] = closed_lot_dict['open_date']
        sheet['E' + str(num_row)] = closed_lot_dict['close_value']
        sheet['G' + str(num_row)] = closed_lot_dict['open_value']

        sheet['H' + str(num_row)] = closed_lot_dict['open_value_ILS']
        sheet['I' + str(num_row)] = closed_lot_dict['open_currency_factor']
        sheet['J' + str(num_row)] = closed_lot_dict['close_currency_factor']
        sheet['K' + str(num_row)] = closed_lot_dict['currency_factor_ratio']
        sheet['L' + str(num_row)] = closed_lot_dict['open_value_ILS_adjusted']
        sheet['N' + str(num_row)] = closed_lot_dict['close_value_ILS']
        if closed_lot_dict['profit_ILS'] >= 0:
            sheet['O' + str(num_row)] = closed_lot_dict['profit_ILS']
        else:
            sheet['P' + str(num_row)] = closed_lot_dict['profit_ILS']
        total_profit_and_loss_ILS += closed_lot_dict['profit_ILS']

        # summing all sell prices (or absolute value of buy prices in case of short position)
        if closed_lot_dict['position_type'] == 'long':
            total_sell_amount_ILS += closed_lot_dict['close_value_ILS']
        elif closed_lot_dict['position_type'] == 'short':
            total_sell_amount_ILS += abs(closed_lot_dict['open_value_ILS'])

        # extra columns not needed for form 1325, but printed for the user:
        sheet['U' + str(num_row)] = closed_lot_dict['position_type']
        sheet['V' + str(num_row)] = closed_lot_dict['quantity']
        sheet['W' + str(num_row)] = closed_lot_dict['open_price']
        sheet['X' + str(num_row)] = closed_lot_dict['close_price']
        sheet['Y' + str(num_row)] = closed_lot_dict['profit']
        sheet['Z' + str(num_row)] = closed_lot_dict['currency']

    sheet['R5'] = total_profit_and_loss_ILS
    sheet['S5'] = total_sell_amount_ILS

    # collect dividends and taxes for forms 1322, 1324
    if len(dividends_list) > 0:
        sheet2 = xfile.get_sheet_by_name('Dividends')
        total_dividends = 0
        total_dividends_ILS = 0
        withholding_tax = 0
        withholding_tax_ILS = 0
        total_dividends_minus_tax = 0
        total_dividends_minus_tax_ILS = 0
        for ind_line, dividend_dict in enumerate(dividends_list):
            num_row = ind_line + 6
            sheet2['B' + str(num_row)] = ind_line + 1
            sheet2['C' + str(num_row)] = dividend_dict['date']
            sheet2['D' + str(num_row)] = dividend_dict['ticker']
            sheet2['E' + str(num_row)] = dividend_dict['dividend']
            sheet2['F' + str(num_row)] = dividend_dict['withholding_tax']
            sheet2['G' + str(num_row)] = dividend_dict['currency_factor']
            sheet2['H' + str(num_row)] = dividend_dict['dividend_ILS']
            sheet2['I' + str(num_row)] = dividend_dict['withholding_tax_ILS']

            total_dividends += dividend_dict['dividend']
            total_dividends_ILS += dividend_dict['dividend_ILS']
            withholding_tax += dividend_dict['withholding_tax']
            withholding_tax_ILS += dividend_dict['withholding_tax_ILS']

            total_dividends_minus_tax += dividend_dict['dividend'] - abs(dividend_dict['withholding_tax'])
            total_dividends_minus_tax_ILS += dividend_dict['dividend_ILS'] - abs(dividend_dict['withholding_tax_ILS'])

        sheet2['E5'] = total_dividends
        sheet2['F5'] = withholding_tax
        sheet2['H5'] = total_dividends_ILS
        sheet2['I5'] = withholding_tax_ILS
        sheet2['K5'] = total_dividends_minus_tax
        sheet2['L5'] = total_dividends_minus_tax_ILS

    xfile.save(file_dir + '/tax_forms_' + csv_file_name + '.xlsx')
    return


def generate_tax_forms(file_dir, csv_file_name, verbosity=0):
    """
    Input a csv report from IB as defined in the Facebook post:
    https://www.facebook.com/groups/Fininja/posts/1439526366410898/
    Output is an Excel file with data necessary for tax forms 1325, 1322, 1324.
    """
    closed_lots_list, inds_sorted_close_dates, dividends_list = extract_data_from_csv(file_dir, csv_file_name,
                                                                                      verbosity=verbosity)
    write_tax_form_files(file_dir, csv_file_name, closed_lots_list, inds_sorted_close_dates, dividends_list)
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tax forms generator")
    parser.add_argument("-dir", "--dir", type=str, required=True, help="directory path of the csv file")
    parser.add_argument("-csv_file_name", "--csv_name", type=str, required=True, help="csv file name (without suffix)")
    parser.add_argument("-verbosity", "--verbosity", default=0, type=int, required=False,
                        help="verbosity of output during run")
    args = parser.parse_args()
    generate_tax_forms(args.dir, args.csv_name, args.verbosity)

import csv

def get_date_format(datetime_string, date_slash_format='normal'):
    """
    datetime comes in different forms in the IB csv output file. Did not recognize the pattern, they come at random.
    """
    if ',' in datetime_string:
        date_format = '%Y-%m-%d, %H:%M:%S'
    elif '-' in datetime_string:
        date_format = '%Y-%m-%d'
    elif '/' in datetime_string:
        if date_slash_format == 'normal':
            date_format = '%d/%m/%Y'
        elif date_slash_format == 'USA':
            date_format = '%m/%d/%Y'
        else:
            raise ValueError('invalid date_slash_format', date_slash_format)
    else:
        raise ValueError('invalid datetime_string', datetime_string)
    return date_format


def get_trades_col_names(csv_file):
    col_names = {}
    with open(csv_file, 'r') as read_obj:
        csv_reader = csv.reader(read_obj)
        for row in csv_reader:
            if row[0] == 'Trades' and row[1] == 'Header':
                col_names['main'] = 0
                col_names['header'] = 1
                for col_index, element in enumerate(row):
                    if element == 'DataDiscriminator':
                        col_names['trade_type'] = col_index
                    if element == 'Asset Category':
                        col_names['asset_category'] = col_index
                    if element == 'Currency':
                        col_names['currency'] = col_index
                    if element == 'Symbol':
                        col_names['ticker'] = col_index
                    if element == 'Date/Time':
                        col_names['datetime'] = col_index
                    if element == 'Quantity':
                        col_names['quantity'] = col_index
                    if element == 'T. Price':
                        col_names['price'] = col_index
                    if element == 'Comm/Fee':
                        col_names['fee'] = col_index
                break
    return col_names


def get_dividends_col_names(csv_file):
    col_names = {}
    with open(csv_file, 'r') as read_obj:
        csv_reader = csv.reader(read_obj)
        for row in csv_reader:
            if row[0] in ['Dividends', 'Withholding Tax'] and row[1] == 'Header':
                col_names['main'] = 0
                col_names['header'] = 1
                for col_index, element in enumerate(row):
                    if element == 'Currency':
                        col_names['currency'] = col_index
                    if element == 'Date':
                        col_names['datetime'] = col_index
                    if element == 'Description':
                        col_names['ticker'] = col_index
                    if element == 'Amount':
                        col_names['amount'] = col_index
                break
    return col_names


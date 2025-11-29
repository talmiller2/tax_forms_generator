# tax_forms_generator

This code generates the tables needed for the Israeli capital gains/losses tax forms for people who have an Interactive Brokers (IB) accounts.

For ease of use for non python users, it is adapted for use in a Google Colab notebook that contain instructions: https://colab.research.google.com/drive/1nYSSYar-MK5CTc0g6tAPepA2iaaORaOz#scrollTo=AUoXTyNeoNKv


## Installing the dependencies

```
pip install -r requirements.txt
```

## How to generate the CSV statement from IBKR

In your Interactive Brokers user area, go to "Performance & Reports" > "Statements".  
Under "Custom Statements", create a new custom statement, call it "Israel Tax Info" or something similar, and select the following sections:  
Account Information, Cash, Trades, Combined Dividends, Combined Interest, Combined Fees, Withholding Tax  

Select "No" in all the Yes/No options.
Then you can generate it every time you need it for the date range of interest.  

Follow Yaacov Rothman's [Facebook](https://www.facebook.com/groups/Fininja/posts/1439526366410898/) and/or [blog](https://fintranslator.com/2022/07/11/ib-annual-statement-for-israel-tax-reporting) post for more information. Note there's a newer recommendation from 2024 to generate two custom reports, but I think that a combined one that includes the trades (as instructed above) is still fine for this tool that will search for "closed lots".

## Running the code to produce the tax report

```
python tax_forms_functions.py --dir=$dir_path --csv_name=$csv_file_name
```

replace `$dir_path` with the path to the folder in which the CSV statement from IBKR is located, and `$csv_file_name` with the statement file name.
import requests
from lxml import etree


def get_israel_cpi_value(date_input):
    """
    Load the israeli CPI data using the israeli CBI (Central Bureau of Statistics) api.
    The returned value is relative to a value of 100 in the date 1-1-1990.
    """

    # URL of the XML data
    url_template = ('https://api.cbs.gov.il/index/data/calculator/120010?value=100&date=1-1-1990'
                    '&toDate=@MONTH@-@DAY@-@YEAR@&format=xml&download=false')
    url = url_template.replace('@DAY@', str(date_input.day))
    url = url.replace('@MONTH@', str(date_input.month))
    url = url.replace('@YEAR@', str(date_input.year))

    # Fetch the XML content from the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the XML content
        root = etree.fromstring(response.content)

        # Load all the tags in the XML
        xml_data_dict = {}
        for element in root.iter():
            # print(element.tag, element.text)
            xml_data_dict[element.tag] = element.text
    else:
        print('url:', url)
        raise ValueError(f"Failed to fetch data from url: Status code {response.status_code}")

    cpi = float(xml_data_dict['to_value'])
    return cpi

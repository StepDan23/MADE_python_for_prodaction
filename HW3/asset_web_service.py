from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from werkzeug.exceptions import InternalServerError

import requests

CBR_CURRENCY_URL = 'https://www.cbr.ru/eng/currency_base/daily/'
CBR_INDICATORS_URL = 'https://www.cbr.ru/eng/key-indicators/'


app = Flask(__name__)
app.bank = {}


class Asset:
    def __init__(self, code: str, name: str, capital: float, interest: float):
        self.code = code
        self.name = name
        self.capital = capital
        self.interest = interest

    def calculate_revenue(self, years: int) -> float:
        revenue = self.capital * ((1.0 + self.interest) ** years - 1.0)
        return revenue

    def return_list(self):
        return [self.code, self.name, self.capital, self.interest]


def parse_cbr_currency_base_daily(html_text):
    currency_dict = {}
    soup = BeautifulSoup(html_text, 'html.parser')
    table = soup.find('table', attrs={'class': 'data'})
    if table:
        table_body = table.find('tbody')
        for row in table_body.find_all('tr')[1:]:
            cols = row.find_all('td')
            try:
                code = cols[1].text
                unit = int(cols[2].text)
                currency = float(cols[4].text.replace(',', ''))
                currency = round(currency / unit, 8)
                currency_dict[code] = currency
            except ValueError:
                continue
    return currency_dict


def parse_indicators_table(table):
    currency_dict = {}
    if table:
        table_body = table.find('tbody')
        for row in table_body.find_all('tr')[1:]:
            cols = row.find_all('td')
            try:
                code = cols[0].find_all('div')[-1].text
                currency = round(float(cols[-1].text.replace(',', '')), 8)
                currency_dict[code] = currency
            except ValueError:
                continue
    return currency_dict


def parse_cbr_key_indicators(html_text):
    indicators_dict = {}
    soup = BeautifulSoup(html_text, 'html.parser')
    tables = soup.find_all('div', attrs={'class': 'table key-indicator_table'})
    indicators_dict.update(parse_indicators_table(tables[0]))
    indicators_dict.update(parse_indicators_table(tables[1]))
    return indicators_dict


@app.route('/cbr/daily')
def get_daily_currency():
    response = requests.get(CBR_CURRENCY_URL)
    if not response.ok:
        return server_unavailable(response.status_code)

    html_text = response.content.decode(encoding=response.encoding)
    currency_dict = parse_cbr_currency_base_daily(html_text)
    return jsonify(currency_dict)


@app.route('/cbr/key_indicators')
def get_key_indicators():
    response = requests.get(CBR_INDICATORS_URL)
    if not response.ok:
        return server_unavailable(response.status_code)

    html_text = response.content.decode(encoding=response.encoding)
    indicators_dict = parse_cbr_key_indicators(html_text)
    return jsonify(indicators_dict)


@app.errorhandler(404)
def not_found(e):
    return "This route is not found", 404


@app.errorhandler(InternalServerError)
def server_unavailable(e):
    return "CBR service is unavailable", 503


@app.route('/api/asset/list')
def asset_return_bank():
    all_assets = [asset.return_list() for asset in app.bank.values()]
    return jsonify(sorted(all_assets, key=lambda x: x[0])), 200


@app.route('/api/asset/add/<char_code>/<name>/<float:capital>/<float:interest>')
@app.route('/api/asset/add/<char_code>/<name>/<float:capital>/<int:interest>')
@app.route('/api/asset/add/<char_code>/<name>/<int:capital>/<float:interest>')
@app.route('/api/asset/add/<char_code>/<name>/<int:capital>/<int:interest>')
def asset_add_active(char_code, name, capital, interest):
    if name in app.bank:
        return f"Asset '{name}' is already exist", 403
    cur_asset = Asset(char_code, name, capital, interest)
    app.bank[name] = cur_asset
    return f"Asset '{name}' was successfully added", 200


@app.route('/api/asset/cleanup')
def asset_clean_bank():
    app.bank = {}
    return 'OK', 200


@app.route('/api/asset/get')
def asset_return_bank_sample():
    args = request.args.to_dict(flat=False)
    names = args.get('name', [])
    if isinstance(names, str):
        names = [names]
    names_set = set(names)
    sample_assets = [asset.return_list() for asset in app.bank.values() if asset.name in names_set]
    return jsonify(sorted(sample_assets, key=lambda x: x[0])), 200


@app.route('/api/asset/calculate_revenue')
def asset_total_revenue():
    revenue_dict = {}
    currency_dict = get_daily_currency().json
    currency_dict.update(get_key_indicators().json)

    args = request.args.to_dict(flat=False)
    period_list = args.get('period', [])
    if isinstance(period_list, str):
        period_list = [period_list]

    for period in map(int, period_list):
        revenue = sum(currency_dict[asset.code] * asset.calculate_revenue(period)
                      for asset in app.bank.values() if asset.code in currency_dict)
        revenue_dict[period] = round(revenue, 8)
    return jsonify(revenue_dict)


if __name__ == '__main__':
    app.run()

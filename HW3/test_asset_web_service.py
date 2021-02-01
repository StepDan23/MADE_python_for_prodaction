from asset_web_service import parse_cbr_currency_base_daily

NOT_EXIST_FILEPATH = 'not_exist_filepath'


def test_currency_parse_empty_html():
    expected_dict = {}
    cur_dict = parse_cbr_currency_base_daily('')
    assert expected_dict == cur_dict


def test_currency_parse_one_country_html():
    html_text = """
    <div class="table-wrapper">
      <div class="table">
        <table class="data">
         <tbody>
            <tr>
              <th>Num сode</th>
              <th>Char сode</th>
              <th>Unit</th>
              <th>Currency</th>
              <th>Rate</th>
            </tr>
            <tr>
              <td>036</td>
              <td>AUD</td>
              <td>1</td>
              <td>Australian Dollar</td>
              <td>57.0229</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    """
    expected_dict = {'AUD': 57.0229}
    cur_dict = parse_cbr_currency_base_daily(html_text)
    assert expected_dict == cur_dict


def test_currency_parse_zero_many_currency_html():
    html_text = """
    <div class="table-wrapper">
      <div class="table">
        <table class="data">
         <tbody>
            <tr>
              <th>Num сode</th>
              <th>Char сode</th>
              <th>Unit</th>
              <th>Currency</th>
              <th>Rate</th>
            </tr>
            <tr>
              <td>036</td>
              <td>AUD</td>
              <td>1</td>
              <td>Australian Dollar</td>
              <td>57.0229</td>
            </tr>
            <tr>
              <td>036</td>
              <td>AE</td>
              <td>1</td>
              <td>Australian Dollar</td>
              <td>null</td>
            </tr>
            <tr>
              <td>036</td>
              <td>BAD</td>
              <td>1</td>
              <td>Australian Dollar</td>
              <td>1.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    """
    expected_dict = {'AUD': 57.0229, 'BAD': 1.}
    cur_dict = parse_cbr_currency_base_daily(html_text)
    assert expected_dict == cur_dict


def test_currency_parse_zero_country_html():
    html_text = """
    <div class="table-wrapper">
      <div class="table">
        <table class="data">
         <tbody>
            <tr>
              <th>Num сode</th>
              <th>Char сode</th>
              <th>Unit</th>
              <th>Currency</th>
              <th>Rate</th>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    """
    expected_dict = {}
    cur_dict = parse_cbr_currency_base_daily(html_text)
    assert expected_dict == cur_dict
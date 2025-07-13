"""
This file (test_stocks.py) contains the functional tests for the 'stocks' blueprint.
"""
from app import app
import requests

######################
### HELPER CLASSES ###
######################

class MockSuccessResponse(object):
    def __init__(self, url):
        self.status_code = 200
        self.url = url
        self.headers = {'blaa': '1234'}
        
    def json(self):
        return {
            "Global Quote": {
                "01. symbol": "MSFT",
                "05. price": "295.3700",
                "07. latest trading day": "2023-04-26"
            }
        }


class MockFailedResponse(object):
    def __init__(self, url):
        self.status_code = 404
        self.url = url
        self.headers = {'blaa': '1234'}
        
    def json(self):
        return {'error': 'bad'}


def test_monkeypatch_get_success(monkeypatch):
    """
    GIVEN a Flask application an da monkeypatched version of requests.get()
    WHEN the HTTP response is set to successful
    THEN check the HTTP response
    """
    def mock_get(url):
        return MockSuccessResponse(url)
    
    url = 'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT&apikey=demo'
    monkeypatch.setattr(requests, 'get', mock_get)
    r = requests.get(url)
    assert r.status_code == 200
    assert r.url == url
    assert 'MSFT' in r.json()['Global Quote']['01. symbol']
    assert '295.3700' in r.json()['Global Quote']['05. price']
    assert '2023-04-26' in r.json()['Global Quote']['07. latest trading day']
    
    
def test_monkeypatch_get_failure(monkeypatch):
    """
    GIVEN a Flask application and a monkeypatched version of requests.get()
    WHEN the HTTP response is set to failed
    THEN check the HTTP response
    """
    def mock_get(url):
        return MockFailedResponse(url)

    url = 'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT&apikey=demo'
    monkeypatch.setattr(requests, 'get', mock_get)
    r = requests.get(url)
    print(r.json())
    assert r.status_code == 404
    assert r.url == url
    assert 'bad' in r.json()['error']    


def test_index_page(test_client):
    """
    GIVEN a Flask application
    WHEN the '/' page is requested (GET)
    THEN check if the response is valid
    """
    response = test_client.get('/')
    assert response.status_code == 200
    assert b'Flask Stock Portfolio App' in response.data
    assert b'Welcome to the' in response.data
    assert b'Flask Stock Portfolio App!' in response.data


def test_about_page(test_client):
    """
    GIVEN a Flask application
    WHEN the '/about' page is requested (GET)
    THEN check if the response is valid
    """
    response = test_client.get('users/about')
    assert response.status_code == 200
    assert b'Flask Stock Portfolio App' in response.data
    assert b'About' in response.data
    assert b'This application is built using the Flask web framework.' in response.data
    assert b'Course developed by TestDriven.io' in response.data


def test_get_add_stock_page(test_client, log_in_default_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/add_stock' page is requested (GET) by a logged in user
    THEN check if the response is valid
    """
    response = test_client.get('/add_stock')
    assert response.status_code == 200
    assert b'Flask Stock Portfolio App' in response.data
    assert b'Add a Stock' in response.data
    assert b'Stock Symbol: <em>(required, 1-5 uppercase letters)</em>' in response.data
    assert b'Number of Shares: <em>(required)</em>' in response.data
    assert b'Purchase Price ($): <em>(required)</em>' in response.data
    assert b'Purchase Date' in response.data
    
    
def test_get_add_stock_page_not_logged_in(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/add_stock' page is requested (GET) by a user who is NOT LOGGED in
    THEN check that the user is redirected to the login page
    """
    response = test_client.get('/add_stock', follow_redirects=True)
    assert response.status_code == 200
    assert b'Add a Stock' not in response.data
    assert b'Please log in to access this page.' in response.data


def test_post_add_stock_page(test_client, log_in_default_user, mock_requests_get_success_quote):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/add_stock' page is posted to (POST) by a user who IS LOGGED in
    THEN check that a message is displayed to the user that the stock was added
    """
    response = test_client.post('/add_stock',
                            data={'stock_symbol': 'AAPL',
                                  'number_of_shares': '23',
                                  'purchase_price': '432.17',
                                  'purchase_date': '2025-07-10'},
                            follow_redirects=True)
    assert response.status_code == 200
    assert b'List of Stocks' in response.data
    assert b'Stock Symbol' in response.data
    assert b'Number of Shares' in response.data
    assert b'Purchase Price' in response.data
    assert b'AAPL' in response.data
    assert b'23' in response.data
    assert b'432.17' in response.data
    assert b'Added new stock (AAPL)!' in response.data
    

def test_post_add_stock_page_not_logged_in(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/add_stock' page is posted to (POST) by a user who IS NOT LOGGED in
    THEN check that an error message is displayed
    """
    response = test_client.post('/add_stock',
                                data={'stock_symbol': 'AAPL',
                                      'number_of_shares': '23',
                                      'purchase_price': '432.17',
                                      'purchase_date': '2025-07-10'},
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'List of Stocks' not in response.data
    assert b'Added new stock (AAPL)!' not in response.data
    assert b'Please log in to access this page.' in response.data


def test_get_stock_list_logged_in(test_client, add_stocks_for_default_user, mock_requests_get_success_quote):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/stocks' page is requested (GET) by a LOGGED IN default user, 
            with default stocks in the database
    THEN check the response is valid and each default stock is displayed
    """
    headers = [b'Stock Symbol', b'Number of Shares', b'Purchase Price', b'Purchase Date',
               b'Current Share Price', b'Stock Position Value', b'TOTAL VALUE']
    data = [b'SAM', b'27', b'301.23', b'2020-07-01',
            b'COST', b'76', b'14.67', b'2019-05-26',
            b'TWTR', b'146', b'34.56', b'2020-02-03']
    
    response = test_client.get('/stocks', follow_redirects=True)
    assert response.status_code == 200
    assert b'List of Stocks' in response.data
    for header in headers:
        assert header in response.data
    for element in data:
        assert element in response.data
        

def test_get_list_stocks_not_logged_in(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/stocks' page is requested (GET) by a NOT LOGGED IN user
    THEN check they are redirected to the login page
    """
    response = test_client.get('/stocks', follow_redirects=True)
    assert response.status_code == 200
    assert b'List of Stocks' not in response.data
    assert b'Please log in to access this page.' in response.data
    
    
def test_get_stock_detail_page(test_client, add_stocks_for_default_user, mock_requests_get_success_weekly):
    """
    GIVEN a Flask application configured for testing, with the default user logged in
          and the default set of stocks in the database
    WHEN the '/stocks/3' page is retrieved (GET) and the response from Alpha Vantage was successful
    THEN check that the response is valid including a chart
    """
    response = test_client.get('/stocks/3', follow_redirects=True)
    assert response.status_code == 200
    assert b'Stock Details' in response.data
    assert b'canvas id="stockChart"' in response.data
    
    
def test_get_stock_detail_page_failed_response(test_client, add_stocks_for_default_user, mock_requests_get_failure):
    """
    GIVEN a Flask application configured for testing, with the default user logged in
          and the default set of stocks in the database
    WHEN the '/stocks/3' page is retrieved (GET)  but the response from Alpha Vantage failed
    THEN check that the response is valid but the chart is not displayed
    """
    response = test_client.get('/stocks/3', follow_redirects=True)
    assert response.status_code == 200
    assert b'Stock Details' in response.data
    assert b'canvas id="stockChart"' not in response.data
    

def test_get_stock_detail_page_incorrect_user(test_client, log_in_second_user):
    """
    GIVEN a Flask application configured for testing with the second user logged in
    WHEN the '/stocks/3' page is retrieved (GET) by the incorrect user
    THEN check that a 403 error is returned
    """
    response = test_client.get('/stocks/3')
    assert response.status_code == 403
    assert b'Stock Details' not in response.data
    assert b'canvas id="stockChart"' not in response.data
    

def test_get_stock_detail_page_invalid_stock(test_client, log_in_default_user):
    """
    GIVEN a Flask application configured for testing with the default user logged in
    WHEN the '/stocks/234' page is retrieved (GET)
    THEN check that a 404 error is returned
    """
    response = test_client.get('/stocks/234')
    assert response.status_code == 404
    assert b'Stock Details' not in response.data
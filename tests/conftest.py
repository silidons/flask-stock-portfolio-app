import os
import pytest
import requests
from project import create_app, database
from project.models import Stock, User
from flask import current_app
from datetime import datetime


######################
### HELPER CLASSES ###
######################

class MockSuccessResponseQuote(object):
    def __init__(self, url):
        self.status_code = 200
        self.url = url
        
    def json(self):
        return {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "148.3400",
                "07. latest trading day": "2020-03-24"
            }
        }
        
        
class MockApiRateLimitExceededResponse(object):
    def __init__(self, url):
        self.status_code = 200
        self.url = url
        
    def json(self):
        return {'Note': 'Thank you for using Alpha Vantage! Our standard API call frequency is ' +
                '5 calls per minute and 500 call per day.'
                }

        
class MockFailedResponse(object):
    def __init__(self, url):
        self.status_code = 404
        self.url = url
        
    def json(self):
        return {'error': 'bad'}
    
    
class MockSuccessResponseWeekly(object):
    def __init__(self, url):
        self.status_code = 200
        self.url = url
        
    def json(self):
        return {
            'Meta Data': {
                "2. Symbol": "AAPL",
                "3. Last Refreshed": "2020-07-28"},
            'Weekly Adjusted Time Series': {
                "2020-07-24": {
                    "4. close": "379.2400"},
                "2020-07-17": {
                    "4. close": "362.7600"},
                "2020-06-11": {
                    "4. close": "354.3400"},
                "2020-02-25": {
                    "4. close": "432.9800"}
            }
        }

    
    
@pytest.fixture(scope='function')
def mock_requests_get_success_quote(monkeypatch):
    # Create a mock for the requests.get() call to prevent making the actual API call
    def mock_get(url):    
        return MockSuccessResponseQuote(url)
    
    url = 'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT&apikey=demo'
    monkeypatch.setattr(requests, 'get', mock_get)
    

@pytest.fixture(scope='function')
def mock_requests_get_api_rate_limited_exceeded(monkeypatch):
    def mock_get(url):
        return MockApiRateLimitExceededResponse(url)
    
    url = 'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT&apikey=demo'
    monkeypatch.setattr(requests, 'get', mock_get)
    

@pytest.fixture(scope='function')
def mock_requests_get_failure(monkeypatch):
    def mock_get(url):
        return MockFailedResponse(url)
    
    url = 'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT&apikey=demo'
    monkeypatch.setattr(requests, 'get', mock_get)
    
    
@pytest.fixture(scope='function')
def mock_requests_get_success_weekly(monkeypatch):
    # Create a mock for the requests.get() call to prevent making the acutal API call
    def mock_get(url):
        return MockSuccessResponseWeekly(url)
    
    url = 'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol=MSFT&apikey=demo'
    monkeypatch.setattr(requests, 'get', mock_get)


@pytest.fixture(scope='function')
def new_stock():
    # Set the Testing configuration prior to creating the Flask application
    os.environ['CONFIG_TYPE'] = 'config.TestingConfig'
    flask_app = create_app()
    flask_app.extensions['mail'].suppress = True
    
    # Create a test client using the Flask application configured for testing
    with flask_app.test_client() as testing_client:
        # Establish an application context before accessing the logger and database
        with flask_app.app_context():
            stock = Stock('AAPL', '16', '406.78', 17, datetime(2025, 7, 10))
            yield stock     # this is where the testing happens!


@pytest.fixture(scope='module')
def test_client():
    # Set the Testing configuration prior to creating the Flask application
    os.environ['CONFIG_TYPE'] = 'config.TestingConfig'
    flask_app = create_app()
    flask_app.extensions['mail'].suppress = True
    
    # Create a test client using the Flask application configured for testing
    with flask_app.test_client() as testing_client:
        # Establish an application context before accessing the logger and database
        with flask_app.app_context():
            flask_app.logger.info('Creating database tables in test_client fixture...')
            
            # Create the database and the database table(s)
            database.create_all()
            
        yield testing_client

        with flask_app.app_context():
            database.drop_all()


@pytest.fixture(scope='function')
def new_user():
    user = User('patrick@gmail.com', 'FlaskIsAwesome123')
    return user


@pytest.fixture(scope='function')
def register_default_user(test_client):
    # Register the default user
    test_client.post('/users/register',
                     data={'email':'patrick@gmail.com',
                           'password':'FlaskIsAwesome123'},
                     follow_redirects=True)
    return


@pytest.fixture(scope='function')
def log_in_default_user(test_client, register_default_user):
    # Ensure user is not confirmed
    query = database.select(User).where(User.email == 'patrick@gmail.com')
    user = database.session.execute(query).scalar_one()
    user.email_confirmed = False
    user.email_confirmed_on = None
    database.session.add(user)
    database.session.commit()
    
    #log in the default user
    test_client.post('/users/login',
                     data={'email':'patrick@gmail.com',
                           'password':'FlaskIsAwesome123'},
                     follow_redirects=True)
    
    yield   # this is where the testing happens!
    
    # Log out the default user
    test_client.get('/users/logout', follow_redirects=True)
    

@pytest.fixture(scope='function')
def confirm_email_default_user(test_client, log_in_default_user):
    # Mark the user as having their email address confirmed
    query = database.select(User).where(User.email == 'patrick@gmail.com')
    user = database.session.execute(query).scalar_one()
    user.email_confirmed = True
    user.email_confirmed_on = datetime(2025, 7, 8)
    database.session.add(user)
    database.session.commit()
    
    yield user # this is where the testing happens!
    
    # Mark the user as having their email address confirmed (clean up)
    query = database.select(User).where(User.email == 'patrick@gmail.com')
    user = database.session.execute(query).scalar_one()
    user.email_confirmed = False
    user.email_confirmed_on = None
    database.session.add(user)
    database.session.commit()
    

@pytest.fixture(scope='function')
def afterwards_reset_default_user_password():
    yield # this is where the testing happens!
    
    # Since a test using this fixture could change the password for the default user,
    # reset the password back to the default password
    query = database.select(User).where(User.email == 'patrick@gmail.com')
    user = database.session.execute(query).scalar_one()
    user.set_password('FlaskIsAwesome123')
    database.session.add(user)
    database.session.commit()
    
    
@pytest.fixture(scope='function')
def add_stocks_for_default_user(test_client, log_in_default_user):
    # Add three stocks for the default user
    test_client.post('/add_stock', data={'stock_symbol': 'SAM',
                                         'number_of_shares': '27',
                                         'purchase_price': '301.23',
                                         'purchase_date': '2020-07-01'})
    test_client.post('/add_stock', data={'stock_symbol': 'COST',
                                         'number_of_shares': '76',
                                         'purchase_price': '14.67',
                                         'purchase_date': '2019-05-26'})
    test_client.post('/add_stock', data={'stock_symbol': 'TWTR',
                                         'number_of_shares': '146',
                                         'purchase_price': '34.56',
                                         'purchase_date': '2020-02-03'})
    return


@pytest.fixture(scope='function')
def register_second_user(test_client):
    """Registers the second user using the '/users/register' route."""
    test_client.post('/users/register',
                     data={'email': 'patrick@yahoo.com',
                           'password': 'FlaskIsTheBest987'})
    
    
@pytest.fixture(scope='function')
def log_in_second_user(test_client, register_second_user):
    # Log in the user
    test_client.post('/users/login',
                     data={'email': 'patrick@yahoo.com',
                           'password': 'FlaskIsTheBest987'})
    
    yield       # this is where the testing happens
    
    # Log out the user
    test_client.post('/users/logout', follow_redirects=True)
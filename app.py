from dotenv import load_dotenv
load_dotenv()

from project import create_app

# Call the application factory function to construct a Flask application
# instance using the development configuration
app = create_app()
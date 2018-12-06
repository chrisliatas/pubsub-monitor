import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'difficult-password'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db?check_same_thread=False')
    # `?check_same_thread=False`
    # fix: https://stackoverflow.com/questions/34009296/using-sqlalchemy-session-from-flask-raises-sqlite-objects-created-in-a-thread-c
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID') or 'awesome-project'
    PUBSUB_TOPIC = os.environ.get('PUBSUB_TOPIC') or 'my-pubsub-topic'
    SUBSCRIPTION_NAME = os.environ.get('SUBSCRIPTION_NAME') or 'sub-items'
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    PYGMENTS_STYLE = 'colorful'
    ITEMS_PER_PAGE = 10


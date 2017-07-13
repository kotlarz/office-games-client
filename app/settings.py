import os

# Amount of seconds before a player can win, this functions as a buffer, so that nobody wins by "accident"
# Used by register_card() in office_game.py
GAME_START_TIME_BUFFER = int(os.environ.get('OG_GAME_START_TIME_BUFFER', 10))
# Amount of seconds before a new card registration times out
GAME_CARD_REGISTRATION_TIMEOUT = int(os.environ.get('OG_GAME_CARD_REGISTRATION_TIMEOUT', 60 * 60))
# Amount of seconds before another player has to register their card to start a new game
GAME_PLAYER_REGISTRATION_TIMEOUT = int(os.environ.get('OG_GAME_PLAYER_REGISTRATION_TIMEOUT', 30))
# Amount of seconds before a game session runs out (in the case when players forget to register a winner)
GAME_SESSION_TIME = int(os.environ.get('OG_GAME_SESSION_TIME', 15 * 60))

# Firebase details
FIREBASE_API_KEY = os.environ.get('OG_FIREBASE_API_KEY', None)
FIREBASE_DATABASE_URL = os.environ.get('OG_FIREBASE_DATABASE_URL', None)
FIREBASE_STORAGE_BUCKET = os.environ.get('OG_FIREBASE_STORAGE_BUCKET', None)
FIREBASE_AUTH_DOMAIN = os.environ.get('OG_FIREBASE_AUTH_DOMAIN', None)
FIREBASE_TYPE = os.environ.get('OG_FIREBASE_TYPE', 'service_account')
FIREBASE_PROJECT_ID = os.environ.get('OG_FIREBASE_PROJECT_ID', None)
FIREBASE_PRIVATE_KEY_ID = os.environ.get('OG_FIREBASE_PRIVATE_KEY_ID', None)
FIREBASE_PRIVATE_KEY = os.environ.get('OG_FIREBASE_PRIVATE_KEY', None)
FIREBASE_CLIENT_EMAIL = os.environ.get('OG_FIREBASE_CLIENT_EMAIL', None)
FIREBASE_CLIENT_ID = os.environ.get('OG_FIREBASE_CLIENT_ID', None)
FIREBASE_AUTH_URI = os.environ.get('OG_FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth')
FIREBASE_TOKEN_URI = os.environ.get('OG_FIREBASE_TOKEN_URI', 'https://accounts.google.com/o/oauth2/token')
FIREBASE_AUTH_PROVIDER_X509_CERT_URL = os.environ.get(
    'OG_FIREBASE_AUTH_PROVIDER_X509_CERT_URL',
    'https://www.googleapis.com/oauth2/v1/certs'
)
FIREBASE_CLIENT_X509_CERT_URL = os.environ.get('OG_FIREBASE_CLIENT_X509_CERT_URL', None)

# Reader details
READER_VENDOR_ID = os.environ.get('OG_READER_VENDOR_ID', '0xffff')
READER_PRODUCT_ID = os.environ.get('OG_READER_PRODUCT_ID', '0x0035')
READER_A_PHYSICAL_PATH = os.environ.get('OG_READER_A_PHYSICAL_PATH', 'usb-3f980000.usb-1.4/input0')
READER_B_PHYSICAL_PATH = os.environ.get('OG_READER_B_PHYSICAL_PATH', 'usb-3f980000.usb-1.5/input0')

# Sensor (buttons) details
SENSOR_A_ADD_POINT_PIN = int(os.environ.get('OG_SENSOR_A_ADD_POINT_PIN', 0))
SENSOR_A_REMOVE_POINT_PIN = int(os.environ.get('OG_SENSOR_A_REMOVE_POINT_PIN', 2))
SENSOR_B_ADD_POINT_PIN = int(os.environ.get('OG_SENSOR_B_ADD_POINT_PIN', 9))
SENSOR_B_REMOVE_POINT_PIN = int(os.environ.get('OG_SENSOR_B_REMOVE_POINT_PIN', 11))

# Slack details
# Notify Slack regarding game events?
SLACK_MESSAGES_ENABLED = os.environ.get('OG_SLACK_MESSAGES_ENABLED', 'True').lower() == 'true'
SLACK_TOKEN = os.environ.get('OG_SLACK_TOKEN', None)
SLACK_DEV_CHANNEL = os.environ.get('OG_SLACK_DEV_CHANNEL', '#kontorspill_dev')
SLACK_CHANNEL = os.environ.get('OG_SLACK_CHANNEL', '#kontorspill')
SLACK_USERNAME = os.environ.get('OG_SLACK_USERNAME', 'Kontor Spill')
SLACK_AVATAR_URL = os.environ.get('OG_SLACK_AVATAR_URL', None)

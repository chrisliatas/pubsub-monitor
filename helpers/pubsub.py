from time import sleep
import json
import os
from google.cloud import pubsub_v1
from google.oauth2 import service_account

# -------------------------------------------------------
# Polling a Pull subscription from Google Cloud Build.
# -------------------------------------------------------

project_id = "YOUR_PROJECT_ID"
subscription_name = "YOUR_SUBSCRIPTION_NAME"


def callback(message):
    """
    message is of the form (https://cloud.google.com/cloud-build/docs/send-build-notifications#pull):
        {
          "receivedMessages": [
            {
              "ackId": "dQNNHlAbEGEIBERNK0EPKVgUWQYyODM2LwgRHFEZDDsLRk1SK...",
              "message": {
                "attributes": {
                  "buildId": "abcd-efgh-...",
                  "status": "SUCCESS"
                },
                "data": "SGVsbG8gQ2xvdWQgUHViL1N1YiEgSGVyZSBpcyBteSBtZXNzYWdlIQ==",
                "messageId": "19917247034"
              }
            }
          ]
        }

        "data" is a base64-encoded JSON representation of your Build resource.
    """
    # print('Received message: {}'.format(message.data))
    print('Received message:\n{}'.format(message))
    print('DATA: ', message.data.decode())
    print('Publish time: ', message.publish_time)
    print('Message id: ', message.message_id)
    if message.attributes:
        print('Attributes:')
        for key in message.attributes:
            value = message.attributes.get(key)
            print('{}: {}'.format(key, value))
    print('\n-----------------------------------------\n')
    message.ack()


def listen():
    # explicit Google Clooud authentication from a loaded service account file
    # https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.service_account.html#module-google.oauth2.service_account
    credentials_env = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    # create a JSON object
    if not credentials_env:
        print('Environment variable GOOGLE_APPLICATION_CREDENTIALS is empty')
        return

    try:
        service_account_info = json.loads(credentials_env)
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
    except json.JSONDecodeError:
        # create credentials using a Google service account private key JSON file
        credentials = service_account.Credentials.from_service_account_file(credentials_env)

    subscriber = pubsub_v1.SubscriberClient(credentials=credentials)

    # The `subscription_path` method creates a fully qualified identifier
    # in the form `projects/{project_id}/subscriptions/{subscription_name}`
    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    subscriber.subscribe(subscription_path, callback=callback)

    print('Listening for messages on {}'.format(subscription_path))

    # The subscriber is non-blocking, so we must keep the main thread from
    # exiting to allow it to process messages in the background, if not using a task queue
    while True:
        sleep(60)


if __name__ == '__main__':
    listen()

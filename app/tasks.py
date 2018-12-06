import sys
import json
from concurrent.futures import TimeoutError
from functools import partial
from google.cloud import pubsub_v1
from google.oauth2 import service_account
from rq import get_current_job
from app import create_app, db
from app.models import User, UserItem, Task
from app.parser import MsgParser


app = create_app()
app.app_context().push()


def _set_task_progress(job, progress, terminated):
    job.meta['progress'] = progress
    job.save_meta()
    task = Task.query.get(job.id)
    task.user.add_notification('task_progress', {'task_id': job.id,
                                                 'description': task.description,
                                                 'progress': progress})
    if terminated and (not task.complete):
        task.complete = True
    db.session.commit()


def _process_msg(message, user_id, job_id):
    """
    For demonstration we are using a Google Cloud Build push-subscritpion message.
    `message` is of the form (https://cloud.google.com/cloud-build/docs/send-build-notifications#pull):
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
    with app.app_context():
        app.logger.info('Processing msg in job: {}'.format(job_id))
        msg = MsgParser(message)
        try:
            user = User.query.get(user_id)
            item = UserItem(payload_json=msg.data, attrs_json=msg.msg_attrs, creator=user)
            db.session.add(item)
            db.session.commit()
            message.ack()
        except:
            db.session.rollback()
            app.logger.error('Unhandled exception:', exc_info=sys.exc_info())


def polling_subscription(user_id):
    """This will continuously poll a Pull-subscription from Google Cloud Build.

    The app is deployed on Heroku where we have only one available worker in the
    free-tier, so our queue will only have the task of continuously listening for
    new messages in the Pull subscription. When a message is received it will be
    processed in the callback.

    ref: https://googleapis.github.io/google-cloud-python/latest/pubsub/subscriber/index.html#creating-a-subscription
    """
    job = get_current_job()
    if job:
        fut_timeout = 30
        project_id = app.config['GCP_PROJECT_ID']
        subscription_name = app.config['SUBSCRIPTION_NAME']
        credentials_env = app.config['GOOGLE_APPLICATION_CREDENTIALS']
        if not credentials_env:
            app.logger.error('Environment variable GOOGLE_APPLICATION_CREDENTIALS is empty')
            return

        # Create credentials using a Google service account private key JSON file
        # https://googleapis.github.io/google-cloud-python/latest/core/auth.html#explicit-credentials
        # https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.service_account.html#domain-wide-delegation
        try:
            # if you already have the service account file loaded
            service_account_info = json.loads(credentials_env)
            credentials = service_account.Credentials.from_service_account_info(service_account_info)
        except json.JSONDecodeError:
            # OR using service account private key JSON file
            credentials = service_account.Credentials.from_service_account_file(credentials_env)

        subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
        # The `subscription_path` method creates a fully qualified identifier
        # in the form `projects/{project_id}/subscriptions/{subscription_name}`
        subscription_path = subscriber.subscription_path(project_id, subscription_name)

        # `future.result()` blocks the thread while messages are coming in through the stream.
        # Any exceptions that crop up on the thread will be set on the future.
        future = None
        terminate = False
        _set_task_progress(job, 'Polling', terminate)
        while True:
            try:
                future = subscriber.subscribe(subscription_path,
                                              callback=partial(_process_msg, user_id=user_id, job_id=job.id))
                app.logger.info('Listening for messages on {}'.format(subscription_path))
                # When timeout is unspecified, e.g. `future.result(timeout=30)`, the result method waits indefinitely.
                # However, the job might be killed by the default (or else) queue job timeout (180 sec).
                future.result(timeout=fut_timeout)
            except TimeoutError:
                with app.app_context():
                    task = Task.query.get(job.id)
                terminate = task.complete
                if terminate:
                    app.logger.info('Stopped listening for messages on {}'.format(subscription_name))
                else:
                    app.logger.info('Renewing listener for messages on {}'.format(subscription_name))
            except Exception as e:
                # job.delete()
                terminate = True
                app.logger.error('Stopped listening for messages on {} - Exception thrown: {}'
                                 .format(subscription_name, e))
            finally:
                if future is not None:
                    future.cancel()
                if terminate:
                    break

        _set_task_progress(job, 'Finished', terminate)

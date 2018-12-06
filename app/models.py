from datetime import datetime
import json
from pygments import highlight
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import rq
from app import db, login


def dt_utc_ts():
    return datetime.utcnow().timestamp()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('UserItem', backref='creator', lazy='dynamic')
    last_item_loaded_ts = db.Column(db.DateTime)
    tasks = db.relationship('Task', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    @classmethod
    def user_exists(cls, usrnam):
        return cls.query.filter_by(username=usrnam).scalar() is not None

    @classmethod
    def add_user(cls, usrnam, email, passwd):
        if not cls.user_exists(usrnam):
            usr = cls(username=usrnam, email=email)
            usr.set_password(passwd)
            db.session.add(usr)
            db.session.commit()

    @classmethod
    def remove_user(cls, usrnam):
        if cls.user_exists(usrnam):
            usr = cls.query.filter_by(username=usrnam).first()
            db.session.delete(usr)
            db.session.commit()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_item(self, useritem):
        return self.items.filter_by(item_id=useritem.item_id).count() > 0

    def add_item(self, useritem):
        if not self.has_item(useritem):
            self.items.append(useritem)

    def remove_item(self, useritem):
        if self.has_item(useritem):
            self.items.remove(useritem)

    def new_items(self):
        last_item_loaded_time = self.last_item_loaded_ts or datetime(1970, 1, 1)
        return UserItem.query.filter_by(creator=self).filter(
            UserItem.timestamp > last_item_loaded_time).order_by(
            UserItem.id.asc()).all()

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id,
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description,
                    user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self, complete=False).first()


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class UserItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    payload_json = db.Column(db.Text)
    attrs_json = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<UserItem {}>'.format(self.item_id)

    def get_data(self, is_attrs=False):
        # return JSON object
        return json.loads(str(self.attrs_json)) if is_attrs else json.loads(str(self.payload_json))

    def get_pretty_json(self, is_attrs=False):
        data = self.attrs_json if is_attrs else self.payload_json
        return json.dumps(json.loads(data), sort_keys=True, indent=2, separators=(',', ': '))

    def get_colour_json(self, is_attrs=False):
        return highlight(self.get_pretty_json(is_attrs), current_app.jsonlexer, current_app.htmlformater)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=dt_utc_ts)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 'Polling') if job is not None else 'Finished'

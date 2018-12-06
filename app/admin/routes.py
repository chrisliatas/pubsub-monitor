from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.forms import LoginForm
from app.models import User, UserItem, Notification
from app.admin import admin


@admin.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@admin.route('/', methods=['GET', 'POST'])
@admin.route('/index', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('admin.user', username=current_user.username))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('admin.index'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('admin.user', username=user.username)
        return redirect(next_page)
    return render_template('index.html', title='Sign In', form=form)


@admin.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('admin.index'))


@admin.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    useritems = user.items.order_by(UserItem.id.desc()).paginate(
        page, current_app.config['ITEMS_PER_PAGE'], True)
    next_url = url_for('admin.user', username=user.username,
                       page=useritems.next_num) if useritems.has_next else None
    prev_url = url_for('admin.user', username=user.username,
                       page=useritems.prev_num) if useritems.has_prev else None
    return render_template('user.html', user=user, items=useritems.items,
                           next_url=next_url, prev_url=prev_url)


@admin.route('/change_password', methods=['POST'])
@login_required
def change_password():
    newpwd = request.form.get('newpwd')
    if current_user.check_password(newpwd):
        newpwd = None
    if newpwd:
        current_user.set_password(newpwd)
        db.session.commit()
        current_app.logger.info('User: <{}>, password changed.'.format(current_user.username))
        return jsonify({'status': 'changed'}), 200
    else:
        return jsonify({'status': 'unchanged'}), 200


@admin.route('/polling_pubsub', methods=['GET', 'POST'])
@login_required
def polling_pubsub():
    current_task = current_user.get_task_in_progress('polling_subscription')
    if request.method == 'GET':
        # Start polling
        if current_task:
            # flash('A polling task is currently in progress')
            current_app.logger.info('A polling task is currently in progress')
            resp_o = {
                'status': 'polling',
                'task_id': current_task.id
            }
            status = 200
        else:
            task = current_user.launch_task('polling_subscription', 'Listening for pub/sub notifications', timeout=3600)
            db.session.commit()
            resp_o = {
                'status': 'success',
                'task_id': task.id
            }
            status = 202
    else:
        # Stop polling
        if current_task:
            # flash('Terminating task polling for builds')
            current_app.logger.info('Terminating task polling for builds')
            current_task.complete = True
            db.session.commit()
            resp_o = {
                'status': 'terminated',
                'task_id': current_task.id
            }
            status = 202
        else:
            resp_o = {
                'status': 'error',
                'task_id': 0
            }
            status = 200
    return jsonify(resp_o), status


@admin.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])


@admin.route('/useritems')
@login_required
def builds():
    items = current_user.new_items()
    current_user.last_item_loaded_ts = datetime.utcnow()
    db.session.commit()
    if items:
        resp_o = {
            'status': 'success',
            'items': [render_template('_useritem.html', item=i,) for i in items]
        }
    else:
        resp_o = {'status': 'unchanged', 'items': []}
    return jsonify(resp_o)


@admin.route('/pygments.css')
def pygments_css():
    return current_app.htmlformater.get_style_defs(), 200, {'Content-Type': 'text/css'}

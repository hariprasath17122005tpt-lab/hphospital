"""Real-time Notification Center Module"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.models import db, Notification
from datetime import datetime
from sqlalchemy import func

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notifications_bp.route('/')
@login_required
def center():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    total = db.session.query(func.count(Notification.id)).filter(
        Notification.user_id == current_user.id
    ).scalar() or 0
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()
    unread = db.session.query(func.count(Notification.id)).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).scalar() or 0

    return render_template('notifications/center.html',
                           notifications=notifications,
                           unread=unread, total=total,
                           page=page, per_page=per_page)


@notifications_bp.route('/api/unread-count')
@login_required
def unread_count():
    count = db.session.query(func.count(Notification.id)).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).scalar() or 0
    return jsonify({'count': count})


@notifications_bp.route('/api/recent')
@login_required
def recent():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(10).all()
    return jsonify([{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'type': n.notification_type,
        'priority': n.priority,
        'icon': n.icon or 'fa-bell',
        'action_url': n.action_url,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M') if n.created_at else '',
        'time_ago': _time_ago(n.created_at)
    } for n in notifications])


@notifications_bp.route('/api/mark-read', methods=['POST'])
@login_required
def mark_read():
    data = request.get_json(silent=True) or {}
    notif_id = data.get('notification_id')

    if notif_id == 'all':
        Notification.query.filter_by(user_id=current_user.id, is_read=False).update({
            'is_read': True, 'read_at': datetime.utcnow()
        })
    else:
        notif = Notification.query.get(notif_id)
        if notif and notif.user_id == current_user.id:
            notif.is_read = True
            notif.read_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'success': True})


@notifications_bp.route('/api/delete', methods=['POST'])
@login_required
def delete_notification():
    data = request.get_json(silent=True) or {}
    notif = Notification.query.get(data.get('notification_id'))
    if notif and notif.user_id == current_user.id:
        db.session.delete(notif)
        db.session.commit()
    return jsonify({'success': True})


def create_notification(user_id, title, message, notification_type='system',
                        priority='normal', icon=None, action_url=None,
                        reference_type=None, reference_id=None):
    """Helper function to create notifications from other modules."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        icon=icon or _default_icon(notification_type),
        action_url=action_url,
        reference_type=reference_type,
        reference_id=reference_id
    )
    db.session.add(notif)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return notif


def _default_icon(notif_type):
    return {
        'appointment': 'fa-calendar-check',
        'lab_result': 'fa-flask',
        'prescription': 'fa-prescription',
        'billing': 'fa-file-invoice-dollar',
        'emergency': 'fa-exclamation-triangle',
        'system': 'fa-bell',
        'message': 'fa-comment-dots',
    }.get(notif_type, 'fa-bell')


def _time_ago(dt):
    if not dt:
        return ''
    diff = datetime.utcnow() - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        return f'{int(seconds/60)}m ago'
    elif seconds < 86400:
        return f'{int(seconds/3600)}h ago'
    elif seconds < 604800:
        return f'{int(seconds/86400)}d ago'
    return dt.strftime('%b %d')

from flask import request
from models import db, User

# Active user sessions: { ip: { 'sid': sid, 'nickname': nickname } }
active_users = {}
# Mapping from socket session id to ip: { sid: ip }
sid_to_ip = {}

def get_client_ip():
    """Extract real client IP address from request."""
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        ip = request.remote_addr or '127.0.0.1'
    if ip == '::1':
        ip = '127.0.0.1'
    return ip

def get_or_create_user(ip):
    """Retrieve existing user by IP or create a new user with IP as default nickname."""
    user = db.session.get(User, ip)
    if not user:
        user = User(ip_address=ip, nickname=ip, is_online=False)
        db.session.add(user)
        db.session.commit()
    return user

def is_ip_connected(ip):
    """Check if the given IP address is currently connected to active chat session."""
    return ip in active_users

def get_active_users_list():
    """Get list of active online users."""
    users = []
    for ip, data in active_users.items():
        users.append({
            'ip': ip,
            'nickname': data.get('nickname', ip)
        })
    return users


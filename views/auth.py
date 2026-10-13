from flask import render_template, request, redirect, url_for, session, flash, jsonify
from . import auth_bp
from user_manager import get_client_ip, get_or_create_user, is_ip_connected, active_users

@auth_bp.route('/')
@auth_bp.route('/login')
def login():
    ip = get_client_ip()
    user = get_or_create_user(ip)
    
    # Check if already connected
    is_connected = is_ip_connected(ip)
    
    return render_template('login.html', 
                           ip=ip, 
                           nickname=user.nickname, 
                           is_connected=is_connected)

@auth_bp.route('/enter', methods=['POST'])
def enter():
    ip = get_client_ip()
    user = get_or_create_user(ip)
    
    # If already active socket session exists
    if is_ip_connected(ip):
        flash('이미 해당 IP 주소로 활성화된 채팅창이 열려 있습니다. 기존 창을 먼저 닫아주세요.', 'danger')
        return redirect(url_for('auth.login'))
    
    session['user_ip'] = ip
    session['user_nickname'] = user.nickname
    return redirect(url_for('chat.chat_room'))

@auth_bp.route('/reset-session', methods=['POST'])
def reset_session():
    """Safety feature: allow user to forcibly disconnect existing ghost session for this IP."""
    ip = get_client_ip()
    if ip in active_users:
        del active_users[ip]
    flash('기존 세션을 초기화했습니다. 다시 입장해주세요.', 'info')
    return redirect(url_for('auth.login'))


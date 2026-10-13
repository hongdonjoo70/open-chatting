from flask import render_template, request, session, redirect, url_for, jsonify, flash
from sqlalchemy import or_, and_
from . import chat_bp
from models import db, User, Message, Notice
from user_manager import get_client_ip, get_or_create_user, get_active_users_list

@chat_bp.route('/chat')
def chat_room():
    ip = get_client_ip()
    user = get_or_create_user(ip)
    
    # Update session
    session['user_ip'] = ip
    session['user_nickname'] = user.nickname
    
    # Retrieve latest active notice if available
    latest_notice = Notice.query.filter_by(is_active=True).order_by(Notice.id.desc()).first()
    
    # Retrieve recent messages accessible to this user
    # Accessible if:
    # 1. msg_type in ('all', 'notice')
    # 2. msg_type == 'dm' and (sender_ip == ip or receiver_ip == ip)
    recent_messages = Message.query.filter(
        or_(
            Message.msg_type.in_(['all', 'notice']),
            and_(
                Message.msg_type == 'dm',
                or_(Message.sender_ip == ip, Message.receiver_ip == ip)
            )
        )
    ).order_by(Message.id.asc()).limit(100).all()
    
    messages_data = [msg.to_dict() for msg in recent_messages]
    active_users = get_active_users_list()
    
    return render_template(
        'chat.html',
        user_ip=ip,
        nickname=user.nickname,
        latest_notice=latest_notice.to_dict() if latest_notice else None,
        initial_messages=messages_data,
        active_users=active_users
    )

@chat_bp.route('/api/search')
def search_messages():
    """Search previous chatting messages with keyword and optional filters."""
    ip = get_client_ip()
    keyword = request.args.get('keyword', '').strip()
    msg_type = request.args.get('type', 'all_types')  # 'all_types', 'all', 'notice', 'dm'
    
    query = Message.query.filter(
        or_(
            Message.msg_type.in_(['all', 'notice']),
            and_(
                Message.msg_type == 'dm',
                or_(Message.sender_ip == ip, Message.receiver_ip == ip)
            )
        )
    )
    
    if keyword:
        query = query.filter(Message.content.ilike(f'%{keyword}%'))
        
    if msg_type in ['all', 'notice', 'dm']:
        query = query.filter(Message.msg_type == msg_type)
        
    messages = query.order_by(Message.id.desc()).limit(100).all()
    return jsonify({
        'success': True,
        'count': len(messages),
        'keyword': keyword,
        'results': [m.to_dict() for m in messages]
    })

@chat_bp.route('/api/nickname', methods=['POST'])
def update_nickname():
    """Update user's nickname."""
    ip = get_client_ip()
    data = request.get_json() or {}
    new_nickname = data.get('nickname', '').strip()
    
    if not new_nickname:
        return jsonify({'success': False, 'message': '닉네임을 입력해주세요.'}), 400
        
    if len(new_nickname) > 30:
        return jsonify({'success': False, 'message': '닉네임은 30자 이하여야 합니다.'}), 400
        
    user = get_or_create_user(ip)
    old_nickname = user.nickname
    user.nickname = new_nickname
    db.session.commit()
    
    session['user_nickname'] = new_nickname
    
    return jsonify({
        'success': True,
        'old_nickname': old_nickname,
        'new_nickname': new_nickname,
        'ip': ip
    })

@chat_bp.route('/api/notice/latest')
def get_latest_notice():
    """Get the latest active notice."""
    latest_notice = Notice.query.filter_by(is_active=True).order_by(Notice.id.desc()).first()
    return jsonify({
        'success': True,
        'notice': latest_notice.to_dict() if latest_notice else None
    })

@chat_bp.route('/api/notice/delete', methods=['POST'])
def delete_notice_api():
    """Deactivate or delete the active notice."""
    data = request.get_json() or {}
    notice_id = data.get('notice_id')
    
    if notice_id:
        notice = db.session.get(Notice, notice_id)
        if notice:
            notice.is_active = False
            db.session.commit()
            return jsonify({'success': True, 'message': '공지사항이 삭제되었습니다.', 'notice_id': notice.id})
        return jsonify({'success': False, 'message': '해당 공지사항을 찾을 수 없습니다.'}), 404
    else:
        count = Notice.query.filter_by(is_active=True).update({'is_active': False})
        db.session.commit()
        return jsonify({'success': True, 'message': '활성 공지사항이 삭제되었습니다.', 'count': count})

import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app, send_from_directory

@chat_bp.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload image or general file for chat."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '파일이 전달되지 않았습니다.'}), 400
        
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': '선택된 파일이 없습니다.'}), 400
        
    original_filename = file.filename
    ext = os.path.splitext(original_filename)[1].lower()
    
    # Block dangerous executables
    disallowed_exts = {'.exe', '.bat', '.cmd', '.sh', '.vbs', '.msi', '.ps1'}
    if ext in disallowed_exts:
        return jsonify({'success': False, 'message': '보안상 실행 파일(.exe, .bat 등)은 업로드할 수 없습니다.'}), 400

    # Generate unique filename
    unique_prefix = uuid.uuid4().hex[:12]
    safe_name = secure_filename(original_filename)
    if not safe_name:
        safe_name = f"file_{unique_prefix}{ext}"
    saved_filename = f"{unique_prefix}_{safe_name}"

    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, saved_filename)
    
    file.save(file_path)
    file_size = os.path.getsize(file_path)
    
    # Check if image
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
    is_image = ext in image_exts
    file_type = 'image' if is_image else 'file'
    file_url = f"/static/uploads/{saved_filename}"

    return jsonify({
        'success': True,
        'file_url': file_url,
        'saved_filename': saved_filename,
        'file_name': original_filename,
        'file_size': file_size,
        'file_type': file_type
    })

@chat_bp.route('/api/download/<filename>')
def download_file(filename):
    """Download uploaded file as attachment."""
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    download_name = request.args.get('name', filename)
    return send_from_directory(upload_dir, filename, as_attachment=True, download_name=download_name)

@chat_bp.route('/api/messages/clear', methods=['POST'])
def clear_all_messages_api():
    """Delete all chat messages from the database."""
    try:
        deleted_count = db.session.query(Message).delete()
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'총 {deleted_count}건의 대화 내용이 모두 삭제되었습니다.',
            'count': deleted_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500




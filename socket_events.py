from flask import request
from flask_socketio import emit, disconnect
from datetime import datetime
from models import db, User, Message, Notice
from user_manager import (
    get_client_ip, 
    get_or_create_user, 
    active_users, 
    sid_to_ip, 
    get_active_users_list
)

current_screen_sharer = None

def register_socket_events(socketio):

    @socketio.on('connect')
    def handle_connect():
        ip = get_client_ip()
        
        # IP based single login enforcement: check if already connected
        if ip in active_users and active_users[ip].get('sid') != request.sid:
            raise ConnectionRefusedError(f'이미 해당 IP({ip})로 접속 중인 다른 채팅 창이 있습니다. 하나의 접속만 허용됩니다.')

        user = get_or_create_user(ip)
        user.is_online = True
        db.session.commit()

        # Save session
        active_users[ip] = {
            'sid': request.sid,
            'nickname': user.nickname
        }
        sid_to_ip[request.sid] = ip

        # Broadcast system notification & updated user list
        emit('system_message', {
            'content': f"[{user.nickname}] 님이 입장하셨습니다.",
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

        emit('user_list_update', get_active_users_list(), broadcast=True)

        # Notify existing screen share if active
        global current_screen_sharer
        if current_screen_sharer:
            emit('screen_share_started', current_screen_sharer)

    @socketio.on('disconnect')
    def handle_disconnect():
        global current_screen_sharer
        sid = request.sid
        ip = sid_to_ip.get(sid)

        # Handle screen share termination if sharer disconnects
        if current_screen_sharer and current_screen_sharer.get('sid') == sid:
            sharer_name = current_screen_sharer.get('nickname', '')
            current_screen_sharer = None
            emit('screen_share_stopped', {}, broadcast=True)
            emit('system_message', {
                'content': f"[{sharer_name}] 님이 접속을 종료하여 화면 공유가 중단되었습니다.",
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, broadcast=True)

        if ip:
            user_data = active_users.get(ip, {})
            nickname = user_data.get('nickname', ip)

            # Remove from active lists
            sid_to_ip.pop(sid, None)
            active_users.pop(ip, None)

            # Update DB status
            user = db.session.get(User, ip)
            if user:
                user.is_online = False
                db.session.commit()

            # Broadcast departure notice and user list
            emit('system_message', {
                'content': f"[{nickname}] 님이 퇴장하셨습니다.",
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, broadcast=True)

            emit('user_list_update', get_active_users_list(), broadcast=True)

    @socketio.on('send_message')
    def handle_send_message(data):
        sid = request.sid
        sender_ip = sid_to_ip.get(sid)
        if not sender_ip:
            emit('error_message', {'message': '유효하지 않은 세션입니다. 새로고침해주세요.'})
            return

        sender_data = active_users.get(sender_ip, {})
        sender_name = sender_data.get('nickname', sender_ip)

        msg_type = data.get('type', 'all')
        content = (data.get('content') or '').strip()
        file_url = data.get('file_url')
        file_name = data.get('file_name')
        file_size = data.get('file_size')
        file_type = data.get('file_type')

        if not content and not file_url:
            emit('error_message', {'message': '메시지 내용 또는 첨부 파일을 입력해주세요.'})
            return

        now = datetime.now()

        if msg_type == 'notice':
            # Save notice and broadcast
            notice = Notice(
                author_ip=sender_ip,
                author_name=sender_name,
                content=content or (f"[파일] {file_name}" if file_name else ''),
                is_active=True
            )
            db.session.add(notice)

            message = Message(
                sender_ip=sender_ip,
                sender_name=sender_name,
                msg_type='notice',
                content=content,
                file_url=file_url,
                file_name=file_name,
                file_size=file_size,
                file_type=file_type,
                created_at=now
            )
            db.session.add(message)
            db.session.commit()

            msg_payload = message.to_dict()
            notice_payload = notice.to_dict()

            emit('receive_notice', notice_payload, broadcast=True)
            emit('receive_message', msg_payload, broadcast=True)

        elif msg_type == 'dm':
            receiver_ip = data.get('receiver_ip')
            if not receiver_ip:
                emit('error_message', {'message': '귓속말 대상을 선택해주세요.'})
                return

            receiver_user = db.session.get(User, receiver_ip)
            receiver_name = receiver_user.nickname if receiver_user else receiver_ip

            message = Message(
                sender_ip=sender_ip,
                sender_name=sender_name,
                msg_type='dm',
                receiver_ip=receiver_ip,
                receiver_name=receiver_name,
                content=content,
                file_url=file_url,
                file_name=file_name,
                file_size=file_size,
                file_type=file_type,
                created_at=now
            )
            db.session.add(message)
            db.session.commit()

            msg_payload = message.to_dict()

            # Send to sender
            emit('receive_message', msg_payload)

            # Send to receiver if online and different from sender
            if receiver_ip in active_users and receiver_ip != sender_ip:
                target_sid = active_users[receiver_ip]['sid']
                emit('receive_message', msg_payload, to=target_sid)

        else:  # 'all'
            message = Message(
                sender_ip=sender_ip,
                sender_name=sender_name,
                msg_type='all',
                content=content,
                file_url=file_url,
                file_name=file_name,
                file_size=file_size,
                file_type=file_type,
                created_at=now
            )
            db.session.add(message)
            db.session.commit()

            msg_payload = message.to_dict()
            emit('receive_message', msg_payload, broadcast=True)

    @socketio.on('change_nickname')
    def handle_change_nickname(data):
        sid = request.sid
        ip = sid_to_ip.get(sid)
        if not ip:
            emit('error_message', {'message': '유효하지 않은 세션입니다.'})
            return

        new_name = (data.get('nickname') or '').strip()
        if not new_name:
            emit('error_message', {'message': '닉네임을 입력해주세요.'})
            return
        if len(new_name) > 30:
            emit('error_message', {'message': '닉네임은 30자 이하여야 합니다.'})
            return

        user = db.session.get(User, ip)
        if not user:
            user = get_or_create_user(ip)

        old_name = user.nickname
        user.nickname = new_name
        db.session.commit()

        if ip in active_users:
            active_users[ip]['nickname'] = new_name

        emit('nickname_changed', {
            'ip': ip,
            'old_nickname': old_name,
            'new_nickname': new_name
        }, broadcast=True)

        emit('system_message', {
            'content': f"[{old_name}] 님이 닉네임을 [{new_name}] (으)로 변경하였습니다.",
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

        emit('user_list_update', get_active_users_list(), broadcast=True)

    @socketio.on('delete_notice')
    def handle_delete_notice(data=None):
        sid = request.sid
        ip = sid_to_ip.get(sid)
        if not ip:
            emit('error_message', {'message': '유효하지 않은 세션입니다.'})
            return

        user_data = active_users.get(ip, {})
        nickname = user_data.get('nickname', ip)

        notice_id = (data or {}).get('notice_id')
        if notice_id:
            notice = db.session.get(Notice, notice_id)
            if notice:
                notice.is_active = False
                db.session.commit()
        else:
            Notice.query.filter_by(is_active=True).update({'is_active': False})
            db.session.commit()

        # Broadcast notice removal to all clients
        emit('notice_deleted', {
            'remover_name': nickname,
            'notice_id': notice_id
        }, broadcast=True)

        emit('system_message', {
            'content': f"[{nickname}] 님이 상단 공지사항을 삭제하였습니다.",
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

    @socketio.on('start_screen_share')
    def handle_start_screen_share():
        global current_screen_sharer
        sid = request.sid
        ip = sid_to_ip.get(sid)
        if not ip:
            emit('error_message', {'message': '유효하지 않은 세션입니다.'})
            return

        if current_screen_sharer and current_screen_sharer.get('sid') != sid:
            emit('error_message', {
                'message': f"현재 [{current_screen_sharer.get('nickname')}] 님이 이미 화면을 공유 중입니다."
            })
            return

        user_data = active_users.get(ip, {})
        nickname = user_data.get('nickname', ip)

        current_screen_sharer = {
            'sid': sid,
            'ip': ip,
            'nickname': nickname
        }

        # Broadcast screen sharing start
        emit('screen_share_started', current_screen_sharer, broadcast=True)

        emit('system_message', {
            'content': f"[{nickname}] 님이 화면 공유를 시작하였습니다.",
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

    @socketio.on('screen_signal')
    def handle_screen_signal(data):
        target_sid = data.get('target_sid')
        signal = data.get('signal')
        if target_sid:
            emit('screen_signal', {
                'from_sid': request.sid,
                'signal': signal
            }, to=target_sid)

    @socketio.on('stop_screen_share')
    def handle_stop_screen_share():
        global current_screen_sharer
        sid = request.sid
        if current_screen_sharer and current_screen_sharer.get('sid') == sid:
            sharer_name = current_screen_sharer.get('nickname', '')
            current_screen_sharer = None
            emit('screen_share_stopped', {}, broadcast=True)

            emit('system_message', {
                'content': f"[{sharer_name}] 님이 화면 공유를 종료하였습니다.",
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, broadcast=True)

    @socketio.on('clear_all_messages')
    def handle_clear_all_messages():
        sid = request.sid
        ip = sid_to_ip.get(sid)
        if not ip:
            emit('error_message', {'message': '유효하지 않은 세션입니다.'})
            return

        user_data = active_users.get(ip, {})
        nickname = user_data.get('nickname', ip)

        try:
            db.session.query(Message).delete()
            db.session.commit()

            # Broadcast chat cleared event to all clients
            emit('chat_cleared', {}, broadcast=True)

            emit('system_message', {
                'content': f"[{nickname}] 님이 현재 대화 내용을 모두 삭제(초기화)하였습니다.",
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, broadcast=True)
        except Exception as e:
            db.session.rollback()
            emit('error_message', {'message': f'대화 삭제 중 오류가 발생했습니다: {str(e)}'})

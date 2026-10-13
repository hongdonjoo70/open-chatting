from app import app, socketio
from models import db, User, Message, Notice

def run_tests():
    client = app.test_client()

    print("--- 1. Testing GET / ---")
    res = client.get('/', headers={'X-Forwarded-For': '192.168.1.100'})
    assert res.status_code == 200
    assert '192.168.1.100' in res.get_data(as_text=True)
    print("GET / passed!")

    print("--- 2. Testing POST /enter ---")
    res = client.post('/enter', headers={'X-Forwarded-For': '192.168.1.100'}, follow_redirects=False)
    assert res.status_code == 302
    assert '/chat' in res.headers['Location']
    print("POST /enter passed!")

    print("--- 3. Testing GET /chat ---")
    res = client.get('/chat', headers={'X-Forwarded-For': '192.168.1.100'})
    assert res.status_code == 200
    assert '192.168.1.100' in res.get_data(as_text=True)
    print("GET /chat passed!")

    print("--- 4. Testing POST /api/nickname ---")
    res = client.post('/api/nickname', 
                       json={'nickname': '테스트유저1'}, 
                       headers={'X-Forwarded-For': '192.168.1.100'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['new_nickname'] == '테스트유저1'
    print("POST /api/nickname passed!")

    # Verify nickname persisted in DB
    with app.app_context():
        user = db.session.get(User, '192.168.1.100')
        assert user is not None
        assert user.nickname == '테스트유저1'
        print("User persistence verified in DB:", user.nickname)

    print("--- 5. Testing SocketIO Events ---")
    socket_client1 = socketio.test_client(app, headers={'X-Forwarded-For': '192.168.1.100'})
    assert socket_client1.is_connected()
    received = socket_client1.get_received()
    print("Socket 1 connected, events received:", len(received))

    # Send 'all' message
    socket_client1.emit('send_message', {'type': 'all', 'content': '안녕하세요 모두!'})
    received = socket_client1.get_received()
    assert any(ev['name'] == 'receive_message' for ev in received)
    print("Socket 1 broadcast sent and received!")

    # Connect Socket 2 from another IP
    socket_client2 = socketio.test_client(app, headers={'X-Forwarded-For': '192.168.1.101'})
    assert socket_client2.is_connected()
    print("Socket 2 connected from 192.168.1.101!")

    # Send Notice message from Socket 1
    socket_client1.emit('send_message', {'type': 'notice', 'content': '필독: 오늘 18시 서버 점검 안내'})
    rec2 = socket_client2.get_received()
    assert any(ev['name'] == 'receive_notice' for ev in rec2)
    assert any(ev['name'] == 'receive_message' for ev in rec2)
    print("Socket 1 notice broadcast successfully received by Socket 2!")

    # Send DM from Socket 1 to Socket 2
    socket_client1.emit('send_message', {
        'type': 'dm', 
        'receiver_ip': '192.168.1.101', 
        'content': '101님 안녕하세요 비밀 메시지입니다.'
    })
    rec1 = socket_client1.get_received()
    rec2 = socket_client2.get_received()
    assert any(ev['name'] == 'receive_message' and ev['args'][0]['msg_type'] == 'dm' for ev in rec1)
    assert any(ev['name'] == 'receive_message' and ev['args'][0]['msg_type'] == 'dm' for ev in rec2)
    print("Direct message (DM) between 100 and 101 verified!")

    print("--- 6. Testing GET /api/search ---")
    res = client.get('/api/search?keyword=서버 점검', headers={'X-Forwarded-For': '192.168.1.100'})
    assert res.status_code == 200
    search_data = res.get_json()
    assert search_data['count'] >= 1
    assert '서버 점검' in search_data['results'][0]['content']
    print("Search API verified! Found count:", search_data['count'])

    # Test duplicate connection from same IP
    print("--- 7. Testing duplicate connection prevention for same IP ---")
    socket_client_dup = socketio.test_client(app, headers={'X-Forwarded-For': '192.168.1.100'})
    assert not socket_client_dup.is_connected()
    print("Duplicate IP connection rejected properly! is_connected is False!")

    # Test Notice deletion via SocketIO
    print("--- 8. Testing Notice Deletion ---")
    socket_client1.emit('delete_notice', {})
    rec1_del = socket_client1.get_received()
    rec2_del = socket_client2.get_received()
    assert any(ev['name'] == 'notice_deleted' for ev in rec1_del)
    assert any(ev['name'] == 'notice_deleted' for ev in rec2_del)
    print("Notice deletion broadcast received by all clients!")

    # Verify notice is deactivated in DB
    with app.app_context():
        active_notice = Notice.query.filter_by(is_active=True).first()
        assert active_notice is None
        print("Notice deactivation verified in DB!")

    # Test Multi-line message
    print("--- 9. Testing Multi-line Message ---")
    multiline_content = "첫 번째 줄\n두 번째 줄\n세 번째 줄"
    socket_client1.emit('send_message', {'type': 'all', 'content': multiline_content})
    rec_multi = socket_client1.get_received()
    assert any(ev['name'] == 'receive_message' and ev['args'][0]['content'] == multiline_content for ev in rec_multi)
    print("Multi-line message transmitted successfully!")

    # Test File Upload and Download
    print("--- 10. Testing File Upload and Download ---")
    import io
    test_file_content = b"Hello, this is a test chat file attachment content!"
    data = {
        'file': (io.BytesIO(test_file_content), 'test_document.txt')
    }
    upload_res = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert upload_res.status_code == 200
    upload_json = upload_res.get_json()
    assert upload_json['success'] is True
    assert upload_json['file_name'] == 'test_document.txt'
    saved_name = upload_json['saved_filename']
    print("File uploaded successfully! URL:", upload_json['file_url'])

    # Test file download
    dl_res = client.get(f"/api/download/{saved_name}?name=test_document.txt")
    assert dl_res.status_code == 200
    assert dl_res.data == test_file_content
    print("File downloaded successfully with matching binary content!")

    # Test sending message with attached file
    socket_client1.emit('send_message', {
        'type': 'all',
        'content': '첨부 파일을 확인해주세요.',
        'file_url': upload_json['file_url'],
        'file_name': upload_json['file_name'],
        'file_size': upload_json['file_size'],
        'file_type': upload_json['file_type']
    })
    rec_file_msg = socket_client1.get_received()
    assert any(ev['name'] == 'receive_message' and ev['args'][0].get('file_name') == 'test_document.txt' for ev in rec_file_msg)
    print("File attached message broadcast verified!")

    # Test Screen Sharing Signaling
    print("--- 11. Testing Screen Sharing Signaling ---")
    socket_client1.emit('start_screen_share')
    rec_ss1 = socket_client1.get_received()
    rec_ss2 = socket_client2.get_received()
    assert any(ev['name'] == 'screen_share_started' for ev in rec_ss1)
    assert any(ev['name'] == 'screen_share_started' for ev in rec_ss2)
    print("start_screen_share broadcast verified!")

    # Test screen signaling (WebRTC Offer/Answer routing)
    start_ev = [ev for ev in rec_ss1 if ev['name'] == 'screen_share_started'][0]
    sharer_sid = start_ev['args'][0]['sid']
    socket_client2.emit('screen_signal', {
        'target_sid': sharer_sid,
        'signal': {'type': 'viewer_ready'}
    })
    rec_sig1 = socket_client1.get_received()
    assert any(ev['name'] == 'screen_signal' and ev['args'][0]['signal']['type'] == 'viewer_ready' for ev in rec_sig1)
    print("screen_signal routing verified!")

    # Test stop screen sharing
    socket_client1.emit('stop_screen_share')
    rec_stop1 = socket_client1.get_received()
    rec_stop2 = socket_client2.get_received()
    assert any(ev['name'] == 'screen_share_stopped' for ev in rec_stop1)
    assert any(ev['name'] == 'screen_share_stopped' for ev in rec_stop2)
    print("stop_screen_share broadcast verified!")

    # Test Clear all messages via SocketIO
    print("--- 12. Testing Clear All Messages ---")
    socket_client1.emit('clear_all_messages')
    rec_clear1 = socket_client1.get_received()
    rec_clear2 = socket_client2.get_received()
    assert any(ev['name'] == 'chat_cleared' for ev in rec_clear1)
    assert any(ev['name'] == 'chat_cleared' for ev in rec_clear2)
    print("chat_cleared event received by all clients!")

    # Verify messages are deleted from DB
    with app.app_context():
        remaining_messages = Message.query.count()
        assert remaining_messages == 0
        print("All messages confirmed deleted in DB! Count is 0")

    # Disconnect sockets
    socket_client1.disconnect()
    socket_client2.disconnect()
    print("Sockets disconnected successfully!")

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == '__main__':
    run_tests()

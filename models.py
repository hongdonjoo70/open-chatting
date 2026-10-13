from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    ip_address = db.Column(db.String(64), primary_key=True)
    nickname = db.Column(db.String(64), nullable=False)
    is_online = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'ip_address': self.ip_address,
            'nickname': self.nickname,
            'is_online': self.is_online
        }

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_ip = db.Column(db.String(64), nullable=False)
    sender_name = db.Column(db.String(64), nullable=False)
    msg_type = db.Column(db.String(20), nullable=False, default='all')  # 'all', 'notice', 'dm'
    receiver_ip = db.Column(db.String(64), nullable=True)
    receiver_name = db.Column(db.String(64), nullable=True)
    content = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(256), nullable=True)
    file_name = db.Column(db.String(256), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    file_type = db.Column(db.String(64), nullable=True)  # 'image', 'file'
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'sender_ip': self.sender_ip,
            'sender_name': self.sender_name,
            'msg_type': self.msg_type,
            'receiver_ip': self.receiver_ip,
            'receiver_name': self.receiver_name,
            'content': self.content or '',
            'file_url': self.file_url,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Notice(db.Model):
    __tablename__ = 'notices'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    author_ip = db.Column(db.String(64), nullable=False)
    author_name = db.Column(db.String(64), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'author_ip': self.author_ip,
            'author_name': self.author_name,
            'content': self.content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


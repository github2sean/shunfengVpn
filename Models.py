from peewee import Model, UUIDField, CharField, DateTimeField, SmallIntegerField, TextField
import uuid
from DB import db, open_close
from datetime import datetime
from urllib.parse import unquote


class Vless(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    blog_url = CharField()
    title = CharField()
    file_id = CharField()
    create_time = DateTimeField(default=datetime.now)
    vpn_link = CharField(unique=True)
    content = TextField()
    type = SmallIntegerField()
    file_type = CharField(max_length=5)
    alist_url = CharField()
    is_ping = SmallIntegerField(default=0)
    ping_time = DateTimeField
    ping_result = SmallIntegerField()
    ping_delay = CharField(default='-1ms')

    class Meta:
        database = db  # 指定数据库连接

    @open_close
    def create_by_vless(self, vpn_link, file_name, file_type, content):
        try:
            url, title, file_id = file_name.split('_A_')
            self.create(vpn_link=vpn_link,
                        blog_url=unquote(url),
                        title=title,
                        file_id=file_id.split('.')[0],
                        type=file_type,
                        file_type=file_id.split('.')[1],
                        content=content
                        )
        except Exception as e:
            print(e)

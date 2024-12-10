from peewee import Model, MySQLDatabase
from functools import wraps
import Models
db = MySQLDatabase(
    database='shunfengvpn',  # 数据库名称
    user='root',  # 数据库用户名
    password='Root!123',  # 数据库密码
    host='localhost',  # 数据库主机地址
    port=3306,  # 数据库端口，默认为 3306
    autorollback=True
)


def init_db():
    # 配置数据库连接参数
    return db


def open_close(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        db.connect()
        try:
            return func(*args, **kwargs)
        finally:
            db.close()

    return wrapper


# 自动识别所有模型并创建表的函数
@open_close
def initialize_database():
    models = Model.__subclasses__()  # 获取所有继承自 BaseModel 的子类
    db.create_tables(models, safe=True)  # 创建所有模型对应的表
    print(f"\n已有{len(models)}个表已经创建成功！")


# 主函数
if __name__ == '__main__':
    initialize_database()

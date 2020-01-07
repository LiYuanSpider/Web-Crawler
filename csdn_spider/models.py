from peewee import *


# 建立数据库连接
db = MySQLDatabase('spider', host='127.0.0.1', port=3306, user='root', password='root')

# 创建模型基类，对应数据库表
class BaseModel(Model):
    class Meta:
        database = db

'''
设计数据表的时候需要注意的点：
    1、char类型,尽量设置MAX(最大长度)
    2、对于无法确定最大长度的,要采用TextField类型
    3、设计表的时候，采集到的数据首先需要先做格式化处理 
    4、default和null=True
    5、主键无法设置int以外的类型(可能是版本问题)
'''

# 帖子问题
class Topic(BaseModel):
    # 帖子名称
    title = CharField()
    # 帖子内容
    content = TextField(default="")
    # 帖子id
    id = IntegerField(primary_key=True)
    # 用户id
    author_id = CharField()
    # 用户名称
    author = CharField()
    # 创建时间
    create_time = DateTimeField()
    # 回复数量
    answer_nums = IntegerField(default=0)
    # 查看数量
    click_nums = IntegerField(default=0)
    # 点赞数量
    praised_nums = IntegerField(default=0)
    # 结帖率
    jtl = FloatField(default=0.0)
    # 赏分
    score = IntegerField(default=0)
    # 状态
    status = CharField()
    # 最后回复时间
    last_answer_time = DateTimeField()

# 帖子内容
class Answer(BaseModel):
    # 问题id
    topic_id = IntegerField()
    # 作者
    author = CharField()
    # 帖子内容
    content = TextField(default="")
    # 创建时间
    create_time = DateTimeField()
    # 点赞数
    parised_nums = IntegerField(default=0)

# 用户信息
class Author(BaseModel):
    # 用户名称
    name = CharField()
    # 用户id
    id = CharField()
    # 访问数
    click_nums = IntegerField(default=0)
    # 原创数
    original_nums = IntegerField(default=0)
    # 转发数
    forward_nums = IntegerField(default=0)
    # 排名
    rate = CharField(default=-1)
    # 评论数
    answer_nums = IntegerField(default=0)
    # 获赞数
    praised_nums = IntegerField(default=0)
    # 描述
    desc = TextField(null=True)
    # 行业
    industry = CharField(null=True)
    # 地址信息
    location = CharField(null=True)
    # 粉丝数
    follower_nums = IntegerField(default=0)
    # 关注数
    following_nums = IntegerField(default=0)

if __name__ == '__main__':
    # 创建三张表
    db.create_tables([Topic, Answer, Author])




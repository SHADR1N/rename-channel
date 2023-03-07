import peewee

database = peewee.SqliteDatabase("db")


class BaseModel(peewee.Model):
    class Meta:
        database = database


class User(BaseModel):
    role = peewee.TextField(default="any")
    uid = peewee.IntegerField()
    lang = peewee.TextField(default="en")


class BotAndAccount(BaseModel):
    uid = peewee.IntegerField()
    token = peewee.TextField(null=True)
    url = peewee.TextField(null=True)
    phone = peewee.TextField()
    delay_before_rename = peewee.IntegerField(default=60)
    status = peewee.BooleanField(default=False)
    proxy = peewee.TextField(null=True)
    type_proxy = peewee.TextField(null=True)
    password = peewee.TextField(null=True)
    # uid_channel = peewee.TextField(null=True)
    # open_channel = peewee.BooleanField(default=True)


database.create_tables([User, BotAndAccount])

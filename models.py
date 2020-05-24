import peewee

from config import basefile

base = peewee.SqliteDatabase(basefile)

class BaseModel(peewee.Model):
	class Meta:
		database = base


class User(BaseModel):
    chat_id = peewee.IntegerField(unique=True)
    nick = peewee.CharField(unique=True, max_length=25)

    def __str__(self):
    	return f'{self.id} #{self.chat_id} - {self.nick}'


class Sticker(BaseModel):
	sticker = peewee.CharField()
	stick_uniq = peewee.CharField(unique=True)
	name = peewee.CharField(max_length=30)
	author = peewee.ForeignKeyField(User, backref='stickers')

	def __str__(self):
		return f'{self.id} {self.name}'


base.connect()
base.create_tables([User, Sticker])
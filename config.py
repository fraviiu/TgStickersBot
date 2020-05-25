from os import environ


delay = 30 # столько секунд займет 1 действие

# файл базы данных
basefile = 'base.db'

logsfile = 'botlogs.log'

# токен бота из переменной окруженья
token = environ['TOKEN']
# сыллка на прокси
try:
	proxy_url = environ['PROXY']
except KeyError:
	proxy_url = None
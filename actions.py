import time
import asyncio

from models import User
import config

# тут задачи ежи
async def main():
	while True:
		start = time.monotonic()
		User.update({User.score: User.score + 1}).execute()
		if (end := time.monotonic() - start) > config.delay: 
			end = config.delay
		await asyncio.sleep(config.delay - end)

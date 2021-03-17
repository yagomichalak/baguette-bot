import aiomysql
import asyncio
import os
from typing import Any

loop = asyncio.get_event_loop()

async def the_database() -> Any:

	pool = await aiomysql.create_pool(
		host=os.getenv('DB_HOST'),
		user=os.getenv('DB_USER'),
		password=os.getenv('DB_PASSWORD'),
		db=os.getenv('DB_NAME'), 
		loop=loop
	)

	db = await pool.acquire()
	mycursor = await db.cursor()
	return mycursor, db


if __name__ == '__main__':
	pass
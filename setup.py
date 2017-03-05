from setuptools import setup

setup(
        name="schedulerbot",
        version="0.1",
        description="A simple Discord bot that allows everyone on a server to create scheduled gaming events. This bot will help gamers with scheduling group gaming sessions at certain times.",
	url="https://github.com/dalisaydavid/SchedulerBot",
        author="David Dalisay",
        author_email="dalisay.david3@gmail.com",
        license="GNU GPL",
        packages=["schedulerbot"],
        install_requires=[
		"asyncio",
        "discord.py",
		"tinydb"
		], # These are dependencies!
        zip_safe=False
)

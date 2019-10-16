import discord
from discord.ext import commands
import asyncio
from song_download import SongDL
import functools

TOKEN = "NjMzODM5MDg1NTY3NDc1NzY2.XaZyvw.MI457hyrMPvd4vypJA32P1Sb_LU" # Give your Discord Access Token here
client = commands.Bot(command_prefix = 'm/')

startup_extensions = ["Rythm2"]

if __name__ == '__main__':
	for extension in startup_extensions:
		client.load_extension(extension)

@client.event
async def on_ready():
	print("Bot online.")

@client.command(pass_context = True)
async def download(ctx, *songname):
	songname = ' '.join(list(songname))
	await client.say("**Searching** and **Downloading** :mag_right: `{}`\nPlease wait as we **upload** the song here!".format(songname))
	ob = SongDL(songname)
	song_data = await client.loop.run_in_executor(None, ob.main)
	import os
	size = os.path.getsize(song_data['filename'])
	if size/(1024**2) <= 8.00 :
		await client.send_file(ctx.message.channel, song_data['filename'], filename = song_data['filename'], content = "<@{}>, here's your song!".format(ctx.message.author.id))
	elif song_data['duration'] >= 10*60:
		await client.say("**Song is greater than 10 minutes, skipping upload!**")
	else:
		await client.say("**Discord doesn't support uploading files of more than 8 mb.**")
	os.remove(song_data['filename'])
	del os
	del ob

client.run(TOKEN)

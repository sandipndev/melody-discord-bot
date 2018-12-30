# Dependencies needed: 
#  - youtube_dl
#  - PyNaCl
#  - opus (or libopus)

import time
import sys
import traceback
import discord
from discord.ext import commands
import asyncio
import youtube_dl
if not discord.opus.is_loaded():
	# The 'opus' library needs to be loaded in order to do voice stuffs on Discord.
	# If this part of the program doesn't run properly, make sure you have 'opus.dll' in Windows or 'libopus' installed if on Linux.
	# If still you get issues here, replace 'opus' with the directory location of 'opus' in the line below.
	discord.opus.load_opus('opus')

#Files used in this program
from song_object import Song
from voice_client import VoiceClient

def __init__(self, client):
	"""This code will be called with client as it's an extension."""
	self.client = client

#Variables
music_logo_url = "https://i.pinimg.com/236x/3f/ba/e2/3fbae296ca6f1237eb77eedfb1fb1e3f--edm-logo-logo-dj.jpg"

# Functions that will be used later on here
def hh_mm_ss(time_in_seconds):
	"""Retrns time_in_seconds to hh mm ss format in a tuple (h, m ,s)"""
	minute, sec = divmod(time_in_seconds, 60)
	hour = 0
	if minute > 60:
		# Has hours
		hour, minute = divmod(minute, 60)
	return (hour, minute, sec)

def timeline(current_s, complete_s):
	"""Returns timeline"""
	#30 charactered
	pointer = "🔘"
	rest = "▬"
	timeratio = current_s/complete_s
	wherepointeerwillbe = int(timeratio*30)
	tl = ""
	for x in range(0,31):
		if x==wherepointeerwillbe:
			tl += pointer
		else:
			tl += rest
	return tl

def double_dig(digit):
	if digit<10:
		return "0" + str(digit)
	else:
		return str(digit)

def emb(desc):
	embed = discord.Embed()
	embed.color = 3553598
	embed.description = desc
	return embed

def time_tuple_to_s(time_tuple):
	if len(time_tuple) == 2:
		h = 0
		m = time_tuple[0]
		s = time_tuple[1]
	else:
		h = time_tuple[0]
		m = time_tuple[1]
		s = time_tuple[2]
	return (h*3600 + m*60 + s)

def validate_time(time_string):
	"""Check dd:dd:dd or dd:dd"""
	time_string = time_string.strip()
	count_colon = 0
	all_dig_except_colon = True
	for x in time_string:
		if x == ':':
			count_colon += 1
		elif not x.isdigit():
			all_dig_except_colon = False
	if all_dig_except_colon == False:
		return (False, "NOT_ALL_DIG")
	if not (count_colon>0 and count_colon<3):
		return (False, "COLONS_DONT_MATCH")
	splitted_time = time_string.split(':')
	time_dig = []
	for d in splitted_time:
		time_dig.append(int(d))
	proper_time = True
	for x in time_dig:
		if x>=60:
			proper_time = False
	if proper_time == False:
		return (False, "TIME_INPROPER")
	return (True, tuple(time_dig))

class Rythm2:
	"""Voice Commands"""
	def __init__(self, client):
		"""Parameterized constructor.

		Parameter:
		client = Instance of bot.
		"""
		self.client = client
		self.voice_clients = {}
		self.client.remove_command('help')
		self.client.loop.create_task(self.disconnect_save_bandwith_task())
		self.client.loop.create_task(self.server_count_sync())

	async def on_command_error(self, error: Exception, ctx: commands.Context):
		"""The event triggered when an error is raised while invoking a command.
		ctx   : Context
		error : Exception"""

		if hasattr(ctx.command, 'on_error'):
			return

		ignored = (commands.UserInputError)
		error = getattr(error, 'original', error)

		if isinstance(error, ignored):
			return

		elif isinstance(error, commands.CommandNotFound):
			await self.client.send_message(ctx.message.channel, embed=emb("**Not a valid command. Use `m/help` if you need help regarding commands.**"))

		print('Ignoring exception in command {}'.format(ctx.command), file=sys.stderr)
		traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

	async def on_reaction_add(self, reaction, user):
		"""React-Work stuff"""
		try:
			npmsg = self.voice_clients[reaction.message.server.id].npmsg
			pmsg = self.voice_clients[reaction.message.server.id].pmsg
			chk = False
			if pmsg is not None:
				if (npmsg.id == reaction.message.id or pmsg.id == reaction.message.id) and not (user is reaction.message.server.me):
					if reaction.emoji in ["🔈", "🔊"]:
						return
					await self.voice_clients[reaction.message.server.id].reac_do(reaction.emoji, user)
					chk = True
			else:
				if (npmsg.id == reaction.message.id) and not (user is reaction.message.server.me):
					if reaction.emoji in ["🔈", "🔊"]:
						if self.check_dj(user):
							await self.voice_clients[reaction.message.server.id].reac_do(reaction.emoji)
						else:
							await self.client.send_message(user, embed = emb("**You are not authorized to use volumes settings in {} server.**".format(reaction.message.server.name)))
						return
					await self.voice_clients[reaction.message.server.id].reac_do(reaction.emoji, user)
					chk = True

			if chk == True:
				if reaction.emoji == "♥" and self.voice_clients[reaction.message.server.id].current_song_obj is not None:
					song_url = self.voice_clients[reaction.message.server.id].current_song_obj.songinfo['webpage_url']
					sname = self.voice_clients[reaction.message.server.id].current_song_obj.songname
					import json
					with open("favourites.json", "r", encoding = "utf-8") as fav:
						try:
							fav_dict = json.load(fav)
						except json.decoder.JSONDecodeError:
							fav_dict = {}

					# Check if the user already has a favourites
					if user.id in fav_dict.keys():
						# He/she indeed has already a favourites list
						his_list = fav_dict[user.id]
						if [sname, song_url] in his_list:
							await self.client.send_message(user, embed = emb(":ballot_box_with_check: `{}` **- Already in your favourites!** :hearts:".format(sname.title())))
							return
						else:
							fav_dict[user.id].append([sname, song_url])
					else:
						# New key needs to be created
						fav_dict[user.id] = []
						fav_dict[user.id].append([sname, song_url])

					with open("favourites.json", "w", encoding = "utf-8") as fav:
						json.dump(fav_dict, fav, ensure_ascii = False)

					await self.client.send_message(user, embed = emb(":ballot_box_with_check: `{}` **- Added to favourites at position** `{}` **!** :hearts:".format(sname.title(), len(his_list))))
		except:
			pass

	async def on_reaction_remove(self, reaction, user):
		"""React-Work stuff"""
		try:
			allow = ["🔂", "🔀", "🔈", "🔊"]
			npmsg = self.voice_clients[reaction.message.server.id].npmsg
			if (npmsg.id == reaction.message.id) and not (user is reaction.message.server.me) and reaction.emoji in allow:
				if reaction.emoji in ["🔈", "🔊"]:
					pass
				else:
					await self.voice_clients[reaction.message.server.id].reac_do(reaction.emoji)
		except:
			pass

	async def disconnect_save_bandwith_task(self):
		"""To disconnect when voice client's should_disconnect flag is true"""
		await self.client.wait_until_ready()
		# This operation will be uninformed
		while True:
			for v in self.voice_clients.keys():
				flag = self.voice_clients[v].should_disconnect
				if flag == True:
					# It must disconnect
					#Disconnecting Voice Client
					await self.voice_clients[v].vc.disconnect()
					#Delete voice client from self.voice_clients
					del self.voice_clients[v]
					break

			# So that everything is okay-ly working
			await asyncio.sleep(2)

	async def server_count_sync(self):
		"""To sync server count, for accurate server-voice clients"""
		await self.client.wait_until_ready()
		while True:
			server_ids = []
			for s in self.client.servers:
				server_ids.append(s.id)
			for vc_key in self.voice_clients.keys():
				if vc_key not in server_ids:
					print("Deleting.")
					await self.voice_clients[vc_key].vc.disconnect()
					del self.voice_clients[vc_key]
					break
			await asyncio.sleep(1)

	async def server_specific_command(self, ctx):
		"""To inform user that this command is server specific"""
		if ctx.message.server is None:
			# Private message
			await self.client.send_message(ctx.message.author, embed = emb("**This command can only be called from a Server!** :poop:"))
			return False
		else:
			return

	def channel_check(self, ch1, ch2):
		# ch1 - discord.Channel user must text into, ch2 - discord.Channel user texted into
		if ch1 is ch2:
			return (True, None)
		else:
			return (False, ch1.id)

	def get_channel_zipperjson(self, sid):
		import json
		with open("zipper.json", "r") as z:
			try:
				zipp = json.load(z)
			except json.decoder.JSONDecodeError:
				zipp = {}
		if sid in zipp.keys():
			return zipp[sid]
		else:
			return

	def check_dj(self, mem):
		for x in mem.roles:
			if x.name.lower() == "dj":
				return True
		return False

	async def author_needs_to_be_in_same_vc(self, vc1, vc2):
		if vc1 is vc2:
			return
		else:
			await self.client.say(embed = emb("**You must be in the same voice channel as me to use this command.**"))
			return False

	@commands.command(pass_context = True, aliases = ['summon'])
	async def join(self, ctx):
		"""Joins the voice channel user is in."""
		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		try:
			if(not ctx.message.server.id in self.voice_clients.keys()):
				#There is no voice client of the server

				chid = self.get_channel_zipperjson(ctx.message.server.id)
				if chid is None:
					chid = ctx.message.channel.id
				ch = self.client.get_channel(chid)
				if ch is None:
					# The channel no longer exists
					pass
				else:
					# Channel check
					aa = self.channel_check(ch, ctx.message.channel)
					if aa[0] == False:
						await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
						return

				#Joining the voice channel author is in
				await self.client.join_voice_channel(ctx.message.author.voice.voice_channel)
				#Informing about the join
				await self.client.say(embed = emb("**Joined** `{}` :mega:".format(ctx.message.author.voice.voice_channel.name)))
				#Storing the voice_client
				thisvc = self.client.voice_client_in(ctx.message.server)
				#Adding the VoiceClient class with voice_client to self.voice_clients with the server id as key
				self.voice_clients[ctx.message.server.id] = VoiceClient(thisvc, self.client, ctx.message.server, ctx.message.channel)
			else:
				#There is a voice client of the server

				#Informing about the voice channel name in which the voice client is in
				await self.client.say(embed = emb("**I am already playing in** `{}` :metal:".format(self.voice_clients[ctx.message.server.id].vc.channel.name)))

		except discord.errors.InvalidArgument:
			#The user is not in any voice channel
			await self.client.say(embed = emb("<@{}>, **you are supposed to be in a voice channel before asking me in.** :baby_chick:".format(ctx.message.author.id)))

	@commands.command(pass_context = True, aliases = ['disconnect'])
	async def leave(self, ctx):
		"""Leaves the voice channel of the server"""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(ctx.message.server.id in self.voice_clients.keys()):
			#VoiceClient present

			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return

			x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
			if x is not None:
				return

			if self.check_dj(ctx.message.author) == True:
				#Disconnecting Voice Client
				await self.voice_clients[ctx.message.server.id].vc.disconnect()

				#Delete voice client from self.voice_clients
				del self.voice_clients[ctx.message.server.id]

				#Inform user
				await self.client.say(embed = emb("**Successfully disconnected**! :art:"))

			else:
				# Not DJ
				await self.client.say(embed = emb("**Only someone with a `DJ` permission can perform this command.**"))

		else:
			#VoiceClient not present

			#Inform user
			await self.client.say(embed = emb("**I am not connected!** :last_quarter_moon_with_face:"))

	@commands.command(pass_context = True, aliases = ['p'])
	async def play(self, ctx, *songname):
		"""Plays a song"""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		# First, join the voice channel user is in, or raise an error accordingly
		try:
			if(not ctx.message.server.id in self.voice_clients.keys()):
				#There is no voice client of the server

				chid = self.get_channel_zipperjson(ctx.message.server.id)
				if chid is None:
					chid = ctx.message.channel.id
				ch = self.client.get_channel(chid)

				if ch is None:
					# The channel no longer exists
					pass
				else:
					# Channel check
					aa = self.channel_check(ch, ctx.message.channel)
					if aa[0] == False:
						await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
						return

				#Joining the voice channel author is in (will cause InvalidArgument if user is not in any voice channel)
				await self.client.join_voice_channel(ctx.message.author.voice.voice_channel)
				#Storing the voice_client
				thisvc = self.client.voice_client_in(ctx.message.server)
				#Adding the VoiceClient class with voice_client to self.voice_clients with the server id as key
				self.voice_clients[ctx.message.server.id] = VoiceClient(thisvc, self.client, ctx.message.server, ctx.message.channel)
			else:
				#There is a already a voice client of the server
				pass

		except discord.errors.InvalidArgument:
			#The user is not in any voice channel
			await self.client.say(embed = emb("<@{}>, you must be in a voice channel before asking me in. :hatched_chick:".format(ctx.message.author.id)))
			#Stop execution here
			return

		x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
		if x is not None:
			return

		if len(songname) == 0:
			if self.voice_clients[ctx.message.server.id].is_playing() and self.voice_clients[ctx.message.server.id].is_paused == True:
				# Something is not playing, paused
				self.voice_clients[ctx.message.server.id].resume()
				await self.client.say(embed = emb("**Player resumed**! :arrow_forward:"))
				return
			else:
				await self.client.say(embed = emb(":x: **Mention the song to play!**"))
				return

		if self.voice_clients[ctx.message.server.id].current_song_obj is None and self.voice_clients[ctx.message.server.id].is_queue_empty() and self.voice_clients[ctx.message.server.id].first_song_getting_added != True:
			self.voice_clients[ctx.message.server.id].first_song_getting_added = True
			print("1st")

		# Checking if url or not
		url = False
		if len(songname) == 1 and (songname[0].startswith("https://www.youtube.com/watch?v=") or songname[0].startswith("www.youtube.com/watch?v=") or songname[0].startswith("https://youtu.be/")):
			url = True
			songname = songname[0]
		else:
			# Formatting the songname properly
			songname = ' '.join(songname)
		# Getting the song's information from Youtube
		def get_song_info(url):
			"""To get the song's information in advance."""
			# Might be blocking, so use run_in_executor
			if url == False:
				# Not an url
				ytdl_options = {
					'default_search': 'auto',
					'quiet' : True
				}
				with youtube_dl.YoutubeDL(ytdl_options) as ydl:
					info_dict = ydl.extract_info(songname, download=False) # To get information about the song
					return info_dict['entries'][0]
			else:
				#An url
				ytdl_options = {
					'quiet' : True
				}
				with youtube_dl.YoutubeDL(ytdl_options) as ydl:
					info_dict = ydl.extract_info(songname, download=False) # To get information about the song
					return info_dict
			
		try:
			#Searching prompt
			await self.client.say("**Searching** `{}` :mag_right:".format(songname))
			#Typing
			await self.client.send_typing(ctx.message.channel)
			#Actually searching, prone of error if song not found.
			songinfo = await self.client.loop.run_in_executor(None, get_song_info, url)
			if songinfo['is_live'] is not None:
				# The song is a live telecast
				await self.client.say(embed = emb("**Melody is under development for live playback.**"))
				return
			# Creating the Song object
			song_object = Song(songname, ctx.message.author, songinfo)
			# Adding the Song object to current server's queue
			if self.voice_clients[ctx.message.server.id].first_song_getting_added != True:
				print("s 5")
				await asyncio.sleep(5)
			pos = self.voice_clients[ctx.message.server.id].add_song_to_queue(song_object)
			if pos == 1 and self.voice_clients[ctx.message.server.id].current_song_obj is None:
				# This is the first song added to queue
				await self.client.say("**Playing** :notes: `{}` **- Now!**".format(songinfo['title'].strip().title()))
			else:
				# Creating added to queue embed
				embed = discord.Embed()
				embed.title = songinfo['title'].strip().title()
				embed.url = songinfo['webpage_url']
				embed.color = 12345678
				embed.set_thumbnail(url = songinfo['thumbnail'])
				embed.set_author(name = "Added to Queue", icon_url = ctx.message.author.avatar_url)
				embed.add_field(inline = True, name = "Channel", value = songinfo['uploader'].strip().title())
				hms = await self.client.loop.run_in_executor(None, hh_mm_ss, songinfo['duration'])
				hms_tuple = ("" if hms[0]==0 else (str(hms[0]) + "h "), "" if hms[1]==0 else (str(hms[1]) + "m "), "" if hms[2]==0 else (str(hms[2]) + "s "))
				embed.add_field(inline = True, name = "Duration", value = "{}{}{}".format(hms_tuple[0], hms_tuple[1], hms_tuple[2]))
				embed.add_field(inline = True, name = "Position in Queue", value = str(pos))
				if self.voice_clients[ctx.message.server.id].current_song_obj is None:
					print("wait 5 s")
					await asyncio.sleep(5)
				eta = self.voice_clients[ctx.message.server.id].eta(len(self.voice_clients[ctx.message.server.id].queue)-1)
				hms = await self.client.loop.run_in_executor(None, hh_mm_ss, eta)
				hms_tuple = ("" if hms[0]==0 else (str(hms[0]) + "h "), "" if hms[1]==0 else (str(hms[1]) + "m "), "" if hms[2]==0 else (str(hms[2]) + "s "))
				embed.add_field(inline = True, name = "ETA until playing", value = "{}{}{}".format(hms_tuple[0], hms_tuple[1], hms_tuple[2]))
				# Sending the Embed
				await self.client.say(embed = embed)
		except youtube_dl.utils.DownloadError:
			# No search results
			await self.client.send_message(ctx.message.channel , embed = emb(":x: **No results!**"))

	@commands.command(pass_context = True, aliases = ['np'])
	async def nowplaying(self, ctx):
		"""Displays the currently playing song information in embed format."""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			#There is a already a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			# Getting the song information
			current_song_info = self.voice_clients[ctx.message.server.id].current_song_info()
			paused = self.voice_clients[ctx.message.server.id].is_paused

			if current_song_info is None:
				# Nothing is playing
				await self.client.say(embed = emb("**Nothing is playing in this server.** :dolphin:"))
			else:
				# Playing somthing
				if paused != True:
					# Not paused
					embed = discord.Embed()
					embed.title = current_song_info['title'].strip().title()
					embed.url = current_song_info['webpage_url']
					embed.color = 654814
					embed.set_thumbnail(url = current_song_info['thumbnail'])
					embed.set_author(name = "Now Playing >")
					currenttime = int(self.voice_clients[ctx.message.server.id].current_playing_time())
					tline = timeline(currenttime, current_song_info['duration'])
					tsnow = hh_mm_ss(currenttime)
					tsnow = "{}{}{}".format(double_dig(tsnow[0]) + ":" if tsnow[0] != 0 else "", double_dig(tsnow[1]) + ":", double_dig(tsnow[2]))
					tstot = hh_mm_ss(current_song_info['duration'])
					tstot = "{}{}{}".format(double_dig(tstot[0]) + ":" if tstot[0] != 0 else "", double_dig(tstot[1]) + ":", double_dig(tstot[2]))
					timestamp = "{} / {}".format(tsnow, tstot)
					if self.voice_clients[ctx.message.server.id].shuffle == True or self.voice_clients[ctx.message.server.id].repeat == True:
						info = "{}{}".format(":twisted_rightwards_arrows: ON" if self.voice_clients[ctx.message.server.id].shuffle == True else "", ":repeat_one: ON" if self.voice_clients[ctx.message.server.id].repeat == True else "")
					else:
						info = ""
					embed.description = "\n`{}`\n`{}`\n{}\nRequested by `{}`".format(tline, timestamp, info, self.voice_clients[ctx.message.server.id].current_song_obj.requester.name)

					#Sending this embed
					await self.client.say(embed = embed)
				else:
					# Paused
					embed = discord.Embed()
					embed.title = current_song_info['title'].strip().title()
					embed.url = current_song_info['webpage_url']
					embed.color = 654814
					embed.set_thumbnail(url = current_song_info['thumbnail'])
					embed.set_author(name = "Now Playing [PAUSED] >")
					currenttime = int(self.voice_clients[ctx.message.server.id].current_playing_time())
					tline = timeline(currenttime, current_song_info['duration'])
					tsnow = hh_mm_ss(currenttime)
					tsnow = "{}{}{}".format(double_dig(tsnow[0]) + ":" if tsnow[0] != 0 else "", double_dig(tsnow[1]) + ":", double_dig(tsnow[2]))
					tstot = hh_mm_ss(current_song_info['duration'])
					tstot = "{}{}{}".format(double_dig(tstot[0]) + ":" if tstot[0] != 0 else "", double_dig(tstot[1]) + ":", double_dig(tstot[2]))
					timestamp = "{} / {}".format(tsnow, tstot)
					if self.voice_clients[ctx.message.server.id].shuffle == True or self.voice_clients[ctx.message.server.id].repeat == True:
						info = "{}{}".format(":twisted_rightwards_arrows: ON" if self.voice_clients[ctx.message.server.id].shuffle == True else "", ":repeat_one: ON" if self.voice_clients[ctx.message.server.id].repeat == True else "")
					else:
						info = ""
					embed.description = "\n`{}`\n`{}`\nPlayer is **PAUSED** :pause_button:\n{}\nRequested by `{}`".format(tline, timestamp, info, self.voice_clients[ctx.message.server.id].current_song_obj.requester.name)
					#Sending this embed
					await self.client.say(embed = embed)

	@commands.command(pass_context = True, aliases = ['ps'])
	async def pause(self, ctx):
		"""Pause song"""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
			if x is not None:
				return
			#There is already a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			if self.voice_clients[ctx.message.server.id].is_playing():
				# Something is playing
				self.voice_clients[ctx.message.server.id].pause()
				await self.client.say(embed = emb("**Player paused!** :pause_button:"))
			else:
				# Nothing is playing
				await self.client.say(embed = emb("**Nothing is playing in this server.** :dolphin:"))

	@commands.command(pass_context = True, aliases = ['continue'])
	async def resume(self, ctx):
		"""Pause song"""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
			if x is not None:
				return
			#There is a already a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			if self.voice_clients[ctx.message.server.id].is_playing() and self.voice_clients[ctx.message.server.id].is_paused == True:
				# Something is not playing, paused
				self.voice_clients[ctx.message.server.id].resume()
				await self.client.say(embed = emb("**Player resumed!** :arrow_forward:"))
			elif self.voice_clients[ctx.message.server.id].is_playing():
				#Player not paused
				await self.client.say(embed = emb("**I'm already playing**"))
			else:
				# Nothing is playing
				await self.client.say(embed = emb("**Nothing is playing in this server.** :dolphin:"))

	@commands.command(pass_context = True, aliases = ['r'])
	async def repeat(self, ctx):
		"""To add the songs on repeat"""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
			if x is not None:
				return
			#There is a already a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			if self.voice_clients[ctx.message.server.id].repeat == True:
				# Already on repeat
				self.voice_clients[ctx.message.server.id].repeat = False
				await self.client.say(embed = emb("**Repeat Disabled**! :arrow_heading_down:"))
			else:
				# Adding to repeat
				self.voice_clients[ctx.message.server.id].repeat = True
				await self.client.say(embed = emb("**Repeat Enabled**! :repeat_one:"))

	@commands.command(pass_context = True, aliases = ['s', 'stop'])
	async def skip(self, ctx):
		"""To add the songs on repeat"""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
			if x is not None:
				return
			#There is a already a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			if self.voice_clients[ctx.message.server.id].current_song_obj is None:
				await self.client.say(embed = emb("**Nothing in queue!** :hatching_chick:"))
			elif len(self.voice_clients[ctx.message.server.id].queue) == 0 and not self.voice_clients[ctx.message.server.id].is_playing():
				await self.client.say(embed = emb(":x: **Nothing in queue**!"))
			else:
				if self.check_dj(ctx.message.author) != True:
					resp = self.voice_clients[ctx.message.server.id].askip_ret_pass(ctx.message.author.id)
					if resp == None:
						await self.client.say(embed = emb("**The same person can't skip twice.** :x:"))
						return
					if resp == False:
						await self.client.say(embed = emb("**More {} skips needed to skip the song!**".format(str(int(0.3*self.voice_clients[ctx.message.server.id].how_many_listening() - len(self.voice_clients[ctx.message.server.id].skip_people)) + 1))))
						return
					self.voice_clients[ctx.message.server.id].skip()
					await self.client.say(embed = emb("**Skipped**! :track_next:"))
				else:
					#DJ
					self.voice_clients[ctx.message.server.id].skip()
					await self.client.say(embed = emb("**Skipped**! :track_next:"))

	@commands.command(pass_context = True, aliases = ['q'])
	async def queue(self, ctx):
		"""To display queue information"""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			#There is a already a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			#Typing
			await self.client.send_typing(ctx.message.channel)
			if self.voice_clients[ctx.message.server.id].is_queue_empty() and self.voice_clients[ctx.message.server.id].is_playing() == True:
				thissonginfo = self.voice_clients[ctx.message.server.id].current_song_info()
				thissongdedication = self.voice_clients[ctx.message.server.id].current_song_obj.dedicatedto
				tstot = hh_mm_ss(thissonginfo['duration'])
				tstot = "{}{}{}".format(double_dig(tstot[0]) + ":" if tstot[0] != 0 else "", double_dig(tstot[1]) + ":", double_dig(tstot[2]))
				if thissongdedication is None:
					np_string_info = "\n[{}]({}) | `{}` | `Requested by {}`".format(thissonginfo['title'].strip().title(), thissonginfo['webpage_url'], tstot, self.voice_clients[ctx.message.server.id].current_song_obj.requester.name)
				else:
					np_string_info = "\n[{}]({}) | `{}` | `Requested by {}` | `Secret Dedication`".format(thissonginfo['title'].strip().title(), thissonginfo['webpage_url'], tstot, self.voice_clients[ctx.message.server.id].current_song_obj.requester.name)


				etaq = self.voice_clients[ctx.message.server.id].eta(len(self.voice_clients[ctx.message.server.id].queue))
				etaq = hh_mm_ss(etaq)
				etaq = "{}{}{}".format(double_dig(etaq[0]) + ":" if etaq[0] != 0 else "", double_dig(etaq[1]) + ":", double_dig(etaq[2]))
				if self.voice_clients[ctx.message.server.id].shuffle == True or self.voice_clients[ctx.message.server.id].repeat == True:
					info = "{}{}".format(":twisted_rightwards_arrows: ON" if self.voice_clients[ctx.message.server.id].shuffle == True else "", ":repeat_one: ON" if self.voice_clients[ctx.message.server.id].repeat == True else "")
				else:
					info = ""
				embed = discord.Embed()
				embed.color = 564712
				embed.set_author(name = "Queue for {}".format(ctx.message.server.name), icon_url= music_logo_url)
				embed.description = "\n__Now Playing__:\n{}\n{}\n**ADD** more *songs* as **queue** is **Empty**!\n\n**{} songs in queue | {} to complete queue**".format(np_string_info, info, "NO", etaq)
				
				await self.client.say(embed = embed)
			elif self.voice_clients[ctx.message.server.id].is_queue_empty() and self.voice_clients[ctx.message.server.id].is_playing() != True:
				await self.client.say(embed = emb("**Nothing is playing in this server.** :dolphin:"))
			else:
				def func():
					# Could be blocking
					queue_string_info = ""
					count = 1
					for thissongobj in self.voice_clients[ctx.message.server.id].queue:
						thissongdedication = thissongobj.dedicatedto
						tstot = hh_mm_ss(thissongobj.songinfo['duration'])
						tstot = "{}{}{}".format(double_dig(tstot[0]) + ":" if tstot[0] != 0 else "", double_dig(tstot[1]) + ":", double_dig(tstot[2]))
						if thissongdedication is None:
							queue_string_info += "\n\n`{}. `[{}]({}) | `{}` | `Requested by {}`".format(count, thissongobj.songinfo['title'].strip().title(), thissongobj.songinfo['webpage_url'], tstot, thissongobj.requester.name)
						else:
							queue_string_info += "\n\n`{}. `[{}]({}) | `{}` | `Requested by {}` | `Secret Dedication`".format(count, thissongobj.songinfo['title'].strip().title(), thissongobj.songinfo['webpage_url'], tstot, thissongobj.requester.name)
						count += 1
					return queue_string_info, count

				queue_string_info, count = await self.client.loop.run_in_executor(None, func)
				thissonginfo = self.voice_clients[ctx.message.server.id].current_song_info()
				tstot = hh_mm_ss(thissonginfo['duration'])
				tstot = "{}{}{}".format(double_dig(tstot[0]) + ":" if tstot[0] != 0 else "", double_dig(tstot[1]) + ":", double_dig(tstot[2]))
				np_string_info = "\n[{}]({}) | `{}` | `Requested by {}`".format(thissonginfo['title'].strip().title(), thissonginfo['webpage_url'], tstot, self.voice_clients[ctx.message.server.id].current_song_obj.requester.name)

				etaq = self.voice_clients[ctx.message.server.id].eta(len(self.voice_clients[ctx.message.server.id].queue))
				etaq = hh_mm_ss(etaq)
				etaq = "{}{}{}".format(double_dig(etaq[0]) + ":" if etaq[0] != 0 else "", double_dig(etaq[1]) + ":", double_dig(etaq[2]))
				if self.voice_clients[ctx.message.server.id].shuffle == True or self.voice_clients[ctx.message.server.id].repeat == True:
					info = "{}{}".format(":twisted_rightwards_arrows: ON" if self.voice_clients[ctx.message.server.id].shuffle == True else "", ":repeat_one: ON" if self.voice_clients[ctx.message.server.id].repeat == True else "")
				else:
					info = ""
				embed = discord.Embed()
				embed.color = 564712
				embed.set_author(name = "Queue for {}".format(ctx.message.server.name), icon_url= music_logo_url)
				embed.description = "\n__Now Playing__:\n{}\n{}\n\n:arrow_down: __Up Next__ :arrow_down:\n{}\n\n\n**{} songs in queue | {} to complete queue**".format(np_string_info, info, queue_string_info, count-1, etaq)

				if len(embed.description) <= 2048:
					await self.client.say(embed = embed)
				else:
					# We need to split the embeds
					# First, splitting the description appropriately
					desc = []
					length = 0
					lastnextline = 0
					currentdesccounter = 0
					for x in queue_string_info:
						length += 1
						currentdesccounter += 1
						if x == '\n':
							lastnextline = length
						if currentdesccounter == 2048:
							desc.append(queue_string_info[(length - currentdesccounter):lastnextline])
							currentdesccounter = length - lastnextline

					if queue_string_info[(length - currentdesccounter):] != "":
						desc.append(queue_string_info[(length - currentdesccounter):])

					#First embed
					if self.voice_clients[ctx.message.server.id].shuffle == True or self.voice_clients[ctx.message.server.id].repeat == True:
						info = "{}{}".format(":twisted_rightwards_arrows: ON" if self.voice_clients[ctx.message.server.id].shuffle == True else "", ":repeat_one: ON" if self.voice_clients[ctx.message.server.id].repeat == True else "")
					else:
						info = ""
					embed.description = "\n__Now Playing__:\n{}\n\n{}\n**{} songs in queue | {} to complete queue**".format(np_string_info, info, count-1, etaq)
					await self.client.say(embed = embed)

					#Continuing embeds
					c = 1
					for thisdesc in desc:
						embed = discord.Embed()
						embed.color = 564712
						if c == 1:
							embed.set_author(name = "Up Next")
						embed.description = thisdesc
						c += 1
						await self.client.say(embed = embed)

	@commands.command(pass_context = True, aliases = ['rm'])
	async def remove(self, ctx, num=None):
		"""To remove num-th position song from queue"""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			#There is a already a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
			if x is not None:
				return
			if num is None:
				await self.client.say(embed = emb("**Enter the index of the song to be removed**"))
			if self.voice_clients[ctx.message.server.id].is_queue_empty():
				await self.client.say(embed = emb("**The queue seems empty!** :comet:"))
			elif num.isdigit():
				if int(num) <= len(self.voice_clients[ctx.message.server.id].queue):
					a = self.voice_clients[ctx.message.server.id].queue.pop(int(num)-1)
					await self.client.say(embed = emb("**Removed** :scissors: `{}`!".format(a.songinfo['title'].strip().title())))
				else:
					await self.client.say(embed = emb("**Enter a valid number in the range of queue indexes.** :owl:"))
			else:
				await self.client.say(embed = emb("**Please enter a numeric value, in range of queue indexes!** :1234:"))

	@commands.command(pass_context = True, aliases = ['shuf'])
	async def shuffle(self, ctx):
		"""To add the songs on repeat"""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
			if x is not None:
				return
			#There is a already a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			x = self.voice_clients[ctx.message.server.id].shuffle_state()
			await self.client.say(embed = emb(":twisted_rightwards_arrows: **{}** ".format("ON" if x==True else "OFF")))

	@commands.command(pass_context = True, aliases = ['vol'])
	async def volume(self, ctx, v=None):
		"""To add the songs on repeat"""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
			if x is not None:
				return
			#There is a already a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			if self.check_dj(ctx.message.author) == True:
				if v is None:
					await self.client.say(embed = emb("**Volume command is followed by +, - or an integer between 0-200**"))
					return
				if v == "+":
					x = self.voice_clients[ctx.message.server.id].volume * 100 + 20
					if int(x) <= 200:
						self.voice_clients[ctx.message.server.id].change_vol_zero2hundred(x)
						await self.client.say(embed = emb(":loud_sound: **{}%**".format(int(self.voice_clients[ctx.message.server.id].volume * 100))))
					else:
						self.voice_clients[ctx.message.server.id].change_vol_zero2hundred(200)
						await self.client.say(embed = emb(":loud_sound: **200 (MAX)**"))
					return
				elif v == "-":
					x = self.voice_clients[ctx.message.server.id].volume * 100 - 20
					if int(x) >= 0:
						self.voice_clients[ctx.message.server.id].change_vol_zero2hundred(x)
						await self.client.say(embed = emb(":speaker: **{}%**".format(int(self.voice_clients[ctx.message.server.id].volume * 100))))
					else:
						self.voice_clients[ctx.message.server.id].change_vol_zero2hundred(0)
						await self.client.say(embed = emb(":mute: **0 (MIN)**"))
					return
				if not v.strip().isdigit():
					await self.client.say(embed = emb("**Please enter a valid integer between 0-200**"))
					return
				v = int(v)
				if not (v>=0 and v<=200):
					await self.client.say(embed = emb("**Please enter a valid integer between 0-200**"))
					return
				v1 = int(self.voice_clients[ctx.message.server.id].volume*100)
				self.voice_clients[ctx.message.server.id].change_vol_zero2hundred(v)
				await self.client.say(embed = emb(":{}: **{}%**".format("loud_sound" if v>=v1 else "speaker", v)))
			else:
				# Not DJ
				await self.client.say(embed = emb("**Only someone with a `DJ` permission can perform this command.**"))

	@commands.command(pass_context = True, aliases = ['afav'])
	async def addfav(self, ctx, pos=None):
		"""To add currently playing song to caller's favourites."""
		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			#There is a already a voice client of the server
			if self.voice_clients[ctx.message.server.id].current_player is None:
				# Server not playing any song
				await self.client.say(embed = emb("**Nothing is playing in this server.** :dolphin:"))
			else:
				# Server playing a song
				if pos is None:
					song_url = self.voice_clients[ctx.message.server.id].current_song_obj.songinfo['webpage_url']
					sname = self.voice_clients[ctx.message.server.id].current_song_obj.songname
				elif pos.isdigit():
					if int(pos) <= len(self.voice_clients[ctx.message.server.id].queue):
						song_url = self.voice_clients[ctx.message.server.id].queue[int(pos)-1].songinfo['webpage_url']
						sname = self.voice_clients[ctx.message.server.id].queue[int(pos)-1].songname
					else:
						await self.client.say(embed = emb("**Enter a valid number in the range of queue indices**. :owl:"))
						return
				else:
					await self.client.say(embed = emb("**Please enter a numeric value, in range of queue indexes**! :1234:"))
					return

				# Do everything here
				# We need to add the song to favourites.json here
				import json
				with open("favourites.json", "r", encoding = "utf-8") as fav:
					try:
						fav_dict = json.load(fav)
					except json.decoder.JSONDecodeError:
						fav_dict = {}

				# Check if the user already has a favourites
				if ctx.message.author.id in fav_dict.keys():
					# He/she indeed has already a favourites list
					his_list = fav_dict[ctx.message.author.id]
					if [sname, song_url] in his_list:
						await self.client.say(embed = emb("`{}` **is already in your favourites**, <@{}>.".format(sname.title(), ctx.message.author.id)))
						return
					else:
						fav_dict[ctx.message.author.id].append([sname, song_url])
				else:
					# New key needs to be created
					fav_dict[ctx.message.author.id] = []
					fav_dict[ctx.message.author.id].append([sname, song_url])

				with open("favourites.json", "w", encoding = "utf-8") as fav:
					json.dump(fav_dict, fav, ensure_ascii = False)

				await self.client.say(embed = emb(":ballot_box_with_check: `{}` - **Added to your favourites at position** `{}`**!**, <@{}>!".format(sname.title(), len(his_list), ctx.message.author.id)))

	@commands.command(pass_context = True, aliases = ['sfav'])
	async def showfav(self, ctx):
		"""Show the user's favourites in his/her private message."""
		favourites = ""
		import json
		with open("favourites.json", "r", encoding = "utf-8") as fav:
			try:
				fav_dict = json.load(fav)
			except json.decoder.JSONDecodeError:
				fav_dict = {}

		# Check if the user has a favourites
		if ctx.message.author.id in fav_dict.keys():
			# He/she indeed has a favourites list
			his_list = fav_dict[ctx.message.author.id]
			c = 1
			for thissong in his_list:
				favourites += "\n`{}.` [{}]({})".format(c, thissong[0].title(), thissong[1])
				c += 1
			embed = discord.Embed()
			embed.set_author(name = "Favourite List", icon_url = music_logo_url)
			embed.description = "\n\n**{}'s FAVOURITES**\n{}".format(ctx.message.author.name.upper(), favourites)
			embed.color = 5420018

			if len(embed.description) <= 2048:
				await self.client.send_message(ctx.message.author, embed=embed)
			else:
				# We need to split the embeds
				# First, splitting the description appropriately
				desc = []
				length = 0
				lastnextline = 0
				currentdesccounter = 0
				for x in embed.description:
					length += 1
					currentdesccounter += 1
					if x == '\n':
						lastnextline = length
					if currentdesccounter == 2048:
						desc.append(embed.description[(length - currentdesccounter):lastnextline])
						currentdesccounter = length - lastnextline

				if embed.description[(length - currentdesccounter):] != "":
					desc.append(embed.description[(length - currentdesccounter):])

				# First embed
				embed.description = desc[0]
				embed.set_footer(text = "Page 1")
				await self.client.send_message(ctx.message.author, embed = embed)

				#Continuing embeds
				embed = discord.Embed()
				embed.color = 5420018
				c = 2
				for thisdesc in desc[1:]:
					embed.description = thisdesc
					embed.set_footer(text = "Page {}".format(c))
					c += 1
					await self.client.send_message(ctx.message.author, embed = embed)

			if not ctx.message.server is None:
				await self.client.say(embed = emb("<@{}>, **please check your private messages.** :dragon_face:".format(ctx.message.author.id)))

		else:
			# No favourites
			await self.client.say(embed = emb("**You don't have any favourites list**, <@{}>!".format(ctx.message.author.id)))

	@commands.command(pass_context = True, aliases = ['rfav'])
	async def removefav(self, ctx, pos=None):
		"""Remove a specific song from the user's favourites"""
		if pos is None:
			await self.client.say(embed = emb("**This command is followed by position of the song you want to remove.**"))
			return

		import json

		with open("favourites.json", "r", encoding = "utf-8") as fav:
			try:
				fav_dict = json.load(fav)
			except json.decoder.JSONDecodeError:
				fav_dict = {}

		# Check if the user has a favourites
		if ctx.message.author.id in fav_dict.keys():
			# He/she indeed has a favourites list
			if pos.isdigit():
				pos = int(pos)
				if pos<=len(fav_dict[ctx.message.author.id]) and pos>0:
					popedsong = fav_dict[ctx.message.author.id].pop(pos-1)
				else:
					await self.client.say(embed = emb("**Please enter a proper number within the range of your favourites list!**"))
					return
			else:
				await self.client.say(embed = emb("**Entered position should be a number!**"))
				return
		else:
			# No favourites
			await self.client.say(embed = emb("**You don't have any favourites list**, <@{}>!".format(ctx.message.author.id)))
			return

		if len(fav_dict[ctx.message.author.id]) == 0:
			# Nothing in his favourite list
			del fav_dict[ctx.message.author.id]

		with open("favourites.json", "w", encoding = "utf-8") as fav:
			json.dump(fav_dict, fav, ensure_ascii = False)

		await self.client.say(embed = emb(":x: `{}` - **Removed from your favourites**, <@{}>!".format(popedsong[0], ctx.message.author.id)))

	@commands.command(pass_context = True, aliases = ['pfav'])
	async def playfav(self, ctx, pos = None):
		"""Add position-ed favourite song to queue."""

		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if pos is None:
			await self.client.say(embed = emb("**This command is followed by position of the song you want to play.**"))
			return

		try:
			if(not ctx.message.server.id in self.voice_clients.keys()):
				#There is no voice client of the server

				chid = self.get_channel_zipperjson(ctx.message.server.id)
				if chid is None:
					chid = ctx.message.channel.id
				ch = self.client.get_channel(chid)

				if ch is None:
					# The channel no longer exists
					pass
				else:
					# Channel check
					aa = self.channel_check(ch, ctx.message.channel)
					if aa[0] == False:
						await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
						return

				#Joining the voice channel author is in (will cause InvalidArgument if user is not in any voice channel)
				await self.client.join_voice_channel(ctx.message.author.voice.voice_channel)
				#Storing the voice_client
				thisvc = self.client.voice_client_in(ctx.message.server)
				#Adding the VoiceClient class with voice_client to self.voice_clients with the server id as key
				self.voice_clients[ctx.message.server.id] = VoiceClient(thisvc, self.client, ctx.message.server, ctx.message.channel)
			else:
				#There is a already a voice client of the server
				pass

		except discord.errors.InvalidArgument:
			#The user is not in any voice channel
			await self.client.say(embed = emb("<@{}>, **you must be in a voice channel before asking me in.** :hatched_chick:".format(ctx.message.author.id)))
			#Stop execution here
			return

		#There is a now a voice client of the server
		import json

		with open("favourites.json", "r", encoding = "utf-8") as fav:
			try:
				fav_dict = json.load(fav)
			except json.decoder.JSONDecodeError:
				fav_dict = {}

		# Check if the user has a favourites
		if ctx.message.author.id in fav_dict.keys():
			# He/she indeed has a favourites list
			if pos.isdigit():
				pos = int(pos)
				if pos<=len(fav_dict[ctx.message.author.id]) and pos>0:
					song_to_play = fav_dict[ctx.message.author.id][pos-1]
				else:
					await self.client.say(embed = emb("**Please enter a proper number within the range of your favourites list!**"))
					return
			else:
				await self.client.say(embed = emb("**Entered position should be a number!**"))
				return
		else:
			# No favourites
			await self.client.say(embed = emb("**You don't have any favourites list**, <@{}>!".format(ctx.message.author.id)))
			return

		#Search and play
		await self.client.say("**Searching** `{}` :mag_right:".format(song_to_play[0]))
		#Typing
		await self.client.send_typing(ctx.message.channel)
		def get_song_info():
			#An url
			ytdl_options = {
				'quiet' : True
			}
			with youtube_dl.YoutubeDL(ytdl_options) as ydl:
				info_dict = ydl.extract_info(song_to_play[1], download=False) # To get information about the song
				return info_dict
		#Actually searching, prone of error if song not found.
		songinfo = await self.client.loop.run_in_executor(None, get_song_info)
		# Creating the Song object
		song_object = Song(song_to_play[0], ctx.message.author, songinfo)
		# Adding the Song object to current server's queue
		pos = self.voice_clients[ctx.message.server.id].add_song_to_queue(song_object)
		if pos == 1 and self.voice_clients[ctx.message.server.id].current_song_obj is None:
			# This is the first song added to queue
			await self.client.say("**Playing** :notes: `{}` - **Now!**".format(songinfo['title'].strip().title()))
		else:
			# Creating added to queue embed
			embed = discord.Embed()
			embed.title = songinfo['title'].strip().title()
			embed.url = songinfo['webpage_url']
			embed.color = 12345678
			embed.set_thumbnail(url = songinfo['thumbnail'])
			embed.set_author(name = "Added to Queue", icon_url = ctx.message.author.avatar_url)
			embed.add_field(inline = True, name = "Channel", value = songinfo['uploader'].strip().title())
			hms = await self.client.loop.run_in_executor(None, hh_mm_ss, songinfo['duration'])
			hms_tuple = ("" if hms[0]==0 else (str(hms[0]) + "h "), "" if hms[1]==0 else (str(hms[1]) + "m "), "" if hms[2]==0 else (str(hms[2]) + "s "))
			embed.add_field(inline = True, name = "Duration", value = "{}{}{}".format(hms_tuple[0], hms_tuple[1], hms_tuple[2]))
			embed.add_field(inline = True, name = "Position in Queue", value = str(pos))
			eta = self.voice_clients[ctx.message.server.id].eta(len(self.voice_clients[ctx.message.server.id].queue)-1)
			hms = await self.client.loop.run_in_executor(None, hh_mm_ss, eta)
			hms_tuple = ("" if hms[0]==0 else (str(hms[0]) + "h "), "" if hms[1]==0 else (str(hms[1]) + "m "), "" if hms[2]==0 else (str(hms[2]) + "s "))
			embed.add_field(inline = True, name = "ETA until playing", value = "{}{}{}".format(hms_tuple[0], hms_tuple[1], hms_tuple[2]))
			# Sending the Embed
			await self.client.say(embed = embed)

	@commands.command(pass_context = True, aliases = ['snploop', 'shownowplayingeveryloop'])
	async def shownplooped(self, ctx):
		"""Toggle show now playing every time a new song pops up!"""
		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
		else:
			#There is a already a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			if self.check_dj(ctx.message.author) == True:
				import json
				with open("snpinfo.json", "r") as snpinfo:
					try:
						snpinf = json.load(snpinfo)
					except json.decoder.JSONDecodeError:
						# File not found/isn't json-compatible
						snpinf = {}
				if ctx.message.server.id in snpinf.keys():
					#Exists
					x = snpinf[ctx.message.server.id] = not snpinf[ctx.message.server.id]
				else:
					# Doesn't exist, if first time, then it will be showing
					x = snpinf[ctx.message.server.id] = True
				with open("snpinfo.json", "w") as snpinfo:
					json.dump(snpinf, snpinfo)
				await self.client.say(embed = emb("{}** **Now Playing every loop!**".format(":white_check_mark: **Showing" if x else ":x: **Not Showing")))
			else:
				# Not DJ
				await self.client.say(embed = emb("**Only someone with a `DJ` permission can perform this command.**"))

	@commands.command(pass_context = True, aliases = ['d'])
	async def dedicate(self, ctx, *songname):
		"""Dedicate songname to someone. Works only in private message."""
		if ctx.message.server is not None:
			# Called in a server text channel
			await self.client.say(embed = emb("**Dedications are a secret.** :wink:\n**You'll have to private message me the song you wanna dedicate.**"))
			return
		
		intended_server = None
		others_in_intended_server = []
		for thisservervc in self.voice_clients.values():
			if thisservervc.search_for_a_member_in_me(ctx.message.author) == True:
				intended_server = thisservervc.server
				others_in_intended_server = thisservervc.vc.channel.voice_members

		if intended_server is None:
			await self.client.say(embed = emb("**You must be connected with me in a server before dedicating a song!** :unamused:"))
			return

		if len(songname) == 0:
			await self.client.say(embed = emb("**You'll have to specify a songname to dedicate.**\n**Proper syntax of this code is:** `m/dedicate <songname/yt_url>`"))
			return

		# Member is connected, eligible to dedicate

		others = ''
		c = 1
		people_who_can_be_dedications = []
		for oiis in others_in_intended_server:
			if oiis.id == intended_server.me.id:
				continue
			elif oiis.id == ctx.message.author.id:
				continue
			else:
				others += "\n{}. {}".format(c, str(oiis.name))
				people_who_can_be_dedications.append(oiis)
				c += 1

		if others == '':
			others = "**There is nobody except you in the voice channel to dedicate this song to**, <@{}>".format(ctx.message.author.id)
			await self.client.say(embed = emb(others))
			return

		# Checking if url or not
		url = False
		if len(songname) == 1 and (songname[0].startswith("https://www.youtube.com/watch?v=") or songname[0].startswith("www.youtube.com/watch?v=") or songname[0].startswith("https://youtu.be/")):
			url = True
			songname = songname[0]
		else:
			# Formatting the songname properly
			songname = ' '.join(songname)
		# Getting the song's information from Youtube
		def get_song_info(url):
			"""To get the song's information in advance."""
			# Might be blocking, so use run_in_executor
			if url == False:
				# Not an url
				ytdl_options = {
					'default_search': 'auto',
					'quiet' : True
				}
				with youtube_dl.YoutubeDL(ytdl_options) as ydl:
					info_dict = ydl.extract_info(songname, download=False) # To get information about the song
					return info_dict['entries'][0]
			else:
				#An url
				ytdl_options = {
					'quiet' : True
				}
				with youtube_dl.YoutubeDL(ytdl_options) as ydl:
					info_dict = ydl.extract_info(songname, download=False) # To get information about the song
					return info_dict
			
		try:
			#Searching prompt
			await self.client.send_message(ctx.message.author, "**Searching** `{}` :mag_right:".format(songname))
			#Actually searching, prone of error if song not found.
			songinfo = await self.client.loop.run_in_executor(None, get_song_info, url)
			if songinfo['is_live'] is not None:
				# The song is a live telecast
				await self.client.say(embed = emb("**Melody is under development for live playback.**"))
				return
			embed = discord.Embed()
			embed.title = "Choose a member to dedicate this song to:"
			embed.color = discord.Colour(0xb82d7)
			embed.set_thumbnail(url = songinfo['thumbnail'])
			embed.set_author(name = "Song Dedicator", icon_url = music_logo_url)
			embed.description = "Searched song :mag_right: is: [{}]({})\n\nYou wish to **dedicate** this song to:\n(Enter the ***number*** of the member you wish to dedicate to, else enter anything else to quit.)\n```text{}\n```".format(songinfo['title'], songinfo['webpage_url'], others)
			await self.client.send_message(ctx.message.author, embed = embed)
		except youtube_dl.utils.DownloadError:
			await self.client.send_message(ctx.message.author, embed = emb(":x: **Sorry, the requested gibberish had no results on YouTube.**"))
			return

		message = await self.client.wait_for_message(timeout=60, author=ctx.message.author)

		if message is None:
			# Timeouted
			await self.client.send_message(ctx.message.author, embed = emb("**Song dedication timeouted, try again**! :frog:"))
			return

		message = message.content

		if not message.strip().isdigit():
			# Non-numeric input
			await self.client.send_message(ctx.message.author, embed = emb("**Song dedication cancelled due to non-numeric input, try again!** :frog:"))
			return

		if not (int(message.strip())>0 and int(message.strip())<c):
			# Integer enetered is not within the range of people indexes
			await self.client.send_message(ctx.message.author, embed = emb("**Song dedication cancelled as the input is not within the indexes of people in the voice channel, try again!** :frog:"))
			return

		await self.client.send_message(ctx.message.author, embed = emb("**Write something about the dedication, send `NA` if you don't wanna.** :smile:"))
		while True:
			dedicationinfo = await self.client.wait_for_message(timeout = 60, author = ctx.message.author)

			if dedicationinfo is None:
				# Timeouted
				await self.client.send_message(ctx.message.author, embed = emb("**Song dedication timeouted, try again!** :frog:"))
				return

			if len(dedicationinfo.content)<=1024:
				break

			else:
				await self.client.send_message(ctx.message.author, embed = emb("**The length of this message must be less than or equal to 1024**"))
				continue
		
		if dedicationinfo.content.strip().lower() == "na":
			dedicationinfo = None
		else:
			dedicationinfo = dedicationinfo.content.strip().title()
	
		# Proper integer input
		pos = int(message)
		# Dedication
		intended_dedication = people_who_can_be_dedications[pos-1]
		# Creating the song object
		song_object = Song(songname, ctx.message.author, songinfo)
		song_object.dedicatedto = intended_dedication
		song_object.dedicationinfo = dedicationinfo
		pos = self.voice_clients[intended_server.id].add_song_to_queue(song_object)
		if pos == 1 and self.voice_clients[intended_server.id].current_song_obj is None:
			# This is the first song added to queue
			await self.client.send_message(self.voice_clients[intended_server.id].channel, embed = emb("**Playing** :notes: `{}` - **Now!**\n**This was a secret dedication** :dog:".format(songinfo['title'].strip().title())))
		else:
			# Creating added to queue embed
			embed = discord.Embed()
			embed.title = songinfo['title'].strip().title()
			embed.url = songinfo['webpage_url']
			embed.color = 12345678
			embed.description = "This song is a **secret dedication**!\nWhenever it'll play, the **dedicated special person** will be **notified**."
			embed.set_thumbnail(url = songinfo['thumbnail'])
			embed.set_author(name = "Added to Queue", icon_url = ctx.message.author.avatar_url)
			embed.add_field(inline = True, name = "Channel", value = songinfo['uploader'].strip().title())
			hms = await self.client.loop.run_in_executor(None, hh_mm_ss, songinfo['duration'])
			hms_tuple = ("" if hms[0]==0 else (str(hms[0]) + "h "), "" if hms[1]==0 else (str(hms[1]) + "m "), "" if hms[2]==0 else (str(hms[2]) + "s "))
			embed.add_field(inline = True, name = "Duration", value = "{}{}{}".format(hms_tuple[0], hms_tuple[1], hms_tuple[2]))
			embed.add_field(inline = True, name = "Position in Queue", value = str(pos))
			eta = self.voice_clients[intended_server.id].eta(len(self.voice_clients[intended_server.id].queue)-1)
			hms = await self.client.loop.run_in_executor(None, hh_mm_ss, eta)
			hms_tuple = ("" if hms[0]==0 else (str(hms[0]) + "h "), "" if hms[1]==0 else (str(hms[1]) + "m "), "" if hms[2]==0 else (str(hms[2]) + "s "))
			embed.add_field(inline = True, name = "ETA until playing", value = "{}{}{}".format(hms_tuple[0], hms_tuple[1], hms_tuple[2]))
			# Sending the Embed
			await self.client.send_message(self.voice_clients[intended_server.id].channel, embed = embed)
			embed.set_author(name = "Added to {}'s Queue".format(intended_server.name), icon_url = ctx.message.author.avatar_url)
			await self.client.send_message(ctx.message.author, ":white_check_mark: **Dedication noted.**!", embed = embed)

	@commands.command(pass_context = True, aliases = ['sk'])
	async def seek(self, ctx, timestamp=None):
		"""Seek through the player"""
		x = await self.server_specific_command(ctx)
		if not x is None:
			# Means called from private msg
			return
		if(not ctx.message.server.id in self.voice_clients.keys()):
			#There is no voice client of the server
			await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
			return
		else:
			x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
			if x is not None:
				return
			# There is a voice client of the server
			# Channel check
			aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
			if aa[0] == False:
				await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
				return
			if timestamp is None:
				await self.client.say(embed = emb("**Please mention the time at which you intend to seek the now playing song.**"))
			response = validate_time(timestamp)
			if response[0] == False:
				# Handling possible scenarios
				response = response[1]
				if response == "NOT_ALL_DIG":
					await self.client.say(embed = emb("**Please enter proper time in hh:mm:ss or mm:ss format.**"))
				elif response == "COLONS_DONT_MATCH":
					await self.client.say(embed = emb("**Please enter the time appropriately in hh:mm:ss or mm:ss format.**"))
				elif response == "TIME_INPROPER":
					await self.client.say(embed = emb("**Please enter proper time in hh:mm:ss or mm:ss format. The 'h', 'm' and 's' fields must be <60 in values.**"))
				return
			else:
				time_tuple = response[1]
				time_s = time_tuple_to_s(time_tuple)
				#Typing
				await self.client.send_typing(ctx.message.channel)
				await self.voice_clients[ctx.message.server.id].seeksong(timestamp, time_s)
				await self.client.say(embed = emb("**Seeked to ** `" + timestamp + "` **!**"))

	def get_webpage_sync(self, url):
		from urllib import request
		html = request.urlopen(url)
		return html.read().decode('utf-8')

	def search_word_modifier_arr(self, arr):
		"""Returns love+story when ['love', 'story'] is passed"""
		wrd = arr[0]
		for x in arr[1:]:
			wrd += "+" + x
		return wrd

	def search_word_modifier_str(self, s):
		"""Returns love+story when 'love story' is passed"""
		arr = s.split(' ')
		x = self.search_word_modifier_arr(arr)
		return x

	def lyr_az(self, name):
		"""Get Lyrics from AZLyrics, if you can't, returns 0, else, returns the lyrics."""
		url = "https://search.azlyrics.com/search.php?q="
		if isinstance(name, str):
			url += self.search_word_modifier_str(name)
		if isinstance(name, tuple):
			url += self.search_word_modifier_arr(name)
		searched_page = self.get_webpage_sync(url)
		if "no results" in searched_page:
			return 0
		from bs4 import BeautifulSoup
		soup = BeautifulSoup(searched_page, 'html.parser')
		req = soup.find_all("table", class_="table table-condensed")
		req = req[-1]
		x = req.find_all("tr")
		if len(x) == 22:
			x = x[1]
		else:
			x = x[0]
		url = x.a['href']
		lyr_page = self.get_webpage_sync(url)
		soup = BeautifulSoup(lyr_page, 'html.parser')
		a = soup.find_all("div", class_ = None)
		return a[1].text

	@commands.command(pass_context = True, aliases = ['l'])
	async def lyrics(self, ctx, *song_name):
		"""Get lyrics"""
		if len(song_name) == 0:
			# Give current song's lyrics

			x = await self.server_specific_command(ctx)
			if not x is None:
				# Means called from private msg
				return
			if(not ctx.message.server.id in self.voice_clients.keys()):
				#There is no voice client of the server
				await self.client.say(embed = emb("**I'm not even connected, buddy!** :chipmunk:"))
				return
			else:
				x = await self.author_needs_to_be_in_same_vc(ctx.message.author.voice.voice_channel, self.voice_clients[ctx.message.server.id].vc.channel)
				if x is not None:
					return
				# There is a voice client of the server
				# Channel check
				aa = self.channel_check(self.voice_clients[ctx.message.server.id].channel, ctx.message.channel)
				if aa[0] == False:
					await self.client.say(embed = emb("**Restricted to commands only in** <#{}>.:fox:".format(aa[1])))
					return

				current_song_info = self.voice_clients[ctx.message.server.id].current_song_info()

				if current_song_info is None:
					await self.client.say(embed = emb("**Nothing's playing to search the lyrics for.**"))
					return
				else:
					song_name = self.voice_clients[ctx.message.server.id].current_song_obj.songname
					song_name = song_name.lower().title()

		lr = await self.client.loop.run_in_executor(None, self.lyr_az, song_name)
		if lr == 0:
			await self.client.say(embed = emb("**Lyrics Not Found**"))
		else:
			count_char = 0
			count = 0
			splitted_lr = []
			for x in lr:
				count_char += 1
				count += 1
				if count_char == 2040:
					splitted_lr.append(lr[count-count_char: count])
					count_char = 0
			if count_char != 0:
				splitted_lr.append(lr[count-count_char: count])
			a = 1
			for x in splitted_lr:
				embed = discord.Embed()
				embed.color = 65324
				if a==1:
					if isinstance(song_name, tuple):
						song_name = ' '.join(song_name)
						song_name = song_name.lower()
					embed.set_author(name = "Lyrics for {}".format(song_name.title()))
					a += 1
				embed.description = x.strip()
				await self.client.say(embed = embed)

	@commands.command(pass_context = True)
	async def help(self, ctx, typ = "short"):
		embed = discord.Embed(colour=discord.Colour(0xb175ff), url="https://discordapp.com", description="This is the command help text for Melody Bot.")
		embed.set_thumbnail(url="https://mir-s3-cdn-cf.behance.net/project_modules/max_1200/3a67ac9349717.56323aac30ee4.jpg")
		embed.set_author(name="Help for Melody")

		embed.add_field(name="1. Join/Summon", value="Joins the Bot to the specified channel\nUsage: `m/join` or `m/summon`", inline=False)
		embed.add_field(name="2. Leave/Disconnect", value="Disconnects bot from the connected channel\nUsage: `m/leave` or `m/disconnect`", inline=False)
		embed.add_field(name="3. Play", value="Plays the specified song or adds it to queue as required\nBoth song names and youtube urls are supported\nUsage: `m/play <songname/url>` or `m/p <songname/url>`", inline=False)
		embed.add_field(name="4. Now Playing", value="Shows the now playing song's information\nUsage: `m/nowplaying` or `m/np`", inline=False)
		embed.add_field(name="5. Pause", value="Pauses the current song\nUsage: `m/pause` or `m/ps`", inline=False)
		embed.add_field(name="6. Resume", value="Resumes the paused song\nUsage: `m/resume` or `m/continue`", inline=False)
		embed.add_field(name="7. Repeat", value="Repeats the currently playing song\nUsage: `m/repeat` or `m/r`", inline=False)
		embed.add_field(name="8. Skip", value="Skips the currently playing song, if any\nUsage: `m/skip` or `m/s`", inline=False)
		embed.add_field(name="9. Queue", value="Shows the currently playing queue\nUsage: `m/queue` or `m/q`", inline=False)

		if typ != "short" and typ != "small":
			embed.add_field(name="10. Remove", value="Removes and pops out a song at specified index in the queue\nUsage: `m/remove <index>` or `m/rm <index>`", inline=False)
			embed.add_field(name="11. Seek", value="Seeks current player to a specific time within the song's duration\nUsage: `m/seek <timestamp>` or `m/sk <timestamp>`, where `timestamp = hh:mm:ss or mm:ss`", inline=False)
			embed.add_field(name="12. Show NP Looped", value="Shows the now playing song every time a song changes\nA toogle switch to on/off this feature\nIt is a saved data for each server\nUsage: `m/shownplooped` or `m/snploop`", inline=False)
			embed.add_field(name="13. Add Favourite", value="Adds the current song or a song at a queue-index to the user's favourites\nIf no index is given, the current song is added\nUsage: `m/addfav [queue-index]` or `m/afav [queue-index]`", inline=False)
			embed.add_field(name="14. Show Favourites", value="Direct messages the saved favourites data of you\nUsage: `m/showfav` or `m/sfav`", inline=False)
			embed.add_field(name="15. Remove Favourite", value="Removes an indexed-favourite\nRefer to index shown before `sfav` message for index\nUsage: `m/removefav <fav-index>` or `m/rfav <fav-index>`", inline=False)
			embed.add_field(name="16. Play from Favourite", value="Plays or adds to queue the indexed favourite song\nUsage: `m/playfav <fav-index>` or `m/pfav <fav-index>`", inline=False)
			embed.add_field(name="17. Dedicate", value="Dedicates a song to someone also listening to the same queue in the same voice channel as the author who wants to dedicate\nUse only in the bot's private message as dedications are a secret\nThe person dedicated to will be informed when the dedicated song starts playing\nUsage: `m/dedicate <songname>` or `m/d <songname>`", inline=False)
			embed.add_field(name="18. Lyrics", value="Shows lyrics for the currently playing song or a song specifically asked for\nCan give wrong results oftentimes as this is under development\nUsage: `m/lyrics [songname]` or `m/l [songname]`", inline=False)

		await self.client.send_message(ctx.message.author, embed = embed)

def setup(client):
	client.add_cog(Rythm2(client))
	print('Rythm is loaded.')
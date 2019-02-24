from song_object import Song
import asyncio
import discord
import time

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

class VoiceClient:
	"""Voice Client to perform all voice tasks in the voice channels."""
	def __init__(self, voice_client, bot_client, server, channel):
		"""Parameterized constructor.

		Parameter:
		voice_client = Instance of voice_client capable of voice stuffs
		bot_client = Instance of bot
		"""
		self.vc = voice_client #Instance of voice_client
		self.server = server # discord.server in which this is connected
		self.client = bot_client #Instance of bot

		self.is_paused = False #Is paused or not
		self.repeat = False # Is on repeat
		self.show_current = False # Show current song when every new song plays
		self.channel = channel # Channel to send np
		self.justskipped = False # Just skipped the song, useful or snploop

		self.disconnect_timer = 0
		self.should_disconnect = False # Timeout of nobody hearing for time_to_delay seconds
		self.time_to_delay = 300

		self.queue = [] # Queue, consisting of Song objects

		self.current_song_obj = None # Current Song object
		self.current_player = None # Current Song Player
		self.current_player_time_started = 0 # To record time when song was started
		self.current_player_total_paused = 0 # To record total pause time
		self.current_player_time_paused = 0 # To record time paused

		self.volume = 1
		self.shuffle = False
		self.npmsg = None
		self.pmsg = None
		self.skp= False
		self.first_song_getting_added = False

		self.skip_people = []

		self.client.loop.create_task(self.song_player_task()) # To check queues and play songs accordingly

	def shuffle_state(self):
		self.shuffle = not self.shuffle
		return self.shuffle

	def change_vol_zero2hundred(self, vol):
		vol = vol/100
		if self.current_player is not None:
			self.current_player.volume = vol
			self.volume = vol

	def check_dj(self, mem):
		for x in mem.roles:
			if x.name.lower() == "dj":
				return True
		return False

	def search_for_a_member_in_me(self, member):
		"""Searches for a member in vc"""
		return member in self.vc.channel.voice_members

	def current_song_info(self):
		"""To return current song information"""
		if not self.current_song_obj is None:
			return self.current_song_obj.songinfo
		else:
			return None

	def current_playing_time(self):
		"""To return current time of song which it is playing."""
		if self.current_player_time_paused != 0:
			# Currently in pause, self.is_paused will also be True
			return time.time() - (self.current_player_time_started + self.current_player_total_paused + (time.time() - self.current_player_time_paused))
		else:
			# Not paused
			a = time.time() - (self.current_player_time_started + self.current_player_total_paused)
			if a > 99999:
				# Unusually high
				print("heh. Unusually high playtime. No idea why.")
				return 0
			else:
				return a

	def eta(self, num):
		"""Returns estimated time until queue[num-1] plays"""
		if self.is_queue_empty() == True:
			return self.current_song_obj.songinfo['duration'] - int(self.current_playing_time())
		else:
			rest_time = 0 # Time for the remaining songs to complete
			for thissongobj in self.queue[0:num]:
				rest_time += thissongobj.songinfo['duration']
			return rest_time + (self.current_song_obj.songinfo['duration'] - int(self.current_playing_time()))

	def reset(self):
		"""Reset player when loop ended"""
		self.time_to_delay = 300 # 30s delayed in case of no song play
		self.current_song_obj = None # Current Song object
		self.current_player = None # Current Song Player
		self.current_player_time_started = 0 # To record time when song was started
		self.current_player_total_paused = 0 # To record total pause time
		self.current_player_time_paused = 0 # To record time paused
		self.time_to_delay = 300
		self.first_song_getting_added = False

	def skip(self):
		"""Skip current song"""
		self.skp= True
		#Stop
		if self.is_playing():
			self.stop()
		# Creates problem when repeat = On

	def how_many_listening(self):
		"""Returns how many are listening to the song"""
		return len(self.vc.channel.voice_members)-1

	def askip_ret_pass(self, mid):
		if mid not in self.skip_people:
			self.skip_people.append(mid)
			if (len(self.skip_people) / self.how_many_listening()) * 100 >= 30:
				return True
			else:
				return False
		else:
			return None

	def add_song_to_queue(self, song_object):
		"""Add Song object to queue"""
		self.queue.append(song_object)
		return len(self.queue)

	def is_queue_empty(self):
		"""Checks if queue empty or not"""
		if self.queue == []:
			return True
		else:
			return False

	def is_playing(self):
		"""Checks if something is playing or not"""
		if self.current_player is None:
			return False
		else:
			return not self.current_player.is_done()

	def pause(self):
		"""Pauses the current song."""
		if self.is_playing():
			#Playing
			self.current_player.pause()
			self.current_player_time_paused = time.time()
			self.is_paused = True

	def stop(self):
		"""Stops the current song."""
		if not self.current_player is None:
			self.current_player.stop()
			self.justskipped = True

	def resume(self):
		"""Resumes the current song."""
		if self.is_paused == True:
			#Not playing
			self.current_player.resume()
			self.current_player_total_paused += time.time() - self.current_player_time_paused
			self.current_player_time_paused = 0
			self.is_paused = False

	def add_next(self):
		"""Adds next song to self.current_player_obj"""
		if self.repeat == True and self.skp== False:
			# Only condition when the song must not change
			return
		else:
			# The song must change
			try:
				if self.shuffle == True:
					# Must shuffle
					if len(self.queue) >= 1:
						# Songs exist in queue
						import random
						self.current_song_obj = self.queue.pop(random.randrange(len(self.queue)))
						del random
					else:
						raise IndexError
				else:
					# No shuffle
					self.current_song_obj = self.queue.pop(0)

				def del_reac():
					self.shoulddelreact = False
					for e in self.reac:
						try:
							if self.npmsg is not None:
								self.client.loop.create_task(self.client.remove_reaction(self.npmsg, e, self.server.me))
								self.client.loop.create_task(asyncio.sleep(0.1))
						except:
							pass
					self.npmsg = None

				del_reac()

				self.current_player_time_started = time.time() # To record time when song was started
				self.current_player_total_paused = 0 # To record total pause time
				self.current_player_time_paused = 0 # To record time paused

			except IndexError:
				# Queue ended
				self.reset()

	async def np_sync(self):
		# Show current song when songs change
		current_song_info = self.current_song_info()
		embed = discord.Embed()
		embed.title = current_song_info['title'].strip().title()
		embed.url = current_song_info['webpage_url']
		embed.color = 654814
		embed.set_thumbnail(url = current_song_info['thumbnail'])
		embed.set_author(name = "Playing Now >")
		embed.description = "{}\nRequested by `{}`".format("" if self.shuffle==False else ":twisted_rightwards_arrows: **ON**",self.current_song_obj.requester.name)
		#Sending this embed
		self.npmsg = await self.client.send_message(self.channel, embed = embed)

		# Reaction Stuff
		# Play/Pause button, Track_next, Repeat one, Twisted rightwards arrow, speaker, loud sound, hearts
		reacting_to = ["\U000023ed", "\U0001f502", "\U0001f500", "\U00002665"]
		self.reac = reacting_to
		for e in reacting_to:
			await self.client.add_reaction(self.npmsg, e)

		self.shoulddelreact = True
		await asyncio.sleep(20)

		if self.shoulddelreact:
			for e in reacting_to:
				try:
					if self.npmsg is not None:
						await self.client.remove_reaction(self.npmsg, e, self.server.me)
						await asyncio.sleep(0.4)
				except:
					pass
		self.npmsg = None

	def get_np_show_inf_sync(self):
		"""json-load and check if snp data is already there"""
		import json
		with open("snpinfo.json", "r") as snpinfo:
			try:
				snpinf = json.load(snpinfo)
			except json.decoder.JSONDecodeError:
				# File not found/isn't json-compatible
				snpinf = {}
		if self.server.id in snpinf.keys():
			self.show_current = snpinf[self.server.id]
		else:
			self.show_current = False

	async def inform_dedication(self):
		"""To inform about the dedication"""
		dedicatedto = self.current_song_obj.dedicatedto
		dedicationinfo = self.current_song_obj.dedicationinfo
		whodedicated = self.current_song_obj.requester
		sname = self.current_song_obj.songinfo['title']
		sinf = self.current_song_obj.songinfo
		msg = "`{}` has a  **secret dedication** for *you*, <@{}>! :heart:".format(whodedicated.name, dedicatedto.id)
		embed = discord.Embed()
		embed.title = sname
		embed.url = sinf['webpage_url']
		embed.color = 16320790
		embed.set_author(name = "Song Dedication", icon_url = whodedicated.avatar_url)
		embed.set_thumbnail(url = sinf['thumbnail'])
		embed.set_footer(text = self.server.name)
		if dedicationinfo is not None:
			embed.add_field(name = "Message from {}".format(whodedicated.name), value = dedicationinfo)
		else:
			embed.description = "Requested by {}".format(whodedicated.name)

		await self.client.send_message(dedicatedto, msg, embed= embed)
		await self.client.send_message(whodedicated, embed = emb("**Your dedication was notified to** `{}` :white_check_mark:\n**Song name:** `{}`".format(dedicatedto.name, sname)))

	def save_whoever_is_listening_and_what(self):
		import json
		with open("listener_records.json", "r") as lr:
			try:
				lr = json.load(lr)
			except json.decoder.JSONDecodeError:
				lr = {}
		members = self.vc.channel.voice_members
		for thismember in members:
			if thismember.id == self.server.me.id:
				continue
			elif thismember.id in lr.keys():
				songshelistened = lr[thismember.id]
				currenturl = self.current_song_obj.songinfo['webpage_url']
				#{songname, songurl, count} will be stored
				entry_found = False
				for songdict in songshelistened:
					if songdict['songurl'] == currenturl:
						entry_found = True
						count_of_times_song_heard = songdict['count']
						songshelistened.remove(songdict)
						songdict['songname'] = self.current_song_obj.songinfo['title']
						songdict['songurl'] = currenturl
						songdict['count'] = count_of_times_song_heard + 1
						lr[thismember.id].append(songdict)
						break
				if entry_found == False:
				 	#Entry wasn't found
				 	lr[thismember.id].append({'songname' : self.current_song_obj.songinfo['title'], 'songurl' : self.current_song_obj.songinfo['webpage_url'], 'count' : 1})
			else:
				lr[thismember.id] = []
				lr[thismember.id].append({'songname' : self.current_song_obj.songinfo['title'], 'songurl' : self.current_song_obj.songinfo['webpage_url'], 'count' : 1})

		with open("listener_records.json", "w") as lrf:
			json.dump(lr, lrf)

	async def seeksong(self, formatted_time, time_in_s):
		"""Seek the song to some time ahead/back"""
		# Use: before_options="-ss 00:00:30"
		cur_song_obj = self.current_song_obj
		url = self.current_song_obj.get_song_url()
		pl = await self.vc.create_ytdl_player(url, ytdl_options = {'quiet':True}, after = self.add_next, before_options = "-ss {}".format(formatted_time))
		self.current_player.pause()
		self.current_player = None
		self.current_player = pl
		self.current_player.volume = self.volume
		self.current_player.start()
		self.current_song_obj = cur_song_obj
		self.current_player_time_started = time.time() - time_in_s
		self.current_player_total_paused = 0
		self.current_player_time_paused = 0

	async def reac_do(self, emoji, user=None):
		# Pause ⏸
		# Next ⏭
		# Repeat 🔂
		# Shuffle 🔀
		# Sound lower 🔈
		# Sound higher 🔊
		# Add to favourites ♥
		if emoji == "⏸" and self.is_paused == False:
			self.pause()
			self.pmsg = await self.client.send_message(self.channel, embed = emb("**Paused** ⏸"))
			await self.client.add_reaction(self.pmsg, "\U000025b6")
			await asyncio.sleep(15)
			try:
				if self.pmsg is not None:
					await self.client.remove_reaction(self.pmsg, "\U000025b6", self.server.me)
			except:
				pass
		elif emoji == "▶" and self.is_paused==True:
			self.resume()
			await self.client.send_message(self.channel, embed = emb("**Resumed** ▶"))
		elif emoji == "⏭":
			if self.check_dj(user) != True:
				resp = self.askip_ret_pass(user.id)
				if resp == None:
					await self.client.send_message(self.channel, embed = emb("**The same person can't skip twice.** :x:"))
					return
				if resp == False:
					await self.client.send_message(self.channel, embed = emb("**More {} skips needed to skip the song!**".format(str(int(0.3*self.how_many_listening() - len(self.skip_people)) + 1))))
					return
				self.skip()
				await self.client.send_message(self.channel, embed = emb("**Skipped** ⏭"))
			else:
				#DJ
				self.skip()
				await self.client.send_message(self.channel, embed = emb("**Skipped** ⏭"))
		elif emoji == "🔂":
			self.repeat = not self.repeat
			await self.client.send_message(self.channel, embed = emb("🔂 **{}**".format("ON" if self.repeat==True else "OFF")))
		elif emoji == "🔀":
			x = self.shuffle_state()
			await self.client.send_message(self.channel, embed = emb("🔀 **{}**".format("ON" if x==True else "OFF")))
		elif emoji == "🔈":
			if (self.volume*100)-20 >= 0:
				self.change_vol_zero2hundred((self.volume*100)-20)
				await self.client.send_message(self.channel, embed = emb("🔈 **{}**".format(str(int(self.volume*100)))))
		elif emoji == "🔊":
			if (self.volume*100)+20 <= 200:
				self.change_vol_zero2hundred((self.volume*100)+20)
				await self.client.send_message(self.channel, embed = emb("🔊 **{}**".format(str(int(self.volume*100)))))

	async def song_player_task(self):
		"""Play the song in this task"""
		while True:
			# To play songs and listen continuously for new songs added.

			# First song to self.current_player_object
			if len(self.queue) == 1 and self.current_song_obj is None :
				# Current Song is the first song object added.
				self.current_song_obj = self.queue.pop(0)
				pass

			# For new songs in queue
			if not self.is_playing() and not self.current_song_obj is None:
				# Player not playing anything
				# This means we need to play the next song

				# URL of the song
				url = self.current_song_obj.get_song_url()
				# Creating the song player
				self.current_player = await self.vc.create_ytdl_player(url, ytdl_options = {'quiet':True}, before_options = " -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", after=self.add_next)
				self.current_player.volume = self.volume
				if self.current_song_obj is not None:
					# Starting the song player
					self.current_player.start()
					print("Playing {}".format(self.current_song_obj.songinfo['title'].strip().title()))
					self.current_player_time_started = time.time()

					# 2 minutes delayed in case of disconnect because of no members
					self.time_to_delay = 500

					await self.client.loop.run_in_executor(None, self.get_np_show_inf_sync)
					if self.show_current == True and (self.repeat != True or self.justskipped == True):
						await self.client.loop.create_task(self.np_sync())
					if self.current_song_obj is not None:
						if self.current_song_obj.dedicatedto is not None:
							# Has dedication
							await self.client.loop.create_task(self.inform_dedication())
						await self.client.loop.run_in_executor(None, self.save_whoever_is_listening_and_what)

				self.justskipped = False
				self.skp= False
				self.skip_people = []
				self.first_song_getting_added = False

			def handle_disconnection():
				members = self.vc.channel.voice_members

				if len(members) > 1 and self.disconnect_timer != 0 and not (self.is_queue_empty() and not self.is_playing()):
					self.should_disconnect = False
					self.disconnect_timer = 0

				if len(members) == 1:
					# Nobody is hearing this song. That one member is the bot itself.
					if self.disconnect_timer == 0:
						self.disconnect_timer = time.time()
					elif (time.time() - self.disconnect_timer) > self.time_to_delay:
						self.should_disconnect = True

				if self.is_queue_empty() and not self.is_playing():
					if self.disconnect_timer == 0:
						self.disconnect_timer = time.time()
					elif (time.time() - self.disconnect_timer) > self.time_to_delay:
						self.should_disconnect = True

			handle_disconnection()

			# So that everything works properly
			await asyncio.sleep(3)

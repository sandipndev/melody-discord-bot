class Song:
	"""To add a song. Holds all stuffs about a song that's required."""
	def __init__(self, songname, requester, songinfo):
		"""Paramterized constructor.

		Parameter:
		songname - Song name asked for
		requester - discord.message.author who requested for the song
		"""
		self.songname = songname
		self.requester = requester
		self.songinfo = songinfo
		self.dedicatedto = None
		self.dedicationinfo = None

	def get_song_url(self):
		"""Returns YouTube URL for the song."""
		return self.songinfo['webpage_url'] # We will use this url for the song
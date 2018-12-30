import youtube_dl as ytdl

class SongDL:
	"""This class takes in a song name in default constructor.
	When it's main() is called, the song name is searched on youtube and the first search result gets downloaded.
	It automatically converts the downloaded .webm file to .mp3 to 192 bitrate.
	
	Data Received:
	main() returns view_count, uploader, like_count, dislike_count, id, description, uploader, title and filename.
	The filename is the song's mp3 version.

	Changes:
	Bitrate change can be made simply in the call of main(bitrate)."""

	def __init__(self, songname):
		"""Initiate only with the song name, doesn't download."""
		self.songname = songname

	def editsongname(self):
		"""Self function, none of your use, fuck off."""
		s = self.songname.split(' ')
		snf = s[0].strip().capitalize()
		for x in s[1:]:
			snf += "_" + x.strip().capitalize()
		self.songnameed = snf

	def download(self, bitrate):
		"""Downloads the song in specified bitrate.
		
		Returns:
		Entries of info_dict containing data about the youtube video equivalent.
		"""
		outtmpl = self.songnameed + '.%(ext)s'
		ydl_opts = {
			'default_search': 'auto',
			'quiet' : True,
			'format': 'bestaudio/best',
			'outtmpl': outtmpl,
			'postprocessors': [
				{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3',
				 'preferredquality': bitrate,
				},
				{'key': 'FFmpegMetadata'},
			],
		}
		with ytdl.YoutubeDL(ydl_opts) as ydl:
			info_dict = ydl.extract_info(self.songname, download=True)
			return info_dict['entries'][0]

	def main(self, bitrate=192):
		"""Actually makes the program work.
		
		Returns:
		A dict containing the basic datas of the youtube video asked for."""
		self.editsongname()
		entries = self.download(str(bitrate))
		req_items = {
			'view_count' : entries['view_count'],
			'id' : entries['id'],
			'description' : entries['description'],
			'thumbnail' : entries['thumbnail'],
			'uploader' : entries['uploader'],
			'like_count' : entries['like_count'],
			'dislike_count' : entries['dislike_count'],
			'title' : entries['title'],
			'webpage_url' : entries['webpage_url'],
			'filename' : self.songnameed + ".mp3",
			'duration' : entries['duration']
		}
		return req_items



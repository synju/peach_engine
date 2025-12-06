from direct.showbase.ShowBase import ShowBase
from panda3d.core import AudioManager

# Global created by ShowBase
base: ShowBase

class SoundPlayer:
	"""Handles sound effects and music playback"""

	def __init__(self):
		self.sounds = {}
		self.music = None
		self.music_volume = 0.7
		self.sfx_volume = 0.7
		self.sound_enabled = True
		self.music_enabled = True

	# Sound Effects
	def load_sound(self, name, filepath):
		"""Load a sound effect"""
		try:
			sound = base.loader.loadSfx(filepath)
			if sound:
				sound.setVolume(self.sfx_volume)
				self.sounds[name] = sound
				return True
		except Exception as e:
			print(f"Could not load sound {filepath}: {e}")
		return False

	def play_sound(self, name, loops=False):
		"""Play a loaded sound effect"""
		if not self.sound_enabled:
			return

		if name in self.sounds:
			sound = self.sounds[name]
			sound.setLoop(loops)
			sound.play()

	def play_effect(self, filepath, loops=False):
		"""Load and play a sound effect in one call"""
		if not self.sound_enabled:
			return

		try:
			sound = base.loader.loadSfx(filepath)
			if sound:
				sound.setVolume(self.sfx_volume)
				sound.setLoop(loops)
				sound.play()
		except Exception as e:
			print(f"Could not play effect {filepath}: {e}")

	def stop_sound(self, name):
		"""Stop a playing sound"""
		if name in self.sounds:
			self.sounds[name].stop()

	def stop_all_sounds(self):
		"""Stop all sound effects"""
		for sound in self.sounds.values():
			sound.stop()

	# Music
	def load_music(self, filepath):
		"""Load background music"""
		try:
			self.music = base.loader.loadMusic(filepath)
			if self.music:
				self.music.setVolume(self.music_volume)
				return True
		except Exception as e:
			print(f"Could not load music {filepath}: {e}")
		return False

	def play_music(self, loops=True):
		"""Play loaded background music"""
		if not self.music_enabled or not self.music:
			return

		self.music.setLoop(loops)
		self.music.play()

	def play_song(self, filepath, loops=True):
		"""Stop current music and play a new song"""
		if not self.music_enabled:
			return

		self.stop_music()

		try:
			self.music = base.loader.loadMusic(filepath)
			if self.music:
				self.music.setVolume(self.music_volume)
				self.music.setLoop(loops)
				self.music.play()
		except Exception as e:
			print(f"Could not play song {filepath}: {e}")

	def stop_music(self):
		"""Stop background music"""
		if self.music:
			self.music.stop()

	def pause_music(self):
		"""Pause background music"""
		# Panda3D doesn't have native pause, so we store time and stop
		if self.music:
			self._music_time = self.music.getTime()
			self.music.stop()

	def unpause_music(self):
		"""Resume background music"""
		if self.music and hasattr(self, '_music_time'):
			self.music.setTime(self._music_time)
			self.music.play()

	# Volume controls
	def set_music_volume(self, volume):
		"""Set music volume (0.0 to 1.0)"""
		self.music_volume = max(0.0, min(1.0, volume))
		if self.music:
			self.music.setVolume(self.music_volume)

	def set_sfx_volume(self, volume):
		"""Set sound effects volume (0.0 to 1.0)"""
		self.sfx_volume = max(0.0, min(1.0, volume))
		for sound in self.sounds.values():
			sound.setVolume(self.sfx_volume)

	def set_master_volume(self, volume):
		"""Set master volume for all audio"""
		self.set_music_volume(volume)
		self.set_sfx_volume(volume)

	# Enable/Disable
	def enable_sound(self, enabled):
		"""Enable or disable sound effects"""
		self.sound_enabled = enabled
		if not enabled:
			self.stop_all_sounds()

	def enable_music(self, enabled):
		"""Enable or disable music"""
		self.music_enabled = enabled
		if not enabled:
			self.stop_music()

	def cleanup(self):
		"""Cleanup all audio"""
		self.stop_all_sounds()
		self.stop_music()
		self.sounds.clear()
		self.music = None
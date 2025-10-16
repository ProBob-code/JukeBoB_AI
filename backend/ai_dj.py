import asyncio
from typing import List, Dict, Optional
import random

class AIDJAgent:
    def __init__(self):
        self.current_playlist = []
        self.is_playing = False
        self.current_track_index = 0
        
    def add_to_playlist(self, song: Dict):
        self.current_playlist.append(song)
    
    def remove_from_playlist(self, song_id: str):
        self.current_playlist = [s for s in self.current_playlist if s.get('id') != song_id]
    
    def get_next_track(self) -> Optional[Dict]:
        if self.current_track_index < len(self.current_playlist):
            track = self.current_playlist[self.current_track_index]
            self.current_track_index += 1
            return track
        return None
    
    async def auto_mix_transition(self, current_track: Dict, next_track: Dict):
        fade_duration = 3
        await asyncio.sleep(fade_duration)
        return {
            "transition": "crossfade",
            "duration": fade_duration,
            "from": current_track,
            "to": next_track
        }
    
    def analyze_crowd_mood(self, recent_votes: List[Dict]) -> str:
        if not recent_votes:
            return "energetic"
        
        avg_votes = sum(v.get('votes', 0) for v in recent_votes) / len(recent_votes)
        
        if avg_votes > 10:
            return "hyped"
        elif avg_votes > 5:
            return "energetic"
        else:
            return "chill"
    
    def suggest_next_song(self, crowd_mood: str, available_songs: List[Dict]) -> Optional[Dict]:
        if not available_songs:
            return None
        
        if crowd_mood == "hyped":
            upbeat_songs = [s for s in available_songs if s.get('votes', 0) > 5]
            if upbeat_songs:
                return max(upbeat_songs, key=lambda x: x.get('votes', 0))
        
        return random.choice(available_songs)
    
    def clear_playlist(self):
        self.current_playlist = []
        self.current_track_index = 0
        self.is_playing = False
    
    def get_playlist_status(self) -> Dict:
        return {
            "is_playing": self.is_playing,
            "current_index": self.current_track_index,
            "playlist_length": len(self.current_playlist),
            "tracks": self.current_playlist
        }

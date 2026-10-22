import musicbrainzngs

class MusicBrainzService:
    def __init__(self, app_name="OrangeRipper", version="0.1", contact="your-email@example.com"):
        musicbrainzngs.set_useragent(app_name, version, contact)

    @staticmethod
    def format_duration(ms):
        if not ms:
            return ""
        try:
            total_seconds = int(ms) // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}:{seconds:02d}"
        except (ValueError, TypeError):
            return ""

    def lookup_release_by_recording(self, recording_id: str, preferred_album: str = None) -> dict:
        """Queries MusicBrainz using a Recording MBID, sorting releases to find the best match."""
        try:
            rec_result = musicbrainzngs.get_recording_by_id(recording_id, includes=["releases", "artist-credits"])
            recording = rec_result.get("recording", {})
            releases = recording.get("release-list", [])

            if not releases:
                return None

            # Try to find a release matching a preferred album title if provided, otherwise pick the first
            selected_release_id = None
            if preferred_album:
                for rel in releases:
                    title = rel.get("title", "")
                    if preferred_album.lower() in title.lower():
                        selected_release_id = rel.get("id")
                        break
            
            if not selected_release_id:
                selected_release_id = releases[0].get("id")

            # Fetch full release metadata for the selected release ID
            rel_result = musicbrainzngs.get_release_by_id(selected_release_id, includes=["recordings", "artist-credits"])
            release = rel_result.get("release", {})

            album_title = release.get("title", "Unknown Album")
            artist_credit = release.get("artist-credit", [])
            artist_name = artist_credit[0].get("artist", {}).get("name", "Unknown Artist") if artist_credit else "Unknown Artist"
            year = release.get("date", "")[:4] if release.get("date") else ""

            # Construct Cover Art Archive URL using the resolved release ID
            cover_art_url = f"https://coverartarchive.org/release/{selected_release_id}/front" if selected_release_id else None

            tracklist = []
            for medium in release.get("medium-list", []):
                for track in medium.get("track-list", []):
                    rec = track.get("recording", {})
                    track_no = track.get("number", str(len(tracklist) + 1))
                    
                    length_ms = track.get("length") or rec.get("length")
                    duration_str = self.format_duration(length_ms)

                    tracklist.append({
                        "track_number": int(track_no) if track_no.isdigit() else len(tracklist) + 1,
                        "number": track_no,
                        "title": rec.get("title", track.get("title", "Unknown Track")),
                        "duration": duration_str
                    })

            return {
                "artist": artist_name,
                "title": album_title,
                "year": year,
                "cover_art_url": cover_art_url,
                "tracks": tracklist,
                "tracklist": tracklist
            }

        except Exception as e:
            print(f"Failed MusicBrainz release lookup for recording {recording_id}: {e}")
            return None

    def lookup_by_discid(self, discid: str):
        try:
            result = musicbrainzngs.get_releases_by_discid(
                discid, 
                includes=["artists", "recordings"]
            )
            
            if "disc" in result and "release-list" in result["disc"]:
                releases = result["disc"]["release-list"]
                if not releases:
                    return None
                
                release = releases[0]
                title = release.get("title", "Unknown Album")
                artist = release.get("artist-credit-phrase", "Unknown Artist")
                year = release.get("date", "")[:4]
                release_id = release.get("id")

                cover_art_url = f"https://coverartarchive.org/release/{release_id}/front" if release_id else None

                tracks = []
                medium_list = release.get("medium-list", [])
                if medium_list:
                    track_list = medium_list[0].get("track-list", [])
                    for i, track in enumerate(track_list):
                        recording = track.get("recording", {})
                        track_title = recording.get("title", track.get("title", "Unknown Track"))
                        length_ms = int(recording.get("length", track.get("length", 0)))
                        
                        tracks.append({
                            "track_number": i + 1,
                            "title": track_title,
                            "duration": self.format_duration(length_ms)
                        })

                return {
                    "id": release_id,
                    "title": title,
                    "artist": artist,
                    "year": year,
                    "cover_art_url": cover_art_url,
                    "tracklist": tracks
                }
                
        except musicbrainzngs.ResponseError as e:
            print(f"MusicBrainz lookup failed: {e}")
        except Exception as e:
            print(f"Unexpected error during MusicBrainz lookup: {e}")
            
        return None

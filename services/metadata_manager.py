from services.musicbrainz import MusicBrainzService
from services.discogs_service import DiscogsService
from services.acoustid_service import AcoustIDService
from ripperCore.ripper import CDRipper
import os

class MetadataManager:
    def __init__(self, discogs_token: str = None, acoustid_key: str = None):
        self.mb_service = MusicBrainzService()
        #self.discogs_service = DiscogsService(user_token=discogs_token) if discogs_token else None
        #self.discogs_service = None                   # comment the line above and uncomment this line to turn off discogs search
        self.acoustid_service = AcoustIDService(api_key=acoustid_key) if acoustid_key else None

    def fetch_metadata_for_cd(self, discid: str, user_query: dict = None):
        """Queries MusicBrainz and Discogs. Returns match or None if fallback is needed."""
        print("[1/2] Querying MusicBrainz via DiscID...")
        #mb_result = None                             # comment the following line and uncomment this line to turn off musicbrainz search
        mb_result = self.mb_service.lookup_by_discid(discid)
        if mb_result:
            print(" -> Found match on MusicBrainz!")
            return {"source": "MusicBrainz", "data": mb_result}

        print("[2/2] MusicBrainz returned no match. Trying Discogs...")
        if self.discogs_service and user_query:
            discogs_results = self.discogs_service.search_release(
                artist=user_query.get("artist"),
                album=user_query.get("album"),
                catno=user_query.get("catno")
            )
            if discogs_results:
                print(" -> Found match on Discogs!")
                return {"source": "Discogs", "data": discogs_results[0]}

        print(" -> MusicBrainz and Discogs returned no match. AcoustID candidate available.")
        return None

    def fetch_acoustid_metadata(self):
        """Specifically executes the AcoustID sample rip and fingerprinting flow."""
        if not self.acoustid_service:
            return {"source": "None", "data": None}

        temp_file_created = False
        path_to_fingerprint = "/tmp/orange_ripper_prod_track1.wav"
        print(" -> Performing temporary sample rip of Track 1 for fingerprinting...")
        
        try:
            ripper = CDRipper()
            if ripper.rip_track(track_number=1, output_wav_path=path_to_fingerprint):
                temp_file_created = True
        except Exception as e:
            print(f" -> Live sample rip failed: {e}")

        try:
            if path_to_fingerprint and os.path.exists(path_to_fingerprint):
                acoustid_matches = self.acoustid_service.lookup_track(path_to_fingerprint)
                if acoustid_matches:
                    print(" -> Found match via AcoustID Fingerprint!")
                    formatted_data = self._format_acoustid_result(acoustid_matches)
                    if formatted_data:
                        return {"source": "AcoustID", "data": formatted_data}
        finally:
            if temp_file_created and os.path.exists(path_to_fingerprint):
                try:
                    os.remove(path_to_fingerprint)
                except OSError:
                    pass

        return {"source": "None", "data": None}

    def _format_acoustid_result(self, matches: list) -> dict:
        """Transforms raw AcoustID match results into a complete release structure using MusicBrainz."""
        if not matches:
            return None

        top_match = matches[0]
        rec_id = top_match.get("recording_id", "")

        if rec_id and self.mb_service:
            print(f" -> Querying MusicBrainz for full release using Recording ID: {rec_id}...")
            full_release = self.mb_service.lookup_release_by_recording(rec_id)
            if full_release:
                print(" -> Successfully retrieved full album tracklist via AcoustID -> MusicBrainz!")
                return full_release

        track_title = top_match.get("title") or "Unknown Track"
        artist_name = top_match.get("artist") or "Unknown Artist"

        track_item = {
            "track_number": 1,
            "number": "1",
            "title": track_title,
            "duration": ""
        }

        return {
            "artist": artist_name,
            "title": f"AcoustID Match ({rec_id[:8]})",
            "year": "",
            "tracks": [track_item],
            "tracklist": [track_item]
        }

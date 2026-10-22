from services.musicbrainz import MusicBrainzService
from services.discogs_service import DiscogsService
from services.acoustid_service import AcoustIDService
from ripperCore.ripper import CDRipper

class MetadataManager:
    def __init__(self, discogs_token: str = None, acoustid_key: str = None):
        self.mb_service = MusicBrainzService()
        self.discogs_service = DiscogsService(user_token=discogs_token) if discogs_token else None
        self.acoustid_service = AcoustIDService(api_key=acoustid_key) if acoustid_key else None

    def fetch_metadata_for_cd(self, discid: str, sample_track_path: str = None, user_query: dict = None):
        # --- ISOLATED TEST MODE TOGGLE ---
        # Set to: "musicbrainz", "discogs", "acoustid", or None for normal production flow
        ACTIVE_TEST_MODE = None 
        #ACTIVE_TEST_MODE = "discogs"
        #ACTIVE_TEST_MODE = "acoustid"  

        if ACTIVE_TEST_MODE:
            return self._execute_test_mode(ACTIVE_TEST_MODE, discid, sample_track_path, user_query)

        # --- NORMAL HIERARCHICAL FLOW ---
        print("[1/3] Querying MusicBrainz via DiscID...")
        mb_result = self.mb_service.lookup_by_discid(discid)
        if mb_result:
            print(" -> Found match on MusicBrainz!")
            return {"source": "MusicBrainz", "data": mb_result}

        print("[2/3] MusicBrainz returned no match. Trying Discogs...")
        if self.discogs_service and user_query:
            discogs_results = self.discogs_service.search_release(
                artist=user_query.get("artist"),
                album=user_query.get("album"),
                catno=user_query.get("catno")
            )
            if discogs_results:
                print(" -> Found match on Discogs!")
                return {"source": "Discogs", "data": discogs_results[0]}

        print("[3/3] Discogs returned no match. Attempting AcoustID Audio Fingerprinting...")
        if self.acoustid_service and sample_track_path:
            acoustid_matches = self.acoustid_service.lookup_track(sample_track_path)
            if acoustid_matches:
                print(" -> Found match via AcoustID Fingerprint!")
                return {"source": "AcoustID", "data": self._format_acoustid_result(acoustid_matches)}

        print(" -> All automated lookups failed. Pivot to Manual Curation Mode.")
        return {"source": "None", "data": None}

    def _execute_test_mode(self, mode: str, discid: str, sample_track_path: str, user_query: dict):
        """Isolates a single metadata service for testing purposes."""
        print(f"\n[TEST MODE ACTIVE] Isolating service: {mode.upper()}")

        if mode == "musicbrainz":
            mb_result = self.mb_service.lookup_by_discid(discid)
            if mb_result:
                print(" -> [Test] MusicBrainz lookup successful!")
                return {"source": "MusicBrainz", "data": mb_result}
            print(" -> [Test] MusicBrainz returned no match.")

        elif mode == "discogs":
            query_to_use = user_query if user_query else {"artist": "Miles Davis", "album": "Kind of Blue"}
            print(f" -> [Test] Querying Discogs with: {query_to_use}")
            if self.discogs_service:
                discogs_results = self.discogs_service.search_release(
                    artist=query_to_use.get("artist"),
                    album=query_to_use.get("album"),
                    catno=query_to_use.get("catno")
                )
                if discogs_results:
                    print(" -> [Test] Discogs search successful!")
                    return {"source": "Discogs", "data": discogs_results[0]}
            print(" -> [Test] Discogs returned no match.")

        elif mode == "acoustid":
            print(" -> [Test] Initiating live sample rip of Track 1 for fingerprinting...")
            temp_sample_path = "/tmp/orange_ripper_test_track1.wav"
            
            try:
                ripper = CDRipper()
                success = ripper.rip_track(track_number=1, output_wav_path=temp_sample_path)
                
                if success:
                    print(f" -> [Test] Fingerprinting audio file: {temp_sample_path}")
                    if self.acoustid_service:
                        acoustid_matches = self.acoustid_service.lookup_track(temp_sample_path)
                        if acoustid_matches:
                            print(" -> [Test] AcoustID fingerprint match successful!")
                            result = self._format_acoustid_result(acoustid_matches)
                            return {"source": "AcoustID", "data": result}
            except Exception as e:
                print(f" -> [Test] Live sample rip or fingerprint failed: {e}")
            finally:
                # Clean up the temporary test wav file
                import os
                if os.path.exists(temp_sample_path):
                    try:
                        os.remove(temp_sample_path)
                    except OSError:
                        pass

            print(" -> [Test] AcoustID returned no match or service uninitialized.")
            return {"source": "None", "data": None}

    def _format_acoustid_result(self, matches: list) -> dict:
        """Helper to safely transform raw AcoustID match results into the UI release structure."""
        top_match = matches[0] if matches else {}
        
        track_title = top_match.get("title") or "So What"
        artist_name = top_match.get("artist") or "Miles Davis"
        rec_id = top_match.get("recording_id", "")

        track_item = {
            "track_number": 1,
            "number": "1",
            "title": track_title,
            "duration": "9:24"
        }

        return {
            "artist": artist_name,
            "title": f"Kind of Blue (AcoustID Match: {rec_id[:8]})",
            "year": "1959",
            "tracks": [track_item],
            "tracklist": [track_item]
        }

    def _format_acoustid_result(self, matches: list) -> dict:
        """Transforms raw AcoustID match results into a complete release structure using MusicBrainz."""
        if not matches:
            return None

        top_match = matches[0]
        rec_id = top_match.get("recording_id", "")

        # 1. Try fetching full release tracklist via MusicBrainz using Recording ID
        if rec_id and self.mb_service:
            print(f" -> Querying MusicBrainz for full release using Recording ID: {rec_id}...")
            full_release = self.mb_service.lookup_release_by_recording(rec_id)
            if full_release:
                print(" -> Successfully retrieved full album tracklist via AcoustID -> MusicBrainz!")
                return full_release

        # 2. Fallback if MB lookup fails or returns no releases
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

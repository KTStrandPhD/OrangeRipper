import discogs_client
import re

class DiscogsService:
    def __init__(self, user_token: str, user_agent="OrangeRipper/0.1"):
        """
        Initialize Discogs client using a Personal Access Token.
        Get a token at https://www.discogs.com/settings/developers
        """
        self.client = discogs_client.Client(user_agent, user_token=user_token)

    def _sanitize_query(self, text: str) -> str:
        """Cleans up search strings by removing parenthetical tags and extra whitespace."""
        if not text:
            return ""
        cleaned = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', text)
        return " ".join(cleaned.split())

    def _parse_release_item(self, item):
        """Helper to parse a discogs_client Release or Master object into a standard dict."""
        tracklist = []
        target_tracklist = getattr(item, 'tracklist', [])
        for track in target_tracklist:
            raw_duration = getattr(track, 'duration', '')
            duration_str = str(raw_duration) if raw_duration else ""

            tracklist.append({
                "position": getattr(track, 'position', ''),
                "title": getattr(track, 'title', 'Unknown Track'),
                "duration": duration_str
            })

        artist_name = ""
        if hasattr(item, 'artists') and item.artists:
            artist_name = item.artists[0].name
        elif hasattr(item, 'title') and " - " in item.title:
            artist_name = item.title.split(" - ")[0]

        release_title = getattr(item, 'title', '')
        if " - " in release_title and hasattr(item, 'artists') and item.artists:
            release_title = release_title.split(" - ", 1)[1]

        formats = []
        if hasattr(item, 'formats') and item.formats:
            for fmt in item.formats:
                formats.append(fmt.get('name', ''))

        cover_url = None
        if hasattr(item, 'images') and item.images and len(item.images) > 0:
            cover_url = item.images[0].get('resource_url') or item.images[0].get('uri')

        return {
            "id": item.id,
            "artist": artist_name,
            "title": release_title,
            "year": getattr(item, 'year', None),
            "formats": formats,
            "labels": [label.name for label in item.labels] if hasattr(item, 'labels') else [],
            "cover_art_url": cover_url,
            "tracklist": tracklist
        }

    def search_release(self, artist: str = None, album: str = None, catno: str = None, expected_track_count: int = None, release_id: int = None):
        """
        Granular multi-pass search strategy designed to capture indie, underground, 
        and hard-to-index releases on Discogs.
        """
        try:
            releases_map = {} # Use a dictionary keyed by item.id to prevent duplicate entries across passes

            def add_results(results_iterable, limit=15):
                count = 0
                for item in results_iterable:
                    if count >= limit:
                        break
                    try:
                        parsed = self._parse_release_item(item)
                        if parsed["id"] not in releases_map and parsed["title"]:
                            releases_map[parsed["id"]] = parsed
                            count += 1
                    except Exception:
                        continue

            # Pass 1: Direct Release ID lookup
            if release_id:
                print(f"[DiscogsService] Pass 1: Direct ID lookup -> {release_id}")
                try:
                    direct_item = self.client.release(release_id)
                    if direct_item:
                        parsed = self._parse_release_item(direct_item)
                        return [parsed]
                except Exception as e:
                    print(f" -> Direct ID lookup failed: {e}")

            clean_artist = self._sanitize_query(artist)
            clean_album = self._sanitize_query(album)

            print(f"[DiscogsService] Searching Discogs -> Artist: '{clean_artist}', Album: '{clean_album}', CatNo: '{catno}'")

            # Pass 2: Catalog number search
            if catno:
                print("[DiscogsService] Pass 2: Searching by Catalog Number...")
                add_results(self.client.search(catno=catno, type="release"))

            # Pass 3: Strict Field Search (Artist + Release Title fields explicitly mapped)
            if clean_artist and clean_album:
                print("[DiscogsService] Pass 3: Searching via strict parameters (artist + release_title)...")
                add_results(self.client.search(artist=clean_artist, release_title=clean_album))

            # Pass 4: Broad General Text Search (q parameter)
            query_str = f"{clean_artist} {clean_album}".strip()
            if query_str:
                print(f"[DiscogsService] Pass 4: Searching via general query string (q='{query_str}')...")
                add_results(self.client.search(q=query_str))

            # Pass 5: Album-Only Fallback (Drops artist name in case artist credit formatting varies)
            if clean_album and len(releases_map) == 0:
                print(f"[DiscogsService] Pass 5: Fallback to album title only ('{clean_album}')...")
                add_results(self.client.search(release_title=clean_album))

            releases = list(releases_map.values())
            print(f"[DiscogsService] Total unique candidates collected: {len(releases)}")

            # Prioritize tracks matching the physical media track count if available
            if expected_track_count and releases:
                releases.sort(key=lambda r: abs(len(r.get("tracklist", [])) - expected_track_count))

            return releases[:5]

        except Exception as e:
            print(f"Discogs search failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return []

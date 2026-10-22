import discogs_client

class DiscogsService:
    def __init__(self, user_token: str, user_agent="OrangeRipper/0.1"):
        """
        Initialize Discogs client using a Personal Access Token.
        Get a token at https://www.discogs.com/settings/developers
        """
        self.client = discogs_client.Client(user_agent, user_token=user_token)

    def search_release(self, artist: str = None, album: str = None, catno: str = None):
        """
        Searches Discogs for a matching release using artist/album query or catalog number.
        Returns a list of structured release objects.
        """
        try:
            # Build search params
            query_params = {"type": "release"}
            if catno:
                query_params["catno"] = catno
            if artist:
                query_params["artist"] = artist
            if album:
                query_params["release_title"] = album

            results = self.client.search(**query_params)
            
            releases = []
            count = 0
            for item in results:
                if count >= 5:
                    break
                count += 1

                tracklist = []
                for track in item.tracklist:
                    raw_duration = getattr(track, 'duration', '')
                    duration_str = str(raw_duration) if raw_duration else ""

                    tracklist.append({
                        "position": getattr(track, 'position', ''),
                        "title": getattr(track, 'title', 'Unknown Track'),
                        "duration": duration_str
                    })

                # Safely parse artist name
                artist_name = ""
                if hasattr(item, 'artists') and item.artists:
                    artist_name = item.artists[0].name
                elif " - " in item.title:
                    artist_name = item.title.split(" - ")[0]

                # Parse release title without artist prefix if combined
                release_title = item.title
                if " - " in release_title and hasattr(item, 'artists') and item.artists:
                    release_title = item.title.split(" - ", 1)[1]

                releases.append({
                    "id": item.id,
                    "artist": artist_name,
                    "title": release_title,
                    "year": getattr(item, 'year', None),
                    "labels": [label.name for label in item.labels] if hasattr(item, 'labels') else [],
                    "cover_art_url": item.images[0]['resource_url'] if item.images and len(item.images) > 0 else None,
                    "tracklist": tracklist
                })
            return releases

        except Exception as e:
            print(f"Discogs search failed: {e}")
            return []

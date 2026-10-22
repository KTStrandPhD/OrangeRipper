import acoustid

class AcoustIDService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def lookup_track(self, file_path: str):
        try:
            results = acoustid.match(self.api_key, file_path)
            matches = []
            for score, recording_id, title, artist in results:
                matches.append({
                    "score": round(score * 100, 2),
                    "recording_id": recording_id,
                    "title": title or "",
                    "artist": artist or ""
                })
            matches.sort(key=lambda x: x["score"], reverse=True)
            return matches
        except Exception as e:
            print(f"Failed to fingerprint or lookup audio: {e}")
            return []

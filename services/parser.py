import re

class TracklistParser:
    @staticmethod
    def parse_text_block(raw_text: str) -> dict:
        """
        Parses a pasted block of text into structured album metadata and a tracklist.
        Handles common formats like:
        - 1. Song Title (3:45)
        - 02 - Song Title - 4:12
        - Track 3: Song Title
        """
        lines = raw_text.strip().split("\n")
        
        metadata = {
            "artist": None,
            "album": None,
            "year": None,
            "tracks": []
        }

        # Regex patterns for matching tracks
        # Matches: Optional track number, separator, title, optional duration at the end
        track_pattern = re.compile(
            r'^(?:track\s*)?(\d{1,2})[\.\)\-\s]+\s*(.+?)(?:\s+[\(\[\-]{1,2}\s*(\d{1,2}:\d{2})\s*[\)\]])?$',
            re.IGNORECASE
        )

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line looks like an album header (e.g., "Artist - Album Name (2020)")
            if not metadata["album"] and (" - " in line or "(" in line) and not track_pattern.match(line):
                if " - " in line:
                    parts = line.split(" - ", 1)
                    metadata["artist"] = parts[0].strip()
                    metadata["album"] = parts[1].strip()
                else:
                    metadata["album"] = line
                continue

            # Match regular track lines
            match = track_pattern.match(line)
            if match:
                track_num, title, duration = match.groups()
                
                # Clean up any trailing garbage on the title
                title = title.strip().strip("-").strip()
                
                metadata["tracks"].append({
                    "track_number": int(track_num),
                    "title": title,
                    "duration": duration if duration else "00:00"
                })
            else:
                # Fallback for unformatted lines that might just be track titles
                # Assign sequential track numbers if regex didn't explicitly catch a number
                next_num = len(metadata["tracks"]) + 1
                metadata["tracks"].append({
                    "track_number": next_num,
                    "title": line,
                    "duration": "00:00"
                })

        return metadata

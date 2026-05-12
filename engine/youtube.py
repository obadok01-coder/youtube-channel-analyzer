import re
from typing import Dict, List, Tuple

import httpx


class YouTubeAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"

    async def _fetch(self, client: httpx.AsyncClient, endpoint: str, params: dict) -> dict:
        params["key"] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise ValueError(data["error"].get("message", "YouTube API error"))
        return data

    async def resolve_channel(self, client: httpx.AsyncClient, url: str) -> Tuple[str, str, str]:
        url = url.strip()

        # --- @handle format ---
        handle_match = re.search(r"@([a-zA-Z0-9_.-]+)", url)
        if handle_match:
            handle = handle_match.group(1)
            try:
                data = await self._fetch(client, "channels", {"part": "snippet", "forHandle": handle})
            except Exception:
                data = await self._fetch(client, "channels", {"part": "snippet", "forUsername": handle})
            if data.get("items"):
                ch = data["items"][0]
                return ch["id"], ch["snippet"]["title"], ch["snippet"]["thumbnails"]["default"]["url"]

        # --- /channel/UCxxx format ---
        cid_match = re.search(r"/channel/(UC[a-zA-Z0-9_-]+)", url)
        if cid_match:
            channel_id = cid_match.group(1)
            data = await self._fetch(client, "channels", {"part": "snippet", "id": channel_id})
            if data.get("items"):
                ch = data["items"][0]
                return ch["id"], ch["snippet"]["title"], ch["snippet"]["thumbnails"]["default"]["url"]

        # --- /c/ or /user/ format ---
        for pat in [r"/c/([a-zA-Z0-9_-]+)", r"/user/([a-zA-Z0-9_-]+)"]:
            m = re.search(pat, url)
            if m:
                username = m.group(1)
                data = await self._fetch(client, "search", {
                    "part": "snippet", "q": username, "type": "channel", "maxResults": 1
                })
                if data.get("items"):
                    cid = data["items"][0]["snippet"]["channelId"]
                    cdata = await self._fetch(client, "channels", {"part": "snippet", "id": cid})
                    if cdata.get("items"):
                        ch = cdata["items"][0]
                        return ch["id"], ch["snippet"]["title"], ch["snippet"]["thumbnails"]["default"]["url"]

        # --- direct channel ID ---
        if re.match(r"^UC[a-zA-Z0-9_-]{22}$", url):
            data = await self._fetch(client, "channels", {"part": "snippet", "id": url})
            if data.get("items"):
                ch = data["items"][0]
                return ch["id"], ch["snippet"]["title"], ch["snippet"]["thumbnails"]["default"]["url"]

        # --- search fallback ---
        data = await self._fetch(client, "search", {
            "part": "snippet", "q": url, "type": "channel", "maxResults": 1
        })
        if data.get("items"):
            cid = data["items"][0]["snippet"]["channelId"]
            cdata = await self._fetch(client, "channels", {"part": "snippet", "id": cid})
            if cdata.get("items"):
                ch = cdata["items"][0]
                return ch["id"], ch["snippet"]["title"], ch["snippet"]["thumbnails"]["default"]["url"]

        raise ValueError("Could not resolve channel from URL. Please provide a valid YouTube channel URL or @handle.")

    async def get_uploads_playlist(self, client: httpx.AsyncClient, channel_id: str) -> str:
        data = await self._fetch(client, "channels", {"part": "contentDetails", "id": channel_id})
        if not data.get("items"):
            raise ValueError("Channel not found")
        return data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    async def get_videos_from_playlist(self, client: httpx.AsyncClient, playlist_id: str, limit: int = 50) -> List[dict]:
        videos = []
        page_token = None
        while len(videos) < limit:
            params = {
                "part": "snippet",
                "playlistId": playlist_id,
                "maxResults": min(50, limit - len(videos)),
            }
            if page_token:
                params["pageToken"] = page_token
            data = await self._fetch(client, "playlistItems", params)
            for item in data.get("items", []):
                snip = item["snippet"]
                videos.append({
                    "video_id": snip["resourceId"]["videoId"],
                    "title": snip["title"],
                    "thumbnail": snip.get("thumbnails", {}).get("default", {}).get("url", ""),
                    "published_at": snip["publishedAt"],
                })
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return videos[:limit]

    async def get_video_details(self, client: httpx.AsyncClient, video_ids: List[str]) -> List[dict]:
        all_details = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            data = await self._fetch(client, "videos", {
                "part": "statistics,contentDetails",
                "id": ",".join(batch),
            })
            for item in data.get("items", []):
                st = item.get("statistics", {})
                cd = item.get("contentDetails", {})
                all_details.append({
                    "video_id": item["id"],
                    "views": int(st.get("viewCount", 0)),
                    "likes": int(st.get("likeCount", 0)),
                    "comments": int(st.get("commentCount", 0)),
                    "duration": cd.get("duration", ""),
                })
        return all_details

    def calculate_outliers(self, videos: List[dict]) -> Tuple[List[dict], float]:
        if not videos:
            return [], 0.0
        views_list = [v["views"] for v in videos if v.get("views", 0) > 0]
        if not views_list:
            return [], 0.0
        avg = sum(views_list) / len(views_list)
        threshold = avg * 3
        outliers = []
        for v in videos:
            vv = v.get("views", 0)
            if vv >= threshold and vv > 0:
                ratio = vv / avg
                outliers.append({
                    **v,
                    "avg_views": round(avg, 2),
                    "ratio": round(ratio, 2),
                })
        outliers.sort(key=lambda x: x["ratio"], reverse=True)
        return outliers, round(avg, 2)

    async def analyze_channel(self, url: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            channel_id, channel_name, channel_thumbnail = await self.resolve_channel(client, url)
            uploads_id = await self.get_uploads_playlist(client, channel_id)
            videos = await self.get_videos_from_playlist(client, uploads_id, limit=50)
            if not videos:
                return {
                    "channel_name": channel_name,
                    "channel_thumbnail": channel_thumbnail,
                    "channel_id": channel_id,
                    "total_videos_analyzed": 0,
                    "average_views": 0.0,
                    "all_videos": [],
                    "outliers": [],
                }
            video_ids = [v["video_id"] for v in videos]
            details = await self.get_video_details(client, video_ids)
            det_map = {d["video_id"]: d for d in details}
            for v in videos:
                det = det_map.get(v["video_id"], {})
                v["views"] = det.get("views", 0)
                v["likes"] = det.get("likes", 0)
                v["comments"] = det.get("comments", 0)
                v["duration"] = det.get("duration", "")
                v["link"] = f"https://youtube.com/watch?v={v['video_id']}"
            outliers, avg_views = self.calculate_outliers(videos)
            return {
                "channel_name": channel_name,
                "channel_thumbnail": channel_thumbnail,
                "channel_id": channel_id,
                "total_videos_analyzed": len(videos),
                "average_views": avg_views,
                "all_videos": videos,
                "outliers": outliers,
            }

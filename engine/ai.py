from typing import Optional

from openai import AsyncOpenAI


class AIAnalyzer:
    def __init__(
        self,
        openai_key: Optional[str] = None,
        gemini_key: Optional[str] = None,
        deepseek_key: Optional[str] = None,
    ):
        self.openai_client = None
        self.deepseek_client = None
        self.gemini_model = None

        if openai_key:
            self.openai_client = AsyncOpenAI(api_key=openai_key)

        if deepseek_key:
            self.deepseek_client = AsyncOpenAI(
                api_key=deepseek_key,
                base_url="https://api.deepseek.com/v1",
            )

        if gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel("models/gemini-2.0-flash")

    async def analyze_title(self, title: str) -> Optional[str]:
        client = self.openai_client or self.deepseek_client
        if not client:
            return None
        try:
            model = "gpt-4o-mini" if self.openai_client else "deepseek-chat"
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a YouTube analytics expert. Analyze the video title in 1-2 concise sentences. "
                            "Explain the engagement hooks, emotional triggers, curiosity gaps, or power words used. "
                            "Reply in Arabic."
                        ),
                    },
                    {"role": "user", "content": f'Analyze this title: "{title}"'},
                ],
                max_tokens=200,
                temperature=0.7,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"[AI unavailable: {str(e)[:80]}]"

    def _fetch_transcript_text(self, video_id: str) -> Optional[str]:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            result = api.fetch(video_id, languages=["en"], preserve_formatting=True)
            return " ".join(s.text for s in result.snippets if s.text.strip())
        except Exception:
            try:
                result = api.fetch(video_id, languages=["en"], preserve_formatting=False)
                return " ".join(s.text for s in result.snippets if s.text.strip())
            except Exception:
                return None

    async def analyze_transcript(self, video_id: str) -> Optional[str]:
        if not self.gemini_model:
            return None
        try:
            full_text = self._fetch_transcript_text(video_id)
            if not full_text:
                return None
            if len(full_text) > 12000:
                full_text = full_text[:12000]

            prompt = (
                "Analyze this YouTube video transcript in 2-3 Arabic sentences:\n"
                "- Key topics covered\n"
                "- Engagement techniques / hooks used\n"
                "- Value provided to viewers\n\n"
                f"Transcript:\n{full_text}"
            )
            resp = self.gemini_model.generate_content(prompt)
            return resp.text.strip()
        except Exception as e:
            return f"[Transcript unavailable: {str(e)[:80]}]"

import asyncio
import uuid
import aiofile
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent


class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, output_stream):
        super().__init__(output_stream)
        self.transcript = ''

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        for result in transcript_event.transcript.results:
            if not result.is_partial:
                self.transcript += result.alternatives[0].transcript + ' '


class TranscriptionService:
    def __init__(self, region='us-east-1'):
        self.region = region

    def transcribe_from_file(self, filepath):
        return asyncio.run(self._start_stream(filepath))

    async def _start_stream(self, filepath):
        client = TranscribeStreamingClient(region=self.region)
        stream = await client.start_stream_transcription(
            language_code='en-US',
            media_sample_rate_hz=16000,
            media_encoding='pcm'
        )

        handler = MyEventHandler(stream.output_stream)

        async def write_chunks():
            async with aiofile.AIOFile(filepath, 'rb') as af:
                reader = aiofile.Reader(af, chunk_size=1024 * 16)
                async for chunk in reader:
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
            await stream.input_stream.end_stream()

        await asyncio.gather(write_chunks(), handler.handle_events())

        return handler.transcript.strip()
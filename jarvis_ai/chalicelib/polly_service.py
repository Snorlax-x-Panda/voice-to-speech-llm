import boto3
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing
import os
import sys
import subprocess
from tempfile import gettempdir
from botocore.exceptions import BotoCoreError, ClientError
import base64

class PollyService:
    def __init__(self):
        self.client = boto3.client('polly')
        

    def synthesize(self, text, voice="Joanna"):
        try:
            response = self.client.synthesize_speech(Text=text, OutputFormat="mp3", VoiceId=voice)
        except (BotoCoreError, ClientError) as error:
            print(error)
            sys.exit(-1)

        if "AudioStream" in response:
            with closing(response["AudioStream"]) as stream:
                output = os.path.join(gettempdir(), "speech.mp3")

                try:
                    # Open a file for writing the output as a binary stream
                    with open(output, "wb") as file:
                        file.write(stream.read())
                    with open(output, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                    return encoded
                except IOError as error:
                    # Could not write to file, exit gracefully
                    print(error)
                    sys.exit(-1)

        else:
            # The response didn't contain audio data, exit gracefully
            print("Could not stream audio")
            sys.exit(-1)
        
        
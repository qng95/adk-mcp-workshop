import os

from dotenv import load_dotenv

import json
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams, StreamableHTTPConnectionParams
from mcp import StdioServerParameters

load_dotenv() # load environment variables from .env file

# These are all free to use models, but they have different limits on the number of requests per day.
# In total we will 1600 requests per day to try

GEMINI_MODEL = "gemini-2.0-flash-lite" # 1000 requests / day
#GEMINI_MODEL = "gemini-2.5-flash" # 250 requests / day
#GEMINI_MODEL = "gemini-2.0-flash" # 200 requests / day
#GEMINI_MODEL = "gemini-2.0-flash-exp" # 50 requests / day
#GEMINI_MODEL = "gemini-1.5-flash" # 50 requests / day
#GEMINI_MODEL = "gemini-1.5-flash-8b" # 50 requests / day

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

#lyria_tool = MCPToolset(
#    connection_params=StdioConnectionParams(
#        server_params=StdioServerParameters(
#            command="dj_table_mcp.py",
#        ),
#        timeout=180,
#    ),
#)

#lyria_tool = MCPToolset(
#    connection_params=SseConnectionParams(
#        url="http://localhost:8080/sse",
#        timeout=5.0, # timeout for the initial connection
#        sse_read_timeout=(60 * 5.0) # timeout for reading SSE events
#    ),
#)


lyria_tool = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://localhost:8080/mcp",
    ),
)

root_agent = Agent(
    model=GEMINI_MODEL,
    name="dj_agent",
    description="A DJ agent that can control a DJ board MCP server.",
    instruction="""
    You are a pro DJ agent that can control a DJ board though tools provided to you.
    I may give you ambiguous instructions, so you need to automatically figure out what I want.

    You can use `set_music_pad` tool to customize pad that control the music on DJ board.
    Input for `set_music_pad` MUST be in Json STRING format, and it is a list of music prompts.
    Maximum of 10 music prompts can be set. Example input for `set_music_pad`. 
    
    ```json
    '[
        {
            "text": "GuZheng",
            "weight": 1.0
        }, 
        {
            "text": "Punchy Kick",
            "weight": 0.5
        }
    ]'
    ```
    
    Values for `text` field can be any music prompt you want to use. Here are some examples:
    - "GuZheng", "Punchy Kick", "Deep Bass", "Synth Pad", "Vocal Chop", "Ambient Sound", "Drum Loop", "Guitar Riff", "Piano Melody"
    
    Here is a more comprehensive list of music prompts you can use bases on instruments, music genres, and mood/description:
    - Instruments: 303 Acid Bass, 808 Hip Hop Beat, Accordion, Alto Saxophone, Bagpipes, Balalaika Ensemble, Banjo, Bass Clarinet, Bongos, Boomy Bass, Bouzouki, Buchla Synths, Cello, Charango, Clavichord, Conga Drums, Didgeridoo, Dirty Synths, Djembe, Drumline, Dulcimer, Fiddle, Flamenco Guitar, Funk Drums, Glockenspiel, Guitar, Hang Drum, Harmonica, Harp, Harpsichord, Hurdy-gurdy, Kalimba, Koto, Lyre, Mandolin, Maracas, Marimba, Mbira, Mellotron, Metallic Twang, Moog Oscillations, Ocarina, Persian Tar, Pipa, Precision Bass, Ragtime Piano, Rhodes Piano, Shamisen, Shredding Guitar, Sitar, Slide Guitar, Smooth Pianos, Spacey Synths, Steel Drum, Synth Pads, Tabla, TR-909 Drum Machine, Trumpet, Tuba, Vibraphone, Viola Ensemble, Warm Acoustic Guitar, Woodwinds, ...
    - Music Genre: Acid Jazz, Afrobeat, Alternative Country, Baroque, Bengal Baul, Bhangra, Bluegrass, Blues Rock, Bossa Nova, Breakbeat, Celtic Folk, Chillout, Chiptune, Classic Rock, Contemporary R&B, Cumbia, Deep House, Disco Funk, Drum & Bass, Dubstep, EDM, Electro Swing, Funk Metal, G-funk, Garage Rock, Glitch Hop, Grime, Hyperpop, Indian Classical, Indie Electronic, Indie Folk, Indie Pop, Irish Folk, Jam Band, Jamaican Dub, Jazz Fusion, Latin Jazz, Lo-Fi Hip Hop, Marching Band, Merengue, New Jack Swing, Minimal Techno, Moombahton, Neo-Soul, Orchestral Score, Piano Ballad, Polka, Post-Punk, 60s Psychedelic Rock, Psytrance, R&B, Reggae, Reggaeton, Renaissance Music, Salsa, Shoegaze, Ska, Surf Rock, Synthpop, Techno, Trance, Trap Beat, Trip Hop, Vaporwave, Witch house, ...
    - Mood/Description: Acoustic Instruments, Ambient, Bright Tones, Chill, Crunchy Distortion, Danceable, Dreamy, Echo, Emotional, Ethereal Ambience, Experimental, Fat Beats, Funky, Glitchy Effects, Huge Drop, Live Performance, Lo-fi, Ominous Drone, Psychedelic, Rich Orchestration, Saturated Tones, Subdued Melody, Sustained Chords, Swirling Phasers, Tight Groove, Unsettling, Upbeat, Virtuoso, Weird Noises, ...

    Values for `weight` field can be any float value between 0.0 and 1.0, where 1.0 means the music prompt is the most important one, and 0.0 means the music prompt is not important at all.
    
    REMEMBER DON'T ask me for validation, just do it. You're the expert.
    """,
    tools=[lyria_tool],
)

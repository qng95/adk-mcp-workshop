#! python3
# -*- coding: utf-8 -*-

"""
DJ Table MCP Server
This module implements a DJ table MCP server that interacts with the Google GenAI Lyria RealTime model.
This server allows users to control a DJ table, play music, pause music, and set musical parameters like BPM and scale.

Author: Hong Quan Nguyen
Date: 2024-01-01
License: Apache License 2.0
"""
import json
import os
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Union, AsyncIterator, Any
from dotenv import load_dotenv

import pyaudio
import asyncio

from google import genai
from google.genai import types
from google.genai.live_music import AsyncMusicSession
from mcp import ServerSession
from mcp.server import Server
from mcp.server.fastmcp import Context, FastMCP

load_dotenv()

BUFFER_SECONDS = 1
CHUNK = 4200
FORMAT = pyaudio.paInt16
CHANNELS = 2
MODEL = "models/lyria-realtime-exp"
OUTPUT_RATE = 48000

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

INIT_PROMPTS: List[types.WeightedPrompt] = [
    types.WeightedPrompt(text="Punchy Kick", weight=0.5),
    types.WeightedPrompt(text="Bossa Nova", weight=0.3),
    types.WeightedPrompt(text="K Pop", weight=0.5),
    types.WeightedPrompt(text="Dupstep", weight=4.0),
]


@dataclass
class DJTableMCPContext:
    audio_steam: pyaudio.Stream | None = None
    session: AsyncMusicSession | None = None
    config: types.LiveMusicGenerationConfig | None = None
    play_task: asyncio.Task | None = None

    # state
    turned_on: bool = False
    is_playing: bool = False


APP_CONTEXT = DJTableMCPContext()


def start_audio_stream() -> pyaudio.Stream:
    """Start an audio stream using PyAudio."""
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=OUTPUT_RATE, output=True, frames_per_buffer=CHUNK)
    return stream


def stop_audio_stream(stream: pyaudio.Stream) -> None:
    """Stop the audio stream."""
    try:
        stream.stop_stream()
    except Exception as e:
        logging.error(f"Failed to stop audio stream: {e}. Will continue trying to close and terminate", exc_info=e)
    finally:
        stream.close()
        pyaudio.PyAudio().terminate()


async def receive_and_play_audio(ctx: DJTableMCPContext) -> None:
    session: AsyncMusicSession = ctx.session
    audio_steam: pyaudio.Stream = ctx.audio_steam

    chunks_count = 0
    async for message in session.receive():
        chunks_count += 1
        if chunks_count == 1:
            # Introduce a delay before starting playback to have a buffer for network jitter.
            await asyncio.sleep(BUFFER_SECONDS)

        if message.server_content:
            audio_data = message.server_content.audio_chunks[0].data
            audio_steam.write(audio_data)

        elif message.filtered_prompt:
            print("Prompt was filtered out: ", message.filtered_prompt)
        else:
            print("Unknown error occured with message: ", message)

        # Sleep for a very short time to yield control back to the event loop
        await asyncio.sleep(10 ** -12)


async def turn_on_dj_table(context: Context[ServerSession, DJTableMCPContext]) -> str:
    """
    Turn on the DJ table by initializing the audio stream and starting the music session.
    """
    logging.info("Turning on DJ table")

    ctx: DJTableMCPContext = context.request_context.lifespan_context

    if ctx.turned_on:
        return "DJ table is already turned on."

    ctx.play_task = asyncio.create_task(receive_and_play_audio(ctx))

    ctx.is_playing = False
    ctx.turned_on = True

    return "DJ table is now turned on and ready to play music."


async def play_music(context: Context[ServerSession, DJTableMCPContext]) -> str:
    """
    Turn on the DJ table by starting the audio stream and playing music.
    """
    logging.info("Playing music on DJ table")

    ctx: DJTableMCPContext = context.request_context.lifespan_context

    if not ctx.turned_on:
        return "DJ table is not turned on. Please turn it on first."

    if not ctx.is_playing:
        await ctx.session.play()
        ctx.is_playing = True

    return "DJ table is now playing music."


async def pause_music(context: Context[ServerSession, DJTableMCPContext]) -> str:
    """
    Pause the DJ table by stopping the audio stream and pausing music playback.
    """
    logging.info("Pause music on DJ table")

    ctx: DJTableMCPContext = context.request_context.lifespan_context

    if not ctx.turned_on:
        return "DJ table is not turned on. Please turn it on first."

    if ctx.is_playing:
        await ctx.session.pause()
        ctx.is_playing = False

    return "DJ table music playback paused."


async def set_bpm(context: Context[ServerSession, DJTableMCPContext], bpm: int) -> str:
    """
    Set the BPM (Beats Per Minute) for the music generation.

    Args:
        bpm (int): The desired BPM to set.
    """
    logging.info(f"Setting BPM to {bpm}")

    ctx: DJTableMCPContext = context.request_context.lifespan_context

    if not ctx.turned_on:
        return "DJ table is not turned on. Please turn it on first."

    if ctx.config:
        ctx.config.bpm = bpm
        await ctx.session.set_music_generation_config(config=ctx.config)
        await ctx.session.reset_context()  # Reset context to apply new BPM
        logging.info(f"BPM set to {bpm}")

    return f"BPM set to {bpm}. Music generation context reset to apply new BPM."


async def set_scale(context: Context[ServerSession, DJTableMCPContext], scale: Union[types.Scale, str]) -> str:
    """
    Set the musical scale for the music generation.

    Args:
        scale (Union[types.Scale, str]): The desired musical scale to set.
            Can be a Scale enum or a string representation of the scale.
    """
    logging.info(f"Setting scale to {scale}")

    ctx: DJTableMCPContext = context.request_context.lifespan_context

    if not ctx.turned_on:
        return "DJ table is not turned on. Please turn it on first."

    if isinstance(scale, str):
        matched_scale = next((s for s in types.Scale if s.value == scale), None)
        if matched_scale is None:
            matched_scale = types.Scale.SCALE_UNSPECIFIED

        scale = matched_scale

    if ctx.config:
        ctx.config.scale = scale
        await ctx.session.set_music_generation_config(config=ctx.config)
        await ctx.session.reset_context()  # Reset context to apply new scale
        await ctx.session.play()
        logging.info(f"Scale set to {scale.name}")

    return f"Scale set to {scale.name}. Music generation context reset to apply new scale."


async def get_possible_scales(context: Context[ServerSession, DJTableMCPContext]) -> List[str]:
    """
    Get a list of possible musical scales.

    Returns:
        List[types.Scale]: A list of available musical scales.
    """
    logging.info("Retrieving possible musical scales")

    return [
        scale.value for scale in types.Scale if scale != types.Scale.SCALE_UNSPECIFIED
    ]

async def set_music_pad(context: Context[ServerSession, DJTableMCPContext], pad: Any) -> str:
    """
    Set the music pad with a list of music prompts in JSON format.

    Args:
        pad (str): A JSON string representing a list of music prompts.
    """
    logging.info(f"Setting music pad with prompts: {pad}")

    if isinstance(pad, str):
        logging.info(f"Pad is a str we will keep it as is.")
        pad = pad.strip()

    if isinstance(pad, list):
        logging.info(f"Pad is a list, now convert it back to string.")
        pad = json.dumps(pad)

    ctx: DJTableMCPContext = context.request_context.lifespan_context

    if not ctx.turned_on:
        return "DJ table is not turned on. Please turn it on first."

    try:
        prompts = [types.WeightedPrompt(**prompt) for prompt in json.loads(pad)]
        await ctx.session.set_weighted_prompts(prompts=prompts)
        await ctx.session.reset_context()  # Reset context to apply new prompts
        logging.info("Music pad set successfully")
        return "Music pad set successfully."
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON format for music pad: {e}")
        return "Invalid JSON format for music pad. Please provide a valid JSON string."

def app_factory() -> FastMCP:
    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncIterator[DJTableMCPContext]:
        """
        Lifespan context manager for the MCP server.
        """
        logging.info("Starting MCP server")

        async with client.aio.live.music.connect(model=MODEL) as session:
            # initialize the session with some default configuration
            await session.set_weighted_prompts(prompts=INIT_PROMPTS)

            # Set initial BPM and Scale
            config.bpm = 160
            config.scale = types.Scale.G_MAJOR_E_MINOR  # Example initial scale
            print(f"Setting initial BPM to {config.bpm} and scale to {config.scale.name}")

            await session.set_music_generation_config(config=config)

            context = DJTableMCPContext(
                audio_steam=stream,
                session=session,
                config=config,
                is_playing=False
            )

            yield context

    client = genai.Client(
        api_key=GOOGLE_API_KEY,
        http_options={'api_version': 'v1alpha', },  # v1alpha since Lyria RealTime is only experimental
    )
    stream: pyaudio.Stream = start_audio_stream()
    logging.info("MCP server started")

    config = types.LiveMusicGenerationConfig()

    mcp = FastMCP("DJ table MCP", lifespan=lifespan, port=8080)
    mcp.tool()(turn_on_dj_table)
    mcp.tool()(play_music)
    mcp.tool()(pause_music)
    mcp.tool()(set_bpm)
    mcp.tool()(set_scale)
    mcp.tool()(set_music_pad)

    return mcp
    
def main():
    app = app_factory()
    app.run(transport="streamable-http")

if __name__ == "__main__":
    main()
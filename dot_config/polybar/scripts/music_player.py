#!/usr/bin/env python
"""
Generalized music player status script for polybar
Supports any MPRIS-compatible player via PlayerCTL or D-Bus
Based on the original Spotify script from https://github.com/Jvanrhijn/polybar-spotify
"""
import sys
import subprocess
import argparse
import dbus
from typing import Optional, Dict, Any

parser = argparse.ArgumentParser()
parser.add_argument(
    '-t',
    '--trunclen',
    type=int,
    metavar='trunclen',
    help='Maximum length of the output string'
)
parser.add_argument(
    '-f',
    '--format',
    type=str,
    metavar='custom format',
    dest='custom_format',
    help='Custom format string (e.g., "{play_pause} {artist}: {song}")'
)
parser.add_argument(
    '-p',
    '--playpause',
    type=str,
    metavar='play-pause indicator',
    dest='play_pause',
    help='Play/pause indicators separated by comma (e.g., "▶,⏸")'
)
parser.add_argument(
    '--font',
    type=str,
    metavar='the index of the font to use for the main label',
    dest='font',
    help='Font index for main label'
)
parser.add_argument(
    '--playpause-font',
    type=str,
    metavar='the index of the font to use to display the playpause indicator',
    dest='play_pause_font',
    help='Font index for play/pause indicator'
)
parser.add_argument(
    '-q',
    '--quiet',
    action='store_true',
    help="if set, don't show any output when the current song is paused",
    dest='quiet',
)
parser.add_argument(
    '--player',
    type=str,
    metavar='player name',
    dest='player',
    help='Specific player to use (e.g., spotify, vlc). If not specified, uses the first available player'
)
parser.add_argument(
    '--method',
    type=str,
    choices=['playerctl', 'dbus', 'auto'],
    default='auto',
    help='Method to use for getting player info (default: auto)'
)

args = parser.parse_args()


def fix_string(string):
    """Corrects encoding for the python version used"""
    if sys.version_info.major == 3:
        return string
    else:
        return string.encode('utf-8')


def truncate(name, trunclen):
    """Truncate string to specified length with ellipsis"""
    if len(name) > trunclen:
        name = name[:trunclen]
        name += '...'
        if ('(' in name) and (')' not in name):
            name += ')'
    return name


def get_player_info_playerctl(player: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get player information using PlayerCTL"""
    try:
        # Build playerctl command
        cmd = ['playerctl']
        if player:
            cmd.extend(['-p', player])

        # Get status
        status_cmd = cmd + ['status']
        status_result = subprocess.run(status_cmd, capture_output=True, text=True, timeout=5)
        if status_result.returncode != 0:
            return None

        status = status_result.stdout.strip()

        # Get metadata
        metadata_cmd = cmd + ['metadata', '--format', '{{artist}}|||{{title}}|||{{album}}']
        metadata_result = subprocess.run(metadata_cmd, capture_output=True, text=True, timeout=5)
        if metadata_result.returncode != 0:
            return None

        metadata_parts = metadata_result.stdout.strip().split('|||')
        artist = metadata_parts[0] if len(metadata_parts) > 0 else ''
        title = metadata_parts[1] if len(metadata_parts) > 1 else ''
        album = metadata_parts[2] if len(metadata_parts) > 2 else ''

        return {
            'status': status,
            'artist': artist,
            'title': title,
            'album': album
        }
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        return None


def get_available_players_dbus() -> list:
    """Get list of available MPRIS players via D-Bus"""
    try:
        session_bus = dbus.SessionBus()
        dbus_names = session_bus.list_names()
        if dbus_names:
            return [name for name in dbus_names if name.startswith('org.mpris.MediaPlayer2.')]
        return []
    except Exception:
        return []


def get_player_info_dbus(player: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get player information using D-Bus"""
    try:
        session_bus = dbus.SessionBus()

        # If no specific player is requested, find the first available one
        if not player:
            available_players = get_available_players_dbus()
            if not available_players:
                return None
            player_bus_name = available_players[0]
        else:
            player_bus_name = f'org.mpris.MediaPlayer2.{player}'

        player_bus = session_bus.get_object(
            player_bus_name,
            '/org/mpris/MediaPlayer2'
        )

        player_properties = dbus.Interface(
            player_bus,
            'org.freedesktop.DBus.Properties'
        )

        metadata = player_properties.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
        status = player_properties.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')

        artist = ''
        if 'xesam:artist' in metadata and metadata['xesam:artist']:
            artist = str(metadata['xesam:artist'][0])

        title = ''
        if 'xesam:title' in metadata:
            title = str(metadata['xesam:title'])

        album = ''
        if 'xesam:album' in metadata:
            album = str(metadata['xesam:album'])

        return {
            'status': str(status),
            'artist': artist,
            'title': title,
            'album': album
        }
    except Exception:
        return None


def get_player_info(method: str = 'auto', player: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get player information using the specified method"""
    if method == 'playerctl':
        return get_player_info_playerctl(player)
    elif method == 'dbus':
        return get_player_info_dbus(player)
    else:  # auto
        # Try PlayerCTL first, then D-Bus as fallback
        info = get_player_info_playerctl(player)
        if info is None:
            info = get_player_info_dbus(player)
        return info


def main():
    # Default parameters
    output = '{play_pause} {artist}: {song}'
    trunclen = 35
    play_pause = '\u25B6,\u23F8'  # first character is play, second is paused

    label_with_font = '%{{T{font}}}{label}%{{T-}}'
    font = args.font
    play_pause_font = args.play_pause_font
    quiet = args.quiet

    # Parameters can be overwritten by args
    if args.trunclen is not None:
        trunclen = args.trunclen
    if args.custom_format is not None:
        output = args.custom_format
    if args.play_pause is not None:
        play_pause = args.play_pause

    # Get player information
    player_info = get_player_info(args.method, args.player)

    if not player_info:
        print('')
        return

    status = player_info['status']
    artist = player_info['artist']
    song = player_info['title']
    album = player_info['album']

    # Handle play/pause label
    play_pause_indicators = play_pause.split(',')

    if status == 'Playing':
        play_pause_symbol = play_pause_indicators[0]
    elif status == 'Paused':
        play_pause_symbol = play_pause_indicators[1] if len(play_pause_indicators) > 1 else play_pause_indicators[0]
    else:
        play_pause_symbol = ''

    if play_pause_font:
        play_pause_symbol = label_with_font.format(font=play_pause_font, label=play_pause_symbol)

    # Handle main label
    if (quiet and status == 'Paused') or (not artist and not song and not album):
        print('')
    else:
        if font:
            artist = label_with_font.format(font=font, label=artist)
            song = label_with_font.format(font=font, label=song)
            album = label_with_font.format(font=font, label=album)

        # Add 4 to trunclen to account for status symbol, spaces, and other padding characters
        print(truncate(output.format(artist=artist,
                                   song=song,
                                   play_pause=play_pause_symbol,
                                   album=album), trunclen + 4))


if __name__ == '__main__':
    main()
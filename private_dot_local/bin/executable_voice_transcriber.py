#!/usr/bin/env python3
"""
Voice Transcriber Service for i3wm
A local voice-to-text system with push-to-talk functionality
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional
import signal

import numpy as np
import sounddevice as sd
from pywhispercpp.model import Model


class NotificationService:
    """Handles desktop notifications using libnotify"""

    @staticmethod
    def send_notification(title: str, message: str, icon: str = "audio-input-microphone", urgency: str = "normal"):
        """Send a desktop notification using notify-send"""
        try:
            cmd = [
                "notify-send",
                "--urgency", urgency,
                "--icon", icon,
                "--app-name", "Voice Transcriber",
                title,
                message
            ]

            subprocess.run(cmd, check=False, capture_output=True, timeout=5)
            logging.info(f"Notification sent: {title} - {message}")
        except subprocess.TimeoutExpired:
            logging.warning("Notification send timed out")
        except FileNotFoundError:
            logging.warning("notify-send not found. Install libnotify-bin for notifications")
        except Exception as e:
            logging.warning(f"Failed to send notification: {e}")

    @staticmethod
    def notify_recording_started():
        """Notify that recording has started"""
        NotificationService.send_notification(
            "Voice Transcriber",
            "🎤 Recording started - speak now!",
            "audio-input-microphone",
            "normal"
        )

    @staticmethod
    def notify_recording_stopped():
        """Notify that recording has stopped"""
        NotificationService.send_notification(
            "Voice Transcriber",
            "⏹️ Recording stopped - processing...",
            "media-playback-stop",
            "normal"
        )

    @staticmethod
    def notify_transcription_complete(text: str):
        """Notify that transcription is complete"""
        # Truncate text for notification if too long
        display_text = text[:50] + "..." if len(text) > 50 else text
        NotificationService.send_notification(
            "Voice Transcriber",
            f"✅ Transcription complete: {display_text}",
            "dialog-information",
            "low"
        )

    @staticmethod
    def notify_transcription_failed():
        """Notify that transcription failed"""
        NotificationService.send_notification(
            "Voice Transcriber",
            "❌ Transcription failed - no text recognized",
            "dialog-error",
            "normal"
        )

    @staticmethod
    def notify_recording_too_short():
        """Notify that recording was too short"""
        NotificationService.send_notification(
            "Voice Transcriber",
            "⚠️ Recording too short - try speaking longer",
            "dialog-warning",
            "normal"
        )


class Config:
    """Configuration management"""

    def __init__(self):
        self.config_dir = Path.home() / ".local/share/voice_transcriber"
        self.config_file = self.config_dir / "config.json"
        self.models_dir = self.config_dir / "models"
        self.logs_dir = self.config_dir / "logs"

        # Create directories
        for dir_path in [self.config_dir, self.models_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Default configuration
        self.defaults = {
            "whisper_model": "small.en",
            "sample_rate": 16000,
            "max_recording_duration": 60.0,  # Increased to 60 seconds
            "device": None,  # None = default device
            "language": "en",
            "n_threads": 12,  # CPU threads for whisper.cpp
            "use_gpu": False,  # GPU acceleration
            "push_to_talk": True,  # Enable push-to-talk mode
            "min_recording_duration": 0.5,  # Minimum duration to consider valid
            "notifications_enabled": True  # Enable desktop notifications
        }

        self.config = self.load_config()

    def load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                return {**self.defaults, **config}
            except Exception as e:
                logging.warning(f"Failed to load config: {e}")

        return self.defaults.copy()

    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save config: {e}")


class WhisperTranscriber:
    """Handles pywhispercpp model loading and transcription"""

    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self._model_lock = threading.Lock()
        self.model_path = None

    def _get_model_path(self, model_name: str) -> str:
        """Get the path to the whisper.cpp model file"""
        # Map model names to whisper.cpp model files
        model_files = {
            "tiny": "ggml-tiny.bin",
            "tiny.en": "ggml-tiny.en.bin",
            "base": "ggml-base.bin",
            "base.en": "ggml-base.en.bin",
            "small": "ggml-small.bin",
            "small.en": "ggml-small.en.bin",
            "medium": "ggml-medium.bin",
            "medium.en": "ggml-medium.en.bin",
            "large": "ggml-large.bin",
            "large-v1": "ggml-large-v1.bin",
            "large-v2": "ggml-large-v2.bin",
            "large-v3": "ggml-large-v3.bin"
        }

        model_file = model_files.get(model_name, f"ggml-{model_name}.bin")
        return str(self.config.models_dir / model_file)

    def _download_model_if_needed(self, model_path: str, model_name: str):
        """Download whisper.cpp model if it doesn't exist"""
        if os.path.exists(model_path):
            return

        logging.info(f"Downloading whisper.cpp model: {model_name}")

        # Base URL for whisper.cpp models
        base_url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
        model_filename = os.path.basename(model_path)
        model_url = f"{base_url}/{model_filename}"

        try:
            import urllib.request

            def download_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(100, (downloaded * 100) // total_size)
                    print(f"\rDownloading {model_name}: {percent}%", end="", flush=True)

            urllib.request.urlretrieve(model_url, model_path, download_progress)
            print()  # New line after progress
            logging.info(f"Model downloaded successfully: {model_path}")

        except Exception as e:
            logging.error(f"Failed to download model {model_name}: {e}")
            # Fallback: try to download with curl or wget
            try:
                result = subprocess.run([
                    "curl", "-L", "-o", model_path, model_url
                ], capture_output=True, timeout=300)

                if result.returncode != 0:
                    result = subprocess.run([
                        "wget", "-O", model_path, model_url
                    ], capture_output=True, timeout=300)

                if result.returncode != 0:
                    raise Exception("Failed to download with curl or wget")

                logging.info(f"Model downloaded successfully with external tool: {model_path}")

            except Exception as e2:
                logging.error(f"All download methods failed: {e2}")
                raise Exception(f"Could not download model {model_name}. Please download manually from: {model_url}")

    def load_model(self):
        """Load pywhispercpp model (thread-safe)"""
        with self._model_lock:
            if self.model is None:
                try:
                    model_name = self.config.config['whisper_model']
                    self.model_path = self._get_model_path(model_name)

                    # Download model if needed
                    self._download_model_if_needed(self.model_path, model_name)

                    logging.info(f"Loading pywhispercpp model: {model_name}")

                    # Initialize pywhispercpp model
                    self.model = Model(
                        self.model_path,
                        n_threads=self.config.config.get('n_threads', 4),
                        print_progress=False,
                        print_realtime=False
                    )

                    logging.info("pywhispercpp model loaded successfully")

                except Exception as e:
                    logging.error(f"Failed to load pywhispercpp model: {e}")
                    raise

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio data to text using pywhispercpp"""
        if self.model is None:
            self.load_model()

        try:
            # Ensure audio is float32 and single channel
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Ensure single channel
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()

            # Normalize audio to [-1, 1] range
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data))

            # pywhispercpp expects 16kHz audio
            target_sample_rate = 16000
            current_sample_rate = self.config.config['sample_rate']

            if current_sample_rate != target_sample_rate:
                # Simple resampling (you might want to use scipy.signal.resample for better quality)
                try:
                    from scipy import signal
                    num_samples = int(len(audio_data) * target_sample_rate / current_sample_rate)
                    audio_data = signal.resample(audio_data, num_samples).astype(np.float32)
                except ImportError:
                    # Fallback: simple linear interpolation if scipy not available
                    old_length = len(audio_data)
                    new_length = int(old_length * target_sample_rate / current_sample_rate)
                    audio_data = np.interp(
                        np.linspace(0, old_length - 1, new_length),
                        np.arange(old_length),
                        audio_data
                    ).astype(np.float32)

            # Get language setting
            language = self.config.config.get('language', 'en')

            # Transcribe using pywhispercpp with language parameter
            # Pass language as a parameter to the transcribe method, not as an attribute
            if language and language != 'auto':
                try:
                    # Try with language parameter
                    segments = self.model.transcribe(audio_data, language=language)
                except TypeError:
                    # If language parameter not supported, try without it
                    logging.info("Language parameter not supported, transcribing without language setting")
                    segments = self.model.transcribe(audio_data)
            else:
                segments = self.model.transcribe(audio_data)

            # Extract text from segments
            text_parts = []
            for segment in segments:
                # Each segment has 'text' attribute
                if hasattr(segment, 'text'):
                    text_parts.append(segment.text.strip())
                elif isinstance(segment, dict) and 'text' in segment:
                    text_parts.append(segment['text'].strip())
                else:
                    # Fallback: convert to string
                    text_parts.append(str(segment).strip())

            text = ' '.join(text_parts).strip()
            logging.info(f"Transcribed: {text}")
            return text

        except Exception as e:
            logging.error(f"Transcription failed: {e}")
            # Fallback: try simple transcription without any parameters
            try:
                logging.info("Retrying transcription with basic parameters...")
                segments = self.model.transcribe(audio_data)
                text_parts = []
                for segment in segments:
                    if hasattr(segment, 'text'):
                        text_parts.append(segment.text.strip())
                    elif isinstance(segment, dict) and 'text' in segment:
                        text_parts.append(segment['text'].strip())
                    else:
                        text_parts.append(str(segment).strip())
                text = ' '.join(text_parts).strip()
                logging.info(f"Transcribed (fallback): {text}")
                return text
            except Exception as e2:
                logging.error(f"Fallback transcription also failed: {e2}")

            return ""


class AudioRecorder:
    """Handles audio recording with push-to-talk functionality"""

    def __init__(self, config: Config):
        self.config = config
        self.is_recording = False
        self.audio_buffer = []
        self.stream = None
        self.audio_file = None

    def start_recording(self) -> bool:
        """Start recording audio (push-to-talk mode)"""
        if self.is_recording:
            logging.warning("Already recording")
            return False

        sample_rate = self.config.config['sample_rate']
        device = self.config.config['device']

        logging.info("Starting push-to-talk recording...")

        self.is_recording = True
        self.audio_buffer = []

        # Create temporary file to store audio data
        self.audio_file = Path(tempfile.gettempdir()) / "voice_transcriber_audio.npy"

        def audio_callback(indata, frames, time, status):
            if status:
                logging.warning(f"Audio callback status: {status}")

            if not self.is_recording:
                return

            # Add audio to buffer
            self.audio_buffer.append(indata.copy())

        try:
            self.stream = sd.InputStream(
                callback=audio_callback,
                channels=1,
                samplerate=sample_rate,
                device=device,
                dtype=np.float32
            )
            self.stream.start()
            logging.info("Recording started - speak now!")

            # Send notification if enabled
            if self.config.config.get('notifications_enabled', True):
                NotificationService.notify_recording_started()

            return True

        except Exception as e:
            logging.error(f"Failed to start recording: {e}")
            self.is_recording = False
            return False

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return audio data"""
        if not self.is_recording:
            logging.warning("Not currently recording")
            return None

        logging.info("Stopping recording...")
        self.is_recording = False

        # Send notification if enabled
        if self.config.config.get('notifications_enabled', True):
            NotificationService.notify_recording_stopped()

        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            if self.audio_buffer:
                # Combine audio chunks
                audio_data = np.concatenate(self.audio_buffer, axis=0).flatten()
                sample_rate = self.config.config['sample_rate']
                duration = len(audio_data) / sample_rate

                logging.info(f"Recording stopped: {duration:.2f} seconds captured")

                # Check minimum duration
                min_duration = self.config.config.get('min_recording_duration', 0.5)
                if duration < min_duration:
                    logging.warning(f"Recording too short ({duration:.2f}s < {min_duration}s), skipping transcription")

                    # Send notification for short recording
                    if self.config.config.get('notifications_enabled', True):
                        NotificationService.notify_recording_too_short()

                    return None

                # Save audio data to temporary file for processing
                if self.audio_file:
                    np.save(self.audio_file, audio_data)

                return audio_data
            else:
                logging.warning("No audio data recorded")
                return None

        except Exception as e:
            logging.error(f"Error stopping recording: {e}")
            return None

    def is_currently_recording(self) -> bool:
        """Check if currently recording"""
        return self.is_recording


class TextInserter:
    """Handles text insertion using X11 tools"""

    @staticmethod
    def insert_text(text: str) -> bool:
        """Insert text at cursor position using xdotool"""
        if not text:
            return False

        try:
            # Method 1: Direct typing (faster, works in most cases)
            result = subprocess.run(
                ["xdotool", "type", "--clearmodifiers", text],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logging.info(f"Text inserted successfully: {text[:50]}...")
                return True

            logging.warning(f"xdotool type failed: {result.stderr}")

            # Method 2: Clipboard + paste (fallback for complex text)
            return TextInserter._insert_via_clipboard(text)

        except subprocess.TimeoutExpired:
            logging.error("Text insertion timed out")
            return False
        except FileNotFoundError:
            logging.error("xdotool not found. Please install: sudo apt install xdotool")
            return False
        except Exception as e:
            logging.error(f"Text insertion failed: {e}")
            return False

    @staticmethod
    def _insert_via_clipboard(text: str) -> bool:
        """Insert text via clipboard as fallback method"""
        try:
            # Copy to clipboard
            proc = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
                text=True
            )
            proc.communicate(input=text)

            if proc.returncode != 0:
                logging.error("Failed to copy to clipboard")
                return False

            # Paste from clipboard
            result = subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                capture_output=True,
                timeout=5
            )

            if result.returncode == 0:
                logging.info("Text inserted via clipboard")
                return True

            logging.error(f"Clipboard paste failed: {result.stderr}")
            return False

        except Exception as e:
            logging.error(f"Clipboard insertion failed: {e}")
            return False


class VoiceService:
    """Main service class"""

    def __init__(self):
        self.config = Config()
        self.setup_logging()
        self.transcriber = WhisperTranscriber(self.config)
        self.recorder = AudioRecorder(self.config)
        self.text_inserter = TextInserter()

        # Lock file for preventing concurrent recordings
        self.lock_file = Path(tempfile.gettempdir()) / "voice_transcriber.lock"
        self.recording_process_file = Path(tempfile.gettempdir()) / "voice_transcriber_recording.pid"

    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.config.logs_dir / "voice_transcriber.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def is_locked(self) -> bool:
        """Check if another instance is running"""
        return self.lock_file.exists()

    def acquire_lock(self) -> bool:
        """Acquire lock for exclusive recording"""
        try:
            if self.is_locked():
                return False

            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except Exception:
            return False

    def release_lock(self):
        """Release the lock"""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception:
            pass

    def start_recording_daemon(self) -> bool:
        """Start recording as a background process"""
        if not self.acquire_lock():
            logging.warning("Another recording session is active")
            return False

        try:
            success = self.recorder.start_recording()
            if not success:
                self.release_lock()
                return False

            # Write PID file for the recording process
            with open(self.recording_process_file, 'w') as f:
                f.write(str(os.getpid()))

            # Set up signal handler for clean shutdown
            def signal_handler(signum, frame):
                logging.info("Recording interrupted by signal")
                self.recorder.stop_recording()
                self.release_lock()
                if self.recording_process_file.exists():
                    self.recording_process_file.unlink()
                sys.exit(0)

            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)

            # Keep the script running until stopped
            logging.info("Recording daemon started, waiting for stop signal...")
            try:
                while self.recorder.is_currently_recording():
                    time.sleep(0.1)  # Check every 100ms
            except KeyboardInterrupt:
                logging.info("Recording interrupted by user")
                self.recorder.stop_recording()

            return True
        except Exception as e:
            logging.error(f"Failed to start recording daemon: {e}")
            self.release_lock()
            return False
        finally:
            if self.recording_process_file.exists():
                self.recording_process_file.unlink()

    def stop_recording_and_transcribe(self) -> bool:
        """Stop recording and transcribe"""
        try:
            # First, stop any running recording process
            if self.recording_process_file.exists():
                try:
                    with open(self.recording_process_file, 'r') as f:
                        pid = int(f.read().strip())
                    # Send SIGTERM to the recording process
                    os.kill(pid, signal.SIGTERM)
                    # Wait a bit for the process to stop
                    time.sleep(0.5)
                except (FileNotFoundError, ProcessLookupError, ValueError):
                    pass  # Process already stopped or PID file invalid

            # Now check if we can load audio data
            audio_file = Path(tempfile.gettempdir()) / "voice_transcriber_audio.npy"
            if audio_file.exists():
                try:
                    audio_data = np.load(audio_file)
                    audio_file.unlink()  # Clean up

                    if len(audio_data) > 0:
                        # Transcribe audio
                        text = self.transcriber.transcribe(audio_data)

                        if text:
                            # Insert transcribed text
                            success = self.text_inserter.insert_text(text)

                            # Send notification for successful transcription
                            if self.config.config.get('notifications_enabled', True):
                                NotificationService.notify_transcription_complete(text)

                            return success
                        else:
                            logging.warning("No text transcribed")

                            # Send notification for failed transcription
                            if self.config.config.get('notifications_enabled', True):
                                NotificationService.notify_transcription_failed()

                            return False
                    else:
                        logging.warning("No audio data found")
                        return False
                except Exception as e:
                    logging.error(f"Failed to load audio data: {e}")
                    return False
            else:
                logging.warning("No audio file found - recording may not have started properly")
                return False

        except Exception as e:
            logging.error(f"Stop and transcribe failed: {e}")
            return False
        finally:
            self.release_lock()

    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.recording_process_file.exists() and self.is_locked()

    def check_dependencies(self) -> bool:
        """Check if required system dependencies are available"""
        dependencies = ["xdotool", "xclip"]
        optional_dependencies = ["notify-send"]
        missing = []
        missing_optional = []

        for dep in dependencies:
            try:
                subprocess.run([dep, "--version"],
                             capture_output=True,
                             timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                missing.append(dep)

        for dep in optional_dependencies:
            try:
                subprocess.run([dep, "--version"],
                             capture_output=True,
                             timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                missing_optional.append(dep)

        if missing:
            print(f"Missing required dependencies: {', '.join(missing)}")
            print("Install with: sudo apt install " + " ".join(missing))
            return False

        if missing_optional:
            print(f"Missing optional dependencies: {', '.join(missing_optional)}")
            print("Install with: sudo apt install libnotify-bin")
            print("(Notifications will be disabled without libnotify-bin)")

        return True


def main():
    parser = argparse.ArgumentParser(description="Voice Transcriber Service - Push-to-Talk")
    parser.add_argument("--start", action="store_true",
                       help="Start recording (push-to-talk begin)")
    parser.add_argument("--stop", action="store_true",
                       help="Stop recording and transcribe (push-to-talk end)")
    parser.add_argument("--status", action="store_true",
                       help="Check if currently recording")
    parser.add_argument("--check-deps", action="store_true",
                       help="Check system dependencies")
    parser.add_argument("--config", action="store_true",
                       help="Show configuration file location")

    args = parser.parse_args()

    service = VoiceService()

    if args.check_deps:
        if service.check_dependencies():
            print("All dependencies are available")
            sys.exit(0)
        else:
            sys.exit(1)

    if args.config:
        print(f"Configuration file: {service.config.config_file}")
        print(f"Models directory: {service.config.models_dir}")
        print(f"Logs directory: {service.config.logs_dir}")
        return

    if args.status:
        if service.is_recording():
            print("Currently recording")
            sys.exit(0)
        else:
            print("Not recording")
            sys.exit(1)

    if not service.check_dependencies():
        sys.exit(1)

    success = False

    if args.start:
        success = service.start_recording_daemon()
        if success:
            print("Recording started")
    elif args.stop:
        success = service.stop_recording_and_transcribe()
        if success:
            print("Recording stopped and transcribed")
        else:
            print("Failed to stop and transcribe")
    else:
        parser.print_help()
        return

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

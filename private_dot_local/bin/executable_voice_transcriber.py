#!/usr/bin/env python3
"""
Voice Transcriber Service for i3wm
A local voice-to-text system with push-to-talk functionality
Using faster-whisper for improved performance
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
from faster_whisper import WhisperModel


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
            "whisper_model": "small.en",  # Options: https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/utils.py#L12
            "sample_rate": 16000,
            "device": None,  # None = default device
            "language": "en",  # Language code or None for auto-detection
            "compute_type": "default",  # Options: default, float16, int8_float16, int8
            "device_index": 0,  # GPU device index (if using CUDA)
            "cpu_threads": 0,  # Number of CPU threads (0 = auto)
            "num_workers": 3,  # Number of workers for parallel processing
            "beam_size": 5,  # Beam size for decoding
            "best_of": 5,  # Number of candidates to consider
            "patience": 1.0,  # Patience for beam search
            "length_penalty": 1.0,  # Length penalty for beam search
            "temperature": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],  # Temperature for sampling
            "compression_ratio_threshold": 2.4,  # Threshold for compression ratio
            "log_prob_threshold": -1.0,  # Threshold for average log probability
            "no_speech_threshold": 0.6,  # Threshold for no speech probability
            "condition_on_previous_text": True,  # Use previous text as context
            "initial_prompt": None,  # Initial prompt for conditioning
            "prefix": None,  # Prefix for all segments
            "suppress_blank": True,  # Suppress blank outputs
            "suppress_tokens": [-1],  # Tokens to suppress
            "without_timestamps": False,  # Disable timestamp generation
            "max_initial_timestamp": 1.0,  # Maximum initial timestamp
            "word_timestamps": False,  # Generate word-level timestamps
            "prepend_punctuations": "\"'\"([{-",  # Punctuations to merge with next word
            "append_punctuations": "\"'.。,，!！?？:：)]}、",  # Punctuations to merge with previous word
            "vad_filter": True,  # Use voice activity detection
            "vad_parameters": None,  # Custom VAD parameters
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
    """Handles faster-whisper model loading and transcription"""

    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self._model_lock = threading.Lock()

    def _get_device(self) -> str:
        """Determine the device to use (cuda or cpu)"""
        try:
            # Check if CUDA is available
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass

        return "cpu"

    def _get_compute_type(self, device: str) -> str:
        """Get appropriate compute type based on device"""
        compute_type = self.config.config.get('compute_type', 'default')

        if compute_type == 'default':
            if device == 'cuda':
                # Use float16 for GPU by default
                return "float16"
            else:
                # Use int8 for CPU by default for better performance
                return "int8"

        return compute_type

    def load_model(self):
        """Load faster-whisper model (thread-safe)"""
        with self._model_lock:
            if self.model is None:
                try:
                    model_name = self.config.config['whisper_model']
                    device = self._get_device()
                    compute_type = self._get_compute_type(device)

                    logging.info(f"Loading faster-whisper model: {model_name}")
                    logging.info(f"Device: {device}, Compute type: {compute_type}")

                    # Download model if needed (faster-whisper handles this automatically)
                    # But we can specify a custom directory
                    model_path = str(self.config.models_dir)

                    # Initialize faster-whisper model
                    self.model = WhisperModel(
                        model_name,
                        device=device,
                        device_index=self.config.config.get('device_index', 0),
                        compute_type=compute_type,
                        cpu_threads=self.config.config.get('cpu_threads', 0),
                        num_workers=self.config.config.get('num_workers', 1),
                        download_root=model_path,
                        local_files_only=False
                    )

                    logging.info("faster-whisper model loaded successfully")

                except Exception as e:
                    logging.error(f"Failed to load faster-whisper model: {e}")
                    raise

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio data to text using faster-whisper"""
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

            # faster-whisper expects 16kHz audio
            target_sample_rate = 16000
            current_sample_rate = self.config.config['sample_rate']

            if current_sample_rate != target_sample_rate:
                # Resample audio if needed
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

            # Prepare transcription parameters
            language = self.config.config.get('language', None)
            if language == 'auto':
                language = None  # Let faster-whisper auto-detect

            # Transcribe using faster-whisper
            segments, info = self.model.transcribe(
                audio_data,
                language=language,
                beam_size=self.config.config.get('beam_size', 5),
                best_of=self.config.config.get('best_of', 5),
                patience=self.config.config.get('patience', 1.0),
                length_penalty=self.config.config.get('length_penalty', 1.0),
                temperature=self.config.config.get('temperature', [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]),
                compression_ratio_threshold=self.config.config.get('compression_ratio_threshold', 2.4),
                log_prob_threshold=self.config.config.get('log_prob_threshold', -1.0),
                no_speech_threshold=self.config.config.get('no_speech_threshold', 0.6),
                condition_on_previous_text=self.config.config.get('condition_on_previous_text', True),
                initial_prompt=self.config.config.get('initial_prompt', None),
                prefix=self.config.config.get('prefix', None),
                suppress_blank=self.config.config.get('suppress_blank', True),
                suppress_tokens=self.config.config.get('suppress_tokens', [-1]),
                without_timestamps=self.config.config.get('without_timestamps', False),
                max_initial_timestamp=self.config.config.get('max_initial_timestamp', 1.0),
                word_timestamps=self.config.config.get('word_timestamps', False),
                prepend_punctuations=self.config.config.get('prepend_punctuations', "\"'([{-"),
                append_punctuations=self.config.config.get('append_punctuations', "\"'.。,，!！?？:：)]}、"),
                vad_filter=self.config.config.get('vad_filter', True),
                vad_parameters=self.config.config.get('vad_parameters', None),
            )

            # Log detected language if auto-detected
            if language is None and hasattr(info, 'language'):
                logging.info(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")

            # Extract text from segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            text = ' '.join(text_parts).strip()
            logging.info(f"Transcribed: {text}")
            return text

        except Exception as e:
            logging.error(f"Transcription failed: {e}")
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

        # Check Python dependencies
        python_deps = {
            "faster-whisper": "faster-whisper",
            "numpy": "numpy",
            "sounddevice": "sounddevice",
            "scipy": "scipy (optional, for better audio resampling)"
        }

        missing_python = []
        for module, name in python_deps.items():
            try:
                __import__(module.replace("-", "_"))
            except ImportError:
                if "optional" not in name:
                    missing_python.append(name)

        if missing_python:
            print(f"\nMissing Python dependencies: {', '.join(missing_python)}")
            print("Install with: pip install " + " ".join(missing_python))
            return False

        return True


def main():
    parser = argparse.ArgumentParser(description="Voice Transcriber Service - Push-to-Talk")
    parser.add_argument("--start", action="store_true",
                       help="Start recording (push-to-talk begin)")
    parser.add_argument("--stop", action="store_true",
                       help="Stop recording and transcribe (push-to-talk end)")
    parser.add_argument("--toggle", action="store_true",
                       help="Toggle current status")
    parser.add_argument("--status", action="store_true",
                       help="Check if currently recording")
    parser.add_argument("--check-deps", action="store_true",
                       help="Check system dependencies")
    parser.add_argument("--config", action="store_true",
                       help="Show configuration file location")
    parser.add_argument("--list-models", action="store_true",
                       help="List available Whisper models")

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
        print("\nCurrent configuration:")
        for key, value in sorted(service.config.config.items()):
            print(f"  {key}: {value}")
        return

    if args.list_models:
        print("Available Whisper models:")
        print("  tiny    - 39M parameters, ~1GB RAM, fastest")
        print("  base    - 74M parameters, ~1GB RAM")
        print("  small   - 244M parameters, ~2GB RAM (recommended)")
        print("  medium  - 769M parameters, ~5GB RAM")
        print("  large-v1 - 1550M parameters, ~10GB RAM")
        print("  large-v2 - 1550M parameters, ~10GB RAM")
        print("  large-v3 - 1550M parameters, ~10GB RAM (best accuracy)")
        print("\nModels will be downloaded automatically on first use.")
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

    if args.toggle:
        if service.is_recording():
            args.stop = True
        else:
            args.start = True

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
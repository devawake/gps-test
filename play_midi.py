#!/usr/bin/env python3
import mido
import sys
from gpiozero import TonalBuzzer
from gpiozero.tones import Tone

# Default Configuration
DEFAULT_PIN = 18  # GPIO 18 (Commonly used for hardware PWM)

def play_midi(midi_file, pin):
    """
    Parses a MIDI file and plays notes on a passive buzzer.
    Note: This is designed for PASSIVE buzzers (those that can play different pitches).
    """
    try:
        # Initialize the tonal buzzer
        buzzer = TonalBuzzer(pin)
    except Exception as e:
        print(f"Error initializing buzzer on GPIO {pin}: {e}")
        return

    try:
        mid = mido.MidiFile(midi_file)
        print(f"--- Playing: {midi_file} ---")
        print(f"--- GPIO Pin: {pin} ---")
        print("Press Ctrl+C to stop.")

        # mid.play() handles the real-time timing of MIDI messages
        for msg in mid.play():
            if msg.type == 'note_on' and msg.velocity > 0:
                # Play the MIDI note (0-127)
                try:
                    # Tone.from_midi produces the correct frequency for the buzzer
                    buzzer.play(Tone.from_midi(msg.note))
                except (ValueError, OverflowError):
                    # Skip notes that are outside the supported frequency range
                    pass
            
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                # Stop the sound
                buzzer.stop()

    except FileNotFoundError:
        print(f"Error: MIDI file '{midi_file}' not found.")
    except KeyboardInterrupt:
        print("\nPlayback stopped by user.")
    finally:
        # Safety: always ensure the buzzer is turned off
        buzzer.stop()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 play_midi.py <midi_file> [gpio_pin]")
        print(f"Example: python3 play_midi.py music.mid {DEFAULT_PIN}")
        sys.exit(1)

    midi_path = sys.argv[1]
    pin_number = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PIN
    
    play_midi(midi_path, pin_number)

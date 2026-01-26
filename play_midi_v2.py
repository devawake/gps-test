#!/usr/bin/env python3
import mido
import time
import sys
import pigpio

# --- CONFIGURATION ---
DEFAULT_PIN = 18         # Must be a hardware PWM pin (12, 13, 18, or 19)
OCTAVE_SHIFT = 2         # Move up 2 octaves (makes it much clearer on small buzzers)
DUTY_CYCLE = 500000      # 50% (Range 0-1,000,000)

def midi_to_freq(note):
    """Converts MIDI note number to frequency in Hz."""
    return 440 * (2 ** ((note - 69) / 12))

def play_midi(midi_file, pin):
    pi = pigpio.pi()
    if not pi.connected:
        print("Error: pigpiod daemon not running. Run 'sudo systemctl start pigpiod'")
        return

    try:
        mid = mido.MidiFile(midi_file)
        print(f"--- Playing: {midi_file} (Hardware PWM) ---")
        print(f"--- Octave Shift: +{OCTAVE_SHIFT} ---")
        
        # Track the currently playing note to prevent polyphony "stutter"
        active_note = None

        for msg in mid.play():
            if msg.type == 'note_on' and msg.velocity > 0:
                # Calculate frequency with octave boost
                freq = midi_to_freq(msg.note + (OCTAVE_SHIFT * 12))
                
                # Use Hardware PWM for stable frequency
                # pi.hardware_PWM(gpio, frequency, duty_cycle)
                pi.hardware_PWM(pin, int(freq), DUTY_CYCLE)
                active_note = msg.note
                
            elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                # Only stop if it's the note we are currently playing
                if msg.note == active_note:
                    pi.hardware_PWM(pin, 0, 0)
                    active_note = None

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        pi.hardware_PWM(pin, 0, 0)
        pi.stop()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 play_midi_v2.py <midi_file> [gpio_pin]")
        sys.exit(1)

    midi_path = sys.argv[1]
    pin_number = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PIN
    
    play_midi(midi_path, pin_number)

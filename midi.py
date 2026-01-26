#!/usr/bin/env python3
import mido
import time
import sys
import pigpio

# --- SETTINGS ---
# GPIO 12, 13, 18, and 19 are Hardware PWM pins on the Pi Zero 2W.
# Pin 18 is the most common.
DEFAULT_PIN = 18         
OCTAVE_SHIFT = 2         # +2 Octaves makes it sharp/clear
DUTY_CYCLE = 250000      # 25% (Makes it sound "crisper" than 50%)

def midi_to_freq(note):
    return 440 * (2 ** ((note - 69) / 12))

def play_midi(midi_file, pin):
    pi = pigpio.pi()
    
    if not pi.connected:
        print("\n[!] ERROR: Cannot connect to pigpiod.")
        print("Please run: sudo pigpiod")
        print("Then try again.")
        return

    # Clear any previous stay PWM
    pi.hardware_PWM(pin, 0, 0)

    try:
        mid = mido.MidiFile(midi_file)
        print(f"--- Playing: {midi_file} ---")
        print(f"--- Using GPIO: {pin} (Hardware PWM) ---")
        
        # We use mid.play() for high-accuracy timing
        active_notes = []

        for msg in mid.play():
            if msg.type == 'note_on' and msg.velocity > 0:
                # Add note to stack (for basic polyphony handling)
                active_notes.append(msg.note)
                freq = int(midi_to_freq(msg.note + (OCTAVE_SHIFT * 12)))
                
                # Hardware PWM: pin, frequency, duty_cycle (0-1,000,000)
                pi.hardware_PWM(pin, freq, DUTY_CYCLE)
                
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in active_notes:
                    active_notes.remove(msg.note)
                
                if not active_notes:
                    # Silence if no notes left
                    pi.hardware_PWM(pin, 0, 0)
                else:
                    # Play the next available note in the stack
                    next_note = active_notes[-1]
                    freq = int(midi_to_freq(next_note + (OCTAVE_SHIFT * 12)))
                    pi.hardware_PWM(pin, freq, DUTY_CYCLE)

    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        pi.hardware_PWM(pin, 0, 0)
        pi.stop()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 play_midi_v3.py <midi_file> [gpio_pin]")
        sys.exit(1)

    file_path = sys.argv[1]
    gpio_pin = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PIN
    
    play_midi(file_path, gpio_pin)

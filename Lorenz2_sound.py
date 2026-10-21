"""
Lorenz Strange Attractor - Animated Visualization
Features:
- Continuous camera orbit, position, and zoom changes
- Parameter display in terminal (updates in real-time)
- Looping animation with smooth resets
"""
import numpy as np
import pygfx as gfx
from rendercanvas.auto import RenderCanvas, loop
import signal
import sys
import threading

# --- Audio Configuration ---
SAMPLE_RATE = 44100
BLOCK_SIZE = 2048

# Audio-reactive parameters (will be updated by audio callback)
audio_level = 0.0       # Overall volume (0-1)
audio_bass = 0.0        # Low frequency energy (0-1)
audio_mid = 0.0         # Mid frequency energy (0-1)
audio_high = 0.0        # High frequency energy (0-1)
audio_enabled = False
audio_stream = None

# Raw frequency energy values for display (in Hz-weighted units)
bass_energy_raw = 0.0
mid_energy_raw = 0.0
high_energy_raw = 0.0
rms_raw = 0.0

def list_audio_devices():
    """List all available audio input devices"""
    import sounddevice as sd
    print("\n" + "="*70)
    print("AVAILABLE AUDIO INPUT DEVICES:")
    print("="*70)
    
    devices = sd.query_devices()
    input_devices = []
    
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            name = dev['name']
            print(f"  [{i}] {name} (inputs: {dev['max_input_channels']})")
            input_devices.append((i, name))
    
    print("="*70)
    return input_devices

def find_loopback_device():
    """Try to find a loopback device for system audio"""
    import sounddevice as sd
    
    # Keywords that indicate system audio capture capability
    loopback_keywords = ['blackhole', 'loopback', 'soundflower', 'stereo mix', 
                         'what u hear', 'wave out', 'virtual', 'cable', 'multi-output']
    
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            name = dev['name'].lower()
            for keyword in loopback_keywords:
                if keyword in name:
                    print(f"Found loopback device: [{i}] {dev['name']}")
                    return i
    return None

def audio_callback(indata, frames, time_info, status):
    """Process incoming audio and extract features"""
    global audio_level, audio_bass, audio_mid, audio_high
    global bass_energy_raw, mid_energy_raw, high_energy_raw, rms_raw
    
    if status:
        pass  # Ignore status messages
    
    try:
        # Get mono audio
        audio = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        
        # Compute overall level (RMS) with higher sensitivity
        rms = np.sqrt(np.mean(audio**2))
        rms_raw = rms
        audio_level = min(1.0, rms * 20)  # Increased sensitivity
        
        # Compute FFT for frequency bands
        fft = np.abs(np.fft.rfft(audio))
        freqs = np.fft.rfftfreq(len(audio), 1/SAMPLE_RATE)
        
        # Define frequency bands
        bass_mask = freqs < 250
        mid_mask = (freqs >= 250) & (freqs < 2000)
        high_mask = freqs >= 2000
        
        # Extract band energies with higher sensitivity
        if np.sum(bass_mask) > 0:
            bass_energy_raw = np.mean(fft[bass_mask])
            audio_bass = min(1.0, bass_energy_raw * 3.0)
        if np.sum(mid_mask) > 0:
            mid_energy_raw = np.mean(fft[mid_mask])
            audio_mid = min(1.0, mid_energy_raw * 5.0)
        if np.sum(high_mask) > 0:
            high_energy_raw = np.mean(fft[high_mask])
            audio_high = min(1.0, high_energy_raw * 10.0)
    except:
        pass

def start_audio_capture(device_index=None):
    """Start capturing audio from specified device"""
    global audio_enabled, audio_stream
    
    try:
        import sounddevice as sd
        
        # If no device specified, try to find loopback
        if device_index is None:
            device_index = find_loopback_device()
        
        if device_index is not None:
            device_info = sd.query_devices(device_index)
            print(f"Using audio device: [{device_index}] {device_info['name']}")
        else:
            print("No loopback device found. Using default input (microphone).")
            print("\nFor system audio capture, install BlackHole:")
            print("  brew install blackhole-2ch")
            print("  Then set up Multi-Output Device in Audio MIDI Setup")
        
        audio_stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            device=device_index,
            channels=1,
            callback=audio_callback
        )
        audio_stream.start()
        audio_enabled = True
        return True
        
    except Exception as e:
        print(f"Audio error: {e}")
        print("Running without audio reactivity")
        audio_enabled = False
        return False

# List devices and start audio
print("\nInitializing audio...")
try:
    import sounddevice as sd
    input_devices = list_audio_devices()
    
    # Check for command line argument for device index
    device_idx = None
    if len(sys.argv) > 1:
        try:
            device_idx = int(sys.argv[1])
            print(f"\nUsing device index from command line: {device_idx}")
        except:
            pass
    
    start_audio_capture(device_idx)
except ImportError:
    print("sounddevice not installed. Run: pip install sounddevice")
    print("Running without audio reactivity")
    audio_enabled = False
except Exception as e:
    print(f"Could not initialize audio: {e}")
    audio_enabled = False

# --- Setup canvas, renderer, scene ---
canvas = RenderCanvas(size=(1280, 720), title="Lorenz Strange Attractor")
renderer = gfx.WgpuRenderer(canvas)
scene = gfx.Scene()

N_POINTS = 100_000

positions = np.zeros((N_POINTS, 3), dtype="f4")
geometry = gfx.Geometry(positions=positions)

# -------- MATERIAL WITH 70% OPACITY ----------
points_material = gfx.PointsMaterial(
    size=0.8,
    color=(1.0, 0.2, 0.9, 0.7),
    aa=True,
)

points = gfx.Points(geometry, points_material)
scene.add(points)

# Background (black)
scene.add(
    gfx.Background.from_color(
        (0.0, 0.0, 0.0, 1.0),
        (0.0, 0.0, 0.0, 1.0),
    )
)

# Main 3D camera
camera = gfx.PerspectiveCamera(50, 16/9)
camera.local.position = (60, 60, 60)

# Initial camera setup - only called once
camera.show_object(scene)

pos_data = geometry.positions.data

# Lorenz attractor parameters (base values)
# Classic Lorenz parameters: sigma=10, rho=28, beta=8/3
sigma_base = 10.0
rho_base = 28.0
beta_base = 8.0 / 3.0

sigma = sigma_base
rho = rho_base
beta = beta_base

dt_base = 0.005
dt = dt_base

# Smoothed audio values (for less jittery response)
smooth_level = 0.0
smooth_bass = 0.0
smooth_mid = 0.0
smooth_high = 0.0
smoothing = 0.85  # Higher = smoother (0-1)

time = 0.0

# Camera animation parameters
camera_time = 0.0
base_distance = 80.0
zoom_amplitude = 30.0
zoom_frequency = 0.15
orbit_speed_h = 0.3  # Horizontal orbit speed
orbit_speed_v = 0.12  # Vertical orbit speed
height_amplitude = 40.0

# Center of the Lorenz attractor (where the camera looks at)
attractor_center = (0, 0, 25)

# For terminal display throttling
last_print_time = 0.0
print_interval = 0.1  # Update terminal every 100ms

# Store velocities for smoother animation
dx = np.zeros(N_POINTS, dtype="f4")
dy = np.zeros(N_POINTS, dtype="f4")
dz = np.zeros(N_POINTS, dtype="f4")

# Initialize particles around the Lorenz attractor's region
# The Lorenz attractor is centered around (0, 0, rho-1) with wings extending out
x = np.random.uniform(-20.0, 20.0, size=(N_POINTS,)).astype("f4")
y = np.random.uniform(-20.0, 20.0, size=(N_POINTS,)).astype("f4")
z = np.random.uniform(0.0, 50.0, size=(N_POINTS,)).astype("f4")

def update_camera():
    """Update camera position with smooth orbital movement and zoom"""
    global camera_time
    
    camera_time += 0.016  # ~60fps
    
    # Calculate orbital position
    # Distance varies smoothly (zoom in/out)
    distance = base_distance + zoom_amplitude * np.sin(zoom_frequency * camera_time * 2 * np.pi)
    
    # Horizontal angle (orbiting around Y axis)
    h_angle = orbit_speed_h * camera_time
    
    # Vertical angle (bobbing up and down)
    v_angle = 0.3 + 0.25 * np.sin(orbit_speed_v * camera_time * 2 * np.pi)
    
    # Convert spherical to Cartesian coordinates
    # Position relative to attractor center
    cam_x = distance * np.cos(v_angle) * np.cos(h_angle)
    cam_y = distance * np.sin(v_angle) + height_amplitude * np.sin(orbit_speed_v * camera_time * 1.5)
    cam_z = distance * np.cos(v_angle) * np.sin(h_angle) + attractor_center[2]
    
    # Update camera position
    camera.local.position = (cam_x, cam_y, cam_z)
    
    # Smoothly look at the center of the attractor
    camera.look_at(attractor_center)
    
    return distance, np.degrees(h_angle) % 360, np.degrees(v_angle)

def print_parameters(cam_distance, cam_h_angle, cam_v_angle, red, green, blue, opacity, mean_velocity, x_range):
    """Print parameters to terminal with ANSI colors"""
    # Move cursor to fixed position and clear lines
    sys.stdout.write("\033[8;0H")  # Move to row 8, column 0
    sys.stdout.write("\033[J")     # Clear from cursor to end of screen
    
    # Line 1: Separator
    print(f"\033[92m{'─'*80}\033[0m")
    
    # Line 2: Attractor parameters (green)
    print(f"\033[92mLORENZ ATTRACTOR | σ={sigma:.2f} | ρ={rho:.2f} | β={beta:.3f} | "
          f"dt={dt:.5f} | Points: {N_POINTS:,} | Time: {time:.1f}s\033[0m")
    
    # Line 3: Audio levels with Hz bands (magenta)
    print(f"\033[95mAudio | Bass(0-250Hz): {bass_energy_raw:.4f} | "
          f"Mid(250-2000Hz): {mid_energy_raw:.4f} | "
          f"High(2000+Hz): {high_energy_raw:.4f} | RMS: {rms_raw:.4f}\033[0m")
    
    # Line 4: Camera stats (cyan)
    print(f"\033[96mCamera: dist={cam_distance:.1f} | orbit={cam_h_angle:.1f} deg | "
          f"elevation={cam_v_angle:.1f} deg | Velocity: {mean_velocity:.3f}\033[0m")
    
    # Line 5: Color info (yellow)
    print(f"\033[93mRGB: ({red:.2f}, {green:.2f}, {blue:.2f}) | "
          f"Opacity: {opacity:.2f} | X-range: [{x_range[0]:.1f}, {x_range[1]:.1f}]\033[0m")
    
    sys.stdout.flush()

def animate():
    global time, x, y, z, dx, dy, dz, last_print_time
    global sigma, rho, beta, dt, smooth_level, smooth_bass, smooth_mid, smooth_high
    
    time += 0.016  # ~60fps timing
    
    # Smooth the audio values for less jittery animation
    smooth_level = smoothing * smooth_level + (1 - smoothing) * audio_level
    smooth_bass = smoothing * smooth_bass + (1 - smoothing) * audio_bass
    smooth_mid = smoothing * smooth_mid + (1 - smoothing) * audio_mid
    smooth_high = smoothing * smooth_high + (1 - smoothing) * audio_high
    
    # === AUDIO-REACTIVE PARAMETERS ===
    # sigma (Prandtl number): affected by bass - controls the rate of rotation
    sigma = sigma_base + smooth_bass * 5.0  # Range: 10 to ~15
    
    # rho (Rayleigh number): affected by mid - controls the size/shape of the wings
    rho = rho_base + smooth_mid * 10.0  # Range: 28 to ~38
    
    # beta: affected by high frequencies - controls the damping
    beta = beta_base + smooth_high * 1.0  # Range: 2.67 to ~3.67
    
    # dt parameter: affected by overall level (affects speed)
    dt = dt_base + smooth_level * 0.003  # Range: 0.005 to ~0.008
    
    # Lorenz attractor differential equations
    # dx/dt = sigma * (y - x)
    # dy/dt = x * (rho - z) - y
    # dz/dt = x * y - beta * z
    dx = sigma * (y - x)
    dy = x * (rho - z) - y
    dz = x * y - beta * z
    
    # Update positions using Euler method
    x += dx * dt
    y += dy * dt
    z += dz * dt
    
    # Add tiny random perturbation for visual effect
    x += np.random.normal(0, 0.001, size=N_POINTS).astype("f4")
    y += np.random.normal(0, 0.001, size=N_POINTS).astype("f4")
    z += np.random.normal(0, 0.001, size=N_POINTS).astype("f4")
    
    # Keep particles from exploding (safety bounds for Lorenz)
    x = np.clip(x, -50, 50)
    y = np.clip(y, -50, 50)
    z = np.clip(z, -10, 60)
    
    # ---- AUDIO-REACTIVE COLOR CYCLING ----
    # Base psychedelic cycling + audio influence
    red = 0.5 + 0.5*np.sin(0.7*time) + smooth_bass * 0.3
    green = 0.5 + 0.5*np.sin(0.9*time + 2.094) + smooth_mid * 0.3
    blue = 0.5 + 0.5*np.sin(1.1*time + 4.189) + smooth_high * 0.3
    
    # Boost brightness for neon effect + audio boost
    brightness_boost = 1.5 + smooth_level * 0.5
    red = min(1.0, red**1.5 * brightness_boost)
    green = min(1.0, green**1.5 * brightness_boost)
    blue = min(1.0, blue**1.5 * brightness_boost)
    
    # Apply constant opacity
    opacity = 0.7
    
    # Audio-reactive point size
    points.material.size = 0.5 + smooth_level * 1.1  # Range: 0.5 to 1.6
    
    # Set color with variable opacity
    points.material.color = (red, green, blue, opacity)
    
    # Update positions in geometry
    pos_data[:, 0] = x.astype("f4")
    pos_data[:, 1] = y.astype("f4")
    pos_data[:, 2] = z.astype("f4")
    
    geometry.positions.update_range(0, N_POINTS)
    
    # Update camera with smooth animation
    cam_distance, cam_h_angle, cam_v_angle = update_camera()
    
    # Calculate some stats for display
    mean_velocity = np.sqrt(np.mean(dx**2 + dy**2 + dz**2))
    x_range = (np.min(x), np.max(x))
    
    # Update terminal display (throttled)
    if time - last_print_time >= print_interval:
        last_print_time = time
        print_parameters(cam_distance, cam_h_angle, cam_v_angle, 
                        red, green, blue, opacity, mean_velocity, x_range)
    
    # Render scene
    renderer.render(scene, camera)
    
    # Request the next frame to keep animation running
    canvas.request_draw(animate)

def cleanup_and_exit(signum=None, frame=None):
    """Clean exit handler"""
    print("\n\033[0m")  # Reset colors
    print("Exiting...")
    try:
        if audio_enabled and audio_stream is not None:
            audio_stream.stop()
            audio_stream.close()
    except:
        pass
    try:
        loop.stop()
    except:
        pass
    sys.exit(0)

# Register signal handlers for clean exit
signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)

if __name__ == "__main__":
    print("\033[2J\033[H")  # Clear screen and move to top
    print("=" * 75)
    print("  LORENZ STRANGE ATTRACTOR - AUDIO REACTIVE VISUALIZATION")
    print("=" * 75)
    print("To capture system audio: brew install blackhole-2ch")
    print("Then run: python script.py <device_number>")
    print("Press Ctrl+C to exit")
    # Row 8 onwards will be used for live data
    
    try:
        canvas.request_draw(animate)  # Start the animation
        loop.run()
    except KeyboardInterrupt:
        cleanup_and_exit()
    except Exception as e:
        print(f"\n\033[0mError: {e}")
        import traceback
        traceback.print_exc()
        cleanup_and_exit()
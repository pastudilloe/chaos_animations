"""
Halvorsen Strange Attractor - Animated Visualization
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

# --- Setup canvas, renderer, scene ---
canvas = RenderCanvas(size=(1280, 720), title="Halvorsen Strange Attractor")
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
camera.local.position = (30, 30, 30)
camera.show_object(scene)

pos_data = geometry.positions.data

# Halvorsen attractor parameters
a = 1.89
dt = 0.005  # Time step for integration

time = 0.0

# Camera animation parameters
camera_time = 0.0
base_distance = 35.0
zoom_amplitude = 15.0
zoom_frequency = 0.15
orbit_speed_h = 0.3  # Horizontal orbit speed
orbit_speed_v = 0.12  # Vertical orbit speed
height_amplitude = 20.0

# For terminal display throttling
last_print_time = 0.0
print_interval = 0.1  # Update terminal every 100ms

# Store velocities for smoother animation
dx = np.zeros(N_POINTS, dtype="f4")
dy = np.zeros(N_POINTS, dtype="f4")
dz = np.zeros(N_POINTS, dtype="f4")

# Initialize particles
x = np.random.uniform(-5.0, 5.0, size=(N_POINTS,)).astype("f4")
y = np.random.uniform(-5.0, 5.0, size=(N_POINTS,)).astype("f4")
z = np.random.uniform(-5.0, 5.0, size=(N_POINTS,)).astype("f4")

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
    cam_x = distance * np.cos(v_angle) * np.cos(h_angle)
    cam_y = distance * np.sin(v_angle) + height_amplitude * np.sin(orbit_speed_v * camera_time * 1.5)
    cam_z = distance * np.cos(v_angle) * np.sin(h_angle)
    
    # Update camera position
    camera.local.position = (cam_x, cam_y, cam_z)
    
    # Always look at the center of the attractor
    camera.show_object(scene, view_dir=(-cam_x, -cam_y, -cam_z), scale=0.8)
    
    return distance, np.degrees(h_angle) % 360, np.degrees(v_angle)

def print_parameters(cam_distance, cam_h_angle, cam_v_angle, red, green, blue, opacity, mean_velocity, x_range):
    """Print parameters to terminal with ANSI colors"""
    # Clear previous lines and move cursor up
    sys.stdout.write("\033[4A")  # Move up 4 lines
    sys.stdout.write("\033[K")   # Clear line
    
    # Line 1: Attractor parameters (green)
    print(f"\033[92m{'─'*70}")
    print(f"HALVORSEN ATTRACTOR │ a={a:.2f} │ dt={dt:.4f} │ "
          f"Points: {N_POINTS:,} │ Time: {time:.1f}s\033[0m")
    
    # Line 2: Camera stats (cyan)
    print(f"\033[96mCamera: dist={cam_distance:.1f} │ orbit={cam_h_angle:.1f}° │ "
          f"elevation={cam_v_angle:.1f}° │ Mean velocity: {mean_velocity:.3f}\033[0m")
    
    # Line 3: Color info (yellow)
    print(f"\033[93mRGB: ({red:.2f}, {green:.2f}, {blue:.2f}) │ "
          f"Opacity: {opacity:.2f} │ X-range: [{x_range[0]:.1f}, {x_range[1]:.1f}]\033[0m", end='')
    
    sys.stdout.flush()

def animate():
    global time, x, y, z, dx, dy, dz, last_print_time
    
    time += 0.016  # ~60fps timing
    
    # Halvorsen attractor differential equations
    dx = -a * x - 4 * y - 4 * z - y**2
    dy = -a * y - 4 * z - 4 * x - z**2
    dz = -a * z - 4 * x - 4 * y - x**2
    
    # Update positions using Euler method
    x += dx * dt
    y += dy * dt
    z += dz * dt
    
    # Add tiny random perturbation for visual effect
    x += np.random.normal(0, 0.001, size=N_POINTS).astype("f4")
    y += np.random.normal(0, 0.001, size=N_POINTS).astype("f4")
    z += np.random.normal(0, 0.001, size=N_POINTS).astype("f4")
    
    # Keep particles from exploding (safety bounds for Halvorsen)
    x = np.clip(x, -15, 15)
    y = np.clip(y, -15, 15)
    z = np.clip(z, -15, 15)
    
    # ---- SMOOTH PSYCHEDELIC COLOR CYCLING ----
    red = 0.5 + 0.5*np.sin(0.7*time)
    green = 0.5 + 0.5*np.sin(0.9*time + 2.094)
    blue = 0.5 + 0.5*np.sin(1.1*time + 4.189)
    
    # Boost brightness for neon effect
    red = min(1.0, red**1.5 * 1.5)
    green = min(1.0, green**1.5 * 1.5)
    blue = min(1.0, blue**1.5 * 1.5)
    
    # Apply constant opacity
    opacity = 0.7
    
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
        loop.stop()
    except:
        pass
    sys.exit(0)

# Register signal handlers for clean exit
signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)

if __name__ == "__main__":
    print("\033[2J\033[H")  # Clear screen
    print("=" * 70)
    print("  HALVORSEN STRANGE ATTRACTOR VISUALIZATION")
    print("=" * 70)
    print("Press Ctrl+C to exit")
    print()
    print()  # Blank lines for the parameter display area
    print()
    print()
    
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
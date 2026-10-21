# strange_attractor_lorenz_neon_loop.py
import numpy as np
import pygfx as gfx
from rendercanvas.auto import RenderCanvas, loop

# --- Setup canvas, renderer, scene ---
canvas = RenderCanvas()
renderer = gfx.WgpuRenderer(canvas)
scene = gfx.Scene()

N_POINTS = 100_000

positions = np.zeros((N_POINTS, 3), dtype="f4")
geometry = gfx.Geometry(positions=positions)

# -------- MATERIAL WITH 70% OPACITY ----------
points_material = gfx.PointsMaterial(
    size=0.8,  # Smaller size for better detail
    color=(1.0, 0.2, 0.9, 0.7),   # Initial neon magenta with 70% opacity
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

camera = gfx.PerspectiveCamera(50, 16/9)
camera.local.position = (80, 80, 80)
camera.show_object(scene)
controller = gfx.OrbitController(camera, register_events=renderer)

pos_data = geometry.positions.data

# Lorenz attractor parameters
sigma = 10.0
rho = 28.0
beta = 8.0 / 3.0
dt = 0.005  # Time step for integration

time = 0.0
loop_duration = 20.0  # Reset every 20 seconds (adjust as needed)
loop_time = 0.0

# Store velocities for smoother animation
dx = np.zeros(N_POINTS, dtype="f4")
dy = np.zeros(N_POINTS, dtype="f4")
dz = np.zeros(N_POINTS, dtype="f4")

def reset_particles():
    """Reset particles to initial positions"""
    global x, y, z
    x = np.random.uniform(-20.0, 20.0, size=(N_POINTS,)).astype("f4")
    y = np.random.uniform(-20.0, 20.0, size=(N_POINTS,)).astype("f4")
    z = np.random.uniform(0.0, 40.0, size=(N_POINTS,)).astype("f4")

# Initialize particles
x = np.random.uniform(-20.0, 20.0, size=(N_POINTS,)).astype("f4")
y = np.random.uniform(-20.0, 20.0, size=(N_POINTS,)).astype("f4")
z = np.random.uniform(0.0, 40.0, size=(N_POINTS,)).astype("f4")

def animate():
    global time, x, y, z, dx, dy, dz, loop_time
    
    time += 0.016  # ~60fps timing
    loop_time += 0.016
    
    # Reset if we've reached the loop duration
    if loop_time >= loop_duration:
        loop_time = 0.0
        reset_particles()
        # Optional: smooth fade-in after reset
        fade_in = 0.0
    else:
        fade_in = min(1.0, loop_time / 2.0)  # 2-second fade-in
    
    # Lorenz attractor differential equations
    dx = sigma * (y - x)
    dy = x * (rho - z) - y
    dz = x * y - beta * z
    
    # Update positions using Euler method
    x += dx * dt
    y += dy * dt
    z += dz * dt
    
    # Add tiny random perturbation
    x += np.random.normal(0, 0.001, size=N_POINTS).astype("f4")
    y += np.random.normal(0, 0.001, size=N_POINTS).astype("f4")
    z += np.random.normal(0, 0.001, size=N_POINTS).astype("f4")
    
    # Keep particles from exploding (safety bounds)
    x = np.clip(x, -50, 50)
    y = np.clip(y, -50, 50)
    z = np.clip(z, 0, 80)
    
    # ---- SMOOTH PSYCHEDELIC COLOR CYCLING ----
    r = 0.5 + 0.5*np.sin(0.7*time)
    g = 0.5 + 0.5*np.sin(0.9*time + 2.094)
    b = 0.5 + 0.5*np.sin(1.1*time + 4.189)
    
    # Boost brightness for neon effect
    r = min(1.0, r**1.5 * 1.5)
    g = min(1.0, g**1.5 * 1.5)
    b = min(1.0, b**1.5 * 1.5)
    
    # Apply fade-in to opacity after reset
    opacity = 0.7 * fade_in
    
    # Set color with variable opacity
    points.material.color = (r, g, b, opacity)
    
    # Update positions in geometry
    pos_data[:, 0] = x.astype("f4")
    pos_data[:, 1] = y.astype("f4")
    pos_data[:, 2] = z.astype("f4")
    
    geometry.positions.update_range(0, N_POINTS)
    
    renderer.render(scene, camera)
    
    # CRITICAL: Request the next frame to keep animation running
    canvas.request_draw(animate)

if __name__ == "__main__":
    canvas.request_draw(animate)  # Start the animation
    loop.run()
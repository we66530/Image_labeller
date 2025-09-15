import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, simpledialog

# Define classes and corresponding colors
class_colors = {
    0: (0, 0, 0),  # Background
    1: (255, 0, 0),  # Red (Class 1)
    2: (0, 255, 0),  # Green (Class 2)
    3: (0, 0, 255)   # Blue (Class 3)
}

current_class = 1  # Default class
brush_size = 5
mode = "brush"  # "brush" or "move"
last_x, last_y = None, None  # For smooth strokes
offset_x, offset_y = 0, 0  # For panning (kept for compatibility)
move_start_x, move_start_y = 0, 0

drawing = False
moving = False
history = []  # Stores snapshots of mask & overlay

# Zoom parameters
scale = 1.0
scale_step = 0.1
min_scale = 0.2
max_scale = 5.0

# Function to open file dialog
def load_image():
    global image, mask, overlay
    root = tk.Tk()
    root.withdraw()  # Hide main Tkinter window
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
    if file_path:
        image = cv2.imread(file_path)
        if image is None:
            print("Failed to load image.")
            root.destroy()
            return
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        overlay = np.zeros_like(image)
    root.destroy()

# Function to save mask with user-specified name and location
def save_mask():
    global image, mask
    root = tk.Tk()
    root.withdraw()  # Hide main Tkinter window
    file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
    if file_path:
        rgb_mask = np.zeros_like(image)
        for class_id, color in class_colors.items():
            class_pixels = (mask == class_id)
            rgb_mask[class_pixels] = color
        cv2.imwrite(file_path, rgb_mask)
        print(f"RGB mask saved at: {file_path}")
    root.destroy()

# Initialize with image loading
load_image()

# Mouse callback function
def draw(event, x, y, flags, param):
    global drawing, moving, mask, overlay, last_x, last_y, offset_x, offset_y, move_start_x, move_start_y

    # Map display coordinates back to image coordinates (account for zoom)
    if scale != 1.0:
        ix = int(x / scale)
        iy = int(y / scale)
    else:
        ix, iy = x, y

    # Then add panning offset (if used)
    ix = ix + offset_x
    iy = iy + offset_y

    # clamp to image bounds
    h, w = mask.shape[:2]
    ix = max(0, min(w - 1, ix))
    iy = max(0, min(h - 1, iy))

    if mode == "brush":
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            last_x, last_y = ix, iy  # store in image coords
            history.append((mask.copy(), overlay.copy()))  # Save state before painting
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            color = class_colors[current_class]
            if last_x is not None and last_y is not None:
                num_steps = max(abs(ix - last_x), abs(iy - last_y), 1)
                for i in range(1, num_steps + 1):
                    interp_x = int(last_x + (ix - last_x) * i / num_steps)
                    interp_y = int(last_y + (iy - last_y) * i / num_steps)
                    cv2.circle(mask, (interp_x, interp_y), brush_size, current_class, -1)
                    cv2.circle(overlay, (interp_x, interp_y), brush_size, color, -1)
            last_x, last_y = ix, iy
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            last_x, last_y = None, None

    elif mode == "move":
        # move mode pans the image (offset_x/offset_y are in image pixels)
        if event == cv2.EVENT_LBUTTONDOWN:
            moving = True
            move_start_x, move_start_y = ix, iy
        elif event == cv2.EVENT_MOUSEMOVE and moving:
            dx = move_start_x - ix
            dy = move_start_y - iy
            offset_x = max(0, offset_x + dx)
            offset_y = max(0, offset_y + dy)
            # clamp so offsets don't go out of image bounds (basic)
            h, w = image.shape[:2]
            offset_x = min(offset_x, max(0, w - 1))
            offset_y = min(offset_y, max(0, h - 1))
            move_start_x, move_start_y = ix, iy
        elif event == cv2.EVENT_LBUTTONUP:
            moving = False

cv2.namedWindow("Painter", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Painter", draw)

while True:
    # Combine image and overlay (overlay is same size as image)
    display = cv2.addWeighted(image, 0.5, overlay, 0.5, 0)

    # Apply zoom (resize the whole image+overlay)
    if scale != 1.0:
        display = cv2.resize(display, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)

    # Display status
    cv2.putText(display, f"Mode: {mode.upper()}  Zoom: {scale:.1f}x  Class: {current_class}  Brush: {brush_size}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.imshow("Painter", display)

    key = cv2.waitKey(1) & 0xFF

    # Change mode (brush <-> move)
    if key == ord('m'):
        mode = "move" if mode == "brush" else "brush"
        print(f"Mode switched to: {mode}")

    # Change class with number keys (1..n)
    if ord('1') <= key <= ord(str(len(class_colors))):
        current_class = int(chr(key))
        print(f"Selected class: {current_class}")

    # Increase brush size
    elif key == ord('+') or key == ord('='):
        brush_size = min(50, brush_size + 2)
        print(f"Brush size: {brush_size}")

    # Decrease brush size
    elif key == ord('-'):
        brush_size = max(1, brush_size - 2)
        print(f"Brush size: {brush_size}")

    # Undo last brush stroke
    elif key == ord('z') and history:
        mask, overlay = history.pop()  # Restore last saved state
        print("Last stroke undone!")

    # Save mask with user input name and location
    elif key == ord('s'):
        save_mask()

    # Load new image
    elif key == ord('l'):
        load_image()
        print("New image loaded!")

    # Zoom controls: 'o' = zoom out, 'p' = zoom in
    elif key == ord('o'):
        scale = max(min_scale, scale - scale_step)
        print(f"Zoom out -> {scale:.1f}x")
    elif key == ord('p'):
        scale = min(max_scale, scale + scale_step)
        print(f"Zoom in -> {scale:.1f}x")

    # Exit (ESC)
    elif key == 27:
        break

cv2.destroyAllWindows()

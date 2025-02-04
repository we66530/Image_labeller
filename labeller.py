import cv2
import numpy as np

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
offset_x, offset_y = 0, 0  # For panning
move_start_x, move_start_y = 0, 0

# Load image
image = cv2.imread(r"D:\CholecSeg8k\train_img\01_frame_149_endo.png")
mask = np.zeros(image.shape[:2], dtype=np.uint8)  # Stores class labels
overlay = np.zeros_like(image)  # Colored overlay
drawing = False
moving = False

# History for undo feature
history = []  # Stores snapshots of mask & overlay

# Mouse callback function
def draw(event, x, y, flags, param):
    global drawing, moving, mask, overlay, last_x, last_y, offset_x, offset_y, move_start_x, move_start_y

    x, y = x + offset_x, y + offset_y  # Adjust for panning

    if mode == "brush":
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            last_x, last_y = x, y  # Store starting point
            history.append((mask.copy(), overlay.copy()))  # Save state before painting
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            color = class_colors[current_class]
            if last_x is not None and last_y is not None:
                num_steps = max(abs(x - last_x), abs(y - last_y))  # Interpolation steps
                for i in range(1, num_steps + 1):
                    interp_x = int(last_x + (x - last_x) * i / num_steps)
                    interp_y = int(last_y + (y - last_y) * i / num_steps)
                    cv2.circle(mask, (interp_x, interp_y), brush_size, current_class, -1)
                    cv2.circle(overlay, (interp_x, interp_y), brush_size, color, -1)
            last_x, last_y = x, y
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            last_x, last_y = None, None

    elif mode == "move":
        if event == cv2.EVENT_LBUTTONDOWN:
            moving = True
            move_start_x, move_start_y = x, y
        elif event == cv2.EVENT_MOUSEMOVE and moving:
            dx, dy = move_start_x - x, move_start_y - y
            offset_x = max(0, offset_x + dx)
            offset_y = max(0, offset_y + dy)
            move_start_x, move_start_y = x, y
        elif event == cv2.EVENT_LBUTTONUP:
            moving = False

cv2.namedWindow("Painter")
cv2.setMouseCallback("Painter", draw)

while True:
    display = image.copy()
    overlay_display = np.zeros_like(image)
    overlay_display[offset_y:offset_y+overlay.shape[0], offset_x:offset_x+overlay.shape[1]] = overlay
    display = cv2.addWeighted(display, 0.5, overlay_display, 0.5, 0)

    cv2.putText(display, f"Mode: {mode.upper()}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.imshow("Painter", display)

    key = cv2.waitKey(1) & 0xFF
    
    # Change mode (brush <-> move)
    if key == ord('m'):
        mode = "move" if mode == "brush" else "brush"
        print(f"Mode switched to: {mode}")

    # Change class with number keys
    if ord('1') <= key <= ord(str(len(class_colors))):
        current_class = int(chr(key))
        print(f"Selected class: {current_class}")

    # Increase brush size
    elif key == ord('+'):
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

    # Save mask as RGB PNG
    elif key == ord('s'):
        rgb_mask = np.zeros_like(image)
        for class_id, color in class_colors.items():
            class_pixels = (mask == class_id)
            rgb_mask[class_pixels] = color
        cv2.imwrite("mask_output/mask_rgb.png", rgb_mask)
        print("RGB mask saved!")

    # Exit
    elif key == 27:  # ESC
        break

cv2.destroyAllWindows()

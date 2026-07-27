"""
Standalone camera test - run this BEFORE debugging the game itself.
It has nothing to do with pygame or MediaPipe, it only checks whether
OpenCV can grab frames from a webcam on this machine.

Usage:
    python test_camera.py
"""

import cv2

print("Scanning camera indices 0-4...")
found_any = False

for idx in range(5):
    cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        print(f"  index {idx}: could not open")
        cap.release()
        continue

    ok, frame = cap.read()
    if ok and frame is not None:
        print(f"  index {idx}: OPENED and read a frame of shape {frame.shape}  <-- use this index")
        found_any = True
    else:
        print(f"  index {idx}: opened but could NOT read a frame")
    cap.release()

if not found_any:
    print("\nNo working camera found. This usually means one of:")
    print("  1. You're running inside a remote/cloud/container dev environment")
    print("     that has no access to your physical webcam.")
    print("  2. Camera permission is blocked for this app/terminal in your OS")
    print("     privacy settings.")
    print("  3. Another app (Zoom, Teams, browser tab) currently has the")
    print("     camera locked.")
else:
    print("\nCamera works. If the game still shows no feed, set CAM_INDEX in")
    print("game/constants.py to the working index printed above.")

# If a camera was found, try to actually show a live preview window so you
# can visually confirm it's not just opening but streaming real video.
print("\nOpening a 5-second live preview window (press 'q' to close early)...")
cap = cv2.VideoCapture(0)
if cap.isOpened():
    import time
    start = time.time()
    while time.time() - start < 5:
        ok, frame = cap.read()
        if not ok:
            print("Frame read failed during preview.")
            break
        cv2.imshow("Camera Preview - press q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
else:
    print("Could not open camera index 0 for the live preview.")

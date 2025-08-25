import cv2
import mss
import time
import requests
import os

# Use OpenCV's built-in cascade files
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

def get_user_preference():
    """Get user preference for screenshot handling"""
    print("\nScreenshot captured! What would you like to do?")
    print("1. Save locally only")
    print("2. Send to server only") 
    print("3. Both (save locally AND send to server)")
    print("4. Don't save and retake")
    print("5. Don't save and quit")
    
    while True:
        choice = input("\nChoose option (1-5): ").strip()
        if choice == "1":
            return "local"
        elif choice == "2":
            return "server"
        elif choice == "3":
            return "both"
        elif choice == "4":
            return "retake"
        elif choice == "5":
            return "quit"
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")

def start_smile_detection_camera():
    print("Starting Smile Detection System...")
    print("Initializing camera...")
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return False
    
    print("Camera initialized successfully!")
    print("Loading AI models...")
    
    # Brief pause to show loading (and give camera time to warm up)
    time.sleep(1)
    
    # Create a window to display the webcam feed
    cv2.namedWindow('Smile Detection', cv2.WINDOW_AUTOSIZE)
    
    print("AI models loaded!")
    print("System ready!")
    
    # Another brief pause for better UX
    time.sleep(0.5)
    
    smile_count = 0  # Counter for unique filenames
    last_capture_time = 0  # Track last capture time to avoid duplicates
    
    print("\n" + "="*50)
    print("SMILE DETECTION ACTIVE")
    print("="*50)
    print("Smile to capture your photo!")
    print("Press 'q' to quit")
    
    print("\n" + "="*50)
    print("� SMILE DETECTION ACTIVE")
    print("="*50)
    print("� Smile to capture your photo!")
    print("Press 'q' to quit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        # Draw rectangles around detected faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            roi_gray = gray[y:y+h, x:x+w]
            # Less sensitive smile detection - higher parameters for more accurate detection
            smiles = smile_cascade.detectMultiScale(
                roi_gray, 
                scaleFactor=1.7,      # Much less sensitive (was 1.5)
                minNeighbors=22,      # Much less sensitive (was 16) 
                minSize=(30, 25),     # Larger minimum size to filter out smaller detections
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            if len(smiles) > 0:
                # Additional filtering: only consider it a smile if we detect multiple smile regions
                # or if the smile region is reasonably sized relative to the face
                valid_smiles = []
                for (sx, sy, sw, sh) in smiles:
                    # Filter out very small detections (likely false positives)
                    if sw > w * 0.35 and sh > h * 0.15:  # Much stricter: 35% of face width, 15% of face height
                        valid_smiles.append((sx, sy, sw, sh))
                
                if len(valid_smiles) > 0:
                    # Draw rectangles around detected valid smiles
                    for (sx, sy, sw, sh) in valid_smiles:
                        cv2.rectangle(frame, (x+sx, y+sy), (x+sx+sw, y+sy+sh), (0, 255, 0), 2)
                
                    # Check if enough time has passed since last capture (3 seconds for less frequent captures)
                    current_time = time.time()
                    if current_time - last_capture_time > 3:
                        # Valid smile detected - save image with unique filename
                        smile_count += 1
                        
                        print(f"\nSmile detected!")
                        
                        # IMPORTANT: Capture screenshot IMMEDIATELY while OpenCV window is still active
                        print("Taking screenshot now...")
                        
                        # Capture screenshot first
                        with mss.mss() as sct:
                            screenshot = sct.grab(sct.monitors[0])
                            screenshot_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
                        
                        # Now get user preference (OpenCV window can lose focus safely now)
                        preference = get_user_preference()
                        
                        # Handle user choice
                        if preference == "quit":
                            print("Closing camera...")
                            cap.release()
                            cv2.destroyAllWindows()
                            return False
                        elif preference == "retake":
                            print("Continuing to look for smiles...")
                            last_capture_time = current_time  # Reset timer
                            continue
                        
                        # Process the already-captured screenshot
                        try:
                            success = process_screenshot(screenshot_bytes, preference)
                            if success:
                                print(f"Screenshot processed successfully!")
                                print("Mission accomplished! Closing camera...")
                                # Close camera and exit after successful capture
                                cap.release()
                                cv2.destroyAllWindows()
                                return True  # Exit the function successfully
                            else:
                                print(f"Failed to process screenshot")
                            
                        except Exception as e:
                            print(f"Error processing screenshot: {e}")
                        
                        last_capture_time = current_time

        # Add text overlay showing smile count
        status_text = f"Smiles captured: {smile_count}"
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add instruction text
        instruction_text = "Smile to capture photo!"
        cv2.putText(frame, instruction_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Display the frame with detection rectangles
        cv2.imshow('Smile Detection', frame)
        
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return False  # Return False if exited without successful capture
    
def process_screenshot(screenshot_bytes, preference):
    """Process a screenshot based on user preference"""
    # Variables to track success
    local_success = True
    server_success = True
    
    # Handle local saving
    if preference in ["local", "both"]:
        try:
            timestamp = int(time.time())
            local_filename = f"screenshot_{timestamp}.png"
            
            with open(local_filename, 'wb') as f:
                f.write(screenshot_bytes)
            print(f"Screenshot saved locally as: {local_filename}")
            local_success = True
        except Exception as e:
            print(f"Error saving screenshot locally: {e}")
            local_success = False
    
    # Handle server sending
    if preference in ["server", "both"]:
        try:
            server_success = send_screenshot_to_server(screenshot_bytes)
        except Exception as e:
            print(f"Error sending to server: {e}")
            server_success = False
    
    # Determine overall success based on preference
    if preference == "local":
        return local_success
    elif preference == "server":
        return server_success
    else:  # "both"
        # For "both", consider success if at least one operation succeeds
        success = local_success or server_success
        if local_success and server_success:
            print(f"Complete! Screenshot saved locally and sent to server")
        elif local_success and not server_success:
            print(f"Screenshot saved locally but server upload failed")
        elif not local_success and server_success:
            print(f"Screenshot sent to server but local save failed")
        else:
            print(f"Both local save and server upload failed")
        return success

def send_screenshot_to_server(image_bytes):
    """Send screenshot bytes to the server for diary generation"""
    try:
        # Replace with your actual server URL
        server_url = "http://localhost:8000/screenshot"  # Adjust the URL as needed
        
        # You can make this configurable or prompt user for userId
        user_id = "demo-user-123"  # TODO: Make this configurable
        
        files = {
            'image': ('screenshot.png', image_bytes, 'image/png')
        }
        
        data = {
            'userId': user_id
        }
        
        response = requests.post(server_url, files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            diary_entry = result.get('diary_entry', {})
            if isinstance(diary_entry, dict):
                content = diary_entry.get('content', 'No diary content received')
            else:
                content = str(diary_entry)
            
            print(f"Diary Entry: {content}")
            print(f"Location: {result.get('location_data', {}).get('city', 'Unknown')}")
            print(f"Weather: {result.get('weather_data', {}).get('description', 'Unknown')}")
            return True
        else:
            print(f"Server error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Error sending to server: {e}")
        return False
    
if __name__ == "__main__":
    start_smile_detection_camera()
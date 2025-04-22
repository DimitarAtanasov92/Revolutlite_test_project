import platform
from django.conf import settings

# Comment out fcntl imports if testing on Windows frequently
# if platform.system() != 'Windows':
#     import fcntl

from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .forms import RegisterForm, LoginForm # VerificationForm not directly used here
from .utils import extract_text_fields

from deepface import DeepFace
import cv2
import base64
import numpy as np
import os
import tempfile
import logging # Import logging

logger = logging.getLogger(__name__) # Setup logger

# --- Other views (register_view, login_view, logout_view, dashboard_view) remain the same ---

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Do not log in automatically, user needs verification
            # login(request, user)
            messages.success(request, "Registration successful! Please log in and verify your account.")
            return redirect('login') # Redirect to login after registration
        else:
            messages.error(request, "Registration failed. Please correct the errors.")
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if not user.is_verified and not user.needs_manual_review: # Only redirect to verify if not verified AND not already under review
                 messages.info(request, "Please complete the verification process.")
                 return redirect('verify')
            elif user.needs_manual_review and not user.is_verified:
                 messages.warning(request, "Your account is pending manual review.")
                 # Decide where to redirect users under review, maybe dashboard with limited access or a specific page.
                 # For now, dashboard is fine, but the template should reflect the status.
                 return redirect('dashboard')
            elif user.is_verified:
                return redirect('dashboard')
            else: # Should not happen, but safety catch
                return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')

@login_required # Ensure user is logged in for dashboard
def dashboard_view(request):
    # No verification check needed here directly, template handles display logic
    return render(request, 'dashboard.html')


# --- Helper function to decode base64 ---
def decode_base64_data(data_url):
    """Decodes base64 data URL (image or video)"""
    try:
        header, encoded = data_url.split(',', 1)
        binary_data = base64.b64decode(encoded)
        return header, binary_data
    except (ValueError, TypeError, base64.binascii.Error) as e:
        logger.error(f"Error decoding base64 data: {e}")
        return None, None

# --- Helper function to extract frame from video ---
def extract_frame_from_video(video_path, frame_num=10):
    """Extracts a specific frame from a video file."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Error opening video file: {video_path}")
        return None

    # Get video properties
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # fps = cap.get(cv2.CAP_PROP_FPS) # Not strictly needed here

    # Ensure frame_num is valid
    if frame_count <= 0:
        logger.error(f"Video has no frames or error reading frame count: {video_path}")
        cap.release()
        return None
    target_frame = min(frame_num, frame_count - 1) # Use specified frame or last frame if too high

    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ret, frame = cap.read()
    cap.release()

    if ret:
        return frame
    else:
        logger.error(f"Failed to read frame {target_frame} from video: {video_path}")
        return None

@login_required
def verification_view(request):
    user = request.user
    # Prevent re-verification if already verified or under review
    if user.is_verified:
        messages.info(request, "Your account is already verified.")
        return redirect('dashboard')
    if user.needs_manual_review:
        messages.warning(request, "Your verification is currently under manual review.")
        return redirect('dashboard')

    if request.method == 'POST':
        id_front_base64 = request.POST.get("id_front_base64")
        id_back_base64 = request.POST.get("id_back_base64") # Optional but good to have
        video_base64 = request.POST.get("recorded_video_base64")

        if not id_front_base64 or not video_base64:
            messages.error(request, "⚠️ Please capture ID front image and record a video.")
            return redirect("verify") # Stay on the same page

        # --- Decode Base64 Data ---
        id_front_header, id_front_data = decode_base64_data(id_front_base64)
        id_back_header, id_back_data = decode_base64_data(id_back_base64) if id_back_base64 else (None, None)
        video_header, video_data = decode_base64_data(video_base64)

        if not id_front_data or not video_data:
             messages.error(request, "❌ Error decoding submitted data.")
             return redirect("verify")

        # Determine file extensions (basic)
        id_front_ext = ".jpg" if "image/jpeg" in id_front_header else ".png" if "image/png" in id_front_header else ".tmp"
        id_back_ext = ".jpg" if id_back_header and "image/jpeg" in id_back_header else ".png" if id_back_header and "image/png" in id_back_header else ".tmp"
        video_ext = ".webm" if "video/webm" in video_header else ".mp4" if "video/mp4" in video_header else ".tmp" # Adjust based on JS recorder mimeType

        # --- Create Temporary Files ---
        # Use NamedTemporaryFile for better context management
        temp_id_front = None
        temp_id_back = None
        temp_video = None
        temp_face_frame = None # For the frame extracted from video

        try:
            with tempfile.NamedTemporaryFile(suffix=id_front_ext, delete=False) as tf_id_front, \
                 tempfile.NamedTemporaryFile(suffix=video_ext, delete=False) as tf_video:

                tf_id_front.write(id_front_data)
                temp_id_front_path = tf_id_front.name

                tf_video.write(video_data)
                temp_video_path = tf_video.name

                temp_id_back_path = None
                if id_back_data:
                     with tempfile.NamedTemporaryFile(suffix=id_back_ext, delete=False) as tf_id_back:
                           tf_id_back.write(id_back_data)
                           temp_id_back_path = tf_id_back.name


                # --- 1. Extract Text from ID Front ---
                logger.info(f"Extracting text from: {temp_id_front_path}")
                text_fields = extract_text_fields(temp_id_front_path)
                user.full_name = text_fields.get('full_name')
                user.birth_date = text_fields.get('birth_date')
                user.document_number = text_fields.get('document_number')
                user.issue_date = text_fields.get('issue_date')
                logger.info(f"Extracted text fields: {text_fields}")

                # --- 2. Extract Face Frame from Video ---
                logger.info(f"Extracting frame from video: {temp_video_path}")
                face_frame_img = extract_frame_from_video(temp_video_path, frame_num=15) # Try ~middle frame

                if face_frame_img is None:
                    messages.error(request, "❌ Could not extract a usable frame from the video.")
                    user.needs_manual_review = True
                    user.save()
                    return redirect("verify") # Or dashboard with review status

                # Save the extracted frame temporarily for DeepFace
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf_face_frame:
                    cv2.imwrite(tf_face_frame.name, face_frame_img)
                    temp_face_frame_path = tf_face_frame.name
                    logger.info(f"Saved extracted face frame to: {temp_face_frame_path}")


                # --- 3. Perform Face Verification (ID Front vs Video Frame) ---
                logger.info(f"Performing face verification between {temp_id_front_path} and {temp_face_frame_path}")
                try:
                    # Use a robust detector and model
                    result = DeepFace.verify(
                        img1_path=temp_id_front_path,
                        img2_path=temp_face_frame_path,
                        model_name='VGG-Face', # Or 'Facenet', 'ArcFace' etc.
                        detector_backend='mtcnn' # Or 'opencv', 'ssd', 'dlib', 'retinaface'
                        # enforce_detection=False # Set to True if you want it to fail if no face is found
                    )
                    logger.info(f"DeepFace Result: {result}")
                    # Convert distance to confidence score (0 distance = 100% confidence)
                    # Adjust multiplier as needed, distance varies by model
                    confidence = max(0, (1 - result['distance']) * 100) # Basic conversion
                    user.confidence_score = round(confidence, 2)
                    user.is_verified = result['verified'] # Use DeepFace's direct verification result

                    # Set manual review if confidence is low but technically 'verified', or if not verified
                    confidence_threshold = 60 # Example threshold
                    if not user.is_verified or (user.is_verified and user.confidence_score < confidence_threshold):
                        user.needs_manual_review = True
                        user.is_verified = False # Mark as not verified if below threshold or failed match
                        messages.warning(request, f"⏳ Face match confidence ({user.confidence_score}%) is below threshold or failed. Submitted for manual review.")
                    else:
                         messages.success(request, f"✅ Face matched successfully (Confidence: {user.confidence_score}%)")


                except ValueError as ve:
                    # Handle cases where DeepFace couldn't find a face
                    logger.error(f"DeepFace ValueError (likely no face detected): {ve}")
                    messages.warning(request, f"⚠️ Could not detect a face in one of the images/video frame. Submitted for manual review.")
                    user.is_verified = False
                    user.needs_manual_review = True
                    user.confidence_score = 0
                except Exception as e:
                    logger.error(f"DeepFace verification error: {e}", exc_info=True)
                    messages.error(request, f"❌ An error occurred during face verification: {e}")
                    user.is_verified = False
                    user.needs_manual_review = True # Send to manual review on unexpected error


                # --- 4. Basic Liveness Check (Placeholder) ---
                # A real liveness check is complex. Here, we just check if the video exists.
                # In a real system, you'd analyze video frames for movement, blinking, etc.
                # Or use a dedicated liveness API/library.
                video_duration = 0
                try:
                    cap = cv2.VideoCapture(temp_video_path)
                    if cap.isOpened():
                         fps = cap.get(cv2.CAP_PROP_FPS)
                         frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                         video_duration = frame_count / fps if fps > 0 else 0
                         cap.release()
                    if video_duration > 1.0: # Example: require at least 1 second of video
                         user.liveness_check_passed = True
                         logger.info(f"Basic liveness check passed (video duration: {video_duration:.2f}s)")
                    else:
                         user.liveness_check_passed = False
                         user.needs_manual_review = True # Failed basic liveness -> manual review
                         user.is_verified = False # Fail verification if liveness fails
                         messages.warning(request, "⚠️ Video seems too short or invalid. Submitted for manual review.")
                         logger.warning(f"Basic liveness check failed (video duration: {video_duration:.2f}s)")
                except Exception as e:
                    logger.error(f"Error during basic liveness check: {e}", exc_info=True)
                    user.liveness_check_passed = False
                    user.needs_manual_review = True
                    user.is_verified = False
                    messages.warning(request, "⚠️ Error processing video for liveness check. Submitted for manual review.")


                # --- 5. Save Files to User Model ---
                # Only save if verification hasn't outright failed before this point
                # Or always save for review purposes
                logger.info("Saving uploaded files to user model")
                user.id_front.save(f"{user.username}_id_front{id_front_ext}", ContentFile(id_front_data), save=False)
                if id_back_data and temp_id_back_path:
                    user.id_back.save(f"{user.username}_id_back{id_back_ext}", ContentFile(id_back_data), save=False)
                user.selfie_video.save(f"{user.username}_selfie{video_ext}", ContentFile(video_data), save=False)

                # --- 6. Final Save and Redirect ---
                user.save() # Save all accumulated changes

                if user.is_verified:
                    messages.success(request, "✅ Verification successful!")
                    return redirect("dashboard")
                elif user.needs_manual_review:
                     # Message already added where needs_manual_review was set
                     return redirect("dashboard") # Go to dashboard, template will show review status
                else:
                     # Should have been caught by confidence/liveness/face detection checks
                     messages.error(request, "❌ Verification failed. Please try again or contact support.")
                     # Optionally clear fields if forcing retry? Depends on policy.
                     # user.id_front = None
                     # user.id_back = None
                     # user.selfie_video = None
                     # user.save()
                     return redirect("verify")


        except Exception as e:
            logger.error(f"Error during verification process for user {user.username}: {e}", exc_info=True)
            messages.error(request, f"❌ An unexpected error occurred during verification: {e}. Please try again.")
            # Ensure user state reflects failure
            user.is_verified = False
            user.needs_manual_review = False # Or True depending on policy for system errors
            user.confidence_score = None
            user.liveness_check_passed = False
            user.save()
            return redirect("verify")

        finally:
            # --- Clean up temporary files ---
            logger.debug("Cleaning up temporary files")
            if temp_id_front_path and os.path.exists(temp_id_front_path):
                os.remove(temp_id_front_path)
                logger.debug(f"Removed temp file: {temp_id_front_path}")
            if temp_id_back_path and os.path.exists(temp_id_back_path):
                os.remove(temp_id_back_path)
                logger.debug(f"Removed temp file: {temp_id_back_path}")
            if temp_video_path and os.path.exists(temp_video_path):
                os.remove(temp_video_path)
                logger.debug(f"Removed temp file: {temp_video_path}")
            if temp_face_frame_path and os.path.exists(temp_face_frame_path):
                os.remove(temp_face_frame_path)
                logger.debug(f"Removed temp file: {temp_face_frame_path}")


    # --- Render initial verification page (GET request) ---
    return render(request, "verification.html")

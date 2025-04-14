import platform
from django.conf import settings

if platform.system() != 'Windows':
    import fcntl

from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import RegisterForm, LoginForm
from .utils import extract_text_fields

from deepface import DeepFace
import cv2
import base64
import numpy as np
import os
import tempfile


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            if not request.user.is_verified:
                return redirect('verify')
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def dashboard_view(request):
    return render(request, 'dashboard.html')


def detect_id_card(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = w / float(h)
            if 1.3 < aspect_ratio < 1.7:
                return True
    return False


@login_required
def real_time_verification_view(request):
    if request.method == 'POST':
        id_img_base64 = request.POST.get("id_image")
        face_img_base64 = request.POST.get("face_image")

        if not id_img_base64 or not face_img_base64:
            messages.error(request, "Both ID and face images are required.")
            return redirect("verify")

        def decode_base64_image(data_url):
            header, encoded = data_url.split(',', 1)
            binary_data = base64.b64decode(encoded)
            np_arr = np.frombuffer(binary_data, dtype=np.uint8)
            return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        id_img = decode_base64_image(id_img_base64)
        face_img = decode_base64_image(face_img_base64)

        # Save to temp files for DeepFace
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as id_file, \
             tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as face_file:

            cv2.imwrite(id_file.name, id_img)
            cv2.imwrite(face_file.name, face_img)

            try:
                # OCR
                text_fields = extract_text_fields(id_file.name)
                request.user.full_name = text_fields.get('full_name', '')
                request.user.birth_date = text_fields.get('birth_date', '')
                request.user.document_number = text_fields.get('document_number', '')
                request.user.issue_date = text_fields.get('issue_date', '')

                # Face verification
                result = DeepFace.verify(img1_path=id_file.name, img2_path=face_file.name)
                request.user.confidence_score = round((1 - result['distance']) * 100, 2)
                request.user.is_verified = result['verified']

                # Detect ID presence
                id_detected = detect_id_card(id_img)
                if not id_detected:
                    messages.warning(request, "⚠️ No valid ID card detected.")
                    request.user.is_verified = False
                    request.user.needs_manual_review = True

                # Liveness detection - NOTE: This only works if you upload video. Here we simulate failure
                request.user.liveness_checked = False
                messages.warning(request, "Liveness check skipped (still image provided).")
                request.user.needs_manual_review = True

                request.user.save()

                if request.user.is_verified:
                    messages.success(request, "✅ Verification successful!")
                elif request.user.needs_manual_review:
                    messages.warning(request, "⏳ Your verification is under manual review.")

            except Exception as e:
                messages.error(request, f"❌ Verification error: {e}")

            finally:
                os.remove(id_file.name)
                os.remove(face_file.name)

        return redirect("dashboard")

    return render(request, "verification.html")


# Optional: liveness check placeholder (requires video input to work properly)
def detect_liveness(video_path):
    cap = cv2.VideoCapture(video_path)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    frame_count = 0
    face_detected = 0
    eyes_opened = 0
    motion_detected = False
    prev_face = None

    while True:
        ret, frame = cap.read()
        if not ret or frame_count > 60:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) > 0:
            face_detected += 1
            (x, y, w, h) = faces[0]
            roi_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            if len(eyes) >= 1:
                eyes_opened += 1

            if prev_face:
                dx = abs(prev_face[0] - x)
                dy = abs(prev_face[1] - y)
                if dx > 5 or dy > 5:
                    motion_detected = True
            prev_face = (x, y)

        frame_count += 1

    cap.release()
    blink_detected = 0 < face_detected and eyes_opened < face_detected
    return blink_detected and motion_detected

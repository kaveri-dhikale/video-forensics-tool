
import cv2
import hashlib
import os
import pandas as pd


def calculate_sha256(video_path):
    """
    Calculate the SHA-256 hash of a video file.
    This helps identify the exact file being analyzed.
    """
    sha256_hash = hashlib.sha256()

    with open(video_path, "rb") as video_file:
        for chunk in iter(lambda: video_file.read(4096), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def get_video_metadata(video_path):
    """
    Extract basic video metadata using OpenCV only.
    FFprobe and FFmpeg are not required.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError("The specified video file does not exist.")

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        cap.release()
        raise ValueError(
            "Unable to open the video. The format or codec may not be supported."
        )

    try:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        duration = frame_count / fps if fps > 0 else 0.0
        file_size = os.path.getsize(video_path)

        metadata = {
            "File Name": os.path.basename(video_path),
            "File Format": os.path.splitext(video_path)[1].lower(),
            "File Size (MB)": round(file_size / (1024 * 1024), 2),
            "Duration (seconds)": round(duration, 2),
            "Resolution": f"{width} x {height}",
            "Frame Width": width,
            "Frame Height": height,
            "Frames Per Second (FPS)": round(fps, 2),
            "Total Frames": frame_count,
            "SHA-256 Hash": calculate_sha256(video_path),
            "Metadata Method": "OpenCV"
        }

        return metadata

    finally:
        cap.release()


def extract_frames(video_path, output_dir, interval_seconds=5, max_frames=8):
    """
    Extract video frames at regular time intervals.

    Example:
    interval_seconds=5 extracts frames at approximately
    0, 5, 10, 15 seconds, and so on.
    """
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        cap.release()
        raise ValueError("Unable to open the video for frame extraction.")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0 or frame_count <= 0:
        cap.release()
        raise ValueError("The video does not provide valid frame information.")

    interval_frames = max(1, int(round(fps * interval_seconds)))
    saved_frames = []

    try:
        frame_index = 0

        while frame_index < frame_count and len(saved_frames) < max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            success, frame = cap.read()

            if not success:
                break

            timestamp = frame_index / fps
            frame_name = f"frame_{timestamp:.2f}s.jpg"
            frame_path = os.path.join(output_dir, frame_name)

            if cv2.imwrite(frame_path, frame):
                saved_frames.append({
                    "Frame": frame_name,
                    "Timestamp (seconds)": round(timestamp, 2),
                    "Path": frame_path
                })

            frame_index += interval_frames

    finally:
        cap.release()

    return saved_frames


def analyze_frame_differences(video_path, sample_interval_seconds=1):
    """
    Compare sampled consecutive video frames.

    Large differences are flagged for manual review.
    A flag does NOT prove video manipulation.
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        cap.release()
        raise ValueError("Unable to open the video for frame analysis.")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0 or frame_count <= 0:
        cap.release()
        raise ValueError("The video does not provide valid frame information.")

    sample_step = max(1, int(round(fps * sample_interval_seconds)))
    differences = []
    previous_gray = None
    previous_timestamp = None

    try:
        for frame_index in range(0, frame_count, sample_step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            success, frame = cap.read()

            if not success:
                continue

            timestamp = frame_index / fps
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (320, 180))

            if previous_gray is not None:
                difference_score = float(
                    cv2.absdiff(previous_gray, gray).mean()
                )

                differences.append({
                    "From Time (seconds)": round(previous_timestamp, 2),
                    "To Time (seconds)": round(timestamp, 2),
                    "Difference Score": round(difference_score, 2)
                })

            previous_gray = gray
            previous_timestamp = timestamp

    finally:
        cap.release()

    if not differences:
        return pd.DataFrame(columns=[
            "From Time (seconds)",
            "To Time (seconds)",
            "Difference Score",
            "Review Flag"
        ])

    df = pd.DataFrame(differences)

    median_score = df["Difference Score"].median()
    threshold = max(10.0, median_score * 2.5)

    df["Review Flag"] = df["Difference Score"].apply(
        lambda score: "Review" if score > threshold else "Normal"
    )

    return df

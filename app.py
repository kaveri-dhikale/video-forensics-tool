
import os
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

from forensic import (
    get_video_metadata,
    extract_frames,
    analyze_frame_differences
)
from report import generate_pdf


# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="Video Forensics Tool",
    page_icon="🔍",
    layout="wide"
)

# ---------------- SIMPLE LIGHT THEME ----------------

st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
        color: #222222;
    }

    .block-container {
        max-width: 1050px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: #202b3c;
    }

    .subtitle {
        color: #667085;
        font-size: 16px;
        margin-bottom: 24px;
    }

    .info-card {
        border: 1px solid #e4e7ec;
        border-radius: 10px;
        padding: 16px;
        background-color: #fafbfc;
        margin-bottom: 12px;
    }

    .hash-box {
        background-color: #f5f7fa;
        border: 1px solid #e4e7ec;
        padding: 12px;
        border-radius: 8px;
        overflow-wrap: anywhere;
        font-family: monospace;
        font-size: 13px;
    }

    div.stButton > button[kind="primary"] {
        background-color: #2563eb;
        border: none;
        border-radius: 7px;
        color: white;
        min-height: 42px;
    }

    div.stButton > button[kind="primary"]:hover {
        background-color: #1d4ed8;
        color: white;
    }

    div[data-testid="stDownloadButton"] button {
        border-radius: 7px;
        min-height: 42px;
    }

    hr {
        border-color: #e4e7ec;
    }
    
    
    
    
    
    /* Video uploader label */
    div[data-testid="stFileUploader"] label,
    div[data-testid="stFileUploader"] label p {
    color: #202b3c !important;
    font-weight: 600 !important;
    }

    /* Upload area */
    div[data-testid="stFileUploader"] section {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    }

    /* Browse files button */
    div[data-testid="stFileUploader"] button {
    background-color: #2598eb !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    }

    /* Upload instructions and supported file types */
    div[data-testid="stFileUploader"] section,
    div[data-testid="stFileUploader"] section span,
    div[data-testid="stFileUploader"] section small,
    div[data-testid="stFileUploader"] section p {
    color: #334155 !important;
    }

    /* Selected file name */
    div[data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] p {
    color: #202b3c !important;
    }

</style>
""", unsafe_allow_html=True)


# ---------------- PAGE HEADER ----------------

st.title("Video Forensics Tool")

st.markdown(
    '<p class="subtitle">'
    'Analyze video properties, verify file integrity, '
    'inspect frame differences, and generate a PDF report.'
    '</p>',
    unsafe_allow_html=True
)

st.info(
    "This tool performs basic video forensic screening. "
    "Flagged frame differences are indicators for manual review, "
    "not proof of video manipulation."
)


# ---------------- VIDEO UPLOAD ----------------

st.subheader("1. Upload Video")

uploaded_file = st.file_uploader(
    "Choose a video file",
    type=["mp4", "avi", "mov", "mkv", "webm", "mpeg", "mpg"],
    help="Select a video stored on your computer."
)

if uploaded_file is not None:
    st.markdown(
        f"**Selected file:** {uploaded_file.name}"
    )

    st.caption(
        f"File size: {uploaded_file.size / (1024 * 1024):.2f} MB"
    )

    # Optional analysis settings
    with st.expander("Analysis settings", expanded=False):
        sample_interval = st.selectbox(
            "Frame comparison interval",
            options=[1, 2, 3, 5],
            index=0,
            format_func=lambda x: f"Every {x} second(s)"
        )

        extraction_interval = st.selectbox(
            "Extract sample frames every",
            options=[2, 5, 10],
            index=1,
            format_func=lambda x: f"{x} seconds"
        )

        max_frames = st.slider(
            "Maximum sample frames to extract",
            min_value=2,
            max_value=20,
            value=8
        )

    analyze_button = st.button(
        "Analyze Video",
        type="primary",
        use_container_width=True
    )

    # ---------------- ANALYSIS ----------------

    if analyze_button:
        # Clear previous results before analyzing another file.
        st.session_state.pop("forensic_result", None)

        try:
            with st.spinner(
                "Analyzing video... Please wait."
            ):
                suffix = Path(uploaded_file.name).suffix.lower()

                with tempfile.TemporaryDirectory() as temp_dir:
                    video_path = os.path.join(
                        temp_dir,
                        "uploaded_video" + suffix
                    )

                    with open(video_path, "wb") as file:
                        file.write(uploaded_file.getvalue())

                    # 1. Extract metadata, including SHA-256.
                    information = get_video_metadata(video_path)

                    sha256_hash = information["SHA-256 Hash"]

                    # 2. Analyze sampled frame differences.
                    differences = analyze_frame_differences(
                        video_path,
                        sample_interval_seconds=sample_interval
                    )

                    # 3. Extract sample frames.
                    frame_results = []
                    frame_warning = None

                    try:
                        frame_dir = os.path.join(
                            temp_dir, "extracted_frames"
                        )

                        extracted_frames = extract_frames(
                            video_path,
                            frame_dir,
                            interval_seconds=extraction_interval,
                            max_frames=max_frames
                        )

                        # Keep image bytes because the temporary
                        # directory will be removed after analysis.
                        for item in extracted_frames:
                            with open(item["Path"], "rb") as image_file:
                                frame_results.append({
                                    "Frame": item["Frame"],
                                    "Timestamp (seconds)": item[
                                        "Timestamp (seconds)"
                                    ],
                                    "Image": image_file.read()
                                })

                    except Exception as exc:
                        frame_warning = str(exc)

                    # 4. Generate the PDF report.
                    pdf_bytes = generate_pdf(
                        information,
                        sha256_hash,
                        differences
                    )

                    st.session_state["forensic_result"] = {
                        "filename": uploaded_file.name,
                        "information": information,
                        "sha256": sha256_hash,
                        "differences": differences,
                        "frames": frame_results,
                        "frame_warning": frame_warning,
                        "pdf": pdf_bytes
                    }

            st.success("Video analysis completed.")

        except Exception as exc:
            st.error(
                "Unable to analyze this video. It may be corrupted "
                "or use an unsupported codec."
            )
            st.caption(f"Technical details: {exc}")


# ---------------- DISPLAY RESULTS ----------------

result = st.session_state.get("forensic_result")

# Display only results belonging to the currently selected file.
if result is not None and (
    uploaded_file is not None
    and result["filename"] == uploaded_file.name
):
    st.divider()
    st.header("2. Analysis Results")

    information = result["information"]
    differences = result["differences"]

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Duration",
        f'{information["Duration (seconds)"]} sec'
    )

    col2.metric(
        "Resolution",
        information["Resolution"]
    )

    col3.metric(
        "Frame Rate",
        f'{information["Frames Per Second (FPS)"]} FPS'
    )

    if "Review Flag" in differences.columns:
        flagged_count = int(
            (differences["Review Flag"] == "Review").sum()
        )
    else:
        flagged_count = 0

    col4.metric(
        "Flagged Intervals",
        flagged_count
    )

    # Metadata table
    st.subheader("Video Information")

    metadata_display = {
        key: value
        for key, value in information.items()
        if key != "SHA-256 Hash"
    }

    metadata_df = pd.DataFrame(
        list(metadata_display.items()),
        columns=["Property", "Value"]
    )

    st.dataframe(
        metadata_df,
        hide_index=True,
        use_container_width=True
    )

    # Hash
    st.subheader("File Integrity")

    st.caption(
        "SHA-256 digital fingerprint of the analyzed file:"
    )

    st.markdown(
        f'<div class="hash-box">{result["sha256"]}</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Save this hash if you need to compare the file with a "
        "trusted reference later. A hash alone cannot establish "
        "the video's authenticity."
    )

    # Frame difference results
    st.divider()
    st.subheader("3. Frame Difference Analysis")

    if not differences.empty:
        st.caption(
            "Scores compare sampled grayscale frames. "
            "A higher score means a larger visual difference."
        )

        st.dataframe(
            differences,
            hide_index=True,
            use_container_width=True
        )

        if flagged_count > 0:
            st.warning(
                f"{flagged_count} interval(s) flagged for manual "
                "review. This does not establish tampering."
            )
        else:
            st.success(
                "No sampled intervals exceeded the screening "
                "threshold. This does not prove authenticity."
            )

    else:
        st.warning(
            "No frame comparisons could be produced for this video."
        )

    # Extracted frames
    st.divider()
    st.subheader("4. Extracted Sample Frames")

    if result["frame_warning"]:
        st.warning(
            "Frame extraction could not be completed: "
            + result["frame_warning"]
        )

    frames = result["frames"]

    if frames:
        for start in range(0, len(frames), 2):
            columns = st.columns(2)

            for offset, column in enumerate(columns):
                index = start + offset

                if index >= len(frames):
                    break

                frame = frames[index]

                with column:
                    st.image(
                        frame["Image"],
                        caption=(
                            f'{frame["Frame"]} | '
                            f'{frame["Timestamp (seconds)"]} seconds'
                        ),
                        use_container_width=True
                    )

    else:
        st.caption("No sample frames were extracted.")

    # PDF download
    st.divider()
    st.subheader("5. Download Report")

    st.write(
        "Download the PDF containing video information, "
        "the SHA-256 hash, flagged intervals, and limitations."
    )

    st.download_button(
        label="Download PDF Report",
        data=result["pdf"],
        file_name="video_forensics_report.pdf",
        mime="application/pdf",
        use_container_width=True
    )

else:
    st.divider()
    st.subheader("How to use this tool")

    st.markdown("""
    1. Upload a supported video file.
    2. Optionally adjust the analysis settings.
    3. Click **Analyze Video**.
    4. Review the metadata, hash, frame comparisons, and sample frames.
    5. Download the PDF report.
    """)

st.divider()

st.caption(
    "Digital Video Forensics Mini Project | "
    "Python, OpenCV and Streamlit | No FFprobe required"
)

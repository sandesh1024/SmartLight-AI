# backend/ai/video_manager.py

import cv2
import threading
import os


class VideoManager:
    def __init__(self, video_paths: dict):
        """
        Example video_paths:

        video_paths = {
            "lane1": "videos/video1.mp4",
            "lane2": "videos/video2.mp4",
            "lane3": "videos/video3.mp4",
            "lane4": "videos/video4.mp4",
            "lane5": "videos/video5.mp4",
            "lane6": "videos/video6.mp4",
            "lane7": "videos/video7.mp4",
            "lane8": "videos/video8.mp4",
        }
        """
        self.video_paths = video_paths
        self.captures = {}
        self.frames = {}
        self.locks = {}
        self.running = True

        self._initialize_videos()

    # -------------------------------------------------------
    # Open all videos and start background reading threads
    # -------------------------------------------------------
    def _initialize_videos(self):

        # Get project root directory (SmartLight-AI)
        BASE_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

        for vid, relative_path in self.video_paths.items():

            full_path = os.path.join(BASE_DIR, relative_path)

            print(f"Opening video: {full_path}")  # Debug print

            cap = cv2.VideoCapture(full_path)

            if not cap.isOpened():
                raise RuntimeError(f"Failed to open video: {full_path}")

            self.captures[vid] = cap
            self.frames[vid] = None
            self.locks[vid] = threading.Lock()

            thread = threading.Thread(
                target=self._update_frames,
                args=(vid,),
                daemon=True
            )
            thread.start()

    # -------------------------------------------------------
    # Continuously read frames
    # -------------------------------------------------------
    def _update_frames(self, video_id):

        cap = self.captures[video_id]

        while self.running:
            ret, frame = cap.read()

            if not ret:
                # Restart video when it ends
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            with self.locks[video_id]:
                self.frames[video_id] = frame

    # -------------------------------------------------------
    # Get latest frame
    # -------------------------------------------------------
    def get_frame(self, video_id):

        if video_id not in self.frames:
            return None

        with self.locks[video_id]:
            return self.frames[video_id]

    # -------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------
    def stop(self):
        self.running = False

        for cap in self.captures.values():
            cap.release()
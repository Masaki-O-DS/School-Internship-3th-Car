# controllers/camera_control.py
import cv2
from cv2 import aruco
from picamera2 import Picamera2
import time
import logging
import threading
import os
import queue

# ログの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def camera_control(audio_queue):
    """
    カメラから映像を取得し、ARマーカーを検出します。
    ARマーカーが検出された場合、画像を保存し、Bluetoothスピーカーで音声を再生します。
    """
    try:
        # Picamera2の初期化
        picam2 = Picamera2()

        # RGB888形式の低解像度設定（パフォーマンス向上のため）
        resolution = (640, 480)
        preview_config = picam2.create_preview_configuration(
            main={"format": 'RGB888', "size": resolution}
        )
        picam2.configure(preview_config)
        picam2.start()
        logging.info("Camera started successfully.")

        # ARUCO辞書とパラメータの初期化
        aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)  # 4x4ビットのARUCOマーカー
        parameters = aruco.DetectorParameters_create()
        parameters.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX  # コーナー精度の向上

        # FPS計算用の変数
        frame_count = 0
        start_time = time.time()
        fps = 0

        def update_fps():
            nonlocal frame_count, start_time, fps
            while True:
                time.sleep(0.5)  # FPSをより頻繁に更新
                elapsed_time = time.time() - start_time
                if elapsed_time > 0:
                    fps = frame_count / elapsed_time
                    logging.info(f"FPS: {fps:.2f}")
                    frame_count = 0
                    start_time = time.time()

        # FPS更新用のスレッドを開始
        fps_thread = threading.Thread(target=update_fps, daemon=True)
        fps_thread.start()

        # imgフォルダのパスを設定
        script_dir = os.path.dirname(os.path.abspath(__file__))
        img_dir = os.path.join(os.path.dirname(script_dir), 'img')
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
            logging.info(f"Image directory created at {img_dir}")

        while True:
            # カメラからフレームをキャプチャ
            frame = picam2.capture_array()

            # キャプチャしたフレームの検証
            if frame is None or frame.size == 0:
                logging.warning("Empty frame captured. Skipping frame processing.")
                continue

            # ARUCO検出のためにグレースケールに変換
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

            # ARUCOマーカーの検出
            corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

            # 検出されたマーカーを元のフレームに描画
            if ids is not None:
                frame_markers = aruco.drawDetectedMarkers(frame.copy(), corners, ids)
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"aruco_detected_{timestamp}.png"
                filepath = os.path.join(img_dir, filename)
                cv2.imwrite(filepath, frame_markers)
                logging.info(f"AR marker detected. Image saved as {filepath}")

                # 音声再生の指示をキューに送信
                audio_queue.put("PLAY_AR_SOUND")

                # 一定時間後に音声停止の指示を送信（例：2秒後）
                threading.Timer(2.0, lambda: audio_queue.put("STOP_AR_SOUND")).start()
            else:
                frame_markers = frame.copy()

            # FPSカウントを増加
            frame_count += 1

    except KeyboardInterrupt:
        logging.info("\nExiting camera program gracefully.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in camera_control: {e}")
    finally:
        # カメラの停止とOpenCVのウィンドウを閉じる（imshowを使用しないため不要）
        if 'picam2' in locals():
            try:
                picam2.stop()
                logging.info("Camera stopped successfully.")
            except Exception as e:
                logging.error(f"Error stopping camera: {e}")
        cv2.destroyAllWindows()
        logging.info("Camera resources have been released.")

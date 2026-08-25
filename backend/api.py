import base64
import logging
import os
import shutil

from flask import Flask, Response, jsonify, request, stream_with_context, send_file

import config
import utils
from data import data, photos_taken, states
from modules.camera import CameraThread


def create(name: str) -> Flask:
    app = Flask(name)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    @app.route("/dashboard")
    def get_dashboard():
        """Serve the current dashboard data.
        Returns:
            dict: The current dashboard data.
        """
        return jsonify(data.get_data())

    @app.route("/dashboard/<string:key>", methods=["PUT"])
    def put_dashboard_value(key: str):
        """Update a dashboard variable with a new value.
        Args:
            key: The key of the variable to update.
        Returns:
            dict: The updated variable or an error message.
        """
        try:
            value = float(request.args.get("value", 0))
        except ValueError:
            return jsonify({"error": "Invalid value"}), 400

        if data.set(key, value):
            return jsonify({key: data.get(key)})
        return jsonify({"error": f" Key '{key}' not found"}), 404

    @app.route("/video/<int:index>")
    def get_video(index: int):
        """Get the connection for generated frames
        Args:
            index: The camera index
        Returns:
            The generator wrapped in a HTTP response
        """
        if index >= len(CameraThread.cameras) or index < 0:
            return Response()

        server = CameraThread.cameras[index]
        return Response(
            stream_with_context(server.generate_frames()),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/photos")
    def get_photos():
        """Get all the photos taken on the last execution"""

        photos_dir = utils.get_session_dirpath(config.CAM_DEST, states.get(states.SESSION))
        formats = (".jpg", ".jpeg", ".png")

        limits = {
            "RGBT": photos_taken.get(photos_taken.TOP),
            "RGB": photos_taken.get(photos_taken.SIDE),
            "RGN": photos_taken.get(photos_taken.UV),
            "RE": photos_taken.get(photos_taken.IR),
        }

        photos = {
            "RGBT": [],
            "RGB": [],
            "RGN": [],
            "RE": [],
        }

        if not states.get(states.TRANSFERRED):
            return jsonify(
                {"photo_counts": limits, "photos": photos, "completed": False}
            )

        files = [file for file in os.listdir(photos_dir) if file.lower().endswith(formats)]
        files.sort(key=lambda file: os.path.getctime(os.path.join(photos_dir, file)), reverse=True)

        if len(files) == 0:
            logging.error("No photos stored.")
            return jsonify(
                {"photo_counts": limits, "photos": photos, "completed": True}
            )

        latest_timestamp = utils.extract_photo_name(files[0])[1]
        session = states.get(states.SESSION)

        for file in files:
            label, timestamp, step, ext = utils.extract_photo_name(file)
            if timestamp != latest_timestamp:
                continue
            if label not in photos:
                continue

            utils.insert_array_padded(
                photos[label],
                int(step),
                {"filename": file, "src": f"/results/{str(session).zfill(8)}/{file}"},
            )

        return jsonify({"photo_counts": limits, "photos": photos, "completed": True})


    @app.route("/session")
    def get_session():
        zipped = utils.zip_dir(config.CAM_DEST)
        print(zipped)
        return send_file(
            zipped,
            mimetype="application/zip",
            as_attachment=True,
            download_name="all_sessions.zip",
        )

    @app.route("/session", methods=["DELETE"])
    def delete_session():
        try:
            for name in os.listdir(config.CAM_DEST):
                path = os.path.join(config.CAM_DEST, name)
                if os.path.isdir(path): shutil.rmtree(path)
                else: os.remove(path)
            return jsonify({"ok": True, "reason": ""})
        except Exception as e:
            return jsonify({"ok": False, "reason": str(e)})

    return app


def run(app: Flask, host: str, port: int):
    app.run(host=host, port=port, debug=False, use_reloader=False)

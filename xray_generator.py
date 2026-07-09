from datetime import datetime, timezone

import cv2
import numpy as np

from deepface import DeepFace
from sklearn.metrics.pairwise import cosine_similarity


class XRayGenerator:
    def __init__(
        self,
        tmdb_client,
        frame_samples_per_second=4,
        interval_seconds=10,
        threshold=0.65,
        high_confidence_threshold=0.78,
        min_detections=2,
        max_actors=30,
        images_per_actor=10,
        tagged_images_per_actor=8,
        use_tagged_images=True,
        model_name="Facenet512",
        detector_backend="mtcnn",
        recognition_image_size="w342",
        xray_image_size="w185"
    ):
        self.tmdb = tmdb_client
        self.frame_samples_per_second = frame_samples_per_second
        self.interval_seconds = interval_seconds
        self.threshold = threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.min_detections = min_detections
        self.max_actors = max_actors
        self.images_per_actor = images_per_actor
        self.tagged_images_per_actor = tagged_images_per_actor
        self.use_tagged_images = use_tagged_images
        self.model_name = model_name
        self.detector_backend = detector_backend
        self.recognition_image_size = recognition_image_size
        self.xray_image_size = xray_image_size

        self.embeddings_db = []
        self.labels_db = []
        self.actors_db = {}

    def generate(self, video_path, movie_query=None, movie_id=None):
        movie = (
            self.tmdb.get_movie(movie_id)
            if movie_id
            else self.tmdb.search_movie(movie_query)
        )
        print(f"Pelicula: {movie['title']} ({movie.get('year') or 'sin fecha'})")

        actors = self.tmdb.get_cast(
            movie["tmdb_id"],
            max_actors=self.max_actors,
            image_size=self.xray_image_size
        )
        print(f"Actores cargados desde TMDb: {len(actors)}")

        self.build_reference_database(actors)
        timeline = self.process_video(video_path)
        return self.create_xray_json(movie, timeline)

    def normalize_embedding(self, rep):
        emb = np.array(rep, dtype=np.float32)
        norm = np.linalg.norm(emb)

        if norm == 0 or np.isnan(norm):
            return None

        return emb / norm

    def get_embeddings(self, img, enforce_detection=True):
        try:
            reps = DeepFace.represent(
                img_path=img,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=enforce_detection
            )

            if isinstance(reps, dict):
                reps = [reps]

            embeddings = []

            for rep in reps:
                emb = self.normalize_embedding(rep["embedding"])
                if emb is not None:
                    embeddings.append(emb)

            return embeddings

        except Exception:
            return []

    def build_reference_database(self, actors):
        print("\n==============================")
        print("CONSTRUYENDO BASE DESDE TMDB")
        print("==============================")

        self.embeddings_db = []
        self.labels_db = []
        self.actors_db = {}

        for actor in actors:
            actor_id = str(actor["tmdb_id"])
            self.actors_db[actor_id] = actor

            print(f"\nACTOR: {actor['name']} - {actor.get('character') or ''}")

            count = 0
            image_paths = self.tmdb.get_actor_images(
                actor["tmdb_id"],
                profile_path=actor.get("profile_path"),
                max_profile_images=self.images_per_actor,
                max_tagged_images=self.tagged_images_per_actor,
                use_tagged_images=self.use_tagged_images
            )
            print(f"Imagenes remotas: {len(image_paths)}")

            for image_path in image_paths:
                img = self.tmdb.download_image(
                    image_path,
                    size=self.recognition_image_size
                )
                if img is None:
                    continue

                for emb in self.get_embeddings(img, enforce_detection=True):
                    self.embeddings_db.append(emb)
                    self.labels_db.append(actor_id)
                    count += 1

            actor["reference_images"] = len(image_paths)
            actor["reference_embeddings"] = count
            actor["reference_quality"] = self.reference_quality(count)

            print(f"Embeddings validos: {count}")

        print("\nBASE LISTA")
        print(f"Total embeddings: {len(self.embeddings_db)}\n")

        if len(self.embeddings_db) == 0:
            raise RuntimeError("No se ha generado ningun embedding valido desde TMDb.")

    def reference_quality(self, embeddings_count):
        if embeddings_count <= 1:
            return "low"
        if embeddings_count <= 4:
            return "medium"
        return "high"

    def identify(self, emb):
        if len(self.embeddings_db) == 0:
            return None, 0.0

        sims = cosine_similarity([emb], self.embeddings_db)[0]

        best_actor_id = None
        best_score = -1.0

        for actor_id in set(self.labels_db):
            idxs = [i for i, label in enumerate(self.labels_db) if label == actor_id]
            score = np.max(sims[idxs])

            if score > best_score:
                best_score = score
                best_actor_id = actor_id

        return best_actor_id, float(best_score)

    def save_interval(self, results, start, end, temp_actors):
        actors = []

        for actor_id, data in sorted(
            temp_actors.items(),
            key=lambda item: (item[1]["detections"], item[1]["score"]),
            reverse=True
        ):
            enough_detections = data["detections"] >= self.min_detections
            high_score = data["score"] >= self.high_confidence_threshold

            if not enough_detections and not high_score:
                continue

            actor = self.actors_db[actor_id]
            actors.append({
                "tmdb_id": actor["tmdb_id"],
                "name": actor["name"],
                "character": actor.get("character"),
                "score": round(data["score"], 4),
                "detections": data["detections"],
                "image_url": actor.get("image_url"),
                "reference_images": actor.get("reference_images", 0),
                "reference_embeddings": actor.get("reference_embeddings", 0),
                "reference_quality": actor.get("reference_quality", "unknown")
            })

        results.append({
            "start": start,
            "end": end,
            "actors": actors
        })

        names = [actor["name"] for actor in actors]
        print(f"Intervalo {start}-{end}: {names}")
        temp_actors.clear()

    def process_video(self, video_path):
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise FileNotFoundError(f"No se pudo abrir el video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps is None or fps == 0:
            fps = 25

        print(f"\nFPS: {fps}")

        step_frame = max(1, int(fps / self.frame_samples_per_second))
        step_save = max(1, int(fps * self.interval_seconds))

        frame_id = 0
        interval_start = 0

        temp_actors = {}
        results = []

        print(f"Procesando cada {step_frame} frames")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_id % step_frame == 0:
                for emb in self.get_embeddings(frame, enforce_detection=True):
                    actor_id, score = self.identify(emb)

                    if actor_id is not None and score > self.threshold:
                        if actor_id not in temp_actors:
                            temp_actors[actor_id] = {
                                "score": 0.0,
                                "detections": 0
                            }

                        temp_actors[actor_id]["score"] = max(
                            temp_actors[actor_id]["score"],
                            score
                        )
                        temp_actors[actor_id]["detections"] += 1

            if frame_id % step_save == 0 and frame_id != 0:
                interval_end = int(frame_id / fps)
                self.save_interval(results, interval_start, interval_end, temp_actors)
                interval_start = interval_end

            frame_id += 1

        duration_seconds = int(frame_id / fps) if fps else 0

        if temp_actors or duration_seconds > interval_start:
            self.save_interval(results, interval_start, duration_seconds, temp_actors)

        cap.release()
        return results

    def create_xray_json(self, movie, timeline):
        return {
            "movie": movie,
            "source": {
                "provider": "TMDb",
                "generated_at": datetime.now(timezone.utc).isoformat()
            },
            "settings": {
                "frame_samples_per_second": self.frame_samples_per_second,
                "interval_seconds": self.interval_seconds,
                "threshold": self.threshold,
                "high_confidence_threshold": self.high_confidence_threshold,
                "min_detections": self.min_detections,
                "images_per_actor": self.images_per_actor,
                "tagged_images_per_actor": self.tagged_images_per_actor,
                "use_tagged_images": self.use_tagged_images,
                "model": self.model_name,
                "detector": self.detector_backend
            },
            "timeline": timeline
        }

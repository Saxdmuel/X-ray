import os
import cv2
import numpy as np
import requests


class TMDbClient:
    def __init__(
        self,
        api_key="",
        bearer_token="",
        language="es-ES",
        api_url="https://api.themoviedb.org/3",
        image_url="https://image.tmdb.org/t/p"
    ):
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.language = language
        self.api_url = api_url
        self.image_url_base = image_url

    def _headers(self):
        token = (
            self.bearer_token
            or os.getenv("TMDB_BEARER_TOKEN")
            or os.getenv("TMDB_TOKEN")
        )

        if token:
            return {
                "Authorization": f"Bearer {token}",
                "accept": "application/json"
            }

        return {"accept": "application/json"}

    def _params(self, params=None):
        params = dict(params or {})
        api_key = self.api_key or os.getenv("TMDB_API_KEY")

        if api_key:
            params["api_key"] = api_key

        return params

    def _has_auth(self):
        return bool(
            self.api_key
            or self.bearer_token
            or os.getenv("TMDB_API_KEY")
            or os.getenv("TMDB_BEARER_TOKEN")
            or os.getenv("TMDB_TOKEN")
        )

    def get(self, path, params=None):
        if not self._has_auth():
            raise RuntimeError(
                "Falta la API de TMDb. Rellena TMDB_API_KEY o TMDB_BEARER_TOKEN."
            )

        response = requests.get(
            f"{self.api_url}{path}",
            headers=self._headers(),
            params=self._params(params),
            timeout=20
        )
        response.raise_for_status()
        return response.json()

    def image_url(self, image_path, size="w185"):
        if not image_path:
            return None

        return f"{self.image_url_base}/{size}{image_path}"

    def search_movie(self, query):
        data = self.get(
            "/search/movie",
            {"query": query, "language": self.language}
        )

        results = data.get("results", [])
        if not results:
            raise RuntimeError(f"No se encontro la pelicula en TMDb: {query}")

        return self._format_movie(results[0])

    def get_movie(self, movie_id):
        data = self.get(
            f"/movie/{movie_id}",
            {"language": self.language}
        )
        return self._format_movie(data)

    def get_cast(self, movie_id, max_actors=30, image_size="w185"):
        data = self.get(
            f"/movie/{movie_id}/credits",
            {"language": self.language}
        )

        actors = []

        for actor in data.get("cast", [])[:max_actors]:
            profile_path = actor.get("profile_path")
            actors.append({
                "tmdb_id": actor["id"],
                "name": actor.get("name"),
                "character": actor.get("character"),
                "order": actor.get("order"),
                "profile_path": profile_path,
                "image_url": self.image_url(profile_path, image_size)
            })

        return actors

    def get_actor_images(
        self,
        actor_id,
        profile_path=None,
        max_profile_images=10,
        max_tagged_images=8,
        use_tagged_images=True
    ):
        images = []

        if profile_path:
            images.append(profile_path)

        try:
            data = self.get(f"/person/{actor_id}/images")
            for image in data.get("profiles", []):
                path = image.get("file_path")
                if path and path not in images:
                    images.append(path)
                if len(images) >= max_profile_images:
                    break
        except requests.RequestException:
            pass

        limit = max_profile_images + max_tagged_images

        if use_tagged_images and len(images) < limit:
            try:
                data = self.get(f"/person/{actor_id}/tagged_images")
                for image in data.get("results", []):
                    path = image.get("file_path")
                    if path and path not in images:
                        images.append(path)
                    if len(images) >= limit:
                        break
            except requests.RequestException:
                pass

        return images[:limit]

    def download_image(self, image_path, size="w342"):
        url = self.image_url(image_path, size)
        if not url:
            return None

        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            return None

        data = np.frombuffer(response.content, np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)

    def _format_movie(self, movie):
        return {
            "tmdb_id": movie["id"],
            "title": movie.get("title") or movie.get("original_title"),
            "original_title": movie.get("original_title"),
            "year": (movie.get("release_date") or "")[:4] or None
        }
    def buscar_peliculas(self, query):
        data = self.get(
            "/search/movie",
            {"query": query, "language": self.language}
        )

        results = data.get("results", [])

        return [self._format_movie(movie) for movie in results]
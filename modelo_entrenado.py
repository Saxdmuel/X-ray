import argparse
import json
import os
from tmdb_client import TMDbClient
from xray_generator import XRayGenerator
print("Modelo OK")
from dotenv import load_dotenv

load_dotenv()
# ===========================
# CONFIG
# ===========================

VIDEO_PATH = "malditos-baja.mp4"
MOVIE_QUERY = "Inglourious Basterds"
OUTPUT_PATH = "resultado.json"

FRAMES_POR_SEGUNDO = 8
INTERVALO_SEGUNDOS = 10

UMBRAL = 0.64
UMBRAL_ALTO = 0.78
MIN_DETECCIONES = 2

MAX_ACTORES = 30
IMAGENES_POR_ACTOR = 10
IMAGENES_TAGGED_POR_ACTOR = 8
USAR_TAGGED_IMAGES = True
IDIOMA = "es-ES"

MODEL_NAME = "Facenet512"
DETECTOR_BACKEND = "mtcnn"

TMDB_IMAGE_SIZE_RECOGNITION = "w342"
TMDB_IMAGE_SIZE_XRAY = "w185"


TMDB_API_KEY = os.getenv("TMDB_BEARER_TOKEN")
TMDB_BEARER_TOKEN = ""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera un JSON X-Ray de actores usando TMDb y DeepFace."
    )
    parser.add_argument(
        "video",
        nargs="?",
        default=VIDEO_PATH,
        help="Ruta del video a analizar."
    )
    parser.add_argument(
        "--movie",
        default=MOVIE_QUERY,
        help="Titulo de la pelicula para buscar en TMDb."
    )
    parser.add_argument(
        "--movie-id",
        type=int,
        default=None,
        help="ID de TMDb. Si se indica, no se busca por titulo."
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_PATH,
        help="Ruta del JSON de salida."
    )
    return parser.parse_args()


def crear_generador(progress_callback=None):
    print("Creando TMDbClient")
    tmdb = TMDbClient(
        api_key=TMDB_API_KEY,
        bearer_token=TMDB_BEARER_TOKEN,
        language=IDIOMA
    )
    print("Creando XRayGenerator")
    return XRayGenerator(
        tmdb_client=tmdb,
        frame_samples_per_second=FRAMES_POR_SEGUNDO,
        interval_seconds=INTERVALO_SEGUNDOS,
        threshold=UMBRAL,
        high_confidence_threshold=UMBRAL_ALTO,
        min_detections=MIN_DETECCIONES,
        max_actors=MAX_ACTORES,
        images_per_actor=IMAGENES_POR_ACTOR,
        tagged_images_per_actor=IMAGENES_TAGGED_POR_ACTOR,
        use_tagged_images=USAR_TAGGED_IMAGES,
        model_name=MODEL_NAME,
        detector_backend=DETECTOR_BACKEND,
        recognition_image_size=TMDB_IMAGE_SIZE_RECOGNITION,
        xray_image_size=TMDB_IMAGE_SIZE_XRAY,
        progress_callback=progress_callback
    )

def generar_xray(
    video_path,
    movie_query,
    movie_id=None,
    output_path=OUTPUT_PATH,
    progress_callback=None
):
    print("1. Entrando en generar_xray")

    generator = crear_generador(progress_callback)
    print("2. Generador creado")

    result = generator.generate(
        video_path=video_path,
        movie_query=movie_query,
        movie_id=movie_id
    )
    print("3. JSON generado")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print("4. Archivo guardado")

    return result

if __name__ == "__main__":
    args = parse_args()

    generar_xray(
        video_path=args.video,
        movie_query=args.movie,
        movie_id=args.movie_id,
        output_path=args.output,
        progress_callback=None
    )

    print(f"FIN: {args.output}")

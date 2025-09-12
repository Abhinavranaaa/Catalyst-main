from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.models import PointStruct
from question.models import Question   # Replace with your actual app name / import path
from itertools import islice
import os

from dotenv import load_dotenv
load_dotenv()

if os.getenv("RENDER") != "true":
    load_dotenv()

class Command(BaseCommand):

    help = "Sync question embeddings and metadata to remote Qdrant instance"

    def handle(self, *args, **kwargs):
        COLLECTION_NAME = "questions"
        VECTOR_SIZE = 384
        BATCH_SIZE = 64

        # Load embedding model
        self.stdout.write(self.style.NOTICE("🔁 Loading embedding model..."))
        model = SentenceTransformer("all-MiniLM-L6-v2")

        # Connect to remote Qdrant
        self.stdout.write("🌐 Connecting to Qdrant...")
        qdrant = QdrantClient(
            url=os.getenv("VECTOR_DB_URL"),          # 🔑 Use env var
            api_key=os.getenv("VECTOR_DB_KEY")   # 🔐 Keep secrets safe
        )

        # Create or recreate the Qdrant collection
        self.stdout.write(f"🧱 Creating/recreating collection '{COLLECTION_NAME}'...")
        qdrant.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )

        # Fetch questions from Postgres
        self.stdout.write("🗃 Fetching questions from database...")
        questions = Question.objects.all()
        self.stdout.write(f"📌 Found {questions.count()} questions.")

        # Prepare embedding points
        def batch_iterable(iterable, batch_size):
            iterator = iter(iterable)
            while True:
                batch = list(islice(iterator, batch_size))
                if not batch:
                    break
                yield batch

        points = []

        for q in questions:
            input_text = f"Subject: {q.subject or ''}. Question: {q.text}"
            vector = model.encode(input_text).tolist()

            point = PointStruct(
                id=str(q.id),  # Qdrant accepts str or int
                vector=vector,
                payload={
                    "difficulty": q.difficulty,
                    "question_id": str(q.id)  # Optional but helpful
                }
            )
            points.append(point)

        # Upsert in batches
        self.stdout.write(f"📤 Uploading {len(points)} vectors to Qdrant in batches of {BATCH_SIZE}...")
        uploaded = 0
        for i, point_batch in enumerate(batch_iterable(points, BATCH_SIZE)):
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=point_batch
            )
            uploaded += len(point_batch)
            self.stdout.write(f"✅ Uploaded batch {i+1} ({uploaded}/{len(points)})")

        self.stdout.write(self.style.SUCCESS(f"🎉 Successfully synced {uploaded} questions to Qdrant!"))

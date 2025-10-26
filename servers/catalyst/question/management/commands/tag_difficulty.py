# from django.core.management.base import BaseCommand
# from question.models import Question
# from transformers import AutoTokenizer, AutoModelForSequenceClassification
# import torch
# from torch.nn.functional import softmax
# from tqdm import tqdm
# import os
# from dotenv import load_dotenv

# load_dotenv()

# class Command(BaseCommand):
#     help = "Update question difficulty using a PyTorch model"

#     def handle(self, *args, **kwargs):
#         print("🔄 Loading PyTorch model...")

#         try:
#             model_path = "/Users/abhinavrana/Catalyst/servers/catalyst/saved_difficulty_model/questionclassification_model"
#             tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")
#             model = AutoModelForSequenceClassification.from_pretrained(model_path)
#             model.eval()
#             device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#             model.to(device)
#         except Exception as e:
#             print(f"🚨 Failed to load PyTorch model: {e}")
#             return

#         print("📥 Fetching questions from database...")
#         questions = Question.objects.all()
#         inputs = []
#         question_ids = []

#         print("🧠 Formatting question-answer pairs...")
#         for q in tqdm(questions, desc="Preparing Inputs"):
#             try:
#                 correct_answer = q.options[q.correct_index]
#                 combined_text = f"{q.text}, {correct_answer}"
#                 inputs.append(combined_text)
#                 question_ids.append(q.id)
#             except (IndexError, TypeError):
#                 continue

#         print(f"🔍 Tokenizing {len(inputs)} entries...")
#         encoded = tokenizer(inputs, padding=True, truncation=True, max_length=256, return_tensors="pt")

#         input_ids = encoded["input_ids"].to(device)
#         attention_mask = encoded["attention_mask"].to(device)

#         print("📊 Running predictions...")
#         try:
#             with torch.no_grad():
#                 outputs = model(input_ids=input_ids, attention_mask=attention_mask)
#                 logits = outputs.logits
#                 probs = softmax(logits, dim=1)
#                 preds = torch.argmax(probs, dim=1).cpu().tolist()
#         except Exception as e:
#             print(f"❌ Error during inference: {e}")
#             return

#         difficulty_map = {0: "Easy", 1: "Medium", 2: "Hard"}

#         print("📝 Updating difficulty labels in DB...")
#         for qid, label in tqdm(zip(question_ids, preds), total=len(preds), desc="Updating Questions"):
#             Question.objects.filter(id=qid).update(difficulty=difficulty_map[label])

#         print("✅ Difficulty tagging completed successfully!")

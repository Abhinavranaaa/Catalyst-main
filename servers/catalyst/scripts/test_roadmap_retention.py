"""
Standalone test: builds a 41-question mock bank, calls the configured roadmap LLM
exactly the way roadmap.service.generate.generate_roadmap_blocks does, and reports
how many input IDs survive in the output.

Reads provider/model/keys from the same .env as the rest of the app. Run from the
catalyst project root:

    python scripts/test_roadmap_retention.py

No Django setup is required — this script imports only the prompt template,
constants, and the parser helper.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_cerebras import ChatCerebras

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env", override=True)

from catalyst.constants import (  # noqa: E402
    PROMPT_TEMPLATE_V4,
    LLM_TEMP2,
    MAX_TOKENS_ROADMAP,
)

import ast
import re

_THINK = re.compile(r"<think>.*?</think>", flags=re.IGNORECASE | re.DOTALL)


def remove_think_blocks(text: str) -> str:
    return _THINK.sub("", text or "").strip()


def parse_llm_response_to_json(response):
    if isinstance(response, dict):
        return response
    cleaned = (response or "").strip()
    cleaned = re.sub(r"^.*?\{", "{", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"```(?:json)?", "", cleaned).strip()
    first = cleaned.find("{")
    if first > 0:
        cleaned = cleaned[first:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            result = ast.literal_eval(cleaned)
            return result if isinstance(result, dict) else None
        except Exception:
            return None


# ----------------------------------------------------------------------------
# Build a 41-question mock bank mirroring the shape of the original log:
# - All on Operating Systems, threads/deadlocks.
# - Mix of populated, null, and edge-case metadata so we can verify nothing
#   except missing text/options/correct_index causes a drop.
# ----------------------------------------------------------------------------

OS_QUESTIONS = [
    ("A process can be ___________",
     ["single threaded", "multithreaded", "both single threaded and multithreaded", "none of the mentioned"], 2,
     "Threads", "hard"),
    ("Termination of the process terminates ___________",
     ["first thread of the process", "first two threads of the process",
      "all threads within the process", "no thread within the process"], 2,
     "Threads", None),
    ("Thread synchronization is required because ___________",
     ["all threads of a process share the same address space",
      "all threads of a process share the same global variables",
      "all threads of a process can share the same files",
      "all of the mentioned"], 3,
     "Thread Synchronization", None),
    ("A problem encountered in multitasking when a process is perpetually denied necessary resources is called ____________",
     ["deadlock", "starvation", "inversion", "aging"], 1,
     "Deadlock", "easy"),
    ("A set of processes is deadlock if __________",
     ["each process is blocked and will remain so forever",
      "each process is terminated",
      "all processes are trying to kill each other",
      "none of the mentioned"], 0,
     "Deadlock", None),
    ("The circular wait condition can be prevented by ____________",
     ["defining a linear ordering of resource types", "using thread", "using pipes", "all of the mentioned"], 0,
     "Deadlock Prevention", None),
    ("A deadlock avoidance algorithm dynamically examines the __________ to ensure that a circular wait condition can never exist.",
     ["resource allocation state", "system storage state", "operating system", "resources"], 0,
     "Deadlock Avoidance", None),
    ("The jacketing technique is used to ___________",
     ["convert a blocking system call into non blocking system call", "create a new thread",
      "communicate between threads", "terminate a thread"], 0,
     "Advanced Thread Management", "hard"),
    ("When the event for which a thread is blocked occurs?",
     ["thread moves to the ready queue", "thread remains blocked",
      "thread completes", "a new thread is provided"], 0,
     "Thread Management", "hard"),
    ("A system is in the safe state if ____________",
     ["the system can allocate resources to each process in some order and still avoid a deadlock",
      "there exist a safe sequence", "all of the mentioned", "none of the mentioned"], 2,
     "Deadlock Evaluation", "hard"),
    ("Those processes should be aborted on occurrence of a deadlock, the termination of which?",
     ["is more time consuming", "incurs minimum cost", "safety is not hampered", "all of the mentioned"], 1,
     "Deadlock Recovery", "hard"),
    ("A thread is also called ____________",
     ["light weight process", "heavy weight process", "process", "kernel"], 0,
     "Threads", "easy"),
    ("A thread shares its resources with ____________",
     ["other threads of the same process", "other threads of a different process",
      "parent process", "child process"], 0,
     "Threads", None),
    ("In Unix, the fork system call ____________",
     ["creates a new process", "creates a new thread",
      "blocks the calling process", "terminates the parent"], 0,
     "Processes", "medium"),
    ("Mutex locks are used for ____________",
     ["mutual exclusion", "memory protection", "scheduling", "deadlock recovery"], 0,
     "Thread Synchronization", "easy"),
    ("Semaphore is a ____________",
     ["integer variable", "process", "thread", "memory area"], 0,
     "Synchronization", "medium"),
    ("Which one is not a deadlock prevention method?",
     ["hold and wait", "no preemption", "circular wait", "wait/die scheme"], 3,
     "Deadlock Prevention", "medium"),
    ("Banker's algorithm is used for ____________",
     ["deadlock avoidance", "deadlock detection", "deadlock recovery", "synchronization"], 0,
     "Deadlock Avoidance", "medium"),
    ("Necessary conditions for deadlock include ____________",
     ["mutual exclusion", "hold and wait", "no preemption", "all of the mentioned"], 3,
     "Deadlock", "easy"),
    ("Resource allocation graph with a cycle and one instance per resource implies ____________",
     ["possible deadlock", "definite deadlock", "no deadlock", "starvation"], 1,
     "Deadlock Detection", "medium"),
    ("In thread cancellation, deferred cancellation ____________",
     ["allows target thread to check periodically",
      "terminates immediately", "ignores the request", "kills the parent"], 0,
     "Thread Management", "medium"),
    ("Kernel-level threads are scheduled by ____________",
     ["the kernel", "the user", "the compiler", "the loader"], 0,
     "Threads", "easy"),
    ("User-level threads are managed by ____________",
     ["a thread library", "the kernel directly", "the CPU", "the disk"], 0,
     "Threads", None),
    ("Which model maps many user threads to many kernel threads?",
     ["many-to-many", "one-to-one", "many-to-one", "none of the mentioned"], 0,
     "Thread Models", "medium"),
    ("Producer-consumer problem is an example of ____________",
     ["synchronization", "deadlock", "scheduling", "paging"], 0,
     "Synchronization", "medium"),
    ("Reader-writer locks favor ____________",
     ["readers when no writer is active", "always writers", "always readers", "neither"], 0,
     "Synchronization", "medium"),
    ("A monitor differs from a semaphore in that it ____________",
     ["encapsulates shared data with synchronization", "is faster",
      "needs no compiler support", "cannot block"], 0,
     "Synchronization", "hard"),
    ("Spinlocks are best when ____________",
     ["critical sections are short", "context switches are cheap",
      "uniprocessor only", "I/O bound"], 0,
     "Synchronization", "hard"),
    ("Priority inversion happens when ____________",
     ["a high-priority task waits on a low-priority task",
      "two tasks have the same priority",
      "a thread has no priority", "scheduling fails"], 0,
     "Thread Synchronization", "hard"),
    ("Recovery from deadlock by process termination chooses victims based on ____________",
     ["minimum cost", "maximum cost", "random selection", "alphabetical order"], 0,
     "Deadlock Recovery", "medium"),
    ("Wait-for graphs are used in ____________",
     ["deadlock detection", "deadlock prevention", "memory management", "scheduling"], 0,
     "Deadlock Detection", "medium"),
    ("Starvation can be prevented using ____________",
     ["aging", "priority inversion", "spinlocks", "context switching"], 0,
     "Starvation", "easy"),
    ("Two-phase locking is used in ____________",
     ["concurrency control", "memory allocation", "thread scheduling", "deadlock avoidance"], 0,
     "Synchronization", "hard"),
    ("A safe sequence in Banker's algorithm guarantees ____________",
     ["no deadlock for that ordering", "fastest completion",
      "fair scheduling", "minimum context switches"], 0,
     "Deadlock Avoidance", "medium"),
    ("Thread pool primarily improves ____________",
     ["response time and resource use", "code readability",
      "memory layout", "compile time"], 0,
     "Advanced Thread Management", "medium"),
    ("Which is NOT a valid thread state?",
     ["new", "ready", "running", "compiling"], 3,
     "Thread Management", "easy"),
    ("Context switching among threads of the same process is cheaper because ____________",
     ["they share address space", "they share PIDs",
      "they share registers", "they share schedulers"], 0,
     "Threads", "medium"),
    ("The dining philosophers problem illustrates ____________",
     ["deadlock and synchronization", "memory leaks",
      "thrashing", "compilation"], 0,
     "Synchronization", "medium"),
    ("Avoidance differs from prevention in that avoidance ____________",
     ["uses runtime state", "uses compile time",
      "is faster", "always terminates"], 0,
     "Deadlock", "hard"),
    ("Detect-and-recover schemes are chosen when ____________",
     ["deadlocks are rare", "deadlocks are common",
      "no recovery is needed", "all of the mentioned"], 0,
     "Deadlock", "hard"),
    ("Coffman conditions number ____________",
     ["four", "three", "five", "two"], 0,
     "Deadlock", "easy"),
]

# Off-topic / off-subject plants — should be flagged as C1 (off-subject) or C2 (off-topic).
OFFTOPIC_PLANTS = [
    ("The derivative of sin(x) with respect to x is ____________",
     ["cos(x)", "-cos(x)", "tan(x)", "sec(x)"], 0,
     "Differential Calculus", "easy"),
    ("Newton's second law states F = ____________",
     ["ma", "mv", "m/a", "v/t"], 0,
     "Classical Mechanics", "easy"),
    ("In TCP, the three-way handshake consists of ____________",
     ["SYN, SYN-ACK, ACK", "GET, POST, PUT",
      "open, close, send", "none of the mentioned"], 0,
     "Computer Networks", "medium"),
]

assert len(OS_QUESTIONS) == 41, f"expected 41 OS, got {len(OS_QUESTIONS)}"
assert len(OFFTOPIC_PLANTS) == 3, f"expected 3 plants, got {len(OFFTOPIC_PLANTS)}"


def build_question_bank() -> tuple[list[dict], set[str]]:
    """Returns (bank, set of plant ids that SHOULD be flagged as off-topic)."""
    bank = []
    plant_ids: set[str] = set()
    for i, (text, options, correct_index, topic, difficulty) in enumerate(OS_QUESTIONS):
        bank.append({
            "id": str(uuid.uuid4()),
            "text": text,
            "difficulty": difficulty or "medium",
            "topic": topic,
            "options": options,
            "similarity_score": round(0.85 - (i * 0.005), 3),
            "correct_index": correct_index,
        })
    for text, options, correct_index, topic, difficulty in OFFTOPIC_PLANTS:
        pid = str(uuid.uuid4())
        plant_ids.add(pid)
        bank.append({
            "id": pid,
            "text": text,
            "difficulty": difficulty or "medium",
            "topic": topic,
            "options": options,
            "similarity_score": 0.62,  # above Qdrant floor but lexically borderline
            "correct_index": correct_index,
        })
    return bank, plant_ids


def build_llm():
    provider = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    model = os.getenv("LLM_MODEL_ROADMAP") or "gpt-4o-mini"
    print(f"[setup] provider={provider} model={model} max_tokens={MAX_TOKENS_ROADMAP}")
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY missing")
        return ChatOpenAI(model=model, api_key=key, temperature=LLM_TEMP2, max_tokens=MAX_TOKENS_ROADMAP)
    if provider == "grok":
        key = os.getenv("GROK_API_KEY")
        if not key:
            raise RuntimeError("GROK_API_KEY missing")
        return ChatOpenAI(model=model, api_key=key, base_url="https://api.groq.com/openai/v1",
                          temperature=LLM_TEMP2, max_tokens=MAX_TOKENS_ROADMAP)
    key = os.getenv("CEREBRAS_API_KEY")
    if not key:
        raise RuntimeError("CEREBRAS_API_KEY missing")
    return ChatCerebras(model_name=model, api_key=key, temperature=LLM_TEMP2, max_tokens=MAX_TOKENS_ROADMAP)


def main():
    bank, plant_ids = build_question_bank()
    n = len(bank)
    input_ids = {q["id"] for q in bank}

    summary = [
        {
            "id": q["id"],
            "text": q["text"],
            "difficulty": q["difficulty"],
            "topic": q["topic"],
            "options": q["options"],
            "similarity_score": q["similarity_score"],
            "correct_index": q["correct_index"],
        }
        for q in bank
    ]

    prompt = PromptTemplate.from_template(PROMPT_TEMPLATE_V4).format(
        user_profile="Mock learner: undergraduate CS student, weak on synchronization, "
                     "moderate on deadlock theory, no prior thread-pool exposure.",
        subject="Operating Systems",
        topic="Threads and Deadlocks",
        additional_comments="Focus on classical concurrency primitives.",
        questions_data=json.dumps(summary, indent=2),
    )

    llm = build_llm()

    print(f"[call] sending {n} questions to LLM...")
    start = time.time()
    response = llm.invoke([HumanMessage(content=prompt)])
    latency = time.time() - start
    usage = response.response_metadata.get("token_usage", {}) or {}
    print(f"[call] latency={latency:.2f}s prompt_tokens={usage.get('prompt_tokens')} "
          f"completion_tokens={usage.get('completion_tokens')}")

    text = remove_think_blocks(response.content)
    roadmap = parse_llm_response_to_json(text)
    if not roadmap:
        print("[FAIL] response did not parse as JSON")
        print("---- raw response (first 2k chars) ----")
        print(text[:2000])
        sys.exit(2)

    retained = set()
    for block in roadmap.get("blocks", []) or []:
        for q in block.get("questions", []) or []:
            qid = q.get("question_id")
            if qid:
                retained.add(str(qid))

    dropped_entries = roadmap.get("dropped_questions", []) or []
    explained_drops: dict[str, dict] = {}
    for entry in dropped_entries:
        qid = entry.get("question_id")
        code = (entry.get("criterion_code") or "").upper().strip()
        reason = (entry.get("reason") or "").strip()
        if qid and code in {"C1", "C2", "C3", "C4", "C5"} and reason:
            explained_drops[str(qid)] = {"code": code, "reason": reason}

    valid = retained & input_ids
    unknown = retained - input_ids
    silent_drops = input_ids - valid - set(explained_drops.keys())
    on_topic_inputs = input_ids - plant_ids
    on_topic_retained = valid & on_topic_inputs

    rate = len(valid) / n
    on_topic_rate = len(on_topic_retained) / len(on_topic_inputs) if on_topic_inputs else 1.0
    blocks = roadmap.get("blocks", []) or []

    plants_caught = plant_ids & set(explained_drops.keys())
    plants_kept = plant_ids & valid

    print()
    print("================ RESULT ================")
    print(f"input bank size       : {n}  ({len(OS_QUESTIONS)} on-topic + {len(plant_ids)} off-topic plants)")
    print(f"retained (valid)      : {len(valid)} / {n} = {rate:.0%}")
    print(f"on-topic retention    : {len(on_topic_retained)} / {len(on_topic_inputs)} = {on_topic_rate:.0%}")
    print(f"explained drops       : {len(explained_drops)}")
    print(f"silent drops          : {len(silent_drops)}  (MUST be 0)")
    print(f"unknown ids (LLM hall): {len(unknown)}")
    print(f"blocks                : {len(blocks)} (sizes={[len(b.get('questions') or []) for b in blocks]})")
    print()
    print(f"PLANT DETECTION (off-topic): caught {len(plants_caught)}/{len(plant_ids)}; kept {len(plants_kept)}")
    for pid in plants_caught:
        e = explained_drops[pid]
        print(f"  - {pid[:8]}... [{e['code']}] {e['reason'][:120]}")
    if plants_kept:
        for pid in plants_kept:
            print(f"  - KEPT (should have dropped): {pid[:8]}...")
    print()
    if explained_drops:
        on_topic_explained = [(pid, e) for pid, e in explained_drops.items() if pid in on_topic_inputs]
        if on_topic_explained:
            print("ON-TOPIC DROPS (review reasoning quality):")
            for pid, e in on_topic_explained[:10]:
                print(f"  - {pid[:8]}... [{e['code']}] {e['reason'][:120]}")
    print("========================================")
    print()

    # Gates: silent drops must be 0, on-topic retention should clear soft target (85%),
    # and at least 2/3 plants should be caught.
    hard_floor = -(-n * 7 // 10)
    soft_target = -(-len(on_topic_inputs) * 17 // 20)
    silent_ok = len(silent_drops) == 0
    retention_ok = len(valid) >= hard_floor
    on_topic_ok = len(on_topic_retained) >= soft_target
    plants_ok = len(plants_caught) >= 2

    print(f"silent_drops == 0          : {'PASS' if silent_ok else 'FAIL'}")
    print(f"retention >= 70% hard floor: {'PASS' if retention_ok else 'FAIL'} ({len(valid)} vs {hard_floor})")
    print(f"on-topic >= 85% soft target: {'PASS' if on_topic_ok else 'FAIL'} ({len(on_topic_retained)} vs {soft_target})")
    print(f"plants caught >= 2/3       : {'PASS' if plants_ok else 'FAIL'} ({len(plants_caught)}/3)")

    sys.exit(0 if (silent_ok and retention_ok and on_topic_ok and plants_ok) else 1)


if __name__ == "__main__":
    main()

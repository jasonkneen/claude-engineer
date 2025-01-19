#!/usr/bin/env python3
import sys
import os
import re
import json
import random
import sqlite3
from collections import deque

###############################################################################
# 1) Common Interface: ChunkStore
###############################################################################


class ChunkStore:
    """
    A minimal interface for storing and retrieving 'chunks'.
    Each chunk is identified by a unique label (the 3-word code).
    The chunk data might include: summary, messages, references, etc.
    """

    def save_chunk(self, label, data: dict):
        """
        Save (insert or replace) the chunk data under 'label'.
        """
        raise NotImplementedError

    def load_chunk(self, label):
        """
        Return the chunk data (a dict) for 'label', or None if not found.
        """
        raise NotImplementedError

    def list_labels(self):
        """
        Return a list of all chunk labels in the store.
        """
        raise NotImplementedError

    def load_all_chunks(self):
        """
        Return a list of all chunk data dicts in the store.
        """
        raise NotImplementedError


###############################################################################
# 2) SQLite-based DocStore: SQLiteDocStore
###############################################################################


class SQLiteDocStore(ChunkStore):
    """
    Stores chunk data in a local SQLite database (clumps table).
    Each row: label (PRIMARY KEY), chunk_data (JSON).
    """

    def __init__(self, db_path="clumps.db"):
        """
        :param db_path: path to the SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """
        Create the table if it doesn't exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clumps (
                    label TEXT PRIMARY KEY,
                    chunk_data TEXT
                )
            """
            )
            conn.commit()

    def save_chunk(self, label, data):
        serialized = json.dumps(data, ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO clumps(label, chunk_data)
                VALUES(?, ?)
            """,
                (label, serialized),
            )
            conn.commit()

    def load_chunk(self, label):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT chunk_data FROM clumps WHERE label = ?", (label,)
            )
            row = cur.fetchone()
        if row:
            return json.loads(row[0])
        return None

    def list_labels(self):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT label FROM clumps")
            rows = cur.fetchall()
        return [r[0] for r in rows]

    def load_all_chunks(self):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT chunk_data FROM clumps")
            rows = cur.fetchall()
        return [json.loads(r[0]) for r in rows]


###############################################################################
# 3) JSON-based DocStore: JsonFileDocStore
###############################################################################


class JsonFileDocStore(ChunkStore):
    """
    Stores each chunk in a separate JSON file named {label}.json in a directory.
    """

    def __init__(self, storage_dir="clump_store"):
        """
        :param storage_dir: directory for JSON chunk files
        """
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def save_chunk(self, label, data):
        filename = os.path.join(self.storage_dir, f"{label}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_chunk(self, label):
        filename = os.path.join(self.storage_dir, f"{label}.json")
        if not os.path.exists(filename):
            return None
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_labels(self):
        labels = []
        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".json"):
                labels.append(os.path.splitext(fname)[0])
        return labels

    def load_all_chunks(self):
        chunks = []
        for lbl in self.list_labels():
            data = self.load_chunk(lbl)
            if data:
                chunks.append(data)
        return chunks


###############################################################################
# 4) SimpleContextManager
###############################################################################


class SimpleContextManager:
    """
    Manages conversation memory with older messages chunked and stored in a doc store.
      - Keeps at most `max_full_messages` in memory
      - If we exceed that, we summarize & compress older ones into a chunk
      - We can recall relevant older chunks by naive text matching in summary/messages
      - We BFS into references if a chunk references other chunk labels
    """

    # Regex to detect references to 3-word codes (e.g. "alpha-beta-gamma")
    THREE_WORD_CODE_PATTERN = re.compile(r"\b[a-zA-Z]+\-[a-zA-Z]+\-[a-zA-Z]+\b")

    def __init__(self, doc_store: ChunkStore, max_full_messages=5):
        """
        :param doc_store: either SQLiteDocStore or JsonFileDocStore
        :param max_full_messages: how many recent messages to keep uncompressed
        """
        self.doc_store = doc_store
        self.max_full_messages = max_full_messages
        self.messages = []  # the "live" messages
        self.used_labels = set()
        self.goal_summary = None

    def set_goal_summary(self, text):
        """
        Sets an overarching 'goal' that we can include as a system message.
        """
        self.goal_summary = text

    def add_message(self, role, content):
        """
        Add a new message (role='user'/'assistant', etc.).
        Compress older if we exceed max_full_messages.
        """
        self.messages.append({"role": role, "content": content})
        self._maybe_compress_old_messages()

    def _maybe_compress_old_messages(self):
        # If messages exceed the limit, chunk/summarize older ones
        if len(self.messages) > self.max_full_messages:
            older = self.messages[: -self.max_full_messages]
            latest = self.messages[-self.max_full_messages :]

            summary_text = self._summarize_messages(older)
            references = self._extract_3word_codes(older, summary_text)

            label = self._generate_3word_label(summary_text[:50])
            chunk_data = {
                "label": label,
                "summary": summary_text,
                "messages": older,
                "references": references,
            }
            self.doc_store.save_chunk(label, chunk_data)

            # keep only the latest
            self.messages = latest

    def _summarize_messages(self, messages):
        # Very naive summary approach
        all_content = " ".join(m["content"] for m in messages)
        return f"Summary: {all_content[:100]}..."

    def _extract_3word_codes(self, messages, summary_text):
        combined = summary_text
        for m in messages:
            combined += " " + m["content"]
        found = set(re.findall(self.THREE_WORD_CODE_PATTERN, combined))
        return list(found)

    def _generate_3word_label(self, seed_text):
        words = re.findall(r"\w+", seed_text.lower())
        unique_words = list(set(words))

        while len(unique_words) < 3:
            unique_words.append(f"word{random.randint(1000,9999)}")

        chosen = random.sample(unique_words, 3)
        label = "-".join(chosen)
        while label in self.used_labels:
            label += str(random.randint(0, 9999))
        self.used_labels.add(label)
        return label

    def recall_relevant_chunks(self, query):
        """
        Naive recall: if any of the query's words appear in chunk's summary or messages.
        Then BFS to expand references.
        """
        query_words = set(query.lower().split())
        all_chunks = self.doc_store.load_all_chunks()

        candidate_labels = []
        for chunk in all_chunks:
            text_for_search = chunk["summary"].lower()
            for msg in chunk["messages"]:
                text_for_search += " " + msg["content"].lower()
            matches = sum(1 for w in query_words if w in text_for_search)
            if matches > 0:
                candidate_labels.append(chunk["label"])

        results = {}
        queue = deque(candidate_labels)
        visited = set()

        while queue:
            lbl = queue.popleft()
            if lbl in visited:
                continue
            visited.add(lbl)

            chunk_data = self.doc_store.load_chunk(lbl)
            if chunk_data:
                results[lbl] = chunk_data
                for ref_lbl in chunk_data.get("references", []):
                    if ref_lbl not in visited:
                        queue.append(ref_lbl)

        return list(results.values())

    def get_context_for_model(self, user_query):
        """
        Build the "context" to feed an LLM:
          1) system (goal) if set
          2) live messages
          3) short recall for each relevant chunk
        """
        context = []
        if self.goal_summary:
            context.append({"role": "system", "content": f"Goal: {self.goal_summary}"})
        context.extend(self.messages)

        # find relevant older chunks
        relevant = self.recall_relevant_chunks(user_query)
        for chunk_data in relevant:
            lbl = chunk_data["label"]
            summ = chunk_data["summary"]
            context.append(
                {"role": "assistant", "content": f"(Recall from {lbl}): {summ}"}
            )

        return context


###############################################################################
# 5) Helper to create doc store with fallback
###############################################################################


def create_store_with_fallback(db_path="clumps.db", fallback_dir="clump_store"):
    """
    Tries to create a SQLiteDocStore at db_path.
    If that fails, falls back to JsonFileDocStore at fallback_dir.
    """
    # Attempt to init SQLite
    try:
        store = SQLiteDocStore(db_path)
        # Test write/read cycle
        label_test = "test-label"
        data_test = {
            "label": label_test,
            "summary": "test summary",
            "messages": [],
            "references": [],
        }
        store.save_chunk(label_test, data_test)
        loaded = store.load_chunk(label_test)
        if not loaded or loaded["label"] != label_test:
            raise RuntimeError("Could not verify test record in SQLite store.")
        # remove the test record
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM clumps WHERE label = ?", (label_test,))
            conn.commit()

        print(f"Using SQLiteDocStore at: {db_path}")
        return store

    except Exception as e:
        print("SQLiteDocStore failed:", e)
        print(f"Falling back to JsonFileDocStore in: {fallback_dir}")
        return JsonFileDocStore(storage_dir=fallback_dir)


###############################################################################
# 6) Self Test
###############################################################################


def run_self_test(db_path="test_clumps.db", fallback_dir="test_clump_store"):
    """
    A quick demonstration and test:
      - We create a store with fallback
      - We create a context manager
      - We add some messages, forcing some older ones to compress
      - We do a recall
      - Print out the final context
    """
    print("=== Running Self-Test ===")

    # 1) Create doc store (db or fallback)
    store = create_store_with_fallback(db_path=db_path, fallback_dir=fallback_dir)

    # 2) Create manager
    mgr = SimpleContextManager(store, max_full_messages=3)
    mgr.set_goal_summary("Help user troubleshoot Docker container crashes.")

    # 3) Add messages
    mgr.add_message("user", "I'm having issues with Docker.")
    mgr.add_message("assistant", "Can you share the Dockerfile?")
    mgr.add_message("user", "Sure, here's a snippet: FROM python:3.8 ...")
    mgr.add_message(
        "assistant",
        "Try adding an ENTRYPOINT. Also consider net-debug-xyz if you have connectivity issues.",
    )

    # (At this point, older messages might have been compressed, depending on the limit)

    mgr.add_message(
        "user", "Still no luck. I'm seeing 'Cannot connect to Docker daemon'."
    )

    # 4) Do a recall
    user_query = "What about net-debug-xyz you mentioned?"
    context = mgr.get_context_for_model(user_query)

    print("\n=== Final Context ===")
    for idx, c in enumerate(context, start=1):
        print(f"{idx}. {c['role'].upper()}: {c['content']}")

    # 5) Check if at least one recall chunk is in the context
    found_recall = any(
        "(Recall from " in msg["content"]
        for msg in context
        if msg["role"] == "assistant"
    )
    if found_recall:
        print("\nSelf-test succeeded: found older chunk recall in context.")
    else:
        print(
            "\nSelf-test warning: no older chunk was recalled. Possibly not enough messages or matching words."
        )


###############################################################################
# 7) Main entry point
###############################################################################

if __name__ == "__main__":
    # If user types "python thisscript.py selftest", run self-test
    if len(sys.argv) > 1 and sys.argv[1].lower() == "selftest":
        run_self_test()
    else:
        # Normal usage demonstration
        print("Usage: python thisscript.py selftest\n")
        print(
            "This script demonstrates a SimpleContextManager with fallback from SQLite to JSON."
        )
        print("Run with 'selftest' to see a quick example in action.")

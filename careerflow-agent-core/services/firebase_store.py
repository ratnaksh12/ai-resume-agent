# services/firebase_store.py

import os
from typing import Any, Dict, Optional
import datetime

import firebase_admin
from firebase_admin import credentials, firestore


# -------------------------
# Firebase initialization
# -------------------------

# We expect a service account JSON file path in env:
# FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-service-account.json
SERVICE_ACCOUNT_PATH = os.getenv(
    "FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-service-account.json"
)

if not firebase_admin._apps:
    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise RuntimeError(
            f"Firebase service account file not found at: {SERVICE_ACCOUNT_PATH}"
        )

    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# -------------------------
# Logging conversation messages
# -------------------------

def log_message(
    user_id: str,
    conversation_id: str,
    role: str,
    content: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a chat message to Firestore under:
    users/{user_id}/conversations/{conversation_id}/messages/{auto_id}
    """
    doc_ref = (
        db.collection("users")
        .document(user_id)
        .collection("conversations")
        .document(conversation_id)
        .collection("messages")
        .document()
    )

    payload: Dict[str, Any] = {
        "role": role,
        "content": content,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }

    if extra:
        payload["extra"] = extra

    doc_ref.set(payload)


# -------------------------
# Logging resume versions
# -------------------------

def log_resume_version(
    user_id: str,
    resume_id: int,
    version_id: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a resume version under:
    users/{user_id}/resumes/{resume_id}/versions/{version_id}
    """
    doc_ref = (
        db.collection("users")
        .document(user_id)
        .collection("resumes")
        .document(str(resume_id))
        .collection("versions")
        .document(str(version_id))
    )

    payload: Dict[str, Any] = {
        "resume_id": resume_id,
        "version_id": version_id,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }

    if metadata:
        payload["metadata"] = metadata

    doc_ref.set(payload, merge=True)

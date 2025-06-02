# backend/app/core/tasks.py
# Defines Celery tasks for background processing.

from celery import Celery
from kombu.utils.url import safe_url # For safely displaying URLs in logs

from app.config import settings # Import your application settings

# Initialize Celery
# The first argument to Celery is the name of the current module.
# The broker argument specifies the URL of the message broker (e.g., Redis).
# The backend argument specifies the URL of the result backend.
celery_app = Celery(
    "worker", # Can be any name, often the module name or a project-specific name
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        # Add other modules that contain tasks here if you have them
        # e.g., 'app.core.another_tasks_module'
    ]
)

# Optional Celery configuration (many options available)
# See Celery documentation for more details: https://docs.celeryq.dev/en/stable/userguide/configuration.html
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],  # Ignore other content
    result_serializer='json',
    timezone='UTC', # Or your application's timezone
    enable_utc=True,
    # Example: Set a default task execution time limit (e.g., 5 minutes)
    # task_time_limit=300, 
    # Example: Set a default task soft time limit (e.g., 4 minutes 50 seconds)
    # task_soft_time_limit=290,
    # Configure broker connection pool (if needed, defaults are usually fine)
    # broker_pool_limit=10, # Default is 10 for Redis
)

# Example: Print broker and backend URLs for verification (optional, good for debugging)
# Be careful with logging sensitive parts of URLs if they contain passwords directly
# and are not managed via environment variables properly.
if settings.CELERY_BROKER_URL:
    print(f"Celery Worker: Connecting to broker at {safe_url(settings.CELERY_BROKER_URL)}")
if settings.CELERY_RESULT_BACKEND:
    print(f"Celery Worker: Using result backend at {safe_url(settings.CELERY_RESULT_BACKEND)}")


# --- Define Your Celery Tasks Below ---

@celery_app.task(name="example_task") # Explicitly naming tasks is a good practice
def example_background_task(x: int, y: int) -> int:
    """
    An example background task that adds two numbers.
    """
    result = x + y
    print(f"Example task: Adding {x} + {y} = {result}")
    return result

@celery_app.task(name="process_long_nlp_job")
def process_long_nlp_job(text_to_process: str, user_id: int | None = None):
    """
    A placeholder for a potentially long-running NLP job.
    """
    print(f"Starting NLP job for user '{user_id}' with text: '{text_to_process[:50]}...'")
    # Simulate work
    import time
    time.sleep(10) # Simulate a 10-second task
    result_summary = f"Processed text starting with: {text_to_process[:20]}"
    print(f"Finished NLP job for user '{user_id}'. Result: {result_summary}")
    return {"user_id": user_id, "summary": result_summary, "status": "completed"}

@celery_app.task(name="send_escalation_notification")
def send_escalation_notification(session_id: int, message_snippet: str, user_email: str | None = None):
    """
    Task to send a notification when a chat is escalated.
    This would typically involve sending an email or calling a third-party API.
    """
    print(f"Escalation Triggered: Session ID {session_id}, Message: '{message_snippet}'")
    if user_email:
        print(f"Sending notification to user: {user_email} (simulation)")
        # In a real app, you'd use an email library here:
        # from app.utils.email_sender import send_email
        # send_email(to=user_email, subject="Chat Escalation", body=f"...")
    else:
        print("No user email provided for notification.")
    
    # Simulate notifying an internal team/system
    print("Notifying internal support team (simulation).")
    # E.g., call a helpdesk API, send a Slack message, etc.
    
    return {"status": "escalation_notified", "session_id": session_id}

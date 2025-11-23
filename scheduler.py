import datetime
import math
from storage import add_subject, add_topic, update_topic_status, update_topic_review_data, get_subjects
from config import REVISION_BUFFER_DAYS, MIN_STUDY_DAYS

def calculate_next_review(interval: int, ease_factor: float, rating: int) -> tuple[int, float]:
    """
    Calculates the next review interval and ease factor using the SuperMemo-2 (SM-2) algorithm.

    Args:
        interval (int): The previous interval in days.
        ease_factor (float): The previous ease factor.
        rating (int): The user's rating of the recall quality (0-5).
                      5 - perfect response
                      4 - correct response after a hesitation
                      3 - correct response recalled with serious difficulty
                      2 - incorrect response; where the correct one seemed easy to recall
                      1 - incorrect response; the correct one remembered
                      0 - complete blackout.

    Returns:
        tuple[int, float]: A tuple containing (next_interval, next_ease_factor).
    """
    if rating < 3:
        return 1, ease_factor  # Reset interval if recall failed

    if interval == 0:
        next_interval = 1
    elif interval == 1:
        next_interval = 6
    else:
        next_interval = math.ceil(interval * ease_factor)

    # Update Ease Factor
    # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    next_ease_factor = ease_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
    if next_ease_factor < 1.3:
        next_ease_factor = 1.3

    return next_interval, next_ease_factor

def create_subject_plan(subject_name: str, syllabus_data: dict, exam_date_str: str) -> None:
    """
    Creates a study plan for a subject and saves it to the database (MySQL).
    """
    topics = syllabus_data.get('topics', [])
    if not topics:
        print("No topics found in syllabus data.")
        return

    today = datetime.date.today()
    try:
        exam_date = datetime.datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
        return
    
    # Check if subject already exists? For now, we assume new subject or duplicate name allowed (ID handles uniqueness)
    subject_id = add_subject(subject_name, exam_date_str)
    if subject_id == -1:
        print("Failed to create subject in database.")
        return

    # 1. Calculate Learning Deadline
    target_finish_date = exam_date - datetime.timedelta(days=REVISION_BUFFER_DAYS)
    days_available = (target_finish_date - today).days
    
    if days_available < len(topics):
        print(f"⚠️ Warning: Compressed schedule active.")
        target_finish_date = exam_date - datetime.timedelta(days=1)
        days_available = (target_finish_date - today).days
        
    if days_available < MIN_STUDY_DAYS: days_available = MIN_STUDY_DAYS

    # 2. Distribute Topics
    daily_pace = max(1, len(topics) / days_available)
    
    for i, topic in enumerate(topics):
        day_offset = int(i / daily_pace)
        assigned_date = today + datetime.timedelta(days=day_offset)
        
        add_topic(
            subject_id=subject_id,
            name=topic['topic_name'],
            type="LEARNING",
            difficulty=topic['difficulty'],
            assigned_date=str(assigned_date)
        )

    # Phase B: Revision (Mock Tests) - We can add these as topics too
    last_learning_date = today + datetime.timedelta(days=int((len(topics)-1)/daily_pace))
    curr_rev = last_learning_date + datetime.timedelta(days=1)
    
    while curr_rev < exam_date:
        add_topic(
            subject_id=subject_id,
            name="🔥 Full Mock Test / Review",
            type="REVISION",
            difficulty="Hard",
            assigned_date=str(curr_rev)
        )
        curr_rev += datetime.timedelta(days=1)

def mark_done(topic_id: int, rating: int, current_interval: int = 0, current_ease_factor: float = 2.5) -> None:
    """
    Marks a topic as done and schedules the next review using SM-2.
    """
    # 1. Update current task status to 'done'
    update_topic_status(topic_id, 'done')
    
    # 2. Calculate next parameters
    next_interval, next_ease_factor = calculate_next_review(current_interval, current_ease_factor, rating)
    next_date = datetime.date.today() + datetime.timedelta(days=next_interval)
    
    # 3. Clone and Schedule: Create a BRAND NEW entry for the future review
    # We need to fetch the original topic details first (name, difficulty, subject_id)
    # Since we don't have them passed in, we should fetch them or rely on the caller.
    # Ideally, we fetch from DB to be safe.
    from storage import get_topic # Import here to avoid circular dependency if any, or move to top
    
    original_topic = get_topic(topic_id)
    if original_topic:
        add_topic(
            subject_id=original_topic['subject_id'],
            name=original_topic['name'],
            type="REVIEW", # It's always a review now
            difficulty=original_topic['difficulty'],
            assigned_date=str(next_date),
            repetition_count=original_topic['repetition_count'] + 1,
            ease_factor=next_ease_factor,
            interval=next_interval
        )
    else:
        print(f"Error: Could not find topic {topic_id} to clone.")

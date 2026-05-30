import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
COURSES_CONFIG = Path("courses/config.yaml")
COURSES_DIR = Path("courses")

def load_courses():
    if not COURSES_CONFIG.exists():
        logger.warning(f"Конфиг не найден: {COURSES_CONFIG}")
        return []
    with open(COURSES_CONFIG, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("courses", [])

def get_day_content(course, day_num):
    days = course.get("days", [])
    if not days:
        return "Контент скоро появится!", "Загружаем..."
    idx = min(day_num - 1, len(days) - 1)
    day = days[idx]
    title = day.get("title", f"День {idx + 1}")
    file_path = COURSES_DIR / day.get("file", "")
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8").strip()
    else:
        content = day.get("content", "Контент этого дня ещё готовится...")
    if len(content) > 3800:
        content = content[:3800] + "..."
    return content, title

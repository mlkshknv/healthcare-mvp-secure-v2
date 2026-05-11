import logging
import sys
import re

logger = logging.getLogger("healthcare_mvp")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)

file_handler = logging.FileHandler("app.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# вывод в консоль и фильтр для маскировки паролей
class PIIFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # Маскировка email
        msg = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '[EMAIL]', msg)
        # Маскировка телефона (10-15 цифр, возможно с +)
        msg = re.sub(r'\b\+\d{1,3}\s?\d{10,15}\b', '[PHONE]', msg)
        msg = re.sub(r'\b\d{10,15}\b', '[PHONE]', msg)
        # Маскировка паролей (например, password=123, "password": "123")
        msg = re.sub(r'(?i)(password|passwd|secret)\s*[=:]\s*\S+', r'\1=[FILTERED]', msg)
        msg = re.sub(r'(?i)"password"\s*:\s*"[^"]*"', '"password":"[FILTERED]"', msg)
        # Маскировка JWT токенов (eyJ...)
        msg = re.sub(r'eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[JWT]', msg)
        record.msg = msg
        return True

logger.addFilter(PIIFilter())
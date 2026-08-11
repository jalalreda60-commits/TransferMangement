"""
utils/constants.py
-------------------
Shared vocabularies (status options per module), enums, and the colour
palette used throughout the UI. Kept as plain string constants (not
SQLAlchemy Enum columns) so new statuses can be introduced without a
schema migration, and so combo boxes can be populated directly.
"""

# ---- Transfer-level ----
TRANSFER_TYPES = ["1-Step", "2-Step"]
ACTIVITIES = ["Stamping", "Molding"]

TRANSFER_STATUS_NOT_STARTED = "Not Started"
TRANSFER_STATUS_ONGOING = "Ongoing"
TRANSFER_STATUS_DELAYED = "Delayed"
TRANSFER_STATUS_COMPLETED = "Completed"
TRANSFER_STATUSES = [
    TRANSFER_STATUS_NOT_STARTED, TRANSFER_STATUS_ONGOING,
    TRANSFER_STATUS_DELAYED, TRANSFER_STATUS_COMPLETED,
]

# ---- Generic 3/4-state status vocabularies reused across modules ----
STATUS_NA_ONGOING_DONE = ["NA", "Ongoing", "Done"]
STATUS_NOT_ONGOING_APPROVED = ["Not Started", "Ongoing", "Approved"]
STATUS_NOT_ONGOING_APPROVED_REJECTED = ["Not Started", "Ongoing", "Approved", "Rejected"]
STATUS_NA_ONGOING_RECEIVED = ["NA", "Ongoing", "Received"]
STATUS_NA_ONGOING_ACCEPTED_REJECTED = ["NA", "Ongoing", "Accepted", "Rejected"]
STATUS_NOT_SENT_SENT_ONGOING_APPROVED = ["Not Sent", "Sent", "Ongoing", "Approved"]
STATUS_NOT_ONGOING_DONE = ["Not Started", "Ongoing", "Done"]
STATUS_CALL_GENERIC = ["Not Started", "Scheduled", "Done"]

YES_NO = ["Yes", "No"]

URGENCY_LEVELS = ["Low", "Medium", "High", "Critical"]

# ---- Release module ----
RELEASE_STATUS_PENDING = "Pending"
RELEASE_STATUS_READY = "Ready for Release"
RELEASE_STATUS_RELEASED = "Released"
RELEASE_STATUS_ON_HOLD = "On Hold"
RELEASE_STATUSES = [
    RELEASE_STATUS_PENDING, RELEASE_STATUS_READY,
    RELEASE_STATUS_RELEASED, RELEASE_STATUS_ON_HOLD,
]

# ---- Colour palette (professional blue industrial theme) ----
COLORS = {
    "primary": "#0F5FA8",
    "primary_dark": "#0B4578",
    "accent": "#F2A900",
    "success": "#1E8E3E",
    "warning": "#F2A900",
    "danger": "#D13438",
    "grey": "#8A8886",
    "info": "#2B88D8",
    "bg_light": "#F3F6FA",
    "bg_dark": "#1B1E24",
    "surface_light": "#FFFFFF",
    "surface_dark": "#262A32",
    "text_light": "#1B1B1F",
    "text_dark": "#E6E6E6",
    "border_light": "#DCE2EA",
    "border_dark": "#3A3F4A",
}

# Colour indicators as specified: Green=Completed, Yellow=Ongoing,
# Red=Delayed, Grey=Not Started
STATUS_COLOR_MAP = {
    "Completed": COLORS["success"],
    "Done": COLORS["success"],
    "Approved": COLORS["success"],
    "Received": COLORS["success"],
    "Accepted": COLORS["success"],
    "Released": COLORS["success"],
    "Ready for Release": COLORS["success"],

    "Ongoing": COLORS["warning"],
    "Sent": COLORS["warning"],
    "Scheduled": COLORS["warning"],

    "Delayed": COLORS["danger"],
    "Rejected": COLORS["danger"],
    "On Hold": COLORS["danger"],

    "Not Started": COLORS["grey"],
    "Not Sent": COLORS["grey"],
    "NA": COLORS["grey"],
    "Pending": COLORS["grey"],
}


def color_for_status(status: str) -> str:
    return STATUS_COLOR_MAP.get(status, COLORS["grey"])

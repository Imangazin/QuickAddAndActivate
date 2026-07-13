from datetime import datetime, timezone
from typing import Optional, Union

from brightspace_api import BRIGHTSPACE_LP_API_VERSION, request


class ActivateCourseError(Exception):
    """Raised when a course offering cannot be activated or deactivated."""


def parse_brightspace_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def format_brightspace_datetime(value: datetime) -> str:
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def get_course(org_unit_id: Union[int, str], access_token: str) -> dict:
    course = request(
        "GET",
        f"/d2l/api/lp/{BRIGHTSPACE_LP_API_VERSION}/courses/{org_unit_id}",
        access_token,
    )
    if not isinstance(course, dict) or not course.get("Name"):
        raise ActivateCourseError("Unable to retrieve course offering.")
    return course


def build_course_update_payload(course: dict, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    activate = bool(course.get("IsActive"))
    start_date = parse_brightspace_datetime(course.get("StartDate")) or now

    if activate and start_date > now:
        activate = True
        start_date = now
    else:
        activate = not activate

    if activate:
        start_date = now

    description = course.get("Description") or {}
    return {
        "Name": course.get("Name"),
        "Code": course.get("Code"),
        "StartDate": format_brightspace_datetime(start_date),
        "EndDate": course.get("EndDate"),
        "IsActive": activate,
        "Description": {
            "Content": description.get("Html") or description.get("Content") or "",
            "Type": "Html",
        },
        "CanSelfRegister": course.get("CanSelfRegister"),
    }


def update_course(
    org_unit_id: Union[int, str],
    payload: dict,
    access_token: str,
) -> dict:
    return request(
        "PUT",
        f"/d2l/api/lp/{BRIGHTSPACE_LP_API_VERSION}/courses/{org_unit_id}",
        access_token,
        json=payload,
    )


def activate_or_deactivate_course(
    org_unit_id: Union[int, str],
    access_token: str,
) -> dict:
    course = get_course(org_unit_id, access_token)
    payload = build_course_update_payload(course)
    update_course(org_unit_id, payload, access_token)

    return {
        "org_unit_id": str(org_unit_id),
        "is_active": payload["IsActive"],
        "message": (
            "The site has been activated successfully."
            if payload["IsActive"]
            else "The site has been deactivated successfully."
        ),
    }

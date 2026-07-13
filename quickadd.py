from typing import Union

from brightspace_api import BRIGHTSPACE_LP_API_VERSION, request


class QuickAddError(Exception):
    """Raised when QuickAdd cannot complete an enrollment workflow."""


def trim_username(username: str) -> str:
    username = (username or "").strip()
    if "@" in username:
        return username.split("@", 1)[0]
    return username


def get_user_by_username(username: str, access_token: str) -> dict:
    user = request(
        "GET",
        f"/d2l/api/lp/{BRIGHTSPACE_LP_API_VERSION}/users/",
        access_token,
        params={"userName": username},
    )
    if not isinstance(user, dict) or not user.get("UserId"):
        raise QuickAddError("No such user.")
    return user


def enroll_user_in_course(
    org_unit_id: Union[int, str],
    user_id: Union[int, str],
    role_id: Union[int, str],
    access_token: str,
) -> dict:
    payload = {
        "OrgUnitId": int(org_unit_id),
        "UserId": int(user_id),
        "RoleId": int(role_id),
    }
    return request(
        "POST",
        f"/d2l/api/lp/{BRIGHTSPACE_LP_API_VERSION}/enrollments/",
        access_token,
        json=payload,
    )


def get_sections(org_unit_id: Union[int, str], access_token: str) -> list:
    sections = request(
        "GET",
        f"/d2l/api/lp/{BRIGHTSPACE_LP_API_VERSION}/{org_unit_id}/sections/",
        access_token,
    )
    if not isinstance(sections, list):
        raise QuickAddError("Unable to retrieve course sections.")
    return sections


def enroll_user_in_section(
    org_unit_id: Union[int, str],
    section_id: Union[int, str],
    user_id: Union[int, str],
    access_token: str,
) -> dict:
    return request(
        "POST",
        (
            f"/d2l/api/lp/{BRIGHTSPACE_LP_API_VERSION}/{org_unit_id}/"
            f"sections/{section_id}/enrollments/"
        ),
        access_token,
        json={"UserId": int(user_id)},
    )


def add_user_to_course_and_sections(
    org_unit_id: Union[int, str],
    username: str,
    role_id: Union[int, str],
    access_token: str,
) -> dict:
    normalized_username = trim_username(username)
    if not normalized_username:
        raise QuickAddError("Please enter a username.")
    if not role_id:
        raise QuickAddError("Please select a role.")

    user = get_user_by_username(normalized_username, access_token)
    user_id = user["UserId"]
    user_is_active = bool(user.get("Activation", {}).get("IsActive"))

    enroll_user_in_course(org_unit_id, user_id, role_id, access_token)

    sections = get_sections(org_unit_id, access_token)
    section_results = []
    for section in sections:
        section_id = section.get("SectionId")
        if section_id is None:
            continue
        section_results.append(
            enroll_user_in_section(org_unit_id, section_id, user_id, access_token)
        )

    return {
        "user_id": user_id,
        "username": normalized_username,
        "user_is_active": user_is_active,
        "section_count": len(section_results),
    }

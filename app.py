import os
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from flask.sessions import SecureCookieSessionInterface
from flask_caching import Cache
from pylti1p3.contrib.flask import FlaskCacheDataStorage, FlaskMessageLaunch
from pylti1p3.contrib.flask import FlaskOIDCLogin
from pylti1p3.contrib.flask.request import FlaskRequest
from pylti1p3.tool_config import ToolConfJsonFile
from werkzeug.middleware.proxy_fix import ProxyFix

from activate_course import ActivateCourseError, activate_or_deactivate_course
from auth2 import get_access_token
from quickadd import QuickAddError, add_user_to_course_and_sections

load_dotenv()

SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
APP_FOLDER = os.getenv("APP_FOLDER")
APP_URL_PREFIX = os.getenv("APP_URL_PREFIX") or (f"/{APP_FOLDER}" if APP_FOLDER else "")
CACHE_DIR = os.getenv("FLASK_CACHE_DIR") or f"/tmp/{APP_FOLDER}-flask-cache"
QUICKADD_DEPLOYMENT_ID = os.getenv("QUICKADD_DEPLOYMENT_ID")
ACTIVATE_COURSE_DEPLOYMENT_ID = os.getenv("ACTIVATE_COURSE_DEPLOYMENT_ID")
QUICKADD_ROLE_OPTIONS = os.getenv(
    "QUICKADD_ROLE_OPTIONS",
    "121:Teaching Assistant,109:Instructor",
)

os.makedirs(CACHE_DIR, exist_ok=True)


class PartitionedSessionInterface(SecureCookieSessionInterface):
    def save_session(self, app, session, response):
        super().save_session(app, session, response)

        session_cookie_name = app.config.get("SESSION_COOKIE_NAME")
        cookies = response.headers.getlist("Set-Cookie")
        if not session_cookie_name or not cookies:
            return

        response.headers.remove("Set-Cookie")
        for cookie in cookies:
            if (
                cookie.startswith(session_cookie_name + "=")
                and "partitioned" not in cookie.lower()
            ):
                cookie = cookie + "; Partitioned"
            response.headers.add("Set-Cookie", cookie)


app = Flask(__name__)
app.session_interface = PartitionedSessionInterface()
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = SECRET_KEY
app.config.from_mapping(
    DEBUG=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    CACHE_TYPE="FileSystemCache",
    CACHE_DEFAULT_TIMEOUT=600,
    CACHE_DIR=CACHE_DIR,
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_NAME=f"{APP_FOLDER}-lti13-sessionid",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="None",
)

cache = Cache(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
tool_conf = ToolConfJsonFile(os.path.join(BASE_DIR, "tool_config.json"))
WORKFLOW_CACHE_PREFIX = "quickadd-workflow:"
DEPLOYMENT_ID_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
CONTEXT_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/context"


def get_launch_data_storage():
    return FlaskCacheDataStorage(cache)


def parse_role_options() -> list:
    roles = []
    for role_option in QUICKADD_ROLE_OPTIONS.split(","):
        role_option = role_option.strip()
        if not role_option:
            continue
        role_id, _, label = role_option.partition(":")
        roles.append({
            "id": role_id.strip(),
            "label": label.strip() or role_id.strip(),
        })
    return roles


def workflow_cache_key(workflow_id: str) -> str:
    return WORKFLOW_CACHE_PREFIX + workflow_id


def save_workflow(workflow_id: str, workflow: dict) -> None:
    cache.set(workflow_cache_key(workflow_id), workflow, timeout=3600)


def allow_workflow_for_session(workflow_id: str) -> None:
    workflow_ids = session.get("workflow_ids", [])
    if workflow_id not in workflow_ids:
        workflow_ids.append(workflow_id)
    session["workflow_ids"] = workflow_ids


def get_workflow(workflow_id: str) -> dict:
    if not workflow_id:
        return None
    if workflow_id not in session.get("workflow_ids", []):
        return None
    return cache.get(workflow_cache_key(workflow_id))


def app_url(path: str) -> str:
    return APP_URL_PREFIX.rstrip("/") + path


def create_workflow(org_unit_id: str, access_token: str) -> dict:
    workflow_id = uuid.uuid4().hex
    workflow = {
        "workflow_id": workflow_id,
        "org_unit_id": org_unit_id,
        "access_token": access_token,
    }
    save_workflow(workflow_id, workflow)
    allow_workflow_for_session(workflow_id)
    return workflow


def launch_error(message: str, status_code: int = 400):
    return jsonify({"success": False, "message": message}), status_code


@app.route("/")
def index():
    return "QuickAdd and ActivateCourse LTI 1.3 tool is running."


@app.route("/login/", methods=["GET", "POST"])
def login():
    flask_request = FlaskRequest()
    target_link_uri = flask_request.get_param("target_link_uri")
    if not target_link_uri:
        return launch_error('Missing "target_link_uri" param')

    oidc_login = FlaskOIDCLogin(
        flask_request,
        tool_conf,
        launch_data_storage=get_launch_data_storage(),
    )
    return oidc_login.enable_check_cookies().redirect(target_link_uri)


@app.route("/launch/", methods=["POST"])
def launch():
    flask_request = FlaskRequest()

    try:
        message_launch = FlaskMessageLaunch(
            flask_request,
            tool_conf,
            launch_data_storage=get_launch_data_storage(),
        )
        launch_data = message_launch.get_launch_data()
        context_data = launch_data.get(CONTEXT_CLAIM, {})
        org_unit_id = context_data.get("id")
        deployment_id = launch_data.get(DEPLOYMENT_ID_CLAIM)

        if not org_unit_id:
            return launch_error("LTI launch did not include a course context.")
        if not deployment_id:
            return launch_error("LTI launch did not include a deployment id.")

        token_response = get_access_token()
        access_token = token_response["access_token"]

        if deployment_id == QUICKADD_DEPLOYMENT_ID:
            workflow = create_workflow(org_unit_id, access_token)
            return render_template(
                "quickadd.html",
                workflow_id=workflow["workflow_id"],
                org_unit_id=org_unit_id,
                add_user_url=app_url("/quickadd/add-user/"),
                role_options=parse_role_options(),
            )

        if deployment_id == ACTIVATE_COURSE_DEPLOYMENT_ID:
            result = activate_or_deactivate_course(org_unit_id, access_token)
            return jsonify({"success": True, **result})

        return launch_error("LTI deployment id is not mapped to a tool.")

    except ActivateCourseError as error:
        app.logger.exception("Activation workflow failed.")
        return launch_error(str(error))
    except Exception:
        app.logger.exception("LTI launch failed.")
        return launch_error("Error occurred.")


@app.route("/quickadd/add-user/", methods=["POST"])
def quickadd_add_user():
    workflow = get_workflow(request.form.get("workflow_id"))
    if not workflow:
        return launch_error("QuickAdd session expired or is invalid.")

    try:
        result = add_user_to_course_and_sections(
            workflow["org_unit_id"],
            request.form.get("username", ""),
            request.form.get("userrole", ""),
            workflow["access_token"],
        )
        if result["user_is_active"]:
            message = (
                "User {username} has been added to course offering {org_unit_id} "
                "and {section_count} section(s)."
            ).format(
                username=result["username"],
                org_unit_id=workflow["org_unit_id"],
                section_count=result["section_count"],
            )
        else:
            message = (
                "User {username} has been added, but the user account is inactive."
            ).format(username=result["username"])

        return jsonify({
            "success": True,
            "message": message,
            "user_id": result["user_id"],
            "section_count": result["section_count"],
        })
    except QuickAddError as error:
        return launch_error(str(error))
    except Exception:
        app.logger.exception("QuickAdd enrollment failed.")
        return launch_error("Error occurred.")


@app.route("/jwks/", methods=["GET"])
def jwks():
    return tool_conf.get_jwks()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5070")))

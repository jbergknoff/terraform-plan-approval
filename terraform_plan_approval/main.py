import base64
import os
import uuid

import flask
import flask_talisman
import redis

MAX_PLAN_SIZE_BYTES = 2 * 1024 * 1024
ONE_HOUR_SECONDS = 60 * 60

app = flask.Flask(__name__, template_folder="templates")
# Use Talisman to redirect to HTTPS
flask_talisman.Talisman(app, content_security_policy=None)

# Keep a small connection pool; don't want to exceed free tier usage.
redis_connection_pool = redis.BlockingConnectionPool.from_url(
    os.environ["REDIS_URL"], max_connections=1
)
redis_client = redis.client.Redis(connection_pool=redis_connection_pool)


class PlanStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    allowed_statuses = set([PENDING, APPROVED, REJECTED])


@app.route("/")
def hello():
    return flask.render_template("index.html")


# POST /plan stashes contents in Redis, returns a uuid.
@app.route("/plan", methods=["POST"])
def store_plan():
    plan_id = uuid.uuid4()
    try:
        plan_base64 = flask.request.json.get("plan_base64")
    except Exception as e:
        print("Request is not JSON", e)
        return (
            flask.jsonify(
                {"error": 'Expecting JSON in the format {"plan_base64": "..."}'}
            ),
            400,
        )

    if not plan_base64:
        print("Request missing `plan_base64` field")
        return flask.jsonify({"error": "`plan_base64` field expected"}), 400

    if len(plan_base64) > MAX_PLAN_SIZE_BYTES:
        print("`plan_base64` is too large")
        return (
            flask.jsonify(
                {
                    "error": f"`plan_base64` value must be less than {MAX_PLAN_SIZE_BYTES} bytes long (got {len(plan_base64)} bytes)"
                }
            ),
            400,
        )

    try:
        base64.b64decode(plan_base64)
    except Exception as e:
        print("`plan_base64` does not appear to be base64-encoded", e)
        return (
            flask.jsonify(
                {"error": "`plan_base64` value does not appear to be base64-encoded"}
            ),
            400,
        )

    redis_client.setex(f"{plan_id}-plan", ONE_HOUR_SECONDS, plan_base64)
    redis_client.setex(f"{plan_id}-status", ONE_HOUR_SECONDS, PlanStatus.PENDING)
    print(f"Accepted plan with id {plan_id}")
    return flask.jsonify({"id": plan_id}), 201


# GET /plan/<uuid> serves an HTML page with an approval form.
@app.route("/plan/<string:plan_id>", methods=["GET"])
def display_plan(plan_id: str):
    plan_base64 = redis_client.get(f"{plan_id}-plan")
    if not plan_base64:
        print("Cannot display form for unknown plan")
        return flask.render_template("not_found.html"), 404

    try:
        plan = base64.b64decode(plan_base64).decode("utf8")
    except Exception as e:
        print("Stored plan could not be decoded as base64", e)
        return flask.render_template("not_found.html"), 500

    status = redis_client.get(f"{plan_id}-status")
    if status:
        status = status.decode("utf8")
    else:
        status = PlanStatus.PENDING

    return flask.render_template(
        "plan.html",
        **{
            "plan_id": plan_id,
            "plan": plan,
            "status": status,
            "pending": status == PlanStatus.PENDING,
        },
    )


# PUT /plan/<uuid>/status approves or rejects the plan.
@app.route("/plan/<string:plan_id>/status", methods=["PUT"])
def set_status(plan_id: str):
    status = None
    try:
        status = flask.request.json.get("status")
    except Exception as e:
        print("Request is not JSON", e)
        return (
            flask.jsonify({"error": 'Expecting JSON with format {"status": "..."}'}),
            400,
        )

    if redis_client.get(f"{plan_id}-status") is None:
        print("Could not set plan status: plan not found")
        return flask.jsonify({"error": f"Plan id {plan_id} not found"}), 404

    if status not in PlanStatus.allowed_statuses:
        print("Attempt to set invalid plan status")
        return (
            flask.jsonify(
                {"error": f"`status` must be one of {PlanStatus.allowed_statuses}"}
            ),
            400,
        )

    redis_client.setex(f"{plan_id}-status", ONE_HOUR_SECONDS, status)
    print(f"Setting plan {plan_id} status to {status}")
    return flask.jsonify({}), 204


# GET /plan/<uuid>/status serves the status. This is the polling endpoint.
@app.route("/plan/<string:plan_id>/status", methods=["GET"])
def get_status(plan_id: str):
    status = redis_client.get(f"{plan_id}-status")
    if status is None:
        print("Could not get plan status: plan not found")
        return flask.jsonify({"error": f"Plan id {plan_id} not found"}), 404

    status = status.decode("utf8")
    if status not in PlanStatus.allowed_statuses:
        print(
            f"Falling back on {PlanStatus.PENDING} for plan with invalid status {status}"
        )
        status = PlanStatus.PENDING

    return flask.jsonify({"status": status})

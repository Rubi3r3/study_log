import os
import pytz
import hashlib
import jwt
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    flash,
    session,
    make_response,
    send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from functools import wraps

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# Database configuration
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD"))
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

belize_tz = pytz.timezone("America/Belize")

# Database URI
DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Configuration for PostgreSQL
app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI  # Update with your PostgreSQL details
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Model to represent a study session
class StudySession(db.Model):
    __tablename__ = "study_sessions"  # Explicitly set the table name

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(
        db.DateTime(timezone=True), nullable=False
    )  # Timestamp with timezone
    end_time = db.Column(
        db.DateTime(timezone=True), nullable=False
    )  # Timestamp with timezone
    total_time_seconds = db.Column(
        db.String(255), nullable=False
    )  # Store total time as a string
    module_name = db.Column(
        db.String(255), nullable=False
    )  # Name of the model (e.g., session description)
    comments = db.Column(db.String(8000), nullable=True)

    def __init__(self, start_time, end_time, total_time_seconds, module_name, comments):
        self.start_time = start_time
        self.end_time = end_time
        self.total_time_seconds = total_time_seconds
        self.module_name = module_name
        self.comments = comments


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), unique=True, nullable=False)
    last_name = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)


# Define the Table Model
class UnigisMscStatus(db.Model):
    __tablename__ = "unigis_msc_status"
    
    id = db.Column(db.Integer, primary_key=True)
    module_name = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False)
    grade_points = db.Column(db.Numeric(5,2))
    grade_text = db.Column(db.Text)
    grade_value = db.Column(db.Integer)
    ects = db.Column(db.Integer)
    equivalent = db.Column(db.Text)
    gpa = db.Column(db.Numeric(3,2))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form["username"]
    password = request.form["password"]

    password_bytes = password.encode("utf-8")
    md5_hash = hashlib.md5(password_bytes)
    hashed_password = md5_hash.hexdigest()

    user = User.query.filter_by(username=username).first()
    first_name = user.first_name

    if user and user.password == hashed_password and user.role == "user":
        session["logged_in"] = True

        return render_template("index.html")

    if user and user.password == hashed_password and user.role == "admin":
        session["logged_in"] = True

        return render_template("index.html")

    else:
        # return make_response('Invalid credentials! Please login or contact server administrator: rramirez@mail.sib.org.bz', 403, {'WWW-Authenticate': 'Basic realm: "Authentication Failed"'})
        error = "Invalid credentials! Please login or contact server administrator: rubiere.ramirez@gmail.com"
        return render_template("login.html", error=error), 403


@app.route("/")
def home():
    if not session.get("logged_in"):
        return render_template("login.html")
    else:
        return render_template("index.html")


# Route to serve the index.html page
# @app.route("/")
# def index():
#    return render_template(
#        "index.html"
#    )  # Serve the HTML file from the 'templates' folder


def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("You must log in to access this page.")
            return render_template("login.html"), 401
        return f(*args, **kwargs)

    return decorated_function


# Route to log a new study session
@app.route("/log_study_session", methods=["POST"])
@auth_required
def log_study_session():
    data = request.get_json()
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")
    module_name = data.get(
        "module_name"
    )  # Retrieve the module_name from the request data
    comments = data.get("comments")  # Retrieve the module_name from the request data

    if not module_name:
        return jsonify({"error": "Model name is required!"}), 400

    try:
        # Convert the start and end times to datetime objects (with timezone)
        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")

        # Calculate the total time in seconds
        total_time_seconds = (end_time - start_time).total_seconds()

        # Store total_time_seconds as a string
        total_time_seconds_str = str(total_time_seconds)

        # Create a new study session
        study_session = StudySession(
            start_time=start_time,
            end_time=end_time,
            total_time_seconds=total_time_seconds_str,  # Store as string
            module_name=module_name,  # Include the model name
            comments=comments,
        )

        # Add the new session to the database
        db.session.add(study_session)
        db.session.commit()

        return jsonify({"message": "Study session logged successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/total_study_time", methods=["GET"])
@auth_required
def total_study_time():
    try:
        # Get the current date in Belize timezone
        current_date = datetime.now(belize_tz).date()

        # Query to filter sessions for the current day, group by module_name, and concatenate comments using string_agg
        results = (
            db.session.query(
                StudySession.module_name,
                db.func.sum(StudySession.total_time_seconds.cast(db.Float)).label(
                    "total_time_seconds"
                ),
                db.func.string_agg(StudySession.comments, " || ").label(
                    "comments"
                ),  # Using string_agg for concatenation
            )
            .filter(db.func.date(StudySession.start_time) == current_date)
            .group_by(StudySession.module_name)
            .all()
        )

        # Prepare the response data
        total_times = []
        for result in results:
            # Calculate hours and minutes
            total_time_seconds = result.total_time_seconds
            hours = int(total_time_seconds // 3600)
            minutes = int((total_time_seconds % 3600) // 60)
            total_time_formatted = f"{hours}h {minutes}m"

            total_times.append(
                {
                    "module_name": result.module_name,
                    "total_time_hours": round(
                        total_time_seconds / 3600, 2
                    ),  # Convert to hours and round to 2 decimals
                    "total_time_formatted": total_time_formatted,  # Add hours and minutes format
                    "comments": (
                        result.comments if result.comments else "No comments"
                    ),  # Handle empty comments
                }
            )

        return jsonify(total_times), 200

    except Exception as e:
        # Handle exceptions and return an error response
        return jsonify({"error": str(e)}), 500


@app.route("/cumulative_time_summary", methods=["GET"])
@auth_required
def cumulative_time_summary():
    try:
        # Query the database
        results = (
            db.session.query(
                StudySession.module_name,
                db.func.sum(StudySession.total_time_seconds.cast(db.Float)).label(
                    "cumulative_time"
                ),
                db.func.string_agg(StudySession.comments, " || ").label("all_comments"),
            )
            .group_by(StudySession.module_name)
            .order_by(StudySession.module_name.asc())
            .all()
        )

        # Debug: Log query results
        print(f"Query results: {results}")

        if not results:
            return jsonify({"message": "No data found for the current date"}), 404

        # Prepare the response data
        summary_data = []
        for result in results:
            # Debug: Log each result
            print(f"Processing result: {result}")

            # Calculate cumulative time in hours and minutes
            cumulative_time_seconds = result.cumulative_time
            hours = int(cumulative_time_seconds // 3600)
            minutes = int((cumulative_time_seconds % 3600) // 60)
            cumulative_time_formatted = f"{hours}h {minutes}m"

            summary_data.append(
                {
                    "module_name": result.module_name,
                    "cumulative_time_hours": round(cumulative_time_seconds / 3600, 2),
                    "cumulative_time_formatted": cumulative_time_formatted,
                    "all_comments": (
                        result.all_comments if result.all_comments else "No comments"
                    ),
                }
            )

        # Debug: Log final response data
        print(f"Final summary data: {summary_data}")

        return jsonify(summary_data), 200

    except Exception as e:
        # Debug: Log the exception
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/study_sessions", methods=["GET"])
@auth_required
def get_study_sessions():
    sessions = StudySession.query.all()
    return jsonify(
        [
            {
                "id": session.id,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "total_time_seconds": session.total_time_seconds,
                "total_time_h_m": (
                    f"{int(float(session.total_time_seconds) // 3600)}h {int((float(session.total_time_seconds) % 3600) // 60)}m"
                    if session.total_time_seconds
                    else "0h 0m"
                ),
                "module_name": session.module_name,
                "comments": session.comments,
            }
            for session in sessions
        ]
    )


@app.route("/profile")
@auth_required
def profile():
    return render_template("profile.html")


@app.route("/table_data")
@auth_required
def table_data():
    return render_template("table_data.html")

@app.route("/grade")
@auth_required
def grade():
    grades = UnigisMscStatus.query.order_by(UnigisMscStatus.module_name).all()
    return render_template("grade.html", grades=grades)
    #return render_template("grade.html")


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.clear()
    return render_template("logout.html")


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=9090)

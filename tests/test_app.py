"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Fixture to provide a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Fixture to reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    })
    yield


class TestRoot:
    """Tests for the root endpoint"""

    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for getting activities"""

    def test_get_activities(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_get_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)

    def test_activities_have_initial_participants(self, client):
        """Test that activities have initial participants"""
        response = client.get("/activities")
        data = response.json()
        
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert len(data["Programming Class"]["participants"]) == 2


class TestSignup:
    """Tests for signup functionality"""

    def test_signup_new_participant(self, client):
        """Test signing up a new participant for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "alex@mergington.edu" in data["message"]

    def test_signup_adds_participant(self, client):
        """Test that signup actually adds the participant"""
        client.post("/activities/Chess Club/signup?email=alex@mergington.edu")
        
        response = client.get("/activities")
        activities_data = response.json()
        
        assert "alex@mergington.edu" in activities_data["Chess Club"]["participants"]
        assert len(activities_data["Chess Club"]["participants"]) == 3

    def test_signup_duplicate_participant(self, client):
        """Test signing up the same participant twice"""
        client.post("/activities/Chess Club/signup?email=alex@mergington.edu")
        client.post("/activities/Chess Club/signup?email=alex@mergington.edu")
        
        response = client.get("/activities")
        activities_data = response.json()
        
        # Count occurrences of the email
        count = activities_data["Chess Club"]["participants"].count("alex@mergington.edu")
        assert count == 2  # Both signup calls succeed

    def test_signup_nonexistent_activity(self, client):
        """Test signing up for a nonexistent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=alex@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_multiple_activities(self, client):
        """Test that a participant can sign up for multiple activities"""
        email = "test@mergington.edu"
        
        client.post(f"/activities/Chess Club/signup?email={email}")
        client.post(f"/activities/Programming Class/signup?email={email}")
        
        response = client.get("/activities")
        activities_data = response.json()
        
        assert email in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Programming Class"]["participants"]


class TestUnregister:
    """Tests for unregister functionality"""

    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        response = client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "Unregistered" in data["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        
        response = client.get("/activities")
        activities_data = response.json()
        
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]
        assert len(activities_data["Chess Club"]["participants"]) == 1

    def test_unregister_nonexistent_participant(self, client):
        """Test unregistering a participant that doesn't exist"""
        response = client.post(
            "/activities/Chess Club/unregister?email=nonexistent@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Participant not found" in data["detail"]

    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from a nonexistent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_multiple_times(self, client):
        """Test unregistering the same participant twice fails on second attempt"""
        client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        
        response = client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 404


class TestIntegration:
    """Integration tests combining multiple operations"""

    def test_signup_and_unregister_flow(self, client):
        """Test full flow: signup, verify, unregister, verify"""
        email = "integration@mergington.edu"
        activity = "Chess Club"
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify unregister
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]

    def test_multiple_operations(self, client):
        """Test multiple signup and unregister operations"""
        emails = ["user1@mergington.edu", "user2@mergington.edu", "user3@mergington.edu"]
        
        # Sign up all users
        for email in emails:
            response = client.post(f"/activities/Programming Class/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all signed up
        response = client.get("/activities")
        participants = response.json()["Programming Class"]["participants"]
        for email in emails:
            assert email in participants
        
        # Unregister first user
        client.post(f"/activities/Programming Class/unregister?email={emails[0]}")
        
        # Verify first user removed, others still there
        response = client.get("/activities")
        participants = response.json()["Programming Class"]["participants"]
        assert emails[0] not in participants
        assert emails[1] in participants
        assert emails[2] in participants

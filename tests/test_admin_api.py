import pytest
import json
from app import db
from app.models import User, Role, Permission # Added Permission
from flask_login import login_user, logout_user

# Helper function to create roles and permissions for tests
def setup_roles_permissions():
    admin_role = Role.query.filter_by(name='Admin').first()
    if not admin_role:
        admin_role = Role(name='Admin')
        # Add any specific permissions an Admin might need by default, if applicable
        # For now, just creating the role is enough for the decorator check
        db.session.add(admin_role)

    editor_role = Role.query.filter_by(name='Editor').first()
    if not editor_role:
        editor_role = Role(name='Editor')
        db.session.add(editor_role)

    # Example permission (not strictly needed for current admin tests but good for completeness)
    view_dashboard_perm = Permission.query.filter_by(name='view_dashboard').first()
    if not view_dashboard_perm:
        view_dashboard_perm = Permission(name='view_dashboard')
        db.session.add(view_dashboard_perm)

    if admin_role and view_dashboard_perm and view_dashboard_perm not in admin_role.permissions:
        admin_role.permissions.append(view_dashboard_perm)

    db.session.commit()
    return admin_role, editor_role

@pytest.fixture(scope='function', autouse=True)
def setup_database(app):
    """Set up the database for each test function."""
    with app.app_context():
        db.create_all()
        setup_roles_permissions() # Ensure roles exist
        yield db # Provide the db session to tests
        db.session.remove()
        db.drop_all()

@pytest.fixture
def admin_user(setup_database): # Depends on setup_database to ensure roles exist
    admin_role = Role.query.filter_by(name='Admin').first()
    if not admin_role: # Should be created by setup_roles_permissions
        admin_role = Role(name='Admin')
        db.session.add(admin_role)
        db.session.commit()

    user = User(username='admin_user', role_id=admin_role.id)
    user.set_password('admin_password')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def editor_user(setup_database): # Depends on setup_database
    editor_role = Role.query.filter_by(name='Editor').first()
    if not editor_role: # Should be created by setup_roles_permissions
        editor_role = Role(name='Editor')
        db.session.add(editor_role)
        db.session.commit()

    user = User(username='editor_user', role_id=editor_role.id)
    user.set_password('editor_password')
    db.session.add(user)
    db.session.commit()
    return user

# --- Test Cases ---

def test_create_user_as_admin(client, admin_user):
    with client.application.test_request_context():
        login_user(admin_user)

    admin_role = Role.query.filter_by(name='Admin').first()
    editor_role = Role.query.filter_by(name='Editor').first()

    response = client.post('/admin/users', json={
        'username': 'new_test_user',
        'password': 'new_password',
        'role_id': editor_role.id
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['username'] == 'new_test_user'
    assert data['role_id'] == editor_role.id
    assert 'password_hash' not in data # Ensure password hash is not returned

    newly_created_user = User.query.filter_by(username='new_test_user').first()
    assert newly_created_user is not None
    assert newly_created_user.role.name == 'Editor'

    with client.application.test_request_context():
        logout_user()

def test_create_user_missing_fields_as_admin(client, admin_user):
    with client.application.test_request_context():
        login_user(admin_user)

    response = client.post('/admin/users', json={
        'username': 'another_user'
        # Missing password and role_id
    })
    assert response.status_code == 400
    data = response.get_json()
    assert "Missing data" in data['message']

    with client.application.test_request_context():
        logout_user()

def test_create_user_duplicate_username_as_admin(client, admin_user):
    with client.application.test_request_context():
        login_user(admin_user)

    editor_role = Role.query.filter_by(name='Editor').first()

    # First, create a user
    client.post('/admin/users', json={
        'username': 'existing_user',
        'password': 'password123',
        'role_id': editor_role.id
    })

    # Attempt to create another user with the same username
    response = client.post('/admin/users', json={
        'username': 'existing_user',
        'password': 'password456',
        'role_id': editor_role.id
    })
    assert response.status_code == 409
    data = response.get_json()
    assert "Username already exists" in data['message']

    with client.application.test_request_context():
        logout_user()

def test_create_user_invalid_role_id_as_admin(client, admin_user):
    with client.application.test_request_context():
        login_user(admin_user)

    invalid_role_id = 99999 # Assuming this role ID does not exist
    response = client.post('/admin/users', json={
        'username': 'user_with_invalid_role',
        'password': 'password123',
        'role_id': invalid_role_id
    })
    assert response.status_code == 404 # Role not found
    data = response.get_json()
    assert "Role not found" in data['message']

    with client.application.test_request_context():
        logout_user()

def test_create_user_as_editor_forbidden(client, editor_user):
    with client.application.test_request_context():
        login_user(editor_user)

    any_role = Role.query.filter_by(name='Editor').first()
    response = client.post('/admin/users', json={
        'username': 'attacker_user',
        'password': 'password123',
        'role_id': any_role.id
    })
    assert response.status_code == 403 # Forbidden
    data = response.get_json()
    assert "Admin access required" in data['message']

    with client.application.test_request_context():
        logout_user()

def test_create_user_unauthenticated_forbidden(client):
    any_role = Role.query.filter_by(name='Editor').first()
    # Need to ensure roles exist even if no user is logged in, for role_id
    if not any_role: # Should be created by setup_database fixture's autouse=True
        with client.application.app_context():
            any_role = Role(name='Editor')
            db.session.add(any_role)
            db.session.commit()
            any_role = Role.query.filter_by(name='Editor').first()


    response = client.post('/admin/users', json={
        'username': 'unauth_user_creation_attempt',
        'password': 'password',
        'role_id': any_role.id if any_role else 1 # Fallback if role somehow not created
    })
    assert response.status_code == 401 # Unauthorized / Authentication required

    data = response.get_json()
    assert "Authentication required" in data['message']


# --- GET /admin/users Tests ---
def test_get_users_as_admin(client, admin_user, editor_user): # Add editor_user to ensure multiple users exist
    with client.application.test_request_context():
        login_user(admin_user)

    response = client.get('/admin/users')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    # We have admin_user and editor_user created by fixtures
    assert len(data) >= 2
    usernames = [u['username'] for u in data]
    assert admin_user.username in usernames
    assert editor_user.username in usernames
    for user_data in data:
        assert 'password_hash' not in user_data

    with client.application.test_request_context():
        logout_user()

def test_get_users_as_editor_forbidden(client, editor_user):
    with client.application.test_request_context():
        login_user(editor_user)

    response = client.get('/admin/users')
    assert response.status_code == 403
    data = response.get_json()
    assert "Admin access required" in data['message']

    with client.application.test_request_context():
        logout_user()

def test_get_users_unauthenticated_forbidden(client):
    response = client.get('/admin/users')
    assert response.status_code == 401
    data = response.get_json()
    assert "Authentication required" in data['message']


# --- PUT /admin/users/{id} Tests ---
def test_update_user_as_admin(client, admin_user):
    with client.application.test_request_context():
        login_user(admin_user) # admin_user is also the one being updated here for simplicity

    editor_role = Role.query.filter_by(name='Editor').first()
    assert editor_role is not None

    new_username = "updated_admin_username"
    response = client.put(f'/admin/users/{admin_user.id}', json={
        'username': new_username,
        'role_id': editor_role.id
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['username'] == new_username
    assert data['role_id'] == editor_role.id

    updated_user = User.query.get(admin_user.id)
    assert updated_user.username == new_username
    assert updated_user.role.name == 'Editor'

    with client.application.test_request_context():
        logout_user()

def test_update_user_change_password_as_admin(client, admin_user):
    with client.application.test_request_context():
        login_user(admin_user)

    old_password_hash = admin_user.password_hash
    new_password = "new_secure_password"
    response = client.put(f'/admin/users/{admin_user.id}', json={
        'password': new_password
    })
    assert response.status_code == 200

    updated_user = User.query.get(admin_user.id)
    assert updated_user.password_hash != old_password_hash
    assert updated_user.check_password(new_password)

    with client.application.test_request_context():
        logout_user()

def test_update_non_existent_user_as_admin(client, admin_user):
    with client.application.test_request_context():
        login_user(admin_user)

    non_existent_user_id = 99999
    response = client.put(f'/admin/users/{non_existent_user_id}', json={'username': 'ghost'})
    assert response.status_code == 404 # Not Found

    with client.application.test_request_context():
        logout_user()

def test_update_user_duplicate_username_as_admin(client, admin_user, editor_user):
    with client.application.test_request_context():
        login_user(admin_user) # admin_user is performing the update

    # Attempt to update editor_user's username to admin_user's username
    response = client.put(f'/admin/users/{editor_user.id}', json={
        'username': admin_user.username
    })
    assert response.status_code == 409 # Conflict
    data = response.get_json()
    assert "Username already exists" in data['message']

    with client.application.test_request_context():
        logout_user()

def test_update_user_invalid_role_id_as_admin(client, admin_user, editor_user):
    with client.application.test_request_context():
        login_user(admin_user)

    invalid_role_id = 99999
    response = client.put(f'/admin/users/{editor_user.id}', json={
        'role_id': invalid_role_id
    })
    assert response.status_code == 404 # Role not found
    data = response.get_json()
    assert "Role not found" in data['message']

    with client.application.test_request_context():
        logout_user()

def test_update_user_as_editor_forbidden(client, editor_user, admin_user):
    with client.application.test_request_context():
        login_user(editor_user) # editor_user is trying to update admin_user

    response = client.put(f'/admin/users/{admin_user.id}', json={'username': 'hacked_admin'})
    assert response.status_code == 403 # Forbidden

    with client.application.test_request_context():
        logout_user()

def test_update_user_unauthenticated_forbidden(client, admin_user):
    response = client.put(f'/admin/users/{admin_user.id}', json={'username': 'unauth_update'})
    assert response.status_code == 401 # Unauthorized

# --- DELETE /admin/users/{id} Tests ---
def test_delete_user_as_admin(client, admin_user, editor_user):
    with client.application.test_request_context():
        login_user(admin_user) # admin_user performs deletion

    user_to_delete_id = editor_user.id
    response = client.delete(f'/admin/users/{user_to_delete_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert f"User with ID {user_to_delete_id} deleted successfully" in data['message']

    deleted_user = User.query.get(user_to_delete_id)
    assert deleted_user is None

    with client.application.test_request_context():
        logout_user()

def test_delete_non_existent_user_as_admin(client, admin_user):
    with client.application.test_request_context():
        login_user(admin_user)

    non_existent_user_id = 99999
    response = client.delete(f'/admin/users/{non_existent_user_id}')
    assert response.status_code == 404 # Not Found

    with client.application.test_request_context():
        logout_user()

def test_delete_user_as_editor_forbidden(client, editor_user, admin_user):
    with client.application.test_request_context():
        login_user(editor_user) # editor_user trying to delete admin_user

    response = client.delete(f'/admin/users/{admin_user.id}')
    assert response.status_code == 403 # Forbidden

    with client.application.test_request_context():
        logout_user()

def test_delete_user_unauthenticated_forbidden(client, admin_user):
    response = client.delete(f'/admin/users/{admin_user.id}')
    assert response.status_code == 401 # Unauthorized

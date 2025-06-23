# AGENTS.md

This file provides information and guidelines for AI agents working with this codebase.

## Project Overview

[To be filled in - A brief description of the project]

## Coding Conventions

*   Follow PEP 8 for Python code.
*   Use descriptive variable and function names.
*   Write clear and concise comments where necessary.
*   Ensure all new features have corresponding tests.

## Running the Application

[To be filled in - Instructions on how to run the application, e.g., `flask run` or `python main.py`]

## Running Tests

[To be filled in - Instructions on how to run tests, e.g., `pytest`]

## Admin API Endpoints for User Management

The following API endpoints are available for managing users. Access to these endpoints requires the user to be authenticated and have the 'Admin' role.

All endpoints are prefixed with `/admin`.

### 1. Create User

*   **Endpoint:** `POST /users`
*   **Description:** Creates a new user.
*   **Request Body (JSON):**
    ```json
    {
        "username": "string (required)",
        "password": "string (required)",
        "role_id": "integer (required, ID of an existing role)"
    }
    ```
*   **Responses:**
    *   `201 Created`: User created successfully. Returns the new user object (excluding password hash).
        ```json
        {
            "id": "integer",
            "username": "string",
            "role_id": "integer",
            "role": "string (name of the role)"
        }
        ```
    *   `400 Bad Request`: Missing data or invalid input.
    *   `401 Unauthorized`: Authentication required.
    *   `403 Forbidden`: Admin access required.
    *   `404 Not Found`: Specified `role_id` does not exist.
    *   `409 Conflict`: Username already exists.

### 2. List All Users

*   **Endpoint:** `GET /users`
*   **Description:** Retrieves a list of all users.
*   **Responses:**
    *   `200 OK`: Successfully retrieved users. Returns a list of user objects.
        ```json
        [
            {
                "id": "integer",
                "username": "string",
                "role_id": "integer",
                "role": "string (name of the role)"
            }
        ]
        ```
    *   `401 Unauthorized`: Authentication required.
    *   `403 Forbidden`: Admin access required.

### 3. Update User

*   **Endpoint:** `PUT /users/{user_id}`
*   **Description:** Updates an existing user's details and/or role.
*   **Path Parameters:**
    *   `user_id`: The ID of the user to update.
*   **Request Body (JSON):** (Provide only fields to be updated)
    ```json
    {
        "username": "string (optional)",
        "password": "string (optional, provide if changing password)",
        "role_id": "integer (optional, ID of an existing role)"
    }
    ```
*   **Responses:**
    *   `200 OK`: User updated successfully. Returns the updated user object.
        ```json
        {
            "id": "integer",
            "username": "string",
            "role_id": "integer",
            "role": "string (name of the role)"
        }
        ```
    *   `400 Bad Request`: No input data provided.
    *   `401 Unauthorized`: Authentication required.
    *   `403 Forbidden`: Admin access required.
    *   `404 Not Found`: User with `user_id` not found, or specified `role_id` does not exist.
    *   `409 Conflict`: New username already exists.

### 4. Delete User

*   **Endpoint:** `DELETE /users/{user_id}`
*   **Description:** Deletes an existing user.
*   **Path Parameters:**
    *   `user_id`: The ID of the user to delete.
*   **Responses:**
    *   `200 OK`: User deleted successfully.
        ```json
        {
            "message": "User with ID {user_id} deleted successfully"
        }
        ```
    *   `401 Unauthorized`: Authentication required.
    *   `403 Forbidden`: Admin access required.
    *   `404 Not Found`: User with `user_id` not found.

## Notes

*   The `User` model currently does not include an `email` field. If this is added in the future, the API endpoints and their request/response bodies will need to be updated accordingly.
*   The `@admin_required` decorator in `app/decorators.py` handles authentication and authorization for these admin routes. It checks if `current_user.is_authenticated` and `current_user.role.name == 'Admin'`.
```

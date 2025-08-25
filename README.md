# 📝 Smile Snap - AI Diary Generator

Smile Snap is a smart diary application that transforms user-provided screenshots into memorable, AI-generated diary entries. A user uploads a screenshot of a happy or significant moment, and the application enriches it with contextual data (location, weather) to create a witty and personal diary entry using a generative AI.

The project features a full-stack architecture with a Python FastAPI backend, a MongoDB database, and a vanilla JavaScript frontend, all supported by a robust real-time update system using WebSockets.

[![Watch the Demo](https://img.youtube.com/vi/j5G1zcZqYFk/0.jpg)](https://www.youtube.com/watch?v=j5G1zcZqYFk)

## ✨ Features

* **Screenshot-Based Diary**: Users upload their own screenshots of meaningful moments to serve as the basis for their diary.
* **AI-Powered Diary Generation**: Leverages the Google Gemini API to analyze screenshots and context (location, weather) to create unique and humorous diary entries.
* **Secure User Authentication**: Full user registration and login system handled by Firebase Authentication, using JWTs to secure the API.
* **Role-Based Access Control (RBAC)**: Two distinct roles:
    * **User**: Can only access and manage their own screenshots and diary entries.
    * **Admin**: Can view a global dashboard of all users and access any user's data for management purposes.
* **Real-Time Updates**: Implements WebSockets to provide instant updates on both user and admin dashboards without requiring a page refresh.
* **Full CRUD Functionality**: The API supports complete data management:
    * **Users**: Full CRUD operations.
    * **Photos**: Users can Create, Read, and Delete photos. Updates are not supported.
    * **Entries**: Entries are created via the photo generation process. Only the text content can be updated.

## 🚀 Tech Stack

* **Backend**: Python, FastAPI
* **Database**: MongoDB (with Motor for async operations)
* **Authentication**: Firebase Authentication (JWT)
* **AI**: Google Gemini API
* **File Storage**: Google Cloud Storage
* **Deployment**: Google Cloud Run (for the backend), Vercel (for the frontend)
* **Frontend**: HTML, CSS, Bootstrap, Vanilla JavaScript
* **Real-time**: WebSockets

## 🌐 Live Links

* **Live Frontend**: <https://smile-snap.vercel.app/>
* **Backend API Docs (Swagger UI)**: <https://smile-snap-959486697650.us-west2.run.app/docs>

## 🔧 Local Setup Instructions

This project is split into two main parts: `server` (the FastAPI backend) and `frontend` (the user interface).

### 1. Backend Setup

The backend runs on Python and handles all API logic.

**Prerequisites**:
* Python 3.10+
* A MongoDB Atlas account (or local MongoDB instance)
* A Google Cloud project with a Service Account key (`serviceAccountKey.json`)
* API keys for Firebase, Google Gemini, IPinfo, and OpenWeatherMap

**Steps**:
1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
    cd your-repo-name/server
    ```
2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Create the environment file**:
    * In the `server/` directory, create a file named `.env`.
    * Fill it with your credentials, using the format below.
5.  **Place your Service Account Key**:
    * Place your downloaded `serviceAccountKey.json` file inside the `server/` directory.
6.  **Run the server**:
    ```bash
    # Run from the project's ROOT directory
    uvicorn server.main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

### 2. Frontend Setup

The frontend is a static site built with HTML, CSS, and JavaScript.

**Steps**:
1.  **Navigate to the `frontend` directory**.
2.  **Run a simple web server**. The easiest way is with Python:
    ```bash
    # Make sure you are in the frontend/ directory
    python -m http.server 8080
    ```
3.  **Open your browser** and go to `http://127.0.0.1:8080`. The application should be running.

---

## 🔑 Environment Variables (`.env` file)

Create a `.env` file in the `server` directory and add the following keys. **Do not commit this file to GitHub.**

```env
# MongoDB Connection String
MONGO_DETAILS="your_mongodb_connection_string"

# Google Cloud Project Info
GCP_PROJECT_ID="your-gcp-project-id"
BUCKET_NAME="your-gcs-bucket-name"
GOOGLE_APPLICATION_CREDENTIALS="serviceAccountKey.json"

# External API Keys
GEMINI_API_KEY="your_gemini_api_key"
IPINFO_API_TOKEN="your_ipinfo_api_token"
WEATHER_API_KEY="your_openweathermap_api_key"
FIREBASE_WEB_API_KEY="your_firebase_web_api_key"
```

## ⚙️ API Usage

The API is secured with JWTs from Firebase Authentication. To use protected endpoints, you must first log in to get a token and then include it in the `Authorization: Bearer <token>` header of your requests.

### 1. Authentication

First, obtain an access token by providing a registered user's credentials.

**Endpoint**: `POST /token`

**Request Body** (`application/x-www-form-urlencoded`):
- `username`: The user's email address.
- `password`: The user's password.

**Successful Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6...",
  "token_type": "bearer"
}
```
You will use this `access_token` for all subsequent authenticated requests.

---

### 2. Key API Endpoints

Below are examples of the primary endpoints. For a complete, interactive list, please visit the **[Live API Docs](https://smile-snap-959486697650.us-west2.run.app/docs)**.

#### User Endpoints

**Create a New User**
- **Endpoint**: `POST /users/`
- **Description**: Creates a new user in Firebase Auth and a corresponding profile in the database. This is a public endpoint.
- **Sample Body**:
  ```json
  {
    "email": "newuser@example.com",
    "password": "a-strong-password",
    "displayName": "New User"
  }
  ```

**Get a User's Own Diary Entries**
- **Endpoint**: `GET /users/{userId}/entries`
- **Description**: Retrieves all diary entries for the specified `userId`. Requires authentication as that user or as an admin.
- **Sample Response**:
  ```json
  [
    {
      "entryId": "e1a2b3c4-d5e6-f7a8-b9c0-d1e2f3a4b5c6",
      "userId": "oYWRgfkvD5NZkBYSR6xuPmarLiI3",
      "timestamp": "2025-07-27T18:30:00Z",
      "imageUrl": "[https://storage.googleapis.com/](https://storage.googleapis.com/)...",
      "content": "Finally fixed that bug! What a relief. 💻"
    }
  ]
  ```

#### Screenshot & Diary Generation

**Upload a Screenshot**
- **Endpoint**: `POST /screenshots/upload`
- **Description**: Uploads a screenshot for the authenticated user and creates a photo record.
- **Request Body** (`multipart/form-data`):
  - `userId`: The ID of the user uploading the photo.
  - `image`: The image file.

**Generate a Diary Entry from a Screenshot**
- **Endpoint**: `POST /screenshots/{photoId}/generate`
- **Description**: Triggers the AI to generate a diary entry for a previously uploaded photo.
- **Request Body** (`multipart/form-data`):
  - `userId`: The ID of the user who owns the photo.

#### Admin Endpoints

**Get All Users (Admin Only)**
- **Endpoint**: `GET /admin/users`
- **Description**: Retrieves a list of all user profiles in the database. Requires authentication as an admin.
- **Sample Response**:
  ```json
  [
    {
      "userId": "oYWRgfkvD5NZkBYSR6xuPmarLiI3",
      "email": "user1@example.com",
      "displayName": "Test User 1",
      "role": "user"
    },
    {
      "userId": "FwC6XTxHo1YKQ5mOp4t3p6sMiQ23",
      "email": "admin@example.com",
      "displayName": "Admin User",
      "role": "admin"
    }
  ]
  

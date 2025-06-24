# The Grand Locus - Refactored

This repository contains the source code for "The Grand Locus" blog, refactored from a legacy Google App Engine application to a modern Python web application using the [FastAPI](https://fastapi.tiangolo.com/) framework. The application is designed to be deployed as a container on [Google Cloud Run](https://cloud.google.com/run).

This document provides an overview of the project's architecture, development setup, authentication flow, and detailed deployment instructions.

## Migration Summary

This project is the result of a step-by-step migration from the original Google App Engine (Python 2.7) implementation. The key migration steps were:

1.  **"Hello World" & Containerization**: A minimal FastAPI application was created, along with a `Dockerfile` and `requirements.txt`, to establish a baseline for deployment on Google Cloud Run.
2.  **Datastore Migration**:
    *   A modern Pydantic model (`models_/blog_post.py`) was created to represent blog posts.
    *   A script (`download_posts.py`) was developed to connect to the legacy App Engine Datastore, extract all blog posts, and write them to a new Firestore database (in Datastore mode) in a new, clean Google Cloud project (`thegrandlocus-2`).
    *   This involved resolving authentication issues (`gcloud auth application-default login`), creating the new database, and handling data-related errors during the write process.
3.  **Image Handling**: Investigation revealed that images were already stored in Google Cloud Storage, not the legacy Blobstore. An API endpoint (`/img/...`) was created to serve these images directly from the existing storage bucket.
4.  **Application Development & Deployment**:
    *   The FastAPI application was built out with API endpoints to serve posts (`/posts`, `/posts/{post_id}`) and a Jinja2-templated frontend to display them.
    *   The application was deployed to a new Cloud Run service in the `thegrandlocus-2` project.
    *   This process required careful configuration of IAM permissions to allow the new Cloud Run service to access both the Firestore database (in `thegrandlocus-2`) and the image storage bucket (in the original `thegrandlocus` project).

---

## Project Architecture

The repository is structured to separate concerns, making it easier to manage and develop.

-   `main.py`: The main FastAPI application file. It initializes the app, includes routers, mounts static files, and defines the primary public-facing and authentication routes.
-   `run.py`: A simple script to run the application locally for development using `uvicorn`.
-   `Dockerfile`: Defines the Docker container image for deployment. It specifies the base image, copies the application code, installs dependencies, and sets the command to run the application.
-   `requirements.txt`: Lists all Python package dependencies for the project.

-   `models_/`: Contains Pydantic models that define the data structures of the application.
    -   `blog_post.py`: Defines the `BlogPost` model, used for type validation and serialization when interacting with the Datastore.

-   `services/`: Modules for interacting with external services, primarily Google Cloud.
    -   `blog.py`: Contains all the logic for interacting with Google Cloud Datastore (for creating, reading, updating, and deleting blog posts).
    -   `google_auth.py`: Configures the `Authlib` client for handling the Google OAuth 2.0 sign-in flow.

-   `routes/`: Contains FastAPI `APIRouter` modules to organize endpoints.
    -   `admin_fastapi.py`: Houses the API endpoints for the admin section of the blog (e.g., `/admin`, `/admin/newpost`). All routes in this module require authentication.

-   `templates/`: Contains Jinja2 HTML templates used to render the frontend of the blog.
-   `static/`: Contains static assets like CSS, JavaScript, and images used by the frontend.
-   `Pics/`: A directory containing the original source images for blog posts.

-   `download_posts.py`: A one-off utility script used for the data migration from the old Datastore to the new one.
-   `app.yaml`, `index.yaml`: Legacy configuration files from the original Google App Engine project.

---

## Data and Configuration

The application's data is stored in Google Cloud Datastore, and its behavior is controlled by a combination of code-based configuration and environment variables.

### Datastore Configuration

The application connects to a Google Cloud Datastore database.

-   **Project ID**: The Datastore is located in the `thegrandlocus-2` Google Cloud project.
-   **Database Mode**: It operates in "Datastore mode" (as opposed to "Firestore Native mode").
-   **Connection**: All interactions with the Datastore are handled by a single, centralized client initialized in `services/datastore.py`. This client uses the `google-cloud-datastore` library and automatically authenticates using the application's service account when deployed on Google Cloud Run. For local development, it uses the credentials from `gcloud auth application-default login`.

### Data Models

The structure of the data stored in Datastore is defined using Pydantic models.

-   **`BlogPost`**: The primary model is `BlogPost`, defined in `models_/blog_post.py`. It specifies the schema for a blog post, including fields like `title`, `body`, `published` date, and `tags`. Pydantic ensures that any data read from or written to the Datastore conforms to this schema, preventing data-consistency errors.

### Datastore Indexes

Efficiently querying the Datastore requires indexes.

-   **`index.yaml`**: This file is critical for the performance of the blog. It defines the composite indexes that the Datastore needs to execute complex queries, such as fetching posts and sorting them by their publication date (`-published`).
-   **Deployment**: While the application code is deployed via Cloud Run, the Datastore indexes must be deployed separately using the `gcloud` command-line tool. Without these indexes in place, queries will fail. To deploy the indexes, run the following command from the root of the project:
    ```bash
    gcloud datastore indexes create index.yaml --project=thegrandlocus-2
    ```

---

## Authentication

The application uses Google OAuth 2.0 to secure the admin section. Here's a detailed breakdown of the components and the login flow.

### Core Components

1.  **`Authlib` Library**: This library is the backbone of the authentication system. It handles the complexities of the OAuth 2.0 "dance," such as generating authorization URLs and exchanging codes for access tokens.
2.  **Session Middleware**: FastAPI's `SessionMiddleware` is used to create and manage user sessions. After a user successfully logs in, their profile information is stored in a secure, signed session cookie. This cookie is sent with subsequent requests, allowing the user to stay logged in.
3.  **Proxy Headers Middleware**: A critical piece for deployment on Google Cloud Run. The `uvicorn.middleware.proxy_headers.ProxyHeadersMiddleware` is used to solve the `redirect_uri_mismatch` error. Cloud Run's proxy terminates HTTPS and forwards traffic to the container as HTTP. This middleware reads the `X-Forwarded-*` headers (like `X-Forwarded-Proto: https`) to ensure the application generates correct `https://` URLs, which is a strict requirement for Google's OAuth flow.

### Authentication Flow

1.  A user attempts to access an admin page (e.g., `/admin/`).
2.  The `get_current_user` dependency in `routes/admin_fastapi.py` checks the request session for user data.
3.  If no user is found in the session, the request is redirected to the `/login` route.
4.  The `/login` route uses `Authlib` to generate a unique authorization URL and redirects the user to Google's sign-in page.
5.  The user signs in with their Google account and grants the requested permissions.
6.  Google redirects the user back to the application's registered **Redirect URI**, which is `/auth`.
7.  The `/auth` route receives the authorization code from Google, exchanges it for an access token, and uses the token to fetch the user's profile (`userinfo`).
8.  This user information is then saved into the session cookie.
9.  Finally, the user is redirected to the `/admin/` page, which they can now access as an authenticated user.
10. To sign out, the user can visit the `/logout` route, which clears the session cookie.

---

## Local Development

To run the blog on your local machine for development:

1.  **Install Dependencies**:
    Make sure you have Python 3.8+ installed, then install the required packages.
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set Up Local Redirect URI**:
    The Google OAuth flow will not work on `127.0.0.1` without a bit of extra setup. For local development, you must add `http://127.0.0.1:8000/auth` as an authorized redirect URI in your [Google Cloud Console Credentials page](https://console.cloud.google.com/apis/credentials) for the `thegrandlocus-2` project, alongside the production `https://` URI.

3.  **Run the Development Server**:
    ```bash
    python run.py
    ```
    The application will be available at `http://127.0.0.1:8000`. You can now test the full login flow locally.

---

## Deployment to Google Cloud Run

This section provides a detailed guide to deploying the blog to Google Cloud Run.

### 1. Secrets and Configuration

For the application to function, it needs access to several secrets. **These should be stored securely in a service like Google Secret Manager and not be committed to version control.** For convenience during development, the required values are listed here.

### 2. Google Cloud Project Setup

1.  **Projects**:
    -   **Application Project**: `thegrandlocus-2` (Hosts Cloud Run, Datastore)
    -   **Image Project**: `thegrandlocus` (Hosts the Cloud Storage bucket with post images)
2.  **APIs**: Ensure the following APIs are enabled in `thegrandlocus-2`:
    -   Cloud Run API (`run.googleapis.com`)
    -   Artifact Registry API (`artifactregistry.googleapis.com`)
3.  **OAuth Client Registration**: An OAuth 2.0 Client ID must be created in the `thegrandlocus-2` project.
    -   Navigate to the [Credentials page](https://console.cloud.google.com/apis/credentials).
    -   Create an **OAuth client ID** for a **Web application**.
    -   Add the following URI to the **Authorized redirect URIs**:
        -   `https://thegrandlocus-818095314483.europe-west9.run.app/auth`
4.  **IAM Permissions**: The Cloud Run service needs permission to access other Google Cloud services. Ensure the service account used by Cloud Run (by default, `[PROJECT_NUMBER]-compute@developer.gserviceaccount.com`) has the following roles:
    -   **Datastore User**: To read and write blog posts.
    -   **Storage Object Viewer**: To read images from the old `thegrandlocus_bucket`.

### 3. Deploying the Application

1.  **Deploy Datastore Indexes**:
    Before deploying the application, ensure your Datastore indexes are up-to-date.
    ```bash
    gcloud datastore indexes create index.yaml --project=thegrandlocus-2
    ```

2.  **Deploy the Application**:
    This command builds the container using Cloud Build, pushes it to Artifact Registry, and deploys it to Cloud Run.

    ```bash
    # Replace [REGION] with your chosen region, e.g., us-central1
    gcloud run deploy thegrandlocus \
      --source . \
      --platform managed \
      --region [REGION] \
      --allow-unauthenticated \
      --project=thegrandlocus-2
    ```
    The `--allow-unauthenticated` flag makes the blog public. The command will provide a URL for the deployed service upon completion.


    ```bash
    gcloud run deploy thegrandlocus \
      --source . \
      --platform managed \
      --region europe-west9 \
      --allow-unauthenticated \
      --project=thegrandlocus-2
    ```

7. **Check**:
    ```bash
    curl -s -o /dev/null -w "%{http_code}" https://thegrandlocus-818095314483.europe-west9.run.app # 200
    curl -s -o /dev/null -w "%{http_code}" https://thegrandlocus-818095314483.europe-west9.run.app/admin/ # 401
    curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer testuser" https://thegrandlocus-818095314483.europe-west9.run.app/admin/ # 200
    ```

8. **Debug**:
    ```bash
    gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.revision_name=\"thegrandlocus-00013-j58\"" --project=thegrandlocus-2 --limit=100 | cat
    ```

9. **Visit the web site**:
    The blog is deployed at `https://thegrandlocus-818095314483.[REGION].run.app/`

    https://thegrandlocus-818095314483.europe-west9.run.app/

# Install gcloud
See details in the [documentation](https://cloud.google.com/sdk/docs/install#deb).

```
sudo apt-get install apt-transport-https ca-certificates gnupg curl sudo
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install google-cloud-cli
```

Once this is done, initialize `gcloud`.

```
gcloud init
gcloud auth login
gcloud config set project thegrandlocus-2
```

# Install virtual environment
First create a virtual environment with `venv` and activate it.

```
/usr/bin/python3 -m venv venv
source venv/bin/activate
```

Then install the requirements with `pip`.

```
pip install -r requirements.txt
```

# Deploy
Use `gcloud` to deploy the app (billing must be enabled).

```
gcloud app deploy --quiet
```

You can monitor the versions of the app on the [console](https://console.cloud.google.com/appengine/versions?project=thegrandlocus&serviceId=default).

# Upload images

```
gsutil cp image.png gs://thegrandlocus_bucket
gsutil -m cp * gs://thegrandlocus_bucket
```

### Acknowledgements
I forked `bloggart` for The Grand Locus.
Here is the original README of bloggart.

Bloggart is a blog application for Google App Engine. It's currently being
developed as a demonstration app for [a series of blog
posts](http://blog.notdot.net/2009/10/Writing-a-blog-system-on-App-Engine) but
is intended to be a useful and versatile blogging system for App Engine by the
time it's done.

![The original picture for bloggart](http://github.com/Arachnid/bloggart/raw/master/themes/default/static/images/bloggart-ae.png)

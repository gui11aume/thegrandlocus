# The Grand Locus - Refactored

This repository contains the source code for "The Grand Locus" blog, refactored from a legacy Google App Engine application to a modern Python web application using the [FastAPI](https://fastapi.tiangolo.com/) framework. The application is designed to be deployed as a container on [Google Cloud Run](https://cloud.google.com/run).

This document provides an overview of the project's architecture, development setup, authentication flow, and detailed deployment instructions.

## Migration Summary

This project is the result of a step-by-step migration from the original Google App Engine (Python 2.7) implementation. The key migration steps were:

1.  **"Hello World" & Containerization**: A minimal FastAPI application was created, along with a `Dockerfile` and `requirements.txt`, to establish a baseline for deployment on Google Cloud Run.
2.  **Datastore Migration**:
    *   A modern Pydantic model (`models/blog_post.py`) was created to represent blog posts.
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

-   `models/`: Contains Pydantic models that define the data structures of the application.
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

-   **`BlogPost`**: The primary model is `BlogPost`, defined in `models/blog_post.py`. It specifies the schema for a blog post, including fields like `title`, `body`, `published` date, and `tags`. Pydantic ensures that any data read from or written to the Datastore conforms to this schema, preventing data-consistency errors.

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

2.  **Register the local redirect URI in Google Cloud (required)**:
    The app sends Google a **redirect URI** built from the address you use in the browser. It must match **character for character** what you list in the console.

    - Open [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials), select project **`thegrandlocus-2`**, and edit the **OAuth 2.0 Client ID** whose **Client ID** matches **`GOOGLE_CLIENT_ID`** in your `.env` file (if you edit the wrong client, sign-in will keep failing).
    - Under **Authorized redirect URIs**, click **Add URI** and add at least:
        - `http://127.0.0.1:8000/auth` — use this if you open the site at `http://127.0.0.1:8000`
        - `http://localhost:8000/auth` — optional; add it if you sometimes use `http://localhost:8000` instead (**`localhost` and `127.0.0.1` are not interchangeable** for Google).
    - Save. Wait a minute for changes to apply, then try **Login** again.

    Production `https://…/auth` URIs stay listed alongside these.

3.  **Run the Development Server**:
    ```bash
    python run.py
    ```
    Or, with Poetry: `poetry run python run.py`, or `make run` from the project root.

    The application will be available at `http://127.0.0.1:8000`. You can now test the full login flow locally.

4.  **Google credentials for Datastore (local)**:
    Reading and writing posts uses the **Google Cloud Datastore API** with **Application Default Credentials**, which are separate from the OAuth client used for admin sign-in. Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) and authenticate:

    ```bash
    gcloud auth login
    gcloud auth application-default login
    ```

    If you use more than one Google account, pick the one that can access project `thegrandlocus-2`:

    ```bash
    gcloud auth list
    gcloud config set account YOUR_ACCOUNT@gmail.com
    gcloud auth application-default login
    ```

### Troubleshooting (local development)

- **Google says the app does not comply with OAuth 2.0, or asks to register the redirect URI** (`redirect_uri=http://127.0.0.1:8000/auth` in the error): The URI in the error must appear under **Authorized redirect URIs** for the **same** OAuth client as `GOOGLE_CLIENT_ID` in `.env`. Fix: add that exact URI in [Credentials](https://console.cloud.google.com/apis/credentials), or always use the same host you registered (e.g. only `127.0.0.1`, not `localhost`, unless both are listed).

- **`invalid_grant: Bad Request` or 500 errors when opening `/`**: Usually means Application Default Credentials are missing or the refresh token expired. Run `gcloud auth login` and `gcloud auth application-default login` again (see step 4 above).

- **`gcloud run revisions list` errors when you only wanted to start the app**: The Makefile runs Cloud Run commands **only** for the `make logs` target. `make run` does not call `gcloud run`; if you still see that error, update this repository (older Makefiles ran `gcloud` while parsing the file) or run the server directly: `poetry run python run.py`.

- **Datastore `UserWarning` about `add_filter`**: Harmless deprecation notices from the `google-cloud-datastore` client; they do not stop the app from running.

---

## Deployment to Google Cloud Run

This section provides a detailed guide to deploying the blog to Google Cloud Run.

### 1. Secrets and Configuration

For the application to function, it needs access to several secrets. **These should be stored securely in a service like Google Secret Manager and not be committed to version control.** For convenience during development, the required values are listed here.

In addition to `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `SECRET_KEY`, production (Cloud Run) requires **`ADMIN_EMAILS`**: a comma-separated list of Google accounts allowed to complete admin login. Without it, OAuth completes but no user is granted a session. The `make deploy-prod` target sets `ENVIRONMENT=production` on the service; `make deploy-staging` sets `ENVIRONMENT=staging`. Optionally set **`TRUSTED_PROXY_HOSTS`** (default `*`) if you need to restrict which proxies’ `X-Forwarded-*` headers are honored.

### 2. Staging and production workflow

Development stays on a single branch (for example `master`). You run **two** Cloud Run **services** in the same Google Cloud project: one for smoke-testing a release, one for the live site. Both use the same Datastore and image bucket; this workflow assumes you only change application code between releases, not blog content.

| Stage | Cloud Run service name | Make target |
|--------|-------------------------|-------------|
| Staging | `thegrandlocus-staging` | `make deploy-staging` |
| Production | `thegrandlocus` | `make deploy-prod` (or `make deploy`) |

Typical flow:

1. Merge or commit on `master` as usual.
2. Run **`make deploy-staging`**, open the staging URL Cloud Run prints (or find it under **Cloud Run** in the console), and verify the site.
3. When satisfied, run **`make deploy-prod`** to update production.

`make logs-staging` and `make logs` (production) tail the latest revision’s logs via Cloud Logging. To remove the staging service only, use `make undeploy-staging`.

Service names and region are defined at the top of the `Makefile` (`SERVICE_NAME_STAGING`, `SERVICE_NAME_PRODUCTION`, `REGION`). Override them there if you rename services.

### 3. Google Cloud Project Setup

1.  **Projects**:
    -   **Application Project**: `thegrandlocus-2` (Hosts Cloud Run, Datastore)
    -   **Image Project**: `thegrandlocus` (Hosts the Cloud Storage bucket with post images)
2.  **APIs**: Ensure the following APIs are enabled in `thegrandlocus-2`:
    -   Cloud Run API (`run.googleapis.com`)
    -   Artifact Registry API (`artifactregistry.googleapis.com`)
3.  **OAuth Client Registration**: An OAuth 2.0 Client ID must be created in the `thegrandlocus-2` project.
    -   Navigate to the [Credentials page](https://console.cloud.google.com/apis/credentials).
    -   Create an **OAuth client ID** for a **Web application**.
    -   Add **every** URL where users can start login to **Authorized redirect URIs** (Google matches the URI exactly, including host). For example:
        -   `https://thegrandlocus-818095314483.europe-west9.run.app/auth` (Cloud Run default URL for production; your project number and region may differ — copy from the Cloud Run service details page)
        -   `https://thegrandlocus-staging-<PROJECT_NUMBER>.<REGION>.run.app/auth` (staging service — add **after** the first `make deploy-staging`, using the exact hostname shown in the console or CLI output)
        -   `https://thegrandlocus.com/auth` (custom domain — required if you use `thegrandlocus.com`; omitting it causes `redirect_uri_mismatch`)
4.  **IAM Permissions**: Each Cloud Run service uses the project’s default compute service account unless you change it. That account (by default, `[PROJECT_NUMBER]-compute@developer.gserviceaccount.com`) needs the following roles (staging and production share the same project, so one account covers both):
    -   **Datastore User**: To read and write blog posts.
    -   **Storage Object Viewer**: To read images from the old `thegrandlocus_bucket`.

### 4. Deploying the Application

1.  **Deploy Datastore Indexes**:
    Before deploying the application, ensure your Datastore indexes are up-to-date.
    ```bash
    gcloud datastore indexes create index.yaml --project=thegrandlocus-2
    ```

2.  **Deploy from the Makefile (recommended)**:
    From the repository root, with `.env` populated and `gcloud` authenticated:

    ```bash
    make deploy-staging   # test on staging first
    make deploy-prod      # or: make deploy — production when ready
    ```

    This builds the container with Cloud Build, pushes it to Artifact Registry, and deploys to Cloud Run with the same flags as in the `Makefile` (including `ENVIRONMENT` and secrets from `.env`).

3.  **Deploy manually (equivalent)**:
    If you prefer `gcloud` directly, match the service name and region from the `Makefile` (`SERVICE_NAME_PRODUCTION`, `SERVICE_NAME_STAGING`, `REGION`). Example for production:

    ```bash
    gcloud run deploy thegrandlocus \
      --source . \
      --platform managed \
      --region europe-west1 \
      --allow-unauthenticated \
      --project=thegrandlocus-2
    ```

    The `--allow-unauthenticated` flag makes the blog public. The command prints the service URL when it finishes.

4. **Check**:
    ```bash
    # Use your real Cloud Run URL (region and project number must match the service)
    curl -s -o /dev/null -w "%{http_code}" https://thegrandlocus-818095314483.europe-west9.run.app/
    curl -s -o /dev/null -w "%{http_code}" https://thegrandlocus-818095314483.europe-west9.run.app/admin/
    ```
    Expect `200` on `/` and `302` on `/admin/` when not signed in.
    After deployment, set **`ADMIN_EMAILS`** on **each** Cloud Run service you use (staging and production) if you need admin login there — Console or:

    `gcloud run services update SERVICE_NAME --region=REGION --project=thegrandlocus-2 --update-env-vars=ADMIN_EMAILS=you@example.com`

    (Replace `SERVICE_NAME` with `thegrandlocus` or `thegrandlocus-staging` as needed.)

5. **Debug**:
    ```bash
    gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.revision_name=\"thegrandlocus-00013-j58\"" --project=thegrandlocus-2 --limit=100 | cat
    ```

6. **Visit the web site**:
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

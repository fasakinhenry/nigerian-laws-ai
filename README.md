# Nigerian Laws (RAG) AI Assistant

This project is an AI-powered assistant for Nigerian legal information, built on a Retrieval-Augmented Generation (RAG) pipeline.

## Getting Started

Follow these steps to set up and run the application locally using Docker Compose.

### Prerequisites

- Docker Desktop (or Docker Engine and Docker Compose) installed and running on your system.

### 1. Environment Configuration

This project relies on several environment variables for its services (MongoDB, Ollama, Backend API, etc.). These variables are sensitive and not committed to the repository.

**Steps:**

1.  Navigate to the root directory of this repository:
    ```bash
    cd nigerian-laws-ai
    ```
2.  **Create your `.env` file** by copying the provided `example.env`:
    ```bash
    cp example.env .env
    ```
3.  Open the newly created `.env` file in your text editor.
4.  **Important:** Replace the placeholder values (e.g., `your_github_personal_access_token_here`, `admin_user`, `admin_password`, `llama3.2:1b`) with your actual desired configuration. Review all comments in the `.env` file for guidance.

    **Reference: `example.env` Content**
    (This section is for reference only; the actual file is `example.env` in your repository)

    ```dotenv
    MONGO_URI=mongodb://mongodb:27017/nigerian_laws_db
    MONGO_DB_NAME=nigerian_laws_db
    MONGO_COLLECTION_NAME=raw_documents

    GITHUB_PERSONAL_ACCESS_TOKEN=your_github_personal_access_token_here

    OLLAMA_BASE_URL=http://ollama:11434
    OLLAMA_MODEL_NAME=llama3.2:1b # You can change this to your preferred model

    ME_CONFIG_MONGODB_SERVER=mongodb
    ME_CONFIG_MONGODB_PORT=27017

    ME_CONFIG_BASICAUTH_USERNAME=admin_user
    ME_CONFIG_BASICAUTH_PASSWORD=admin_pass
    ME_CONFIG_MONGODB_URL=mongodb://mongodb:27017/

    NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
    ```

### 2. Running the Application

Once your `.env` file is configured:

1.  Make sure you are in the root directory of the project.
2.  Execute the `run.sh` script to start all services:

    ```bash
    sh run.sh
    ```

    This script will:

    - Ensure Docker Desktop is running.
    - Build (if necessary) and start all the services defined in `docker-compose.yml` in detached mode (`-d`). This includes the MongoDB, Ollama, Backend, and Frontend services.
    - The `ollama-setup` service will pull the specified AI model. This might take some time depending on your internet connection and the model size.

3.  Access the application:
    - **Frontend UI:** Once all services are up, open your web browser and go to `http://localhost:4000`.
    - **Mongo Express UI:** Access your MongoDB database visually at `http://localhost:8081` using the credentials you set in `.env`.
    - **Ollama API:** The Ollama API is exposed on `http://localhost:11434`.

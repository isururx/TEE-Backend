# 🌱 TEE Backend

<p align="center">
  <img src="https://readme-typing-svg.demolab.com/?font=Fira+Code&size=24&duration=3000&pause=1000&color=2E8B57&center=true&vCenter=true&width=650&lines=AI-Powered+Tea+Estate+Management;FastAPI+%7C+PostgreSQL+%7C+Machine+Learning;Smart+Agriculture+for+Sri+Lankan+Tea+Estates" alt="Typing Animation" />
</p>

<p align="center">
  <strong>TEE — AI-Based Tea Disease Detection & Estate Management System</strong>
</p>

<p align="center">
  <a href="https://github.com/isururx/TEE-Backend">
    <img src="https://img.shields.io/github/stars/isururx/TEE-Backend?style=for-the-badge" alt="Stars">
  </a>
  <a href="https://github.com/isururx/TEE-Backend/issues">
    <img src="https://img.shields.io/github/issues/isururx/TEE-Backend?style=for-the-badge" alt="Issues">
  </a>
  <a href="https://github.com/isururx/TEE-Backend">
    <img src="https://img.shields.io/github/last-commit/isururx/TEE-Backend?style=for-the-badge" alt="Last Commit">
  </a>
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
</p>

---

## 📖 About

TEE Backend is the backend service for an **AI-powered Tea Estate Management System** designed to modernize tea estate operations through centralized digital management and machine-learning-based disease detection.

The backend provides RESTful APIs for:

* 🔐 Authentication & authorization
* 👥 User management
* 🌿 Tea disease detection
* 🗺️ Plantation block management
* 👷 Worker management
* 📋 Task management
* 🕒 Attendance management
* 📊 Operational metrics
* 🤖 AI model inference
* 🗄️ Database operations

The system is designed around a modular service-oriented backend architecture using **FastAPI**, **SQLAlchemy**, **PostgreSQL**, and an integrated ML inference layer.

---

# 🏗️ System Architecture

```text
                         ┌──────────────────────┐
                         │      React Web App   │
                         └──────────┬───────────┘
                                    │
                              REST / JSON
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     FastAPI Backend  │
                         │                      │
                         │      /api            │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │ API Routers │       │   Services  │       │   Schemas   │
       │             │──────▶│             │──────▶│  Pydantic   │
       └─────────────┘       └──────┬──────┘       └─────────────┘
                                    │
                      ┌─────────────┴─────────────┐
                      │                           │
                      ▼                           ▼
              ┌──────────────┐            ┌──────────────┐
              │ PostgreSQL   │            │ ML Inference │
              │   Database   │            │    Service   │
              └──────────────┘            └──────────────┘
```

---

# 🚀 Technology Stack

| Layer             | Technology                     |
| ----------------- | ------------------------------ |
| Language          | Python                         |
| Web Framework     | FastAPI                        |
| ORM               | SQLAlchemy                     |
| Database          | PostgreSQL                     |
| Validation        | Pydantic                       |
| AI/ML             | CNN-based image classification |
| API Standard      | REST                           |
| API Specification | OpenAPI                        |
| API Documentation | Swagger UI / ReDoc             |
| Authentication    | Login + 2FA                    |
| Architecture      | Router → Service → Database    |
| Version Control   | Git / GitHub                   |

---

# 🔌 API Architecture

The backend exposes APIs through the `/api` prefix.

```text
/api
│
├── /auth
│   ├── login
│   ├── verify-2fa
│   ├── worker-login
│   └── protected
│
├── /detection
│   └── detect
│
├── /users
│
├── /blocks
│   ├── CRUD
│   ├── harvest-history
│   └── activities
│
├── /workers
│   └── CRUD
│
├── /tasks
│   ├── CRUD
│   ├── status
│   └── metrics
│
└── /attendance
    ├── records
    └── metrics
```

---

# 📚 API Documentation

TEE Backend uses FastAPI's automatic **OpenAPI specification generation**.

Once the backend is running:

### Swagger UI

```text
http://localhost:8000/docs
```

### ReDoc

```text
http://localhost:8000/redoc
```

### OpenAPI JSON

```text
http://localhost:8000/openapi.json
```

The application is configured with the API title **TEE Backend** and version **1.0.0**.

---

# 🔐 Authentication

TEE implements a multi-step authentication workflow.

```text
┌──────────────┐
│    Client    │
└──────┬───────┘
       │
       │ POST /api/auth/login
       ▼
┌──────────────────┐
│ Credential Check │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Generate 6-digit │
│       OTP        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   SMS Delivery   │
└────────┬─────────┘
         │
         │ POST /verify-2fa
         ▼
┌──────────────────┐
│  Verify OTP      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Authenticated    │
│      User        │
└──────────────────┘
```

### Authentication Endpoints

| Method | Endpoint                 | Description           |
| ------ | ------------------------ | --------------------- |
| POST   | `/api/auth/login`        | Authenticate user     |
| POST   | `/api/auth/verify-2fa`   | Verify OTP            |
| POST   | `/api/auth/worker-login` | Worker authentication |
| GET    | `/api/auth/protected`    | Protected endpoint    |

---

# 🤖 AI Disease Detection

The disease detection service accepts a tea leaf image and sends it through the ML inference pipeline.

```text
Image Upload
     │
     ▼
Image Validation
     │
     ▼
Preprocessing
     │
     ▼
CNN Model
     │
     ▼
Disease Prediction
     │
     ▼
Confidence Score
     │
     ▼
Treatment Recommendation
     │
     ▼
Database Record
```

### Endpoint

```http
POST /api/detection/detect
```

### Request

```text
Content-Type: multipart/form-data
```

| Parameter | Type | Required |
| --------- | ---- | -------- |
| image     | File | Yes      |

### Example

```bash
curl -X POST \
  http://localhost:8000/api/detection/detect \
  -F "image=@tea_leaf.jpg"
```

---

# 🌿 Plantation Block API

The Block API manages plantation areas and their associated operational records.

### Available Operations

| Method | Endpoint                                             |
| ------ | ---------------------------------------------------- |
| GET    | `/api/blocks`                                        |
| GET    | `/api/blocks/{block_id}`                             |
| POST   | `/api/blocks`                                        |
| PUT    | `/api/blocks/{block_id}`                             |
| DELETE | `/api/blocks/{block_id}`                             |
| GET    | `/api/blocks/{block_id}/harvest-history`             |
| POST   | `/api/blocks/{block_id}/harvest-history`             |
| DELETE | `/api/blocks/{block_id}/harvest-history/{record_id}` |
| GET    | `/api/blocks/{block_id}/activities`                  |

---

# 👷 Worker API

| Method | Endpoint                   | Description      |
| ------ | -------------------------- | ---------------- |
| GET    | `/api/workers`             | Retrieve workers |
| GET    | `/api/workers/{worker_id}` | Retrieve worker  |
| POST   | `/api/workers`             | Create worker    |
| PUT    | `/api/workers/{worker_id}` | Update worker    |
| DELETE | `/api/workers/{worker_id}` | Delete worker    |

---

# 📋 Task API

| Method | Endpoint                      | Description    |
| ------ | ----------------------------- | -------------- |
| GET    | `/api/tasks`                  | Retrieve tasks |
| GET    | `/api/tasks/metrics`          | Task metrics   |
| POST   | `/api/tasks`                  | Create task    |
| PUT    | `/api/tasks/{task_id}/status` | Update status  |
| PUT    | `/api/tasks/{task_id}`        | Update task    |
| DELETE | `/api/tasks/{task_id}`        | Delete task    |

---

# 🕒 Attendance API

| Method | Endpoint                  | Description         |
| ------ | ------------------------- | ------------------- |
| GET    | `/api/attendance`         | Retrieve attendance |
| GET    | `/api/attendance/metrics` | Attendance metrics  |
| POST   | `/api/attendance`         | Log attendance      |

---

# 🧪 Testing

The backend follows an API testing workflow covering:

```text
Development
    │
    ▼
Unit Testing
    │
    ▼
API Testing
    │
    ▼
Integration Testing
    │
    ▼
Regression Testing
```

Testing can be performed using:

* Pytest
* Swagger UI
* Postman
* Automated CI tests

---

# ⚙️ CI/CD Pipeline

The target engineering workflow is:

```text
                 ┌─────────────┐
                 │    Git Push │
                 └──────┬──────┘
                        │
                        ▼
                ┌───────────────┐
                │  CI Pipeline  │
                └──────┬────────┘
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
          Linting    Testing   Security
             │         │         │
             └─────────┼─────────┘
                       ▼
                 Build Validation
                       │
                       ▼
                ┌───────────────┐
                │  Docker Build │
                └──────┬────────┘
                       │
                       ▼
                ┌───────────────┐
                │ CD / Deploy   │
                └───────────────┘
```

### Pipeline Goals

* Automated testing on code changes
* Build validation
* Dependency/security checks
* Reproducible builds
* Automated deployment
* Reduced manual deployment errors

---

# 📊 Engineering Metrics

The project tracks software-engineering metrics alongside functional development.

| Metric                     | Description                       |
| -------------------------- | --------------------------------- |
| API Coverage               | Implemented API endpoints         |
| API Documentation Coverage | Documented endpoints              |
| Test Pass Rate             | Successful automated tests        |
| Test Coverage              | Code exercised by tests           |
| CI Success Rate            | Successful CI pipeline executions |
| Deployment Success Rate    | Successful deployments            |
| API Response Time          | Backend latency                   |
| Error Rate                 | Failed API requests               |
| Code Quality               | Static analysis results           |
| Pull Requests              | Reviewed team contributions       |
| Commit Activity            | Development activity              |

> Metrics should be updated from actual CI/GitHub/test data rather than manually estimated values.

---

# 🗄️ Database Architecture

The backend uses **PostgreSQL** as the primary relational database.

```text
FastAPI
   │
   ▼
Service Layer
   │
   ▼
SQLAlchemy ORM
   │
   ▼
PostgreSQL
```

Pydantic schemas are used to validate API request and response structures.

Example:

```python
class BlockCreate(BaseModel):
    area: float
    tea_variety: Optional[str] = None
    plant_date: Optional[date] = None
    supervisor_id: Optional[int] = None
```

---

# 📁 Project Structure

```text
TEE-Backend/
│
├── api/
│   ├── router.py
│   └── routes/
│       ├── users/
│       ├── detection/
│       ├── blocks/
│       ├── workers/
│       ├── tasks/
│       └── attendance/
│
├── core/
│
├── db/
│   ├── database.py
│   └── models/
│
├── ml/
│
├── models/
│
├── schemas/
│
├── services/
│
├── main.py
├── requirements.txt
└── README.md
```

---

# 🛠️ Local Development

## 1. Clone Repository

```bash
git clone https://github.com/isururx/TEE-Backend.git
cd TEE-Backend
```

## 2. Create Virtual Environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a `.env` file:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/tee
```

Add other required service credentials according to the environment configuration.

## 5. Run Backend

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

---

# 📈 Repository Activity

### Contributors

<a href="https://github.com/isururx/TEE-Backend/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=isururx/TEE-Backend" alt="TEE Backend Contributors"/>
</a>

### Contribution Graph

<a href="https://github.com/isururx/TEE-Backend/graphs/contributors">
  <img src="https://github-readme-activity-graph.vercel.app/graph?username=isururx&repo=TEE-Backend&theme=github-compact&hide_border=true" alt="TEE Backend Contribution Graph"/>
</a>

---

# 👥 Development Team

TEE is developed as a collaborative first-year ICT project.

| Role               | Responsibility                               |
| ------------------ | -------------------------------------------- |
| AI/ML Engineer     | Disease detection and ML integration         |
| Frontend Developer | React UI and dashboard development           |
| Frontend Developer | User interfaces and reporting                |
| Backend Developer  | API and authentication services              |
| Backend Developer  | Database, inventory and operational services |

---

# 🔄 Development Workflow

```text
Issue
  ↓
Development Branch
  ↓
Implementation
  ↓
Pull Request
  ↓
Code Review
  ↓
CI Validation
  ↓
Merge
  ↓
Build
  ↓
Deployment
```

---

# 📌 Current Project Status

### Backend

| Component             | Status            |
| --------------------- | ----------------- |
| FastAPI Application   | 🟢 Active         |
| REST API              | 🟢 Active         |
| Authentication        | 🟢 Implemented    |
| 2FA                   | 🟢 Implemented    |
| Disease Detection     | 🟢 Integrated     |
| User Management       | 🟢 Implemented    |
| Plantation Blocks     | 🟢 Implemented    |
| Worker Management     | 🟢 Implemented    |
| Task Management       | 🟢 Implemented    |
| Attendance            | 🟢 Implemented    |
| Inventory             | 🟡 In Development |
| Analytics             | 🟡 In Development |
| CI/CD                 | 🟡 In Development |
| Production Deployment | 🟡 Planned        |

---

# 📖 Documentation

* **API Documentation:** `/docs`
* **Alternative API Documentation:** `/redoc`
* **OpenAPI Specification:** `/openapi.json`
* **Architecture Documentation:** Project documentation
* **Database Design:** ERD documentation

---

# 🎯 Project Goals

TEE aims to provide a centralized digital platform for tea estate operations by combining:

**AI Disease Detection + Estate Management + Workforce Management + Inventory + Analytics**

into a single integrated platform.

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:2E8B57,100:66CDAA&height=120&section=footer" alt="Footer Animation"/>
</p>

<p align="center">
  <strong>🌱 TEE — Smart Technology for Smarter Tea Estates</strong>
</p>

<p align="center">
  Built with ❤️ by the TEE Development Team
</p>

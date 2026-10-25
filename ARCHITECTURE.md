# System Design: Attendance Tracker & Risk Calculator

## 1. System Overview
The Attendance Tracker is a scalable, decoupled web service designed to manage student attendance records and compute real-time risk metrics regarding the 75% mandatory attendance threshold. The architecture separates the synchronous request-response cycle from asynchronous batch processing to ensure high availability and low latency.

## 2. High-Level Architecture
The system follows a modern multi-tier microservices pattern orchestrated via Docker Compose:

* **Client Level:** Web or mobile client initiating RESTful HTTP requests.
* **API Gateway / Load Balancer:** **Nginx** handles incoming traffic on port 80, terminating the connection and distributing requests across multiple backend replicas via round-robin load balancing.
* **Application Server:** **FastAPI** (Python) instances handle business logic, JWT authentication, and request validation. Deployed as stateless replicas to allow horizontal scaling.
* **Caching Layer:** **Redis** stores computationally expensive mathematical risk evaluations (safe-leaves calculations) with Time-To-Live (TTL) expiration and active cache invalidation.
* **Primary Database:** **PostgreSQL** provides persistent relational storage with strict ACID compliance, ensuring data integrity through foreign keys and check constraints.
* **Asynchronous Task Queue:** **Celery** (Worker & Beat) utilizes Redis as a message broker to decouple heavy scheduled tasks (daily risk scans) from the main web server threads.

## 3. Data Flow & Component Interactions
* **Synchronous Read (Cache Hit):** Client requests course status -> Nginx routes to FastAPI -> FastAPI queries Redis -> Redis returns JSON -> Client receives 200 OK.
* **Synchronous Write (Cache Invalidation):** Client posts attendance -> FastAPI validates via Pydantic -> Commits to PostgreSQL -> Deletes corresponding course key in Redis -> Returns 201 Created.
* **Asynchronous Cron Job:** At 00:00 UTC, Celery Beat pushes a "scan_risk" task to the Redis broker -> Celery Worker consumes the task -> Worker executes an aggregation query on PostgreSQL -> Worker dispatches external notifications (e.g., email/SMS via third-party API).

## 4. Database Schema (PostgreSQL)
The relational model is normalized to Third Normal Form (3NF) to eliminate data redundancy.
* **`users`**: `id` (PK), `email` (Unique), `hashed_password`, `created_at`
* **`courses`**: `id` (PK), `user_id` (FK -> users.id), `name`, `credits`
* **`class_schedules`**: `id` (PK), `course_id` (FK), `day_of_week` (Check: 0-6), `start_time`
* **`attendance_records`**: `id` (PK), `course_id` (FK), `date`, `status` (Check: present, absent, cancelled).
  * *Constraint:* Unique composite index on `(course_id, date)` to prevent duplicate entries and enable PostgreSQL upsert logic.

## 5. Key Trade-offs & Engineering Decisions
* **Stateless Authentication (JWT) vs. Session IDs:** 
  * *Decision:* JWT. 
  * *Justification:* By storing the user state on the client side, the Nginx load balancer does not need sticky sessions. Any FastAPI replica can seamlessly authorize any request.
* **Database Constraints vs. Application Logic:**
  * *Decision:* Enforced at the DB layer (Check Constraints, Cascades).
  * *Justification:* Prevents race conditions from corrupting the database. If two API requests attempt to mark attendance for the same day simultaneously, the database's unique constraint handles the collision gracefully rather than relying on application-level locks.
* **Read-Through Caching Strategy:**
  * *Decision:* Redis caches the final computed risk string. 
  * *Justification:* Calculating the risk margin requires scanning multiple rows. Caching the output turns an O(N) database aggregation into an O(1) memory read.
* **Asynchronous Processing (Celery):**
  * *Decision:* Offloading daily scans to a worker process.
  * *Justification:* A query grouping tens of thousands of attendance records across all users would block the Python GIL and cause API timeouts. Celery processes this data safely in the background.
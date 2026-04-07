# 🚀 PayFlow

PayFlow is a production-oriented digital payments system inspired by platforms like Mercado Pago, PayPal, and Cash App.

Unlike typical CRUD projects, PayFlow focuses on **real-world financial system challenges** such as consistency, idempotency, and resilience to external provider failures.

---

## 🌐 Live Demo

- Frontend: https://payflow-ochre.vercel.app  
- Backend API: Railway

---

## ⚡ Key Features

- 💸 Peer-to-peer payments (atomic & consistent)
- 📩 Payment requests
- 💳 Wallet top-up via Mercado Pago (real integration)
- 📊 Transaction history & metrics dashboard
- 🧾 Full ledger system (financial traceability)
- 🔍 Audit logs for all operations

---

## 🧠 Why This Project Matters

Most junior projects are simple CRUD apps.

PayFlow is different — it solves **real backend problems found in financial systems**:

- Preventing double transactions  
- Handling asynchronous external payments  
- Ensuring data consistency under concurrency  
- Recovering from partial failures  

---

## 🏗️ Architecture Overview

### Backend
- Django + Django REST Framework
- PostgreSQL (Neon)
- JWT Authentication (SimpleJWT)
- pytest + coverage (~93%)

### Frontend
- React + Vite
- Axios (interceptors + token refresh)
- React Router
- Context API

---

## 💸 Payment System Design

### 🔹 P2P Payments (Synchronous)

- `transaction.atomic`
- `select_for_update` (row-level locking)
- Idempotency enforcement
- Ledger + audit integration

👉 Guarantees:
- No race conditions  
- No double spending  

---

### 🔹 Funding Flow (Asynchronous)

1. Create payment intent (PENDING)
2. Redirect to Mercado Pago checkout
3. Receive webhook confirmation
4. Fallback via reconciliation
5. Update wallet balance

---

## 🔁 Consistency Strategy

PayFlow does **not trust external providers blindly**.

It uses multiple mechanisms:

- Webhooks (event-driven)
- Reconciliation (polling fallback)
- Manual refresh (user-triggered)
- Idempotency keys

👉 Result:
- No duplicated credits  
- No inconsistent balances  
- System remains reliable even if provider fails  

---

## 🧾 Ledger & Audit

Every operation generates:

- Ledger entries (financial record)
- Audit logs (traceability)
- Domain events

👉 This enables:
- Debugging complex issues  
- Full financial trace  
- Production-level observability  

---

## 🧪 Testing

- 169 tests  
- ~93% coverage  

Includes:

- Concurrency tests  
- Service-level tests  
- API tests  
- Edge cases  

---

## 📊 Observability

Endpoints:

- `/core/health/`
- `/core/metrics/`
- `/core/dashboard-summary/`

---

## ⚠️ Current Limitations

- Webhooks not fully validated in all environments
- Auth strategy not finalized (email vs username vs OAuth)
- Dockerization pending

---

## 🎯 Project Status

Core system is **production-oriented**:

- Atomic and safe payments ✔  
- Reliable funding flow ✔  
- Strong consistency guarantees ✔  
- High test coverage ✔  

Current focus:

- UX improvements  
- Product clarity  
- Deployment polish  

---

## 🧠 Key Takeaway

PayFlow is designed around a core principle:

> **Correctness over immediacy**

Instead of assuming external systems are reliable, it uses redundancy mechanisms (webhooks, reconciliation, manual refresh) to guarantee consistency in asynchronous payment flows.

---

## 📌 Future Work

- Improve webhook reliability in production  
- Dockerize infrastructure  
- Refine onboarding & UX  

---

## 👨‍💻 Author

Emiliano David Sanabria  
Backend Developer (Django)

GitHub: https://github.com/EmilianoDavidSanabria
# SmartBiz Manager

**SmartBiz Manager** is a comprehensive, web-based business management system built to empower entrepreneurs. It simplifies inventory tracking, sales processing, supplier management, and financial reporting while providing actionable insights and real-time notifications.

---

## 🔧 Features

### 👥 User Roles
- **Manager**
  - Add/remove operators
  - Set discounts
  - View daily/weekly sales and profit reports
  - Receive low stock SMS alerts
  - Full access to all operator features
- **Operator**
  - Process sales
  - Record customer needs and feedback
  - Log expenses
  - Track item availability

### 📦 Inventory Management
- Categorized item database with optional images
- Multi-supplier support with price comparisons
- Real-time buying price updates
- Low stock thresholds with dashboard alerts and SMS

### 📊 Sales & Financials
- Tracks sales, expenses, and change due
- Cash and manual MPESA payment tracking
- Daily/weekly reports with top operator insights

### 🔐 Security
- JWT authentication
- Hashed passwords with enforced complexity
- First-login password update required

### 🧾 Supplier Management
- Store supplier profiles and contact info
- Link items to multiple suppliers with historical pricing

---

## 🛠️ Tech Stack

- **Frontend:** HTML + CSS (mobile-first), Jinja2 Templates
- **Backend:** FastAPI (Python)
- **Database:** MongoDB (NoSQL)
- **Auth:** JWT, hashed credentials
- **SMS Alerts:** Africa’s Talking / Twilio
- **MPESA Integration:** Manual entry (Daraja API planned for Phase 2)

---

## 📁 Project Structure

smartbiz-manager/
├── app/
│ ├── main.py
│ ├── models/
│ ├── routes/
│ ├── templates/
│ ├── static/
│ └── utils/
├── requirements.txt
├── README.md

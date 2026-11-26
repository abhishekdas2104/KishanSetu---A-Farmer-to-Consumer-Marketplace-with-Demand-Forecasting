# 🌾 KisanSetu – A Farmer-to-Consumer Marketplace with Demand Forecasting

<p align="center">

  **Kisano Se Seedha, Aapke Ghar Tak.**  
  *From Farmers, Directly to Your Home.*

  A Django-powered agricultural marketplace connecting farmers directly with consumers while helping farmers make better inventory decisions through demand forecasting.

  [![Live Website](https://img.shields.io/badge/Live%20Website-Visit%20KisanSetu-2E8B57?style=for-the-badge)](https://kishansetu.pythonanywhere.com/)
  [![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![Django](https://img.shields.io/badge/Django-4.2.7-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)

</p>

---

## 📌 About the Project

KisanSetu is a web-based farmer-to-consumer marketplace designed to reduce unnecessary intermediaries in the traditional agricultural supply chain.

Traditionally, agricultural products pass through multiple intermediaries, including local aggregators, mandi brokers, wholesalers, and retailers. This reduces farmers' profit margins while increasing prices for consumers.

KisanSetu addresses this problem by providing a digital platform where farmers can list their agricultural products and sell them directly to customers.

The platform also includes a basic demand forecasting system that analyzes historical order data using a **7-day moving average** to help farmers estimate upcoming product demand and manage their inventory more effectively.

## 🎯 Problem Statement

- Farmers often receive lower prices because of multiple intermediaries.
- Consumers pay higher prices due to additional supply-chain costs.
- Farmers have limited visibility into upcoming product demand.
- Poor inventory planning can lead to overstocking, product wastage, and stock shortages.
- There is a need for a transparent digital platform that connects farmers and consumers directly.

## 💡 Project Objectives

1. **Direct Farmer-to-Consumer Connection:** Eliminate unnecessary intermediaries by allowing farmers to sell directly to customers.
2. **Transparent Pricing:** Enable farmers to set product prices and optionally display reference market prices.
3. **Demand Forecasting:** Analyze recent order history to estimate weekly product demand.
4. **Inventory Management:** Help farmers monitor stock levels and identify products requiring restocking.
5. **Secure Role-Based Platform:** Provide separate functionalities for Farmers, Customers, and Administrators.

---

## 🚀 Live Demo

<https://kishansetu.pythonanywhere.com/>

The application is deployed using **PythonAnywhere**.

---

## ✨ Key Features

### 1. 🌐 Public Website & Marketplace

Accessible without requiring users to log in.

- Responsive homepage with platform statistics.
- Featured agricultural products.
- Product categories and quick navigation.
- Marketplace with keyword-based product search.
- Category filtering and price sorting.
- Product pagination (12 products per page).
- Individual product detail pages.
- Farmer information and product availability.
- Related product recommendations.
- About Us and Contact Us pages.
- Contact form with optional image attachments.

### 2. 👨‍🌾 Farmer Hub

A dedicated dashboard for registered farmers.

- Dashboard displaying total products, active products, orders, and earnings.
- Low-stock alerts for products with 5 kg or less remaining.
- Recent order information.
- Add, edit, and delete agricultural products.
- Upload product images.
- Manage product prices and available quantities.
- View incoming customer orders.
- Filter orders by status.
- Accept or reject pending orders.
- Mark accepted orders as completed.
- View demand forecasting insights.

### 3. 🛒 Customer Hub

A dedicated shopping experience for registered customers.

- Personalized customer dashboard.
- Browse and search agricultural products.
- View detailed product information.
- Add products to a session-based shopping cart.
- Live cart subtotal preview.
- Single-farmer-per-order restriction.
- Secure checkout with Cash on Delivery.
- View previous orders and order status.
- Track pending, accepted, completed, and rejected orders.

### 4. 📊 Demand Forecasting

One of the key features of KisanSetu is its basic demand forecasting system.

It analyzes actual historical order data to estimate future product demand.

**Forecasting Method: 7-Day Moving Average**

The calculation uses non-rejected orders from the previous seven days.

```text
Average Daily Demand =
Total Quantity Ordered During Last 7 Days / 7

Predicted Weekly Demand =
Average Daily Demand × 7
```

Features include:

- Product-wise demand analysis.
- Seven-day daily demand visualization.
- Chart.js bar charts.
- Most demanded product highlights.
- Low-stock restocking recommendations.
- Product selection for individual forecasts.
- Informative messages when insufficient order history is available.

The forecasting system is designed to provide basic inventory planning assistance rather than guaranteed future demand predictions.

### 5. 🛡️ Admin Control Center

A dedicated administration interface for managing the platform.

- Secret-code-based Admin registration.
- Platform-wide statistics and overview.
- Farmer and customer management.
- Activate or deactivate user accounts.
- Product moderation.
- Activate, deactivate, or delete products.
- View and manage all platform orders.
- View customer contact messages and attachments.
- Reply to contact messages through email.
- Track unreplied messages.
- Access to the Django Admin panel.

---

## 🔐 Security Features

Security and data integrity are important parts of KisanSetu.

| Security Feature | Description |
|---|---|
| Password Hashing | Django PBKDF2 password hashing |
| Login Protection | Five failed attempts trigger a 30-second lockout |
| Session Expiry | Automatic logout after 15 minutes of inactivity |
| Role-Based Access | Separate Farmer, Customer, and Admin permissions |
| Ownership Validation | Users can only manage their authorized resources |
| CSRF Protection | Django CSRF protection on POST forms |
| Server-Side Validation | Validates product prices, stock, forms, and uploaded images |
| Image Validation | JPG, JPEG, PNG, and WEBP; maximum 5 MB |
| Secure Configuration | Environment variables for secrets and email credentials |
| Order Integrity | Transaction-based stock deduction and restoration |
| State Validation | Prevents invalid order status transitions |

Additional protections include homepage auto-logout behavior for authenticated users and server-side authorization checks on protected views.

---

## 🧰 Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python 3 |
| Backend Framework | Django 4.2.7 |
| Frontend | HTML5, CSS3, JavaScript |
| UI Framework | Bootstrap 5 |
| Icons | Bootstrap Icons |
| Typography | Inter Google Font |
| Database | SQLite |
| ORM | Django ORM |
| Data Visualization | Chart.js |
| Image Processing | Pillow |
| Deployment | PythonAnywhere |
| Version Control | Git & GitHub |

---

## 🏗️ Project Architecture

KisanSetu follows Django's Model-View-Template (MVT) architecture with a single main application named `marketplace`.

```text
KishanSetu/
│
├── kisan_setu/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── marketplace/
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   │       └── seed_demo.py
│   │
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── forecast.py
│   ├── urls.py
│   ├── admin.py
│   └── tests.py
│
├── templates/
│   ├── includes/
│   │   └── dashboard_sidebar.html
│   └── [page templates]
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── images/
│
├── media/
│   ├── products/
│   └── contact_attachments/
│
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

*The structure above highlights the main application components. Additional page templates and static assets are included in the project.*

---

## 🗄️ Database Design

KisanSetu uses SQLite with Django ORM.

The application uses Django's built-in `User` model along with five application models.

| Model | Purpose |
|---|---|
| `Profile` | Stores user information and account roles |
| `Product` | Stores agricultural product information, pricing, stock, and farmer details |
| `Order` | Stores customer orders, delivery information, payment method, and order status |
| `OrderItem` | Stores individual products and quantities associated with an order |
| `ContactMessage` | Stores customer inquiries, attachments, and administrator replies |

### Important Database Relationships

- Each user has one associated profile.
- A farmer can list multiple products.
- A customer can place multiple orders.
- Each order is associated with a customer and a farmer.
- An order can contain multiple order items.
- Contact messages can be reviewed and answered by administrators.

---

## ⚙️ Getting Started – Run Locally

Follow these steps to run KisanSetu on your local machine.

### Prerequisites

Make sure you have installed:

- Python 3
- Git
- Visual Studio Code (recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/abhishekdas2104/KishanSetu---A-Farmer-to-Consumer-Marketplace-with-Demand-Forecasting.git
```

### 2. Navigate to the Project Directory

```bash
cd KishanSetu---A-Farmer-to-Consumer-Marketplace-with-Demand-Forecasting
```

### 3. Create a Virtual Environment

```bash
python -m venv .venv
```

### 4. Activate the Virtual Environment

**Windows:**

```bash
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure Environment Variables

Create a `.env` file in the project root and configure the required application settings.

The project uses environment-based configuration for:

- Django secret key.
- Admin registration code.
- Email credentials.

Use your own local values and follow the environment-variable names expected by the project's settings. Never commit real secrets to GitHub.

### 7. Apply Database Migrations

```bash
python manage.py migrate
```

### 8. Create an Administrator Account

```bash
python manage.py createsuperuser
```

Follow the prompts to create your administrator account.

### 9. Run the Development Server

```bash
python manage.py runserver
```

Open the following URL in your browser:

<http://127.0.0.1:8000/>

---

## 🧪 Testing & Verification

KisanSetu includes automated tests in `marketplace/tests.py` covering important application workflows.

**Test execution:**

```bash
python manage.py test
```

**Django system check:**

```bash
python manage.py check
```

### Testing Coverage

The automated test suite covers:

- Public page accessibility.
- Marketplace search, category filtering, and sorting.
- Registration and role-based redirection.
- Admin registration code validation.
- Login lockout enforcement.
- Farmer product ownership restrictions.
- Customer dashboard access restrictions.
- Cart and checkout functionality.
- Stock deduction and restoration.
- Order privacy and status management.
- Seven-day demand forecasting calculations.
- Contact form submission and administrator replies.

**Latest documented test results:**

- ✅ 10/10 automated tests passed.
- ✅ Django system check completed with 0 issues.

---

## 🚀 Deployment

KisanSetu is deployed on **PythonAnywhere** using Django's WSGI configuration.

**Live Application:**  
https://kishansetu.pythonanywhere.com/

Deployment includes:

- Django application configuration.
- WSGI setup.
- Production static and media file configuration.
- Database migrations.
- Environment-based secret configuration.

---

## 🔮 Future Enhancements

Potential improvements for future versions include:

- Online payment gateway integration.
- Real-time order notifications.
- Advanced demand forecasting using machine learning.
- Location-based product discovery.
- Delivery tracking.
- Multilingual support for regional languages.
- Mobile application for farmers and customers.
- More detailed agricultural market price insights.

---

## 👨‍💻 Developer

**Abhishek Das**

B.Tech – Computer Science and Engineering

- GitHub: [@abhishekdas2104](https://github.com/abhishekdas2104)
- LinkedIn: [Abhishek Das](https://www.linkedin.com/in/abhishek-das-468b60289/)

---

## 📄 License

This project was developed as an academic project.

You may explore the source code for learning and educational purposes. Please contact the author before redistributing or using substantial portions of the project commercially.

---

<p align="center">

  **🌱 KisanSetu – Empowering Farmers, Connecting Communities.**

  *Kisano Se Seedha, Aapke Ghar Tak.*

</p>

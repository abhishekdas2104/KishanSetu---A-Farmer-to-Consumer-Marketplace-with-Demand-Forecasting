# KisanSetu – A Farmer-to-Consumer Marketplace with Demand Forecasting

**Hindi Tagline:** Kisano Se Seedha, Aapke Ghar Tak.  
**English Tagline:** From Farmers, Directly to Your Home.

KisanSetu is a Django full-stack web application that connects farmers directly with consumers, removing unnecessary intermediaries and providing a 7-day moving average demand forecasting dashboard for farmers.

## Features
- **Public Website & Marketplace**: Browse, search, filter by category, and sort agricultural produce by price without logging in.
- **Role-Based Authentication**: Separate registration and login flows for **Farmers**, **Customers**, and **Admins** (with secret admin code protection, password visibility toggle, 30-second login lockout after 5 failed attempts, and automatic inactive session expiration).
- **Farmer Hub**: Product CRUD with image uploads, low-stock alerts, order acceptance/rejection/completion with transactional stock restoration, and 7-day demand forecasting using Chart.js.
- **Customer Dashboard & Cart**: Session-based single-farmer shopping cart, Cash on Delivery checkout, and order tracking.
- **Admin Control Center & Django Admin**: Platform-wide overview, user/product moderation, and Contact Us message management with direct email replies.

## Tech Stack
- **Backend**: Python, Django
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript, Chart.js
- **Database**: SQLite

## Quick Start
```powershell
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

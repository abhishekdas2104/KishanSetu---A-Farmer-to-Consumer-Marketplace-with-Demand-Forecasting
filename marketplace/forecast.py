from datetime import timedelta
from django.utils import timezone

from .models import Order, OrderItem, Product


def get_product_forecast(product):
    """
    Calculate 7-day moving average demand forecast for a single product
    using actual non-rejected orders from the last 7 days.
    """
    today = timezone.localdate()
    start_date = today - timedelta(days=6)
    start_dt = timezone.now() - timedelta(days=7)

    items = (
        OrderItem.objects.filter(
            product=product,
            order__order_date__gte=start_dt,
        )
        .exclude(order__status=Order.STATUS_REJECTED)
        .select_related('order')
    )

    # Build day-by-day totals for the last 7 days
    daily_map = {}
    for offset in range(7):
        day = start_date + timedelta(days=offset)
        daily_map[day] = 0

    total_last_7_days = 0
    order_ids = set()

    for item in items:
        item_day = timezone.localtime(item.order.order_date).date()
        if item_day in daily_map:
            daily_map[item_day] += item.quantity
        total_last_7_days += item.quantity
        order_ids.add(item.order_id)

    avg_daily_demand = round(total_last_7_days / 7, 2)
    predicted_weekly_demand = round(avg_daily_demand * 7, 2)

    labels = [day.strftime('%d %b') for day in daily_map.keys()]
    daily_quantities = list(daily_map.values())

    return {
        'product': product,
        'total_last_7_days': total_last_7_days,
        'avg_daily_demand': avg_daily_demand,
        'predicted_weekly_demand': predicted_weekly_demand,
        'order_count': len(order_ids),
        'labels': labels,
        'daily_quantities': daily_quantities,
        'has_sufficient_data': total_last_7_days > 0,
    }


def get_farmer_forecast_summary(farmer):
    """
    Return demand summary, most demanded products, and low stock recommendations
    for all products owned by the given farmer.
    """
    products = Product.objects.filter(farmer=farmer)
    forecasts = [get_product_forecast(product) for product in products]

    most_demanded = sorted(
        [f for f in forecasts if f['total_last_7_days'] > 0],
        key=lambda f: f['total_last_7_days'],
        reverse=True,
    )[:5]

    low_stock_recommendations = []
    for f in forecasts:
        product = f['product']
        if product.available_quantity <= 5 or (
            f['predicted_weekly_demand'] > 0
            and product.available_quantity < f['predicted_weekly_demand']
        ):
            low_stock_recommendations.append(f)

    return {
        'forecasts': forecasts,
        'most_demanded': most_demanded,
        'low_stock_recommendations': low_stock_recommendations,
    }

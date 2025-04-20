from datetime import datetime, timedelta, date


def today_or_yesterday_date(day):
    if day == "t":
        date_for_scraping = datetime.today().strftime("%Y%m%d")
        date_for_storing = datetime.today().strftime("%Y-%m-%d")
        return date_for_scraping, date_for_storing
    elif day == "y":
        yesterday = datetime.today() - timedelta(days=1)
        date_for_scraping = yesterday.strftime("%Y%m%d")
        date_for_storing = yesterday.strftime("%Y-%m-%d")
        return date_for_scraping, date_for_storing
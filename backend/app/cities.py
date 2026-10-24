"""Popular Indian cities used by the local MVP.

Stage 3 will refresh only this list on a schedule. Other places stay on demand.
"""

POPULAR_CITIES = [
    {
        "name": "New Delhi",
        "city": "New Delhi",
        "country": "India",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timezone": "Asia/Kolkata",
        "stations": [
            {"name": "ITO", "latitude": 28.6280, "longitude": 77.2410, "profile": "very_poor"},
            {"name": "Anand Vihar", "latitude": 28.6469, "longitude": 77.3153, "profile": "severe_pm"},
        ],
    },
    {
        "name": "Mumbai",
        "city": "Mumbai",
        "country": "India",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "timezone": "Asia/Kolkata",
        "stations": [
            {"name": "Bandra Kurla Complex", "latitude": 19.0660, "longitude": 72.8690, "profile": "moderate"},
            {"name": "Colaba", "latitude": 18.9067, "longitude": 72.8147, "profile": "satisfactory"},
        ],
    },
    {
        "name": "Bengaluru",
        "city": "Bengaluru",
        "country": "India",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timezone": "Asia/Kolkata",
        "stations": [
            {"name": "BTM Layout", "latitude": 12.9166, "longitude": 77.6101, "profile": "satisfactory"},
            {"name": "Peenya", "latitude": 13.0280, "longitude": 77.5190, "profile": "moderate"},
        ],
    },
    {
        "name": "Kolkata",
        "city": "Kolkata",
        "country": "India",
        "latitude": 22.5726,
        "longitude": 88.3639,
        "timezone": "Asia/Kolkata",
        "stations": [
            {"name": "Victoria Memorial", "latitude": 22.5448, "longitude": 88.3426, "profile": "poor"},
            {"name": "Rabindra Bharati", "latitude": 22.6270, "longitude": 88.3780, "profile": "poor"},
        ],
    },
    {
        "name": "Chennai",
        "city": "Chennai",
        "country": "India",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "timezone": "Asia/Kolkata",
        "stations": [
            {"name": "Alandur", "latitude": 13.0040, "longitude": 80.2010, "profile": "moderate"},
            {"name": "Manali", "latitude": 13.1630, "longitude": 80.2570, "profile": "poor"},
        ],
    },
    {
        "name": "Hyderabad",
        "city": "Hyderabad",
        "country": "India",
        "latitude": 17.3850,
        "longitude": 78.4867,
        "timezone": "Asia/Kolkata",
        "stations": [
            {"name": "Sanathnagar", "latitude": 17.4560, "longitude": 78.4430, "profile": "moderate"},
            {"name": "Zoo Park", "latitude": 17.3500, "longitude": 78.4510, "profile": "satisfactory"},
        ],
    },
    {
        "name": "Pune",
        "city": "Pune",
        "country": "India",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "timezone": "Asia/Kolkata",
        "stations": [
            {"name": "Karve Road", "latitude": 18.5074, "longitude": 73.8077, "profile": "satisfactory"},
            {
                "name": "School Campus",
                "latitude": 18.5310,
                "longitude": 73.8440,
                "profile": "partial_no_pm",
            },
        ],
    },
    {
        "name": "Ahmedabad",
        "city": "Ahmedabad",
        "country": "India",
        "latitude": 23.0225,
        "longitude": 72.5714,
        "timezone": "Asia/Kolkata",
        "stations": [
            {"name": "Maninagar", "latitude": 22.9960, "longitude": 72.6030, "profile": "poor"},
            {"name": "Chandkheda", "latitude": 23.1100, "longitude": 72.5800, "profile": "moderate"},
        ],
    },
]

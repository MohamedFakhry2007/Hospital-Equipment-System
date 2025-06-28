
from app import create_app, db
from app.services.ocm_service import OCMService

app = create_app()

with app.app_context():
    print("Fetching all OCM equipment directly from OCMService...")
    # Call the service to get the first page of data
    paginated_data = OCMService.get_all_equipment(page=1, per_page=20)
    
    total_records = paginated_data.get('total', 0)
    items = paginated_data.get('items', [])
    
    print(f"Total records found by OCMService: {total_records}")
    
    if items:
        print(f"Successfully fetched {len(items)} items for the first page.")
        print("First item details:")
        print(items[0])
    else:
        print("No items were returned by the service for the first page.")

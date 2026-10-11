# Integration Development Guide

This guide explains how to create new integrations for external services.

## 📋 Integration Checklist

Before creating a new integration, ensure:

- [ ] The service has a public API
- [ ] You have API access/credentials
- [ ] You understand the data model
- [ ] You've identified what data to sync
- [ ] You've planned the database schema
- [ ] You've registered the related account under `accounts/{platform}/{purpose}/{account-name}/`

## 🏗️ Integration Structure

Each integration should follow this structure:

```text
integrations/
└── service_name/
    └── README.md              # Integration-specific documentation

infra/scripts/sync/
└── service_sync.py            # Reusable sync logic, when needed
```

For platform accounts, keep the account identity separate from reusable
integration code:

```text
accounts/{platform}/{purpose}/{account-name}/  # account metadata and workflows
integrations/{platform}/                  # integration documentation
infra/scripts/sync/{service}.py                # reusable sync implementation
infra/mcp-server/                              # shared Solo Empire MCP tools
```

Account credentials remain outside the repository. The account README and
metadata may reference environment-variable or credential-store names, but
must never contain their values.

## 🔧 Step-by-Step Guide

### Step 1: Create Integration Documentation

```bash
mkdir -p integrations/service_name
cd integrations/service_name
```

### Step 2: Define Database Schema

Add tables through the database migration/schema workflow under
the operating hub:

```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS service_data (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        -- Add your fields here
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
```

### Step 3: Create Requirements File

```txt
# Keep dependency declarations with the implementation that uses them.
api-client-library==1.0.0
requests==2.31.0
```

### Step 4: Create Setup Script

Template for `setup_service.py`:

```python
#!/usr/bin/env python3
"""
Service Integration Setup
"""

import os
import sys
from pathlib import Path

CREDENTIALS_DIR = Path.home() / ".config" / "solo-empire" / "integrations" / "service_name"

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import service_client
        return True
    except ImportError:
        return False

def setup_credentials():
    """Guide user through credential setup"""
    print("🔑 Setting up credentials...")
    # Add your setup instructions here
    pass

def test_connection():
    """Test the API connection"""
    print("🧪 Testing connection...")
    # Add your test logic here
    pass

def main():
    print("🚀 Service Integration Setup")
    
    if not check_dependencies():
        print("❌ Dependencies not installed")
        sys.exit(1)
    
    setup_credentials()
    test_connection()
    
    print("✅ Setup complete!")

if __name__ == "__main__":
    main()
```

### Step 5: Create Sync Script

Template for `service_sync.py`:

```python
#!/usr/bin/env python3
"""
Service Data Sync
"""

import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ["OPERATIONAL_DB_PATH"])

def fetch_data_from_api():
    """Fetch data from external API"""
    # Add your API call logic here
    return []

def transform_data(api_data):
    """Transform API data to database format"""
    transformed = []
    for item in api_data:
        transformed.append({
            'id': item['id'],
            'source': 'service_name',
            # Map other fields
        })
    return transformed

def sync_data():
    """Sync data to database"""
    print("📊 Syncing data...")
    
    # Fetch from API
    api_data = fetch_data_from_api()
    
    # Transform
    db_data = transform_data(api_data)
    
    # Save to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for item in db_data:
        cursor.execute("""
            INSERT OR REPLACE INTO service_data
            (id, source, ...)
            VALUES (?, ?, ...)
        """, (item['id'], item['source'], ...))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Synced {len(db_data)} items")
    return len(db_data)

if __name__ == "__main__":
    sync_data()
```

### Step 6: Update Master Sync Script

Add your integration to `scripts/sync_all_integrations.py`:

```python
def sync_service_name():
    """Sync Service Name data"""
    print("\n" + "="*70)
    print("🔧 Syncing Service Name...")
    print("="*70)
    
    try:
        from service_name.service_sync import sync_data
        count = sync_data()
        return {'status': 'success', 'synced': count}
    except ImportError:
        print("⚠️  Service Name integration not set up")
        return {'status': 'not_configured'}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {'status': 'error', 'error': str(e)}

# Add to main() function:
if args.all or args.service_name:
    results['service_name'] = sync_service_name()
```

### Step 7: Update Documentation

1. Update `integrations/README.md` with your integration
2. Create `integrations/service_name/README.md` with specific docs
3. Update the related account record under `accounts/` if the integration uses
   a platform account
4. Update main `README.md` and relevant dashboard/source-of-truth docs if needed

### Step 8: Test Everything

```bash
# Test setup (use the implementation's actual path)
python3 path/to/setup_service.py

# Test sync
python3 infra/scripts/sync/service_sync.py

# Test master sync
python3 infra/scripts/sync/sync_all_integrations.py --service_name

# Query data
sqlite3 <operational-db> "SELECT * FROM service_data LIMIT 5;"
```

## 🔐 Security Best Practices

1. **Never commit credentials**
   - Add to `.gitignore`
   - Use environment variables
   - Store in `~/.config/solo-empire/integrations/`

2. **Use OAuth when possible**
   - More secure than API keys
   - Can be revoked
   - Limited scope

3. **Encrypt sensitive data**
   - Use keyring for credentials
   - Encrypt tokens at rest

4. **Rate limiting**
   - Respect API rate limits
   - Implement exponential backoff
   - Cache responses when possible

## 📊 Data Transformation Tips

1. **Normalize dates**
   - Convert all dates to ISO 8601 format
   - Store in UTC
   - Handle timezone conversions

2. **Handle missing data**
   - Use NULL for missing values
   - Provide sensible defaults
   - Log warnings for unexpected data

3. **Deduplication**
   - Use unique IDs from source
   - Implement INSERT OR REPLACE
   - Track sync timestamps

4. **Data validation**
   - Validate required fields
   - Check data types
   - Handle edge cases

## 🧪 Testing Checklist

- [ ] Setup script works from scratch
- [ ] Credentials are properly stored
- [ ] API connection works
- [ ] Data is fetched correctly
- [ ] Data is transformed correctly
- [ ] Data is saved to database
- [ ] Master sync includes new integration
- [ ] Documentation is complete
- [ ] Error handling works
- [ ] Rate limiting is implemented

## 📝 Example: Todoist Integration

Here's a complete example structure:

```python
# infra/scripts/sync/service_sync.py

import requests
import sqlite3
from pathlib import Path

TODOIST_API = "https://api.todoist.com/rest/v2/tasks"
TOKEN_FILE = Path.home() / ".config/solo-empire/integrations/todoist/token.json"

def fetch_tasks():
    """Fetch tasks from Todoist API"""
    with open(TOKEN_FILE) as f:
        token = json.load(f)['token']
    
    response = requests.get(
        TODOIST_API,
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()

def transform_task(task):
    """Transform Todoist task to database format"""
    return {
        'id': task['id'],
        'source': 'todoist',
        'title': task['content'],
        'description': task.get('description', ''),
        'due_date': task.get('due', {}).get('date'),
        'priority': task.get('priority', 3),
        'status': 'completed' if task.get('is_completed') else 'pending',
        'project': task.get('project_id'),
        'tags': json.dumps(task.get('labels', [])),
        'url': task.get('url')
    }

def sync_todoist_tasks():
    """Sync all tasks from Todoist"""
    tasks = fetch_tasks()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for task in tasks:
        data = transform_task(task)
        cursor.execute("""
            INSERT OR REPLACE INTO external_tasks
            (id, source, title, description, due_date, priority, 
             status, project, tags, url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['id'], data['source'], data['title'], data['description'],
            data['due_date'], data['priority'], data['status'], data['project'],
            data['tags'], data['url'], datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    return len(tasks)
```

## 🚀 Next Steps

After creating your integration:

1. Commit your code
2. Update documentation
3. Test with real data
4. Set up automation (cron/systemd)
5. Monitor for errors
6. Iterate based on usage

## 📚 Resources

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Python SQLite Tutorial](https://docs.python.org/3/library/sqlite3.html)
- [API Design Best Practices](https://restfulapi.net/)
- [OAuth 2.0 Simplified](https://aaronparecki.com/oauth-2-simplified/)

## 🤝 Need Help?

Check existing integrations for examples:
- Google Calendar: `integrations/google/calendar_sync.py`
- More coming soon...

---

Happy integrating! 🎉

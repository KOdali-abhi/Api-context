# API Context Memory System

A streamlined library for recording, analyzing, and maintaining context across API interactions.

## Overview

The API Context Memory System provides an intuitive interface for managing API interactions. It helps you maintain context across multiple API calls, debug issues, and optimize your API usage patterns.

## Installation

```bash
pip install api-context-memory
```

## Quick Start

```python
from api_context_memory import APIContextMemory

# Initialize the system
api_memory = APIContextMemory()

# Create a tab for organizing API contexts
tab = api_memory.create_tab(metadata={"name": "My API"})
tab_id = tab["tab_id"]
session_id = tab["session_id"]

# Create an API client
client = api_memory.create_client()

# Make API requests with context tracking
response = client.get(session_id, "https://api.example.com/data")

# Get recorded interactions
interactions = api_memory.get_interactions(tab_id)
print(f"Total interactions: {len(interactions)}")

# Find errors
errors = api_memory.find_errors(tab_id)
print(f"Total errors: {len(errors)}")
```

## Key Features

- **Context Maintenance**: Preserves state and context across multiple API calls
- **Tab-Based Organization**: Manages different API contexts with a familiar tab interface
- **Memory Transfer**: Allows sharing context between different tabs/sessions
- **Error Tracking**: Identifies and categorizes errors for easier debugging
- **Simple API**: Intuitive interface that follows expected patterns

## Core Concepts

### Tabs

Tabs help you organize different API contexts. Each tab has an associated session for storing state.

```python
# Create a tab
tab = api_memory.create_tab(metadata={"name": "Payment API"})
tab_id = tab["tab_id"]
session_id = tab["session_id"]

# Get a tab
tab = api_memory.get_tab(tab_id)

# Get the active tab
active_tab = api_memory.get_active_tab()

# Switch tabs
api_memory.switch_tab(tab_id)

# List all tabs
tabs = api_memory.list_tabs()

# Close a tab
api_memory.close_tab(tab_id)
```

### Sessions

Sessions store state and context for API interactions.

```python
# Get a session
session = api_memory.get_session(session_id)

# Store data in a session
session.set("context", {"user_id": "123"})

# Get data from a session
user_id = session.get("context")["user_id"]

# Save session changes
api_memory.save_session(session)
```

### API Client

The API client makes requests and automatically records interactions.

```python
# Create a client
client = api_memory.create_client()

# Make requests
response = client.get(session_id, "https://api.example.com/users")
response = client.post(session_id, "https://api.example.com/users", json={"name": "John"})
response = client.put(session_id, "https://api.example.com/users/123", json={"name": "John"})
response = client.delete(session_id, "https://api.example.com/users/123")
response = client.patch(session_id, "https://api.example.com/users/123", json={"name": "John"})

# Custom request method
response = client.request(session_id, "OPTIONS", "https://api.example.com/users")
```

### Interactions

Interactions record API requests and responses for analysis and debugging.

```python
# Get all interactions for a tab
interactions = api_memory.get_interactions(tab_id)

# Find error interactions
errors = api_memory.find_errors(tab_id)

# Manually record an interaction
interaction_id = api_memory.record_interaction(
    session_id,
    {"method": "GET", "url": "https://api.example.com/data"},
    {"status_code": 200, "text": '{"success": true}'}
)
```

### Memory Transfer

Transfer context between tabs to maintain state across different API contexts.

```python
# Transfer all memory from one tab to another
api_memory.transfer_memory(source_tab_id, target_tab_id)

# Transfer specific keys
api_memory.transfer_memory(source_tab_id, target_tab_id, keys=["auth_token", "user_id"])
```

### Reconnection Handling

Handle API reconnection scenarios with automatic context transfer.

```python
# Handle reconnection
response, new_tab_id = api_memory.handle_restart(tab_id, "https://api.example.com/data")
```

## Storage Options

The API Context Memory System supports different storage options:

```python
# In-memory storage (default)
api_memory = APIContextMemory()

# File-based storage
api_memory = APIContextMemory(storage_type="file", file_path="./api_data.json")
```

## Complete Example

```python
from api_context_memory import APIContextMemory

def main():
    # Initialize with file storage
    api_memory = APIContextMemory(storage_type="file", file_path="./api_data.json")
    
    # Create a tab
    tab = api_memory.create_tab(metadata={"name": "Weather API"})
    tab_id = tab["tab_id"]
    session_id = tab["session_id"]
    
    print(f"Created tab with ID: {tab_id}")
    print(f"Session ID: {session_id}")
    
    # Create an API client
    client = api_memory.create_client()
    
    # Store context in the session
    session = api_memory.get_session(session_id)
    session.set("location", "New York")
    api_memory.save_session(session)
    
    # Make API requests
    try:
        # Get weather data
        response = client.get(
            session_id,
            "https://api.example.com/weather",
            params={"location": session.get("location")}
        )
        print(f"Weather API Status: {response.status_code}")
        
        # Process response
        if response.status_code == 200:
            weather_data = response.json()
            print(f"Temperature: {weather_data.get('temperature')}°C")
            print(f"Conditions: {weather_data.get('conditions')}")
            
            # Store the result in the session
            session.set("last_weather", weather_data)
            api_memory.save_session(session)
    
    except Exception as e:
        print(f"Error getting weather data: {str(e)}")
    
    # Get interactions
    interactions = api_memory.get_interactions(tab_id)
    print(f"\nTotal interactions: {len(interactions)}")
    
    # Print interaction details
    for i, interaction in enumerate(interactions):
        print(f"\nInteraction {i+1}:")
        print(f"  Method: {interaction['request']['method']}")
        print(f"  URL: {interaction['request']['url']}")
        print(f"  Status: {interaction['response'].get('status_code', 'N/A')}")
        print(f"  Timestamp: {interaction['timestamp']}")
    
    # Find errors
    errors = api_memory.find_errors(tab_id)
    print(f"\nTotal errors: {len(errors)}")

if __name__ == "__main__":
    main()
```

## API Reference

### APIContextMemory

```python
APIContextMemory(storage_type="memory", file_path=None)
```

Main class for the API Context Memory System.

**Parameters:**
- `storage_type` (str): Type of storage ("memory" or "file")
- `file_path` (str, optional): Path to file storage (required if storage_type is "file")

**Methods:**

#### Tab Management

```python
create_tab(tab_id=None, metadata=None)
```
Create a new tab with an associated session.

```python
get_tab(tab_id)
```
Get tab information.

```python
get_active_tab()
```
Get the active tab.

```python
switch_tab(tab_id)
```
Switch the active tab.

```python
list_tabs()
```
List all tabs.

```python
close_tab(tab_id)
```
Close a tab.

#### Session Management

```python
get_session(session_id)
```
Get a session.

```python
save_session(session)
```
Save a session.

```python
transfer_memory(source_tab_id, target_tab_id, keys=None)
```
Transfer memory (context) from one tab to another.

#### Interaction Management

```python
record_interaction(session_id, request_data, response_data)
```
Record an API interaction.

```python
get_interactions(tab_id=None)
```
Get recorded interactions for a tab.

```python
find_errors(tab_id=None)
```
Find error interactions for a tab.

#### Client Management

```python
create_client()
```
Create an API client.

#### Reconnection Handling

```python
handle_restart(tab_id, url, method="GET", **kwargs)
```
Handle API reconnection by creating a new tab and transferring memory.

### Session

```python
Session(session_id, data=None)
```

Represents an API session with state.

**Methods:**

```python
get(key, default=None)
```
Get a value from the session data.

```python
set(key, value)
```
Set a value in the session data.

```python
delete(key)
```
Delete a value from the session data.

```python
clear()
```
Clear all session data.

```python
to_dict()
```
Convert session to dictionary.

### APIClient

```python
APIClient(api_memory)
```

API client with context recording.

**Methods:**

```python
request(session_id, method, url, **kwargs)
```
Make an API request and record the interaction.

```python
get(session_id, url, **kwargs)
```
Make a GET request.

```python
post(session_id, url, **kwargs)
```
Make a POST request.

```python
put(session_id, url, **kwargs)
```
Make a PUT request.

```python
delete(session_id, url, **kwargs)
```
Make a DELETE request.

```python
patch(session_id, url, **kwargs)
```
Make a PATCH request.

## Troubleshooting

### Common Issues

1. **Missing Context**: If context appears to be lost between calls, ensure you're using the same session ID and that you've saved the session after making changes.

   ```python
   session = api_memory.get_session(session_id)
   session.set("key", "value")
   api_memory.save_session(session)  # Don't forget this step!
   ```

2. **File Storage Issues**: When using file storage, ensure the directory exists and is writable.

   ```python
   import os
   os.makedirs(os.path.dirname(os.path.abspath("./api_data.json")), exist_ok=True)
   api_memory = APIContextMemory(storage_type="file", file_path="./api_data.json")
   ```

3. **Request Errors**: If requests are failing, check the error interactions for details.

   ```python
   errors = api_memory.find_errors(tab_id)
   for error in errors:
       print(f"Error: {error['response'].get('error')}")
       print(f"Error Type: {error['response'].get('error_type')}")
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

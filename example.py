"""
Example script demonstrating the API Context Memory System
"""
import json
from api_context_memory import APIContextMemory

def print_separator(title):
    """Print a separator with a title."""
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60 + "\n")

def main():
    # Initialize the API Context Memory System
    print_separator("INITIALIZING API CONTEXT MEMORY")
    api_memory = APIContextMemory()
    print("API Context Memory initialized successfully")
    
    # Create a tab for organizing API contexts
    print_separator("CREATING API CONTEXT TAB")
    tab = api_memory.create_tab(metadata={"name": "JSONPlaceholder API"})
    tab_id = tab["tab_id"]
    session_id = tab["session_id"]
    
    print(f"Created tab with ID: {tab_id}")
    print(f"Session ID: {session_id}")
    print(f"Tab metadata: {tab['metadata']}")
    
    # Create an API client
    print_separator("CREATING API CLIENT")
    client = api_memory.create_client()
    print("API client created successfully")
    
    # Make API requests with context tracking
    print_separator("MAKING API REQUESTS")
    
    # Example 1: Get posts
    print("\n--- Example 1: Get Posts ---")
    try:
        posts_response = client.get(
            session_id,
            "https://jsonplaceholder.typicode.com/posts?_limit=3"
        )
        print(f"GET posts status: {posts_response.status_code}")
        posts = posts_response.json()
        print(f"Retrieved {len(posts)} posts")
        print(f"First post title: {posts[0]['title']}")
    except Exception as e:
        print(f"Error getting posts: {str(e)}")
    
    # Example 2: Get a specific post
    print("\n--- Example 2: Get Specific Post ---")
    try:
        post_response = client.get(
            session_id,
            "https://jsonplaceholder.typicode.com/posts/1"
        )
        print(f"GET post status: {post_response.status_code}")
        post = post_response.json()
        print(f"Retrieved post with title: {post['title']}")
        
        # Store post ID in session for later use
        session = api_memory.get_session(session_id)
        session.set("last_post_id", post['id'])
        api_memory.save_session(session)
        print(f"Stored post ID {post['id']} in session")
    except Exception as e:
        print(f"Error getting post: {str(e)}")
    
    # Example 3: Create a new post
    print("\n--- Example 3: Create New Post ---")
    try:
        create_response = client.post(
            session_id,
            "https://jsonplaceholder.typicode.com/posts",
            json={
                "title": "New Post",
                "body": "This is a new post created with API Context Memory",
                "userId": 1
            }
        )
        print(f"POST create status: {create_response.status_code}")
        new_post = create_response.json()
        print(f"Created post with ID: {new_post['id']}")
    except Exception as e:
        print(f"Error creating post: {str(e)}")
    
    # Example 4: Try to access a non-existent endpoint (to generate an error)
    print("\n--- Example 4: Access Invalid Endpoint ---")
    try:
        error_response = client.get(
            session_id,
            "https://jsonplaceholder.typicode.com/nonexistent"
        )
        print(f"GET error status: {error_response.status_code}")
    except Exception as e:
        print(f"Error accessing non-existent endpoint: {str(e)}")
    
    # Retrieve and analyze recorded interactions
    print_separator("RETRIEVING RECORDED INTERACTIONS")
    
    # Get all recorded interactions
    interactions = api_memory.get_interactions(tab_id)
    print(f"Total interactions recorded: {len(interactions)}")
    
    # Print a summary of each interaction
    for i, interaction in enumerate(interactions):
        request = interaction["request"]
        response = interaction["response"]
        print(f"\nInteraction {i+1}:")
        print(f"  Method: {request['method']}")
        print(f"  URL: {request['url']}")
        print(f"  Status: {response.get('status_code', 'N/A')}")
        print(f"  Timestamp: {interaction['timestamp']}")
    
    # Find errors
    print_separator("FINDING ERRORS")
    
    # Find errors
    errors = api_memory.find_errors(tab_id)
    print(f"Total errors found: {len(errors)}")
    
    # Print details of each error
    for i, error in enumerate(errors):
        request = error["request"]
        response = error["response"]
        print(f"\nError {i+1}:")
        print(f"  Method: {request['method']}")
        print(f"  URL: {request['url']}")
        print(f"  Status: {response.get('status_code', 'N/A')}")
        print(f"  Timestamp: {error['timestamp']}")
    
    # Demonstrate context maintenance
    print_separator("DEMONSTRATING CONTEXT MAINTENANCE")
    
    # Get the stored post ID from the session
    session = api_memory.get_session(session_id)
    last_post_id = session.get("last_post_id")
    print(f"Retrieved post ID {last_post_id} from session")
    
    # Use the stored post ID to get comments
    print("\n--- Using Stored Context ---")
    try:
        comments_response = client.get(
            session_id,
            f"https://jsonplaceholder.typicode.com/posts/{last_post_id}/comments"
        )
        print(f"GET comments status: {comments_response.status_code}")
        comments = comments_response.json()
        print(f"Retrieved {len(comments)} comments for post {last_post_id}")
        print(f"First comment by: {comments[0]['name']}")
    except Exception as e:
        print(f"Error getting comments: {str(e)}")
    
    # Demonstrate tab management
    print_separator("DEMONSTRATING TAB MANAGEMENT")
    
    # Create a second tab
    second_tab = api_memory.create_tab(metadata={"name": "Users API"})
    second_tab_id = second_tab["tab_id"]
    second_session_id = second_tab["session_id"]
    
    print(f"Created second tab with ID: {second_tab_id}")
    print(f"Second session ID: {second_session_id}")
    
    # Make a request with the second tab
    try:
        users_response = client.get(
            second_session_id,
            "https://jsonplaceholder.typicode.com/users?_limit=2"
        )
        print(f"GET users status: {users_response.status_code}")
        users = users_response.json()
        print(f"Retrieved {len(users)} users")
        print(f"First user name: {users[0]['name']}")
        
        # Store user ID in session
        second_session = api_memory.get_session(second_session_id)
        second_session.set("user_id", users[0]['id'])
        api_memory.save_session(second_session)
        print(f"Stored user ID {users[0]['id']} in second session")
    except Exception as e:
        print(f"Error getting users: {str(e)}")
    
    # List all tabs
    tabs = api_memory.list_tabs()
    print(f"\nTotal tabs: {len(tabs)}")
    for i, tab_info in enumerate(tabs):
        print(f"Tab {i+1}: {tab_info['tab_id']} - {tab_info['metadata'].get('name', 'Unnamed')}")
    
    # Switch between tabs
    print("\n--- Switching Tabs ---")
    api_memory.switch_tab(tab_id)
    active_tab = api_memory.get_active_tab()
    print(f"Active tab: {active_tab['tab_id']} - {active_tab['metadata'].get('name', 'Unnamed')}")
    
    api_memory.switch_tab(second_tab_id)
    active_tab = api_memory.get_active_tab()
    print(f"Active tab: {active_tab['tab_id']} - {active_tab['metadata'].get('name', 'Unnamed')}")
    
    # Demonstrate memory transfer
    print_separator("DEMONSTRATING MEMORY TRANSFER")
    
    # Transfer memory from second tab to first tab
    api_memory.transfer_memory(second_tab_id, tab_id, keys=["user_id"])
    
    # Verify transfer
    session = api_memory.get_session(session_id)
    transferred_user_id = session.get("user_id")
    print(f"Transferred user ID {transferred_user_id} from second tab to first tab")
    
    # Use the transferred user ID
    try:
        user_posts_response = client.get(
            session_id,
            f"https://jsonplaceholder.typicode.com/users/{transferred_user_id}/posts?_limit=2"
        )
        print(f"GET user posts status: {user_posts_response.status_code}")
        user_posts = user_posts_response.json()
        print(f"Retrieved {len(user_posts)} posts for user {transferred_user_id}")
        print(f"First post title: {user_posts[0]['title']}")
    except Exception as e:
        print(f"Error getting user posts: {str(e)}")
    
    # Demonstrate reconnection handling
    print_separator("DEMONSTRATING RECONNECTION HANDLING")
    
    # Handle reconnection
    try:
        print("Simulating API reconnection...")
        response, new_tab_id = api_memory.handle_restart(
            tab_id,
            "https://jsonplaceholder.typicode.com/posts?_limit=1"
        )
        
        print(f"Reconnection successful with new tab ID: {new_tab_id}")
        print(f"Response status: {response.status_code}")
        
        # Verify context was transferred
        new_session = api_memory.get_session(api_memory.get_tab(new_tab_id)["session_id"])
        print(f"Transferred user ID: {new_session.get('user_id')}")
        print(f"Transferred post ID: {new_session.get('last_post_id')}")
    except Exception as e:
        print(f"Error during reconnection: {str(e)}")
    
    print_separator("EXAMPLE COMPLETED")
    print("The API Context Memory System has successfully:")
    print("1. Created and managed tabs for different API contexts")
    print("2. Made API requests and recorded interactions")
    print("3. Maintained context across requests")
    print("4. Identified errors")
    print("5. Transferred memory between tabs")
    print("6. Handled reconnection scenarios")
    print("\nThis example demonstrates the core functionality of the system.")

if __name__ == "__main__":
    main()

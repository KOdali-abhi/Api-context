"""
Simple test script for the API Context Memory System
"""
import unittest
from api_context_memory import APIContextMemory

class APIContextMemoryTest(unittest.TestCase):
    def setUp(self):
        # Initialize the API Context Memory System
        self.api_memory = APIContextMemory()
        
        # Create a tab
        tab = self.api_memory.create_tab(metadata={"name": "Test Tab"})
        self.tab_id = tab["tab_id"]
        self.session_id = tab["session_id"]
        
        # Create an API client
        self.client = self.api_memory.create_client()
    
    def test_basic_functionality(self):
        """Test basic functionality of the API Context Memory System."""
        # Make a request
        response = self.client.get(
            self.session_id,
            "https://jsonplaceholder.typicode.com/posts/1"
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        post = response.json()
        self.assertEqual(post["id"], 1)
        
        # Check that the interaction was recorded
        interactions = self.api_memory.get_interactions(self.tab_id)
        self.assertEqual(len(interactions), 1)
        
        # Verify interaction details
        interaction = interactions[0]
        self.assertEqual(interaction["request"]["method"], "GET")
        self.assertEqual(interaction["request"]["url"], "https://jsonplaceholder.typicode.com/posts/1")
        self.assertEqual(interaction["response"]["status_code"], 200)
    
    def test_session_management(self):
        """Test session management in the API Context Memory System."""
        # Get the session
        session = self.api_memory.get_session(self.session_id)
        
        # Set some data
        session.set("test_key", "test_value")
        session.set("user_id", 123)
        
        # Save the session
        self.api_memory.save_session(session)
        
        # Get the session again
        session = self.api_memory.get_session(self.session_id)
        
        # Verify the data was saved
        self.assertEqual(session.get("test_key"), "test_value")
        self.assertEqual(session.get("user_id"), 123)
    
    def test_tab_management(self):
        """Test tab management in the API Context Memory System."""
        # Create a second tab
        second_tab = self.api_memory.create_tab(metadata={"name": "Second Tab"})
        second_tab_id = second_tab["tab_id"]
        
        # List tabs
        tabs = self.api_memory.list_tabs()
        self.assertEqual(len(tabs), 2)
        
        # Switch tabs
        self.api_memory.switch_tab(second_tab_id)
        active_tab = self.api_memory.get_active_tab()
        self.assertEqual(active_tab["tab_id"], second_tab_id)
        
        # Close the second tab
        self.api_memory.close_tab(second_tab_id)
        tabs = self.api_memory.list_tabs()
        self.assertEqual(len(tabs), 1)
    
    def test_memory_transfer(self):
        """Test memory transfer in the API Context Memory System."""
        # Create a second tab
        second_tab = self.api_memory.create_tab(metadata={"name": "Second Tab"})
        second_tab_id = second_tab["tab_id"]
        second_session_id = second_tab["session_id"]
        
        # Set data in the first session
        session = self.api_memory.get_session(self.session_id)
        session.set("user_id", 123)
        session.set("auth_token", "abc123")
        self.api_memory.save_session(session)
        
        # Transfer memory
        self.api_memory.transfer_memory(self.tab_id, second_tab_id)
        
        # Verify data was transferred
        second_session = self.api_memory.get_session(second_session_id)
        self.assertEqual(second_session.get("user_id"), 123)
        self.assertEqual(second_session.get("auth_token"), "abc123")
        
        # Transfer specific keys
        session.set("extra_data", "not_transferred")
        self.api_memory.save_session(session)
        
        # Clear second session
        second_session.clear()
        self.api_memory.save_session(second_session)
        
        # Transfer only specific keys
        self.api_memory.transfer_memory(self.tab_id, second_tab_id, keys=["user_id"])
        
        # Verify only specified data was transferred
        second_session = self.api_memory.get_session(second_session_id)
        self.assertEqual(second_session.get("user_id"), 123)
        self.assertIsNone(second_session.get("auth_token"))
        self.assertIsNone(second_session.get("extra_data"))
    
    def test_error_handling(self):
        """Test error handling in the API Context Memory System."""
        # Make a request to a non-existent endpoint
        response = self.client.get(
            self.session_id,
            "https://jsonplaceholder.typicode.com/nonexistent"
        )
        
        # Verify response
        self.assertEqual(response.status_code, 404)
        
        # Check that the error was recorded
        errors = self.api_memory.find_errors(self.tab_id)
        self.assertEqual(len(errors), 1)
        
        # Verify error details
        error = errors[0]
        self.assertEqual(error["request"]["method"], "GET")
        self.assertEqual(error["request"]["url"], "https://jsonplaceholder.typicode.com/nonexistent")
        self.assertEqual(error["response"]["status_code"], 404)
    
    def test_reconnection(self):
        """Test reconnection handling in the API Context Memory System."""
        # Set some data in the session
        session = self.api_memory.get_session(self.session_id)
        session.set("user_id", 123)
        self.api_memory.save_session(session)
        
        # Handle restart
        response, new_tab_id = self.api_memory.handle_restart(
            self.tab_id,
            "https://jsonplaceholder.typicode.com/posts/1"
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Verify new tab was created
        new_tab = self.api_memory.get_tab(new_tab_id)
        self.assertIsNotNone(new_tab)
        
        # Verify memory was transferred
        new_session = self.api_memory.get_session(new_tab["session_id"])
        self.assertEqual(new_session.get("user_id"), 123)

if __name__ == "__main__":
    unittest.main()

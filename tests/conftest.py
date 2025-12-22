# tests/conftest.py
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(autouse=True)
def mock_settings():
    """Automatically mock settings for all tests."""
    with patch('tradedesk.client.settings') as mock_client_settings, \
         patch('tradedesk.strategy.settings') as mock_strategy_settings, \
         patch('tradedesk.runner.settings') as mock_runner_settings:
        
        # Configure all mocked settings
        for mock_setting in [mock_client_settings, mock_strategy_settings, mock_runner_settings]:
            mock_setting.ig_api_key = "test-api-key"
            mock_setting.ig_username = "test-username"
            mock_setting.ig_password = "test-password"
            mock_setting.environment = "DEMO"
            mock_setting.log_level = "INFO"
            mock_setting.validate = MagicMock()
        
        yield mock_client_settings

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

class AsyncContextManagerMock:
    """Helper class to mock async context managers."""
    def __init__(self, return_value=None):
        self.return_value = return_value or MagicMock()
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, *args):
        return None

@pytest.fixture
def mock_http_response():
    """Create a mock HTTP response."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.headers = {"CST": "CST_TOKEN", "X-SECURITY-TOKEN": "XST_TOKEN"}
    mock_response.json = AsyncMock(return_value={
        "accountId": "ABC123",
        "clientId": "CLIENT123",
        "currentAccountId": "ACC456",
        "cst": "CST_TOKEN",
        "x-security-token": "XST_TOKEN"
    })
    mock_response.text = AsyncMock(return_value="")
    mock_response.raise_for_status = MagicMock()
    return mock_response

@pytest.fixture
def mock_aiohttp_session(mock_http_response):
    """Mock aiohttp ClientSession."""
    # Create the async context manager for responses
    response_context = AsyncContextManagerMock(mock_http_response)
    
    # Create mock session
    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=response_context)
    mock_session.request = MagicMock(return_value=response_context)
    mock_session.close = AsyncMock()
    mock_session.headers = {}  # Add headers attribute
    
    # Make session itself an async context manager
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    return mock_session

@pytest.fixture
def mock_lightstreamer():
    """Mock Lightstreamer client and subscription."""
    with patch('tradedesk.strategy.LightstreamerClient') as mock_ls_client_class, \
         patch('tradedesk.strategy.Subscription') as mock_subscription_class:
        
        # Create mock LightstreamerClient instance
        mock_ls_client = MagicMock()
        mock_ls_client.connectionDetails = MagicMock()
        mock_ls_client.connectionDetails.setUser = MagicMock()
        mock_ls_client.connectionDetails.setPassword = MagicMock()
        mock_ls_client.connect = MagicMock()
        mock_ls_client.subscribe = MagicMock()
        mock_ls_client.disconnect = MagicMock()
        mock_ls_client.addListener = MagicMock()
        
        mock_ls_client_class.return_value = mock_ls_client
        
        # Create mock Subscription instance
        mock_subscription = MagicMock()
        mock_subscription.addListener = MagicMock()
        mock_subscription_class.return_value = mock_subscription
        
        yield {
            'client': mock_ls_client,
            'subscription': mock_subscription,
            'client_class': mock_ls_client_class,
            'subscription_class': mock_subscription_class
        }
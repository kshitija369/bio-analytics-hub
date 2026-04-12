import pytest
import os
import requests
from unittest.mock import patch, MagicMock
from app.adapters.oura import OuraProvider
from datetime import datetime

# --- [AUTHENTICATION UNIT TESTS] ---

def test_oura_auth_header_formatting():
    """
    Verifies that the Bearer token is correctly formatted in headers.
    """
    test_pat = "  my_secret_token_123  "
    provider = OuraProvider(pat=test_pat)
    
    headers = provider._get_headers()
    
    # Should be stripped of whitespace
    assert headers['Authorization'] == "Bearer my_secret_token_123"
    assert headers['Accept'] == "application/json"
    assert "Witness-State-Monitor" in headers['User-Agent']

def test_oura_empty_token_behavior():
    """
    Ensures the provider identifies and handles missing tokens.
    """
    provider = OuraProvider(pat="")
    assert provider.pat == ""
    
    # Fetch should return empty list immediately without making a request
    with patch("requests.get") as mock_get:
        data = provider.fetch_data(datetime.now(), datetime.now())
        assert data == []
        assert not mock_get.called

def test_oura_auth_failure_handling():
    """
    Simulates a 401 Unauthorized response from Oura and 
    verifies the provider handles it gracefully.
    """
    provider = OuraProvider(pat="invalid_token")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"message":"Unauthorized"}'
    
    # Test both heartrate and daily loops
    with patch("requests.get", return_value=mock_resp):
        data = provider.fetch_data(datetime.now(), datetime.now())
        assert data == [] # Should still return empty list, not crash

def test_oura_environment_variable_loading(monkeypatch):
    """
    Verifies that OURA_PAT is correctly picked up from the environment.
    """
    monkeypatch.setenv("OURA_PAT", "env_token_456")
    provider = OuraProvider()
    assert provider.pat == "env_token_456"

def test_oura_successful_handshake():
    """
    Verifies the full request chain includes headers when SUCCESSful.
    """
    provider = OuraProvider(pat="good_token")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": []}
    
    with patch("requests.get", return_value=mock_resp) as mock_get:
        provider.fetch_data(datetime.now(), datetime.now())
        
        # Check that the FIRST call (heartrate) had the header
        args, kwargs = mock_get.call_args_list[0]
        assert "Authorization" in kwargs['headers']
        assert kwargs['headers']['Authorization'] == "Bearer good_token"

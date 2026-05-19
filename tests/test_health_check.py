"""Tests for the health_check module."""

import pytest
import sys
import os
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from health_check import health_handler


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_handler_success(self):
        """Test that health handler returns ok status."""
        mock_request = MagicMock()
        response = await health_handler(mock_request)

        # Check that response is a JSON response with status ok
        assert response.status == 200
        assert "status" in response.text or response.body is not None

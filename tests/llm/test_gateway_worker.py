import pytest
from unittest.mock import patch, MagicMock
from pxos.llm.gateway_worker import GatewayWorker
from pxos.hostcalls_llm import LlmRequest, LlmChunk
from pxos.llm.base_worker import LlmLimits
import requests

@pytest.fixture
def gateway_config():
    return {
        "url": "https://fake-gateway.com/stream",
        "headers": {"Authorization": "Bearer FAKE_KEY"},
        "timeout": 5
    }

@patch('requests.Session.post')
def test_gateway_worker_stream_success(mock_post, gateway_config):
    # Mock the SSE stream from the server
    mock_response = MagicMock()
    sse_data = [
        'data: {"delta": "Hello"}\n\n',
        'data: {"delta": ", "}\n\n',
        'data: {"delta": "world"}\n\n',
        'data: {"delta": "!", "done": true}\n\n',
        'data: [DONE]\n\n'
    ]
    mock_response.iter_lines.return_value = iter(sse_data)
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    worker = GatewayWorker(gateway_config)
    req = LlmRequest(model="test-model", prompt="hi")
    limits = LlmLimits(max_tokens=100)

    chunks = list(worker.stream(req, limits))

    # The [DONE] message is a sentinel and doesn't always produce a chunk.
    # The important part is that the last chunk has done=True.
    assert len(chunks) == 4
    assert chunks[0].text == "Hello"
    assert chunks[1].text == ", "
    assert chunks[2].text == "world"
    assert chunks[3].text == "!"
    assert chunks[3].done is True
    mock_post.assert_called_once()

@patch('requests.Session.post')
def test_gateway_worker_network_error(mock_post, gateway_config):
    # Mock a network error
    mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

    worker = GatewayWorker(gateway_config)
    req = LlmRequest(model="test-model", prompt="hi")
    limits = LlmLimits(max_tokens=100)

    chunks = list(worker.stream(req, limits))

    assert len(chunks) == 1
    assert "[gateway_error: Connection failed]" in chunks[0].text
    assert chunks[0].done is True
    mock_post.assert_called_once()

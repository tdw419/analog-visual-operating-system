from unittest.mock import patch
from pxos.llm.adapter import LlmAdapter
from pxos.hostcalls_llm import LlmRequest, LlmChunk

class DummyKeystore(dict): pass

@patch('pxos.llm.local_worker.LocalWorker.stream')
def test_model_policy_blocks_local(mock_local_stream):
    # The stream should not be called, but we mock it to prevent network errors
    mock_local_stream.return_value = iter([LlmChunk(text="allowed", done=True)])

    policy = {"llm_models_allow": ["pxos-*"], "llm_models_deny": ["pxos-bad*"], "max_prompts_per_min": 1000, "max_tokens_per_min": 100000}
    caps = {"max_tokens": 32, "net": False}
    adapter = LlmAdapter(policy, DummyKeystore(), caps)
    req = LlmRequest(model="pxos-bad-1", prompt="hi", max_tokens=16, meta={"identity":"t"})

    chunks = list(adapter.infer(req))

    # Verify that the stream was NOT called because the model was blocked
    mock_local_stream.assert_not_called()

    # Verify that the returned chunk contains the blocked message
    assert len(chunks) == 1
    assert "blocked" in chunks[0].text
    assert chunks[0].done is True

@patch('pxos.llm.gateway_worker.GatewayWorker.stream')
@patch('pxos.llm.local_worker.LocalWorker.stream')
def test_adapter_chooses_gateway(mock_local_stream, mock_gateway_stream):
    mock_gateway_stream.return_value = iter([LlmChunk(text="from gateway", done=True)])

    policy = {
        "trust_verdict": "trusted",
        "llm_gateway": "test-gateway",
        "max_prompts_per_min": 1000,
        "max_tokens_per_min": 100000,
        "llm_models_allow": ["*"] # Allow any model for this test
    }
    caps = {"max_tokens": 32, "net": True}
    keystore = {"api_key": "fake_key"}
    adapter = LlmAdapter(policy, keystore, caps)
    req = LlmRequest(model="some-model", prompt="hi")

    chunks = list(adapter.infer(req))

    # Verify that the gateway stream was called and the local one was not
    mock_gateway_stream.assert_called_once()
    mock_local_stream.assert_not_called()

    # Verify we got the chunk from the gateway
    assert len(chunks) == 1
    assert chunks[0].text == "from gateway"

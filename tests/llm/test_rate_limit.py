from unittest.mock import patch
from pxos.llm.adapter import LlmAdapter
from pxos.hostcalls_llm import LlmRequest, LlmChunk

class DummyKeystore(dict): pass

@patch('pxos.llm.local_worker.LocalWorker.stream')
def test_rate_limit(mock_stream):
    # The stream should be called once, then not again.
    mock_stream.return_value = iter([LlmChunk(text="allowed", done=True)])

    policy = {"max_prompts_per_min": 1, "max_tokens_per_min": 64, "llm_models_allow":["pxos-*"]}
    caps = {"max_tokens": 32, "net": False}
    adapter = LlmAdapter(policy, DummyKeystore(), caps)
    req = LlmRequest(model="pxos-mini-3b", prompt="hi", max_tokens=32, meta={"identity":"u1"})

    # First call should be allowed and call the stream
    list(adapter.infer(req))
    mock_stream.assert_called_once()

    # Immediate second call should be rate limited
    chunks = list(adapter.infer(req))

    # Verify that the stream was not called a second time
    mock_stream.assert_called_once()

    # Verify that the returned chunk contains the rate limited message
    assert len(chunks) == 1
    assert "rate limited" in chunks[0].text
    assert chunks[0].done is True

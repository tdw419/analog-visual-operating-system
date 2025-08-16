from unittest.mock import patch
from pxos.llm.adapter import LlmAdapter
from pxos.hostcalls_llm import LlmRequest, LlmChunk

class DummyKeystore(dict): pass

@patch('pxos.llm.local_worker.LocalWorker.stream')
def test_model_policy_blocks(mock_stream):
    # The stream should not be called, but we mock it to prevent network errors
    mock_stream.return_value = iter([LlmChunk(text="allowed", done=True)])

    policy = {"llm_models_allow": ["pxos-*"], "llm_models_deny": ["pxos-bad*"], "max_prompts_per_min": 1000, "max_tokens_per_min": 100000}
    caps = {"max_tokens": 32, "net": False}
    adapter = LlmAdapter(policy, DummyKeystore(), caps)
    req = LlmRequest(model="pxos-bad-1", prompt="hi", max_tokens=16, meta={"identity":"t"})

    chunks = list(adapter.infer(req))

    # Verify that the stream was NOT called because the model was blocked
    mock_stream.assert_not_called()

    # Verify that the returned chunk contains the blocked message
    assert len(chunks) == 1
    assert "blocked" in chunks[0].text
    assert chunks[0].done is True

import pytest

from tools_Houdini.Houdini_Agentic_Mode import skills_houdini, mcp_houdini


def test_llm_translate_intent_without_api_key(monkeypatch):
    monkeypatch.delenv('RAPTOR_MINI_API_KEY', raising=False)
    out = skills_houdini.interpret_request('add navy blue box with x:1 y:2 z:.42 position it 2 units above terrain')
    assert out['intent'] == 'llm_interpreted_command'
    assert out['tool'] == 'run_houdini_python'
    assert out['tool'] == 'run_houdini_python'


def test_add_navy_blue_box_with_llm(monkeypatch):
    def fake_llm(intent, context=None):
        assert 'navy blue box' in intent.lower()
        return "obj = hou.node('/obj'); # box creation placeholder"

    monkeypatch.setattr(skills_houdini, 'llm_translate_intent_to_houdini_code', fake_llm)
    out = skills_houdini.interpret_request('add navy blue box with x:1 y:2 z:.42 position it 2 units above terrain')
    assert out['intent'] == 'llm_interpreted_command'
    assert out['tool'] == 'run_houdini_python'
    assert 'box creation placeholder' in out['args']['code']


def test_rotate_cube_42_degrees_with_llm(monkeypatch):
    def fake_llm(intent, context=None):
        assert 'rotate cube 42 degrees' in intent.lower()
        return "n = hou.node('/obj/cube'); n.parm('rx').set(42)"

    monkeypatch.setattr(skills_houdini, 'llm_translate_intent_to_houdini_code', fake_llm)
    out = skills_houdini.interpret_request('rotate cube 42 degrees')
    assert out['intent'] == 'llm_interpreted_command'
    assert 'n.parm' in out['args']['code']


def test_apply_point_wrangle_with_llm(monkeypatch):
    def fake_llm(intent, context=None):
        assert 'apply point wrangle' in intent.lower()
        return "n = hou.node('/obj/geo1/attribwrangle1'); n.parm('snippet').set('...')"

    monkeypatch.setattr(skills_houdini, 'llm_translate_intent_to_houdini_code', fake_llm)
    out = skills_houdini.interpret_request('apply point wrangle')
    assert out['intent'] == 'llm_interpreted_command'
    assert 'attribwrangle1' in out['args']['code']


def test_mcp_no_api_key_allowed(monkeypatch):
    monkeypatch.delenv('RAPTOR_MINI_API_KEY', raising=False)
    out = mcp_houdini.preprocess_request('create sphere')
    assert out['status'] == 'ok'
    assert out['payload']['tool'] == 'run_houdini_python'





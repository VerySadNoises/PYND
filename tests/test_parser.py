from vn_engine.script_parser import load_story


def test_load_story(tmp_path):
    yaml = """
scenes:
  - id: a
    actions:
      - say:
          speaker: Narrateur
          text: Hello
"""
    p = tmp_path / "story.yaml"
    p.write_text(yaml, encoding='utf-8')
    scenes = load_story(str(p))
    assert 'a' in scenes
    assert scenes['a']['actions'][0]['say']['text'] == 'Hello'

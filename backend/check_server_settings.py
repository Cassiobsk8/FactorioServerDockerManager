from pathlib import Path
from docker_manager import load_server_settings, SERVER_SETTINGS_PATH, SERVER_SETTINGS_EXAMPLE_PATH

if __name__ == '__main__':
    p = Path(SERVER_SETTINGS_PATH)
    print('settings path:', p)
    print('exists:', p.exists())
    try:
        size = p.stat().st_size if p.exists() else 0
    except Exception as e:
        size = 0
    print('size:', size)
    print('example exists:', Path(SERVER_SETTINGS_EXAMPLE_PATH).exists())
    settings = load_server_settings()
    print('loaded keys:', list(settings.keys()))
    # print preview
    try:
        print('preview:\n', p.read_text(encoding='utf-8')[:1000])
    except Exception as e:
        print('cannot read preview:', e)

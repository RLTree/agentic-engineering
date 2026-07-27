from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('profile', choices=['core','lifecycle','rust','ultragoal','full'])
    parser.add_argument('--plugin-root', type=Path, default=ROOT)
    args = parser.parse_args()
    profile = json.loads((ROOT/'profiles'/f'{args.profile}.json').read_text())
    enabled = set(profile['enabled_skills'])
    for skill in sorted((args.plugin_root/'skills').iterdir()):
        if not (skill/'SKILL.md').is_file():
            continue
        print('[[skills.config]]')
        print(f'path = "{(skill/"SKILL.md").resolve()}"')
        print(f'enabled = {str(skill.name in enabled).lower()}')
        print()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

import os
import sys
import hashlib
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from retrospark.extractors import parser
from retrospark.privacy.anonymizer import Anonymizer

# Set MOCK_HOME for the generator and the test
MOCK_HOME = Path("/tmp/retrospark_verify_home")
os.environ["MOCK_HOME"] = str(MOCK_HOME)

# Import the generator
sys.path.append(str(Path(__file__).parent))
import generate_mock_data

class MockAnonymizer(Anonymizer):
    def path(self, p): return p
    def text(self, t): return t

def test_all_extractors():
    print(f"Generating mock data in {MOCK_HOME}...")
    generate_mock_data.generate_all()
    
    # Monkeypatch extractor directory constants
    # We must patch the individual modules because parser.py imports them
    from retrospark.extractors import claude, codex, gemini, opencode, openclaw, kimi, custom, antigravity
    
    claude.PROJECTS_DIR = MOCK_HOME / ".claude" / "projects"
    codex.CODEX_SESSIONS_DIR = MOCK_HOME / ".codex" / "sessions"
    gemini.GEMINI_DIR = MOCK_HOME / ".gemini" / "tmp"
    opencode.OPENCODE_DB_PATH = MOCK_HOME / ".local" / "share" / "opencode" / "opencode.db"
    openclaw.OPENCLAW_AGENTS_DIR = MOCK_HOME / ".openclaw" / "agents"
    kimi.KIMI_DIR = MOCK_HOME / ".kimi"
    kimi.KIMI_SESSIONS_DIR = kimi.KIMI_DIR / "sessions"
    kimi.KIMI_CONFIG_PATH = kimi.KIMI_DIR / "kimi.json"
    custom.CUSTOM_DIR = MOCK_HOME / ".dataclaw" / "custom"
    antigravity.ANTIGRAVITY_DIR = MOCK_HOME / ".gemini" / "antigravity" / "brain"

    anonymizer = MockAnonymizer()
    
    sources = [
        (parser.CLAUDE_SOURCE, "my-claude-project"),
        (parser.CODEX_SOURCE, "/home/user/my-codex-project"),
        (parser.GEMINI_SOURCE, hashlib.sha256("/home/user/my-gemini-project".encode()).hexdigest()),
        (parser.OPENCODE_SOURCE, "/home/user/my-opencode-project"),
        (parser.OPENCLAW_SOURCE, "/home/user/my-openclaw-project"),
        (parser.KIMI_SOURCE, "/home/user/my-kimi-project"),
        (parser.CUSTOM_SOURCE, "my-custom-project"),
        (parser.ANTIGRAVITY_SOURCE, "project-uuid"),
    ]
    

    results = {}
    for source, dir_name in sources:
        print(f"Verifying {source}...")
        try:
            sessions = parser.parse_project_sessions(dir_name, anonymizer, source=source)
            if sessions and len(sessions) > 0:
                print(f"  ✅ {source}: Found {len(sessions)} session(s)")
                results[source] = True
            else:
                print(f"  ❌ {source}: No sessions found for {dir_name}")
                results[source] = False
        except Exception as e:
            print(f"  ❌ {source}: Raised error: {e}")
            results[source] = False

    all_passed = all(results.values())
    print("\n" + "="*20)
    print("FINAL RESULTS:")
    for src, passed in results.items():
        print(f"{src}: {'PASSED' if passed else 'FAILED'}")
    
    if all_passed:
        print("\nAll extractors verified successfully! 🚀")
        sys.exit(0)
    else:
        print("\nSome extractors failed verification.")
        sys.exit(1)

if __name__ == "__main__":
    test_all_extractors()

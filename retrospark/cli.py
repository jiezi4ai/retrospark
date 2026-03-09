import json
import logging
import sys
from datetime import datetime
from pathlib import Path
import click

from retrospark.config import load_config, save_config, get_interaction_dir, DEFAULT_INTERACTION_DIR
from retrospark.extractors.parser import (
    discover_projects, 
    parse_project_sessions, 
    CUSTOM_SOURCE, 
    CLAUDE_SOURCE, 
    CODEX_SOURCE, 
    GEMINI_SOURCE, 
    OPENCODE_SOURCE, 
    OPENCLAW_SOURCE,
    ANTIGRAVITY_SOURCE,
    KIMI_SOURCE
)
from retrospark.markdown.transformer import format_session_to_markdown
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.vcs.git_manager import init_repo, sync_repo
from retrospark.skills.manager import SkillManager
from retrospark.extractors.antigravity import ANTIGRAVITY_DIR

logging.basicConfig(level=logging.ERROR)

VALID_SOURCES = ["antigravity", "claude", "codex", "gemini", "opencode", "openclaw", "kimi", "all"]

def print_output(data, force_json):
    """Outputs data either as JSON or as a human-readable string depending on the environment."""
    if force_json or not sys.stdout.isatty():
        click.echo(json.dumps(data, indent=2))
    else:
        if data.get("status") == "success":
            click.secho("✅ " + data.get("message", "Success"), fg="green")
            if "synced_sessions" in data:
                click.secho(f"   Synced Sessions: {data['synced_sessions']}", fg="cyan")
                click.secho(f"   Exported Files: {data['exported_files_count']}", fg="cyan")
            if "next_steps" in data:
                click.secho(f"➡️  Next Steps: {data['next_steps']}", fg="yellow")
        else:
            click.secho("❌ Error: " + data.get("message", "Unknown error"), fg="red", err=True)

@click.group()
def main():
    """RetroSpark (retrospark) - Review, rethink, reinvent with AI."""
    pass

@main.command()
@click.option("--remote-url", default="", help="The remote repository URL.")
@click.option("--skill", default=None, help="Automatically configure remote URL from a skill manifest.")
@click.option("--json", "force_json", is_flag=True, help="Force JSON output for Agent execution.")
def init(remote_url, skill, force_json):
    """Initialize RetroSpark and GitHub repository."""
    config = load_config()
    interaction_dir = get_interaction_dir()
    
    # 1. Check for manual skill discovery if none provided
    if not skill and not remote_url: # Only check config.yaml if no skill or remote_url is explicitly given
        local_config_path = Path("config.yaml")
        if local_config_path.exists():
            if not force_json and sys.stdout.isatty():
                click.secho("🔍 Found local config.yaml, attempting to auto-discover remote URL...", fg="blue")
            
            # Load the config.yaml as a SkillManifest
            try:
                manager = SkillManager(Path.cwd() / "skills")
                manifest = manager.load_config(local_config_path)
                if manifest and manifest.remote_url:
                    remote_url = manifest.remote_url
                    if not force_json and sys.stdout.isatty():
                        click.secho(f"✨ Discovered remote URL from config.yaml: {remote_url}", fg="green")
            except Exception as e:
                if not force_json and sys.stdout.isatty():
                    click.secho(f"⚠️  Could not parse config.yaml: {e}", fg="yellow")

    # 2. Discover from specified skill if provided and remote_url is still not set
    if skill and not remote_url:
        manager = SkillManager(Path.cwd() / "skills")
        manifest = manager.load_manifest(skill)
        if manifest and manifest.remote_url:
            remote_url = manifest.remote_url
            if not force_json and sys.stdout.isatty():
                click.secho(f"🔍 Auto-discovered remote URL from skill '{skill}': {remote_url}", fg="blue")
        elif not force_json and sys.stdout.isatty():
            click.secho(f"⚠️  Skill '{skill}' not found or has no remote_url defined.", fg="yellow")

    # 3. Validation: Check if GITHUB_LLM_SYNC_TOKEN is present if needed
    import os
    token = os.getenv("GITHUB_LLM_SYNC_TOKEN")
    if not token and not force_json and sys.stdout.isatty():
        # Just a warning, not a blocker as user might have a local credential helper
        click.secho(f"ℹ️  GITHUB_LLM_SYNC_TOKEN not found in environment. Git push might require manual auth.", fg="yellow")

    # Check if already initialized
    already_initialized = interaction_dir.exists() and (interaction_dir / ".git").exists()
    
    # Check existing remote from github_repo
    github_cfg = config.get("github_repo", {})
    existing_remote = github_cfg.get("remote_url") if isinstance(github_cfg, dict) else None
    
    if already_initialized:
        if remote_url and remote_url != existing_remote:
            if not force_json and sys.stdout.isatty():
                click.secho(f"🔄 Updating remote URL to: {remote_url[:20]}...", fg="yellow")
            
            if not isinstance(github_cfg, dict):
                github_cfg = {}
            github_cfg["remote_url"] = remote_url
            config["github_repo"] = github_cfg
            # Also clean up top-level remote_url if it exists
            config.pop("remote_url", None)
            
            save_config(config)
            init_repo(interaction_dir, remote_url)
            output = {
                "status": "success",
                "message": f"RetroSpark remote URL updated.",
                "interaction_dir": str(interaction_dir),
                "remote_url": remote_url[:20] + "..." # Don't leak full token in output
            }
        else:
            output = {
                "status": "success",
                "message": "RetroSpark is already initialized.",
                "interaction_dir": str(interaction_dir),
                "remote_url": (existing_remote[:20] + "...") if existing_remote else "None",
                "next_steps": "You are ready to run `retrospark sync`."
            }
        print_output(output, force_json)
        return

    # First time initialization
    if remote_url:
        if not isinstance(github_cfg, dict):
            github_cfg = {}
        github_cfg["remote_url"] = remote_url
        config["github_repo"] = github_cfg
    
    # Clean up redundant keys
    config.pop("remote_url", None)
    config.pop("antigravity", None)
    config.pop("output", None)
    
    save_config(config)
    
    # Init Git
    init_repo(interaction_dir, remote_url if remote_url else None)
    
    output = {
        "status": "success",
        "message": f"RetroSpark initialized. Interaction directory at {interaction_dir}",
        "remote_url": (remote_url[:20] + "...") if remote_url else "None",
        "next_steps": "You are ready to run `retrospark sync` to capture sessions."
    }
    print_output(output, force_json)

@main.command()
@click.option("--project", default=None, help="Specific project to sync. Syncs all if omitted.")
@click.option("--source", required=True, help="Source system (antigravity, claude, codex, gemini, opencode, openclaw, kimi, all, or custom local path).")
@click.option("--json", "force_json", is_flag=True, help="Force JSON output for Agent execution.")
def sync(project, source, force_json):
    """Extract, parse, format, and sync sessions to RetroSpark."""
    interaction_dir = get_interaction_dir()
    anonymizer = Anonymizer()
    
    if not interaction_dir.exists():
        print_output({"status": "error", "message": "Interaction directory not initialized. Run `retrospark init`."}, force_json)
        return

    # Determine source type (Built-in Enum or Custom Path)
    custom_path_mode = False
    source_enum = source.lower()
    
    if source_enum not in VALID_SOURCES:
        # Check if it's a valid local path
        if Path(source).is_dir():
            custom_path_mode = True
            if not force_json and sys.stdout.isatty():
                click.secho(f"🔍 Custom path detected: {source}", fg="blue")
        else:
            print_output({"status": "error", "message": f"Invalid source. Must be one of {VALID_SOURCES} or a valid local directory path."}, force_json)
            return

    projects_to_sync = []
    
    if custom_path_mode:
        # Wait: the current parser has a CUSTOM_SOURCE workflow but it relies on CUSTOM_DIR constant. 
        # For a truly custom path passed as arg, we can hack it by passing the exact path to parse_project_sessions 
        # using source="custom" if we configure the parser properly, or we extract it right here.
        # But for MVP let's assume `project_dir_name` will be the custom path.
        projects_to_sync = [{"dir_name": str(Path(source).resolve()), "display_name": Path(source).name, "source": CUSTOM_SOURCE}]
    elif project:
        projects_to_sync = [{"dir_name": project, "source": source_enum}]
    else:
        all_projects = discover_projects()
        if source_enum == "all":
            projects_to_sync = all_projects
        else:
            projects_to_sync = [p for p in all_projects if p["source"] == source_enum]

    if not force_json and sys.stdout.isatty():
        click.secho(f"🚀 Starting sync for {len(projects_to_sync)} project(s)...", fg="magenta", bold=True)

    synced_count = 0
    exported_files = []

    for p in projects_to_sync:
        dir_name = p.get("dir_name")
        proj_source = p.get("source")
        display_name = p.get("display_name", Path(dir_name).name).replace(":", "_").replace(" ", "_")
        
        if not force_json and sys.stdout.isatty():
            click.echo(f"  ⏳ Parsing {display_name} ({proj_source})...")
            
        sessions = parse_project_sessions(
            project_dir_name=dir_name, 
            anonymizer=anonymizer, 
            source=proj_source
        )
        
        if not sessions:
            continue
            
        # Target directory inside interaction: interaction_dir / source / project_name
        target_dir = interaction_dir / proj_source / display_name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Discovery context artifacts for Antigravity
        context_artifacts = []
        if proj_source == ANTIGRAVITY_SOURCE:
            # dir_name for antigravity is the session ID (UUID)
            brain_path = ANTIGRAVITY_DIR / dir_name
            if brain_path.exists():
                # We specifically look for the core artifacts
                for art_name in ["implementation_plan.md", "task.md", "walkthrough.md"]:
                    art_file = brain_path / art_name
                    if art_file.exists():
                        try:
                            context_artifacts.append({
                                "title": art_name.replace(".md", "").replace("_", " ").title(),
                                "content": art_file.read_text()
                            })
                        except Exception as e:
                            logging.warning(f"Failed to read artifact {art_name}: {e}")

        for session in sessions:
            markdown_content = format_session_to_markdown(session, context_artifacts=context_artifacts)
            
            # Use timestamp or session ID for filename
            start_time = session.get("start_time")
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    filename = f"{dt.strftime('%Y-%m-%d_%H%M%S')}_{session.get('session_id')}.md"
                except ValueError:
                    filename = f"session_{session.get('session_id')}.md"
            else:
                filename = f"session_{session.get('session_id')}.md"
                
            out_file = target_dir / filename
            with open(out_file, "w") as f:
                f.write(markdown_content)
                
            exported_files.append(str(out_file))
            synced_count += 1
            
        if not force_json and sys.stdout.isatty():
            click.echo(f"  ✅ Synthesized {display_name}")

    if not force_json and sys.stdout.isatty():
        click.secho("🔄 Committing changes to Git...", fg="blue")
        
    # Perform Git Sync
    sync_result = sync_repo(interaction_dir, commit_msg=f"Auto-sync {synced_count} sessions from {source}.")
    
    output = {
        "status": "success",
        "message": "Sync completed successfully.",
        "synced_sessions": synced_count,
        "exported_files_count": len(exported_files),
        "git_status": sync_result,
        "next_steps": "Sync completed. Check your GitHub repository.",
        "next_command": None
    }
    
    print_output(output, force_json)

if __name__ == "__main__":
    main()


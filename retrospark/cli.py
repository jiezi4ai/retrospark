import json
import logging
import sys
from datetime import datetime
from pathlib import Path
import click

from retrospark.config import load_config, save_config, get_brain_dir, DEFAULT_BRAIN_DIR
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

logging.basicConfig(level=logging.ERROR)

VALID_SOURCES = ["antigravity", "claude", "codex", "gemini", "opencode", "openclaw", "all"]

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
    """RetroSpark CLI - Vibe Coding Digital Second Brain."""
    pass

@main.command()
@click.option("--remote-url", prompt="GitHub Remote URL (optional)", default="", help="The remote repository URL.")
@click.option("--json", "force_json", is_flag=True, help="Force JSON output for Agent execution.")
def init(remote_url, force_json):
    """Initialize RetroSpark and GitHub repository."""
    config = load_config()
    brain_dir = get_brain_dir()
    
    if remote_url:
        config["remote_url"] = remote_url
    
    save_config(config)
    
    # Init Git
    init_repo(brain_dir, remote_url if remote_url else None)
    
    output = {
        "status": "success",
        "message": f"RetroSpark initialized. Brain directory at {brain_dir}",
        "remote_url": remote_url or "None",
        "next_steps": "You are ready to run `retrospark sync` to capture sessions."
    }
    print_output(output, force_json)

@main.command()
@click.option("--project", default=None, help="Specific project to sync. Syncs all if omitted.")
@click.option("--source", required=True, help="Source system (claude, opencode, gemini, all, or custom local path).")
@click.option("--json", "force_json", is_flag=True, help="Force JSON output for Agent execution.")
def sync(project, source, force_json):
    """Extract, parse, format, and sync sessions to the second brain."""
    brain_dir = get_brain_dir()
    anonymizer = Anonymizer()
    
    if not brain_dir.exists():
        print_output({"status": "error", "message": "Brain directory not initialized. Run `retrospark init`."}, force_json)
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
            
        # Target directory inside brain: brain_dir / source / project_name
        target_dir = brain_dir / proj_source / display_name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for session in sessions:
            markdown_content = format_session_to_markdown(session)
            
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
    sync_result = sync_repo(brain_dir, commit_msg=f"Auto-sync {synced_count} sessions from {source}.")
    
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


#!/usr/bin/env python3
"""
CLI interface for Workspace File Indexer.

This tool operates as a Skill for an AI agent, allowing headless querying
and tagging using the same underlying database as the GUI application.
All commands output JSON format for machine-readability.
"""

import json
import sys
import os
from typing import Dict, List, Any, Optional

import click

# Add the parent directory to the Python path so we can import core modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.models import Workspace, WorkspacePath, Tag
from core.scanner import FileEntry
from core.db import get_connection, ensure_database_initialized


def output_json(data: Any, error: bool = False) -> None:
    """
    Output data as JSON to stdout.

    Args:
        data: The data to output as JSON
        error: Whether this is an error response
    """
    if error:
        result = {"success": False, "error": data}
    else:
        result = {"success": True, "data": data}

    click.echo(json.dumps(result, indent=2))


def handle_error(error_message: str) -> None:
    """Handle and output error messages as JSON."""
    output_json(error_message, error=True)
    sys.exit(1)


@click.group()
@click.version_option(version='1.0.0', prog_name='Workspace File Indexer CLI')
def cli():
    """
    Workspace File Indexer CLI Tool

    A command-line interface for navigating, searching, and tagging files
    across multiple workspaces. Operates on the same SQLite database as
    the GUI application.
    """
    # Ensure database is initialized before any CLI commands
    try:
        ensure_database_initialized()
    except Exception as e:
        handle_error(f"Failed to initialize database: {str(e)}")


@cli.command()
@click.option('--workspace', '-w', required=True, help='Name of the workspace')
def list_files(workspace: str):
    """
    List all files in a specific workspace.

    Outputs JSON containing file paths, types, and basic metadata.
    """
    try:
        # Get workspace by name
        workspaces = Workspace.list_all()
        target_workspace = None
        for ws in workspaces:
            if ws.name == workspace:
                target_workspace = ws
                break

        if not target_workspace:
            handle_error(f"Workspace '{workspace}' not found")

        # Get all files for this workspace
        files = FileEntry.get_files_for_workspace(target_workspace.id)

        # Format the output
        file_data = []
        for file_entry in files:
            file_data.append({
                "id": file_entry.id,
                "relative_path": file_entry.relative_path,
                "absolute_path": file_entry.absolute_path,
                "file_type": file_entry.file_type,
                "workspace_id": file_entry.workspace_id
            })

        output_json({
            "workspace": {
                "id": target_workspace.id,
                "name": target_workspace.name,
                "created_at": target_workspace.created_at
            },
            "files": file_data,
            "total_files": len(file_data)
        })

    except Exception as e:
        handle_error(f"Failed to list files: {str(e)}")


@cli.command()
@click.option('--path', '-p', required=True, help='Absolute path to the file')
def get_tags(path: str):
    """
    Get all tags assigned to a specific file.

    Outputs JSON containing the file information and its tags.
    """
    try:
        # Find the file by absolute path
        file_entry = FileEntry.get_by_absolute_path(path)

        if not file_entry:
            handle_error(f"File not found: {path}")

        # Get all tags for this file
        tags = Tag.get_tags_for_file(file_entry.id)

        # Get workspace information
        workspace = Workspace.get_by_id(file_entry.workspace_id)

        output_json({
            "file": {
                "id": file_entry.id,
                "relative_path": file_entry.relative_path,
                "absolute_path": file_entry.absolute_path,
                "file_type": file_entry.file_type,
                "workspace": {
                    "id": workspace.id if workspace else None,
                    "name": workspace.name if workspace else None
                }
            },
            "tags": [{"id": tag.id, "name": tag.tag_name} for tag in tags],
            "total_tags": len(tags)
        })

    except Exception as e:
        handle_error(f"Failed to get tags: {str(e)}")


@cli.command()
@click.option('--path', '-p', required=True, help='Absolute path to the file')
@click.option('--tag', '-t', required=True, help='Tag name to add')
def add_tag(path: str, tag: str):
    """
    Add a tag to a specific file.

    Creates the tag association if it doesn't already exist.
    """
    try:
        # Find the file by absolute path
        file_entry = FileEntry.get_by_absolute_path(path)

        if not file_entry:
            handle_error(f"File not found: {path}")

        # Add the tag
        new_tag = Tag.add_tag_to_file(file_entry.id, tag)

        output_json({
            "file": {
                "id": file_entry.id,
                "absolute_path": file_entry.absolute_path,
                "relative_path": file_entry.relative_path
            },
            "tag": {
                "id": new_tag.id,
                "name": new_tag.tag_name
            },
            "message": f"Successfully added tag '{tag}' to file"
        })

    except ValueError as e:
        # Handle validation errors (like duplicate tags)
        handle_error(str(e))
    except Exception as e:
        handle_error(f"Failed to add tag: {str(e)}")


@cli.command()
@click.option('--path', '-p', required=True, help='Absolute path to the file')
@click.option('--tag', '-t', required=True, help='Tag name to remove')
def remove_tag(path: str, tag: str):
    """
    Remove a tag from a specific file.

    Removes the tag association if it exists.
    """
    try:
        # Find the file by absolute path
        file_entry = FileEntry.get_by_absolute_path(path)

        if not file_entry:
            handle_error(f"File not found: {path}")

        # Remove the tag
        success = Tag.remove_tag_from_file(file_entry.id, tag)

        if not success:
            handle_error(f"Tag '{tag}' not found on file: {path}")

        output_json({
            "file": {
                "id": file_entry.id,
                "absolute_path": file_entry.absolute_path,
                "relative_path": file_entry.relative_path
            },
            "tag": tag,
            "message": f"Successfully removed tag '{tag}' from file"
        })

    except Exception as e:
        handle_error(f"Failed to remove tag: {str(e)}")


@cli.command()
def list_tags():
    """
    List all unique tags across all workspaces.

    Outputs JSON containing all tag names currently in use.
    """
    try:
        tags = Tag.get_all_unique_tags()

        output_json({
            "tags": tags,
            "total_tags": len(tags)
        })

    except Exception as e:
        handle_error(f"Failed to list tags: {str(e)}")


@cli.command()
def list_workspaces():
    """
    List all available workspaces.

    Outputs JSON containing workspace information.
    """
    try:
        workspaces = Workspace.list_all()

        workspace_data = []
        for ws in workspaces:
            workspace_data.append({
                "id": ws.id,
                "name": ws.name,
                "created_at": ws.created_at
            })

        output_json({
            "workspaces": workspace_data,
            "total_workspaces": len(workspace_data)
        })

    except Exception as e:
        handle_error(f"Failed to list workspaces: {str(e)}")


@cli.command()
@click.option('--keyword', '-k', help='Search by keyword in file path')
@click.option('--tags', '-t', help='Search by tags (comma-separated)')
@click.option('--workspace', '-w', help='Limit search to specific workspace')
def search(keyword: Optional[str], tags: Optional[str], workspace: Optional[str]):
    """
    Search for files by keyword or tags.

    Supports searching by file path keywords, tags, or both.
    Can be limited to a specific workspace.
    """
    if not keyword and not tags:
        handle_error("Must provide either --keyword or --tags (or both)")

    try:
        # Get workspace ID if workspace name is provided
        workspace_id = None
        if workspace:
            workspaces = Workspace.list_all()
            for ws in workspaces:
                if ws.name == workspace:
                    workspace_id = ws.id
                    break
            if workspace_id is None:
                handle_error(f"Workspace '{workspace}' not found")

        # Parse tag list if provided
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

        # Perform the search
        if keyword and tag_list:
            # Search by both keyword and tags
            files = FileEntry.search_by_keyword_and_tags(keyword, tag_list, workspace_id)
        elif keyword:
            # Search by keyword only
            files = FileEntry.search_by_keyword(keyword, workspace_id)
        elif tag_list:
            # Search by tags only
            files = FileEntry.search_by_tags(tag_list, workspace_id)
        else:
            files = []

        # Format results
        results = []
        for file_entry in files:
            # Get workspace info
            ws = Workspace.get_by_id(file_entry.workspace_id)

            # Get tags for this file
            file_tags = Tag.get_tags_for_file(file_entry.id)

            results.append({
                "id": file_entry.id,
                "relative_path": file_entry.relative_path,
                "absolute_path": file_entry.absolute_path,
                "file_type": file_entry.file_type,
                "workspace": {
                    "id": ws.id if ws else None,
                    "name": ws.name if ws else None
                },
                "tags": [{"id": tag.id, "name": tag.tag_name} for tag in file_tags]
            })

        output_json({
            "search_criteria": {
                "keyword": keyword,
                "tags": tag_list,
                "workspace": workspace
            },
            "results": results,
            "total_results": len(results)
        })

    except Exception as e:
        handle_error(f"Search failed: {str(e)}")


if __name__ == '__main__':
    cli()
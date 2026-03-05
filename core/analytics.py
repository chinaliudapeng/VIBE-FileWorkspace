"""
Analytics and statistics module for Workspace File Indexer.

This module provides comprehensive statistics and analytics about workspaces,
files, tags, and system performance metrics.
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
from datetime import datetime

from .db import get_connection, get_db_path
from .models import Workspace, WorkspacePath, Tag
from .scanner import FileEntry
from .logging_config import get_logger

logger = get_logger('analytics')


class WorkspaceAnalytics:
    """
    Analytics and statistics provider for Workspace File Indexer.

    Provides comprehensive statistics about workspaces, files, tags,
    and system performance metrics.
    """

    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """
        Get database-level statistics.

        Returns:
            Dict containing database size, table counts, etc.
        """
        logger.info("Generating database statistics")

        try:
            db_path = get_db_path()
            db_size = 0
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path)

            with get_connection() as conn:
                cursor = conn.cursor()

                # Get table row counts
                table_counts = {}
                tables = ['workspace', 'workspace_path', 'file_entry', 'tags']

                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = cursor.fetchone()[0]

                # Get database creation time (use workspace table if available)
                cursor.execute("SELECT MIN(created_at) FROM workspace")
                oldest_workspace = cursor.fetchone()[0]

                return {
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / (1024 * 1024), 2),
                    "database_path": str(db_path),
                    "table_counts": table_counts,
                    "total_records": sum(table_counts.values()),
                    "oldest_workspace_created": oldest_workspace,
                    "generated_at": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to generate database statistics: {e}")
            raise

    @staticmethod
    def get_workspace_stats() -> Dict[str, Any]:
        """
        Get workspace-level statistics.

        Returns:
            Dict containing workspace counts, sizes, file distributions, etc.
        """
        logger.info("Generating workspace statistics")

        try:
            workspaces = Workspace.list_all()
            workspace_data = []
            total_files = 0

            for workspace in workspaces:
                files = FileEntry.get_files_for_workspace(workspace.id)
                paths = WorkspacePath.get_paths_for_workspace(workspace.id)

                # Calculate total size for this workspace's files
                total_size = 0
                for file_entry in files:
                    try:
                        if os.path.exists(file_entry.absolute_path):
                            total_size += os.path.getsize(file_entry.absolute_path)
                    except (OSError, IOError):
                        # File may have been deleted or is inaccessible
                        continue

                workspace_info = {
                    "id": workspace.id,
                    "name": workspace.name,
                    "created_at": workspace.created_at,
                    "file_count": len(files),
                    "path_count": len(paths),
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "paths": [{"path": p.root_path, "type": p.type, "hiding_rules": p.hiding_rules} for p in paths]
                }

                workspace_data.append(workspace_info)
                total_files += len(files)

            return {
                "total_workspaces": len(workspaces),
                "total_files_across_all_workspaces": total_files,
                "workspaces": workspace_data,
                "average_files_per_workspace": round(total_files / len(workspaces), 1) if workspaces else 0
            }

        except Exception as e:
            logger.error(f"Failed to generate workspace statistics: {e}")
            raise

    @staticmethod
    def get_file_type_stats() -> Dict[str, Any]:
        """
        Get file type statistics and distributions.

        Returns:
            Dict containing file type counts, percentages, etc.
        """
        logger.info("Generating file type statistics")

        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                # Get file type distribution
                cursor.execute("""
                    SELECT file_type, COUNT(*) as count
                    FROM file_entry
                    GROUP BY file_type
                    ORDER BY count DESC
                """)

                file_types = cursor.fetchall()
                total_files = sum(count for _, count in file_types)

                type_stats = []
                for file_type, count in file_types:
                    percentage = round((count / total_files * 100), 2) if total_files > 0 else 0
                    type_stats.append({
                        "file_type": file_type or "no_extension",
                        "count": count,
                        "percentage": percentage
                    })

                # Get top 10 most common file types
                top_types = type_stats[:10]

                return {
                    "total_files": total_files,
                    "unique_file_types": len(file_types),
                    "file_type_distribution": type_stats,
                    "top_file_types": top_types
                }

        except Exception as e:
            logger.error(f"Failed to generate file type statistics: {e}")
            raise

    @staticmethod
    def get_tag_stats() -> Dict[str, Any]:
        """
        Get tag usage statistics.

        Returns:
            Dict containing tag counts, most used tags, etc.
        """
        logger.info("Generating tag statistics")

        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                # Get tag usage distribution
                cursor.execute("""
                    SELECT tag_name, COUNT(*) as usage_count
                    FROM tags
                    GROUP BY tag_name
                    ORDER BY usage_count DESC
                """)

                tag_usage = cursor.fetchall()
                total_tag_instances = sum(count for _, count in tag_usage)

                # Get files with tags vs without tags
                cursor.execute("""
                    SELECT
                        (SELECT COUNT(DISTINCT file_id) FROM tags) as files_with_tags,
                        (SELECT COUNT(*) FROM file_entry) as total_files
                """)

                tagged_stats = cursor.fetchone()
                files_with_tags = tagged_stats[0]
                total_files = tagged_stats[1]
                files_without_tags = total_files - files_with_tags

                # Format tag usage data
                tag_stats = []
                for tag_name, count in tag_usage:
                    percentage = round((count / total_tag_instances * 100), 2) if total_tag_instances > 0 else 0
                    tag_stats.append({
                        "tag_name": tag_name,
                        "usage_count": count,
                        "percentage": percentage
                    })

                return {
                    "total_unique_tags": len(tag_usage),
                    "total_tag_instances": total_tag_instances,
                    "files_with_tags": files_with_tags,
                    "files_without_tags": files_without_tags,
                    "tag_coverage_percentage": round((files_with_tags / total_files * 100), 2) if total_files > 0 else 0,
                    "average_tags_per_file": round(total_tag_instances / total_files, 2) if total_files > 0 else 0,
                    "tag_usage_distribution": tag_stats,
                    "most_used_tags": tag_stats[:10]  # Top 10 most used tags
                }

        except Exception as e:
            logger.error(f"Failed to generate tag statistics: {e}")
            raise

    @staticmethod
    def get_comprehensive_stats() -> Dict[str, Any]:
        """
        Get comprehensive statistics combining all analytics.

        Returns:
            Dict containing all statistics combined for a complete overview.
        """
        logger.info("Generating comprehensive statistics report")

        try:
            stats = {
                "report_generated_at": datetime.now().isoformat(),
                "database": WorkspaceAnalytics.get_database_stats(),
                "workspaces": WorkspaceAnalytics.get_workspace_stats(),
                "file_types": WorkspaceAnalytics.get_file_type_stats(),
                "tags": WorkspaceAnalytics.get_tag_stats()
            }

            # Add summary section
            stats["summary"] = {
                "total_workspaces": stats["workspaces"]["total_workspaces"],
                "total_files": stats["file_types"]["total_files"],
                "total_unique_tags": stats["tags"]["total_unique_tags"],
                "database_size_mb": stats["database"]["database_size_mb"],
                "tag_coverage": f"{stats['tags']['tag_coverage_percentage']}%"
            }

            logger.info("Comprehensive statistics report generated successfully")
            return stats

        except Exception as e:
            logger.error(f"Failed to generate comprehensive statistics: {e}")
            raise

    @staticmethod
    def get_workspace_detailed_stats(workspace_id: int) -> Dict[str, Any]:
        """
        Get detailed statistics for a specific workspace.

        Args:
            workspace_id: The workspace ID to analyze

        Returns:
            Dict containing detailed workspace statistics
        """
        logger.info(f"Generating detailed statistics for workspace {workspace_id}")

        try:
            workspace = Workspace.get_by_id(workspace_id)
            if not workspace:
                raise ValueError(f"Workspace with ID {workspace_id} not found")

            files = FileEntry.get_files_for_workspace(workspace_id)
            paths = WorkspacePath.get_paths_for_workspace(workspace_id)

            # Analyze file types in this workspace
            file_type_counter = Counter(file.file_type for file in files)

            # Analyze directory structure
            directory_counter = Counter()
            for file in files:
                directory = str(Path(file.relative_path).parent)
                if directory != ".":
                    directory_counter[directory] += 1

            # Get tag statistics for this workspace
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.tag_name, COUNT(*) as count
                    FROM tags t
                    JOIN file_entry f ON t.file_id = f.id
                    WHERE f.workspace_id = ?
                    GROUP BY t.tag_name
                    ORDER BY count DESC
                """, (workspace_id,))

                workspace_tag_usage = cursor.fetchall()

            # Calculate sizes
            total_size = 0
            file_sizes = []
            for file in files:
                try:
                    if os.path.exists(file.absolute_path):
                        size = os.path.getsize(file.absolute_path)
                        total_size += size
                        file_sizes.append(size)
                except (OSError, IOError):
                    continue

            return {
                "workspace": {
                    "id": workspace.id,
                    "name": workspace.name,
                    "created_at": workspace.created_at
                },
                "file_statistics": {
                    "total_files": len(files),
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "average_file_size_bytes": round(sum(file_sizes) / len(file_sizes), 2) if file_sizes else 0,
                    "file_type_distribution": [
                        {"file_type": ft, "count": count}
                        for ft, count in file_type_counter.most_common()
                    ]
                },
                "directory_structure": {
                    "total_directories": len(directory_counter),
                    "directory_file_counts": [
                        {"directory": dir_path, "file_count": count}
                        for dir_path, count in directory_counter.most_common(20)  # Top 20 directories
                    ]
                },
                "path_configuration": {
                    "total_paths": len(paths),
                    "paths": [
                        {
                            "path": p.root_path,
                            "type": p.type,
                            "hiding_rules": p.hiding_rules
                        }
                        for p in paths
                    ]
                },
                "tag_statistics": {
                    "unique_tags_in_workspace": len(workspace_tag_usage),
                    "tag_usage": [
                        {"tag_name": tag, "usage_count": count}
                        for tag, count in workspace_tag_usage
                    ]
                }
            }

        except Exception as e:
            logger.error(f"Failed to generate detailed workspace statistics: {e}")
            raise
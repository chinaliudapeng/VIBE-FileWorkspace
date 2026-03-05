"""
Simplified tests for the analytics module - focuses on core functionality.
"""

import unittest
from unittest.mock import patch, MagicMock

from core.analytics import WorkspaceAnalytics


class TestAnalyticsSimple(unittest.TestCase):
    """Simple test cases for analytics functionality."""

    @patch('core.analytics.get_db_path')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('core.analytics.get_connection')
    def test_get_database_stats(self, mock_get_connection, mock_getsize, mock_exists, mock_get_db_path):
        """Test database statistics generation with mocked database."""
        # Setup mocks
        mock_get_db_path.return_value = '/test/db.sqlite'
        mock_exists.return_value = True
        mock_getsize.return_value = 1048576  # 1MB

        # Mock database cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        # Mock table count queries
        mock_cursor.fetchone.side_effect = [
            (5,),  # workspace
            (10,),  # workspace_path
            (25,),  # file_entry
            (15,),  # tags
            ('2024-01-01 10:00:00',)  # oldest_workspace_created
        ]

        stats = WorkspaceAnalytics.get_database_stats()

        # Verify the structure and data
        self.assertIsInstance(stats, dict)
        self.assertIn('database_size_bytes', stats)
        self.assertIn('table_counts', stats)
        self.assertEqual(stats['database_size_bytes'], 1048576)
        self.assertEqual(stats['database_size_mb'], 1.0)
        self.assertEqual(stats['table_counts']['workspace'], 5)
        self.assertEqual(stats['total_records'], 55)  # 5+10+25+15

    @patch('core.analytics.get_connection')
    def test_get_file_type_stats(self, mock_get_connection):
        """Test file type statistics generation."""
        # Mock database cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        # Mock file type query results
        mock_cursor.fetchall.return_value = [
            ('py', 10),
            ('js', 5),
            ('txt', 3),
            ('md', 2)
        ]

        stats = WorkspaceAnalytics.get_file_type_stats()

        # Verify the results
        self.assertIsInstance(stats, dict)
        self.assertEqual(stats['total_files'], 20)
        self.assertEqual(stats['unique_file_types'], 4)

        # Check distribution
        distribution = stats['file_type_distribution']
        self.assertEqual(len(distribution), 4)
        self.assertEqual(distribution[0]['file_type'], 'py')
        self.assertEqual(distribution[0]['count'], 10)
        self.assertEqual(distribution[0]['percentage'], 50.0)  # 10/20 * 100

    @patch('core.analytics.get_connection')
    def test_get_tag_stats(self, mock_get_connection):
        """Test tag statistics generation."""
        # Mock database cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        # Mock tag usage query
        mock_cursor.fetchall.return_value = [
            ('python', 8),
            ('javascript', 4),
            ('documentation', 3),
            ('test', 2)
        ]

        # Mock files with/without tags query
        mock_cursor.fetchone.return_value = (12, 20)  # files_with_tags, total_files

        stats = WorkspaceAnalytics.get_tag_stats()

        # Verify the results
        self.assertIsInstance(stats, dict)
        self.assertEqual(stats['total_unique_tags'], 4)
        self.assertEqual(stats['total_tag_instances'], 17)  # 8+4+3+2
        self.assertEqual(stats['files_with_tags'], 12)
        self.assertEqual(stats['files_without_tags'], 8)  # 20-12
        self.assertEqual(stats['tag_coverage_percentage'], 60.0)  # 12/20 * 100

    @patch.object(WorkspaceAnalytics, 'get_database_stats')
    @patch.object(WorkspaceAnalytics, 'get_workspace_stats')
    @patch.object(WorkspaceAnalytics, 'get_file_type_stats')
    @patch.object(WorkspaceAnalytics, 'get_tag_stats')
    def test_get_comprehensive_stats(self, mock_tag_stats, mock_file_stats,
                                   mock_workspace_stats, mock_db_stats):
        """Test comprehensive statistics generation."""
        # Mock individual stat methods
        mock_db_stats.return_value = {"database_size_mb": 2.5, "total_records": 150}
        mock_workspace_stats.return_value = {"total_workspaces": 3, "total_files_across_all_workspaces": 45}
        mock_file_stats.return_value = {"total_files": 45, "unique_file_types": 8}
        mock_tag_stats.return_value = {"total_unique_tags": 12, "tag_coverage_percentage": 75.5}

        stats = WorkspaceAnalytics.get_comprehensive_stats()

        # Verify structure
        self.assertIsInstance(stats, dict)
        self.assertIn('report_generated_at', stats)
        self.assertIn('database', stats)
        self.assertIn('workspaces', stats)
        self.assertIn('file_types', stats)
        self.assertIn('tags', stats)
        self.assertIn('summary', stats)

        # Verify all methods were called
        mock_db_stats.assert_called_once()
        mock_workspace_stats.assert_called_once()
        mock_file_stats.assert_called_once()
        mock_tag_stats.assert_called_once()

        # Verify summary
        summary = stats['summary']
        self.assertEqual(summary['total_workspaces'], 3)
        self.assertEqual(summary['total_files'], 45)
        self.assertEqual(summary['total_unique_tags'], 12)
        self.assertEqual(summary['database_size_mb'], 2.5)
        self.assertEqual(summary['tag_coverage'], "75.5%")

    @patch('core.analytics.Workspace.get_by_id')
    def test_get_workspace_detailed_stats_not_found(self, mock_get_workspace):
        """Test detailed workspace stats with non-existent workspace."""
        mock_get_workspace.return_value = None

        with self.assertRaises(ValueError) as context:
            WorkspaceAnalytics.get_workspace_detailed_stats(999)

        self.assertIn("Workspace with ID 999 not found", str(context.exception))


if __name__ == '__main__':
    unittest.main()
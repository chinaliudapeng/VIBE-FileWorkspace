"""Custom delegates for the Workspace File Indexer GUI application."""

import hashlib
from typing import List
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget, QApplication, QStyle
from PySide6.QtCore import QRect, Qt, QSize, QModelIndex
from PySide6.QtGui import QPainter, QBrush, QPen, QFont, QFontMetrics, QColor

# Import core data models
from core.models import Tag


class TagPillDelegate(QStyledItemDelegate):
    """Custom delegate to render tags as pills/badges with colored backgrounds."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Design constants for tag pills
        self.pill_height = 22
        self.pill_padding = 8
        self.pill_margin = 4
        self.pill_border_radius = 11
        self.font_size = 10

        # Color palette for tag pills
        self.color_palette = [
            "#3b82f6",  # blue
            "#10b981",  # emerald
            "#f59e0b",  # amber
            "#ef4444",  # red
            "#8b5cf6",  # violet
            "#06b6d4",  # cyan
            "#84cc16",  # lime
            "#f97316",  # orange
            "#ec4899",  # pink
            "#6366f1",  # indigo
        ]

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint the tags as pills/badges."""
        # Only handle the tags column
        if index.column() != 3:  # COL_TAGS = 3
            super().paint(painter, option, index)
            return

        painter.save()

        # Get the FileEntry object from the model
        file_entry = index.data(Qt.UserRole)
        if not file_entry:
            super().paint(painter, option, index)
            painter.restore()
            return

        # Get tags for this file
        try:
            tags = Tag.get_tags_for_file(file_entry.id)
        except Exception:
            # If there's an error getting tags, fall back to default painting
            super().paint(painter, option, index)
            painter.restore()
            return

        # Clear the cell background
        # Handle both integer and StateFlag enum values for option.state
        try:
            state_value = option.state.value if hasattr(option.state, 'value') else int(option.state)
        except (ValueError, AttributeError):
            state_value = int(option.state)

        if state_value & int(QStyle.StateFlag.State_Selected.value):
            painter.fillRect(option.rect, option.palette.highlight())
        elif index.row() % 2 == 1:
            # Alternate row color
            painter.fillRect(option.rect, QColor("#2d2d30"))
        else:
            painter.fillRect(option.rect, option.palette.base())

        if not tags:
            # No tags to display
            painter.restore()
            return

        # Setup font
        font = QFont()
        font.setPointSize(self.font_size)
        font.setWeight(QFont.Medium)
        painter.setFont(font)

        # Calculate pill positions
        x_offset = option.rect.x() + self.pill_margin
        y_center = option.rect.y() + option.rect.height() // 2
        y_top = y_center - self.pill_height // 2

        max_width = option.rect.width() - (2 * self.pill_margin)
        current_width = 0

        for i, tag in enumerate(tags):
            tag_name = tag.tag_name

            # Calculate pill dimensions
            font_metrics = QFontMetrics(font)
            text_width = font_metrics.horizontalAdvance(tag_name)
            pill_width = text_width + (2 * self.pill_padding)

            # Check if we have space for this pill
            if current_width + pill_width > max_width:
                # Draw "..." to indicate more tags
                if current_width < max_width - 30:
                    ellipsis_rect = QRect(x_offset + current_width, y_top, 30, self.pill_height)
                    painter.setPen(QPen(QColor("#969696")))
                    painter.drawText(ellipsis_rect, Qt.AlignCenter, "...")
                break

            # Generate color for this tag
            color = self._get_tag_color(tag_name)
            text_color = self._get_contrasting_text_color(color)

            # Define pill rectangle
            pill_rect = QRect(x_offset + current_width, y_top, pill_width, self.pill_height)

            # Draw pill background
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(pill_rect, self.pill_border_radius, self.pill_border_radius)

            # Draw tag text
            painter.setPen(QPen(text_color))
            painter.drawText(pill_rect, Qt.AlignCenter, tag_name)

            # Update position for next pill
            current_width += pill_width + self.pill_margin

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return the size hint for the tag pills."""
        if index.column() != 3:  # COL_TAGS = 3
            return super().sizeHint(option, index)

        # Return a consistent height for the tags column
        return QSize(option.rect.width(), self.pill_height + (2 * self.pill_margin))

    def _get_tag_color(self, tag_name: str) -> QColor:
        """
        Generate a consistent color for a tag name using hash.

        Args:
            tag_name: The tag name

        Returns:
            QColor: The color for the tag
        """
        # Use hash of tag name to get consistent color
        hash_value = hashlib.md5(tag_name.encode()).hexdigest()
        color_index = int(hash_value[:2], 16) % len(self.color_palette)
        return QColor(self.color_palette[color_index])

    def _get_contrasting_text_color(self, background_color: QColor) -> QColor:
        """
        Get contrasting text color (white or black) for a background color.

        Args:
            background_color: The background color

        Returns:
            QColor: White or black text color for best contrast
        """
        # Calculate luminance using the relative luminance formula
        r = background_color.red() / 255.0
        g = background_color.green() / 255.0
        b = background_color.blue() / 255.0

        # Apply gamma correction
        r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
        g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
        b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)

        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

        # Use white text for dark backgrounds, black text for light backgrounds
        return QColor("white") if luminance < 0.5 else QColor("black")
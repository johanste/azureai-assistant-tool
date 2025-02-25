# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

# This software uses the PySide6 library, which is licensed under the GNU Lesser General Public License (LGPL).
# For more details on PySide6's license, see <https://www.qt.io/licensing>

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtGui import QFont, QTextCursor,QDesktopServices, QMouseEvent, QGuiApplication, QPalette
from PySide6.QtCore import Qt, QUrl

import html, os, re, subprocess, sys
import base64

from azure.ai.assistant.management.assistant_config_manager import AssistantConfigManager
from azure.ai.assistant.management.message import TextMessage, FileMessage, ImageMessage
from azure.ai.assistant.management.logger_module import logger


class ConversationInputView(QTextEdit):
    PLACEHOLDER_TEXT = "Message Assistant..."

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window  # Store a reference to the main window
        self.setInitialPlaceholderText()

    def setInitialPlaceholderText(self):
        self.setText(self.PLACEHOLDER_TEXT)

    def focusInEvent(self, event):
        # Clear the placeholder text on first focus and do not set it again
        if self.toPlainText() == self.PLACEHOLDER_TEXT:
            self.clear()
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        # Clear the placeholder text on first key press and do not set it again
        if self.toPlainText() == self.PLACEHOLDER_TEXT and not event.text().isspace():
            self.clear()

        # Check if Enter key is pressed
        if event.key() == Qt.Key_Return and not event.modifiers():
            # Call on_user_input on the main window reference
            self.main_window.on_user_input_complete(self.toPlainText())
            self.clear()
        elif event.key() == Qt.Key_Enter:
            # Call on_user_input on the main window reference
            self.main_window.on_user_input_complete(self.toPlainText())
            self.clear()
        else:
            # Let the parent class handle all other key events
            super().keyPressEvent(event)

    def insertFromMimeData(self, mimeData):
        if mimeData.hasText():
            text = mimeData.text()
            # Convert URL to local file path
            fileUrl = QUrl(text)
            if fileUrl.isLocalFile():
                file_path = fileUrl.toLocalFile()
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, 'r') as file:
                            content = file.read()
                            self.insertPlainText(content)
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {e}")
                else:
                    logger.error(f"File {file_path} does not exist")
            else:
                # If it's not a file URL, proceed with the default paste operation
                super().insertFromMimeData(mimeData)

    def mouseReleaseEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        anchor = cursor.charFormat().anchorHref()

        if anchor:
            QDesktopServices.openUrl(QUrl(anchor))

        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        # Call on_text_field_clicked on the main window reference
        self.main_window.on_text_input_field_clicked()

        # Call the base class implementation to ensure normal text editing functionality
        super().mousePressEvent(event)


class ClickableTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def mousePressEvent(self, event: QMouseEvent):
        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()
        text = self.toPlainText()

        text_to_url_map = self.parent.get_text_to_url_map()
        cursor.select(QTextCursor.BlockUnderCursor)  # Select the entire line (block) of text
        line_text = cursor.selectedText()

        # Check if the click is on a link in this line
        if line_text.strip() in text_to_url_map.keys():
            # get the path from map
            file_path = text_to_url_map[line_text.strip()]["path"]
            self.open_file(file_path)

        # Handle regular HTTP URLs
        for url, start, end in self.find_urls(text):
            if start <= pos <= end:
                QDesktopServices.openUrl(QUrl(url))
                return

        super().mousePressEvent(event)

    def open_file(self, file_path):
        if sys.platform.startswith('linux'):
            subprocess.call(["xdg-open", file_path])
        elif sys.platform.startswith('win32'):
            os.startfile(file_path)
        elif sys.platform.startswith('darwin'):
            subprocess.call(["open", file_path])

    def find_urls(self, text):
        url_pattern = r'https?://\S+'
        for match in re.finditer(url_pattern, text):
            yield (match.group(0), match.start(), match.end())


class ConversationView(QWidget):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window  # Store a reference to the main window
        self.assistant_config_manager = AssistantConfigManager.get_instance()
        self.init_ui()
        self.text_to_url_map = {}
        # TODO make this better configurable. To have the output folder for each assistant is good, however
        # if assistant gets destroyed at some point, the output folder cannot be accessed from assistant config
        # anymore. So maybe it could be better to have a global output folder and then subfolders for each 
        # assistant names
        self.file_path = 'output'
        # Create the output directory if it doesn't exist
        os.makedirs(self.file_path, exist_ok=True)

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        self.conversationView = ClickableTextEdit(self)
        self.conversationView.setReadOnly(True)
        self.conversationView.setFont(QFont("Arial", 11))
        self.conversationView.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)

        self.inputField = ConversationInputView(self, self.main_window)
        self.inputField.setAcceptRichText(False)  # Accept only plain text
        self.inputField.setFixedHeight(100)  # Set an initial height
        self.inputField.setFont(QFont("Arial", 11))

        self.layout.addWidget(self.conversationView)
        self.layout.addWidget(self.inputField)

        self.conversationView.setStyleSheet("""
            QTextEdit {
                border: 1px solid #c0c0c0; /* Adjusted to have a 1px solid border */
                border-color: #a0a0a0 #ffffff #ffffff #a0a0a0;
                border-radius: 4px;
                padding: 1px; /* Adds padding inside the QTextEdit widget */
            }
            .code-block {
                background-color: #eeeeee;
                font-family: "Courier New", monospace;
                border: 1px solid #cccccc; /* Thin border for code blocks */
                white-space: pre-wrap;
                display: block; /* Ensures that the block is on its own line */
                margin: 2px 0; /* Adds a small margin above and below the code block */
                outline: 1px solid #cccccc; /* Add an outline to ensure visibility */
            }
            .text-block {
                background-color: white;
                font-family: Arial;
                white-space: pre-wrap;
                display: block; /* Ensures that the block is on its own line */
                margin: 2px 0; /* Adds a small margin above and below the text block */
            }
        """)

        self.inputField.setStyleSheet(
            "QTextEdit {"
            "  border-style: solid;"
            "  border-width: 1px;"
            "  border-color: #a0a0a0 #ffffff #ffffff #a0a0a0;"  # Light on top and left, dark on bottom and right
            "  padding: 1px;"
            "}"
        )

    def get_text_to_url_map(self):
        return self.text_to_url_map

    def is_dark_mode(self):
        app = QGuiApplication.instance()
        if app is not None:
            # Get the default window background color from the application palette
            windowBackgroundColor = app.palette().color(QPalette.ColorRole.Window)
            # Calculate the lightness (value between 0 for black and 255 for white)
            lightness = windowBackgroundColor.lightness()
            # Assuming dark mode if the lightness is below a certain threshold
            # Here, 127 is used as a threshold, considering the scale is from 0 to 255
            return lightness < 127
        return False

    def append_messages(self, messages):
        self.text_to_url_map = {}
        for message in reversed(messages):
            if message.type == "text":
                text_message : TextMessage = message
                # Determine the color based on the role and the theme
                if self.is_dark_mode():
                    # Colors for dark mode
                    color = 'blue' if text_message.role != "assistant" else '#D3D3D3'
                else:
                    # Colors for light mode
                    color = 'blue' if text_message.role != "assistant" else 'black'
                if text_message.role == "assistant":
                    self.append_message(text_message.sender, text_message.content, color=color)
                else:
                    self.append_message(text_message.sender, text_message.content, color=color)
            elif message.type == "file":
                file_message : FileMessage = message
                file_path = file_message.retrieve_file(self.file_path)
            elif message.type == "image_file":
                image_message : ImageMessage = message
                file_path = image_message.retrieve_image(self.file_path)
                self.append_image(file_path, image_message.sender)

    def convert_image_to_base64(self, image_path):
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return encoded_string

    def append_image(self, image_path, assistant_name):
        base64_image = self.convert_image_to_base64(image_path)
        # Move cursor to the end for each insertion
        cursor = self.conversationView.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.conversationView.setTextCursor(cursor)

        image_html = f"<img src='data:image/png;base64,{base64_image}' alt='Image' style='width:100px; height:auto;'>"
        cursor.insertHtml(image_html)
        cursor.insertText("\n\n")  # Add newlines for spacing

        # Scroll to the latest update
        scrollbar = self.conversationView.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.conversationView.update()  # Force the widget to update and redraw

    def append_message(self, sender, message, color='black'):
        # Move cursor to the end for each insertion
        cursor = self.conversationView.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.conversationView.setTextCursor(cursor)

        # Insert sender's name in bold
        cursor.insertHtml(f"<b style='color:{color};'>{sender}:</b> ")

        # Parse the message into segments
        segments = self.parse_message(message)

        for is_code, text in segments:
            if is_code:
                escaped_code = html.escape(text).replace('\n', '<br>')
                formatted_code = f"<pre class='code-block'>{escaped_code}</pre>"
                cursor.insertHtml(formatted_code)
            else:
                text = self.format_file_links(text)
                text = self.format_urls(text)
                formatted_text = f"<span class='text-block' style='white-space: pre-wrap;'>{text}</span>"
                cursor.insertHtml(formatted_text)
            cursor.insertText("\n")  # Add a newline after each segment for spacing
        cursor.insertText("\n")
        # Scroll to the latest update
        scrollbar = self.conversationView.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.conversationView.update()  # Force the widget to update and redraw

    def append_message_chunk(self, sender, message_chunk, is_start_of_message):
        # Move cursor to the end for each insertion
        cursor = self.conversationView.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.conversationView.setTextCursor(cursor)

        # If this is the start of a new message, insert the sender's name in bold
        if is_start_of_message:
            cursor.insertHtml(f"<b style='color:black;'>{html.escape(sender)}:</b> ")

        # Insert the message chunk as plain text.
        escaped_text = html.escape(message_chunk)
        #print(escaped_text)
        formatted_text = f"<span class='text-block' style='white-space: pre-wrap;'>{escaped_text}</span>"
        cursor.insertHtml(formatted_text)

        # Scroll to the latest update without adding new lines after each chunk.
        scrollbar = self.conversationView.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.conversationView.update()

    def format_urls(self, text):
        # Regular expression to match URLs
        url_pattern = r'(https?://\S+)'
        url_regex = re.compile(url_pattern)

        # Replace URLs with HTML anchor tags
        def replace_with_link(match):
            url = match.group(0)
            return f'<a href="{url}" style="color:blue;">{url}</a>'

        return url_regex.sub(replace_with_link, text)

    def format_file_links(self, text):
        # Pattern to find citations in the form [Download text]( [index])
        citation_link_pattern = r'\[([^\]]+)\]\(\s*\[(\d+)\]\s*\)'
        # Dictionary to store file paths indexed by the citation index
        citation_to_filename = {}

        # First, extract all file citations like "[0] finance_sector_revenue_chart.png"
        file_citations = re.findall(r'\[(\d+)\]\s*(.+)', text)
        for index, filename in file_citations:
            citation_to_filename[index] = filename

        # Function to replace citation links with clickable HTML links
        def replace_with_clickable_text(match):
            link_text = match.group(1)
            citation_index = match.group(2)
            file_name = citation_to_filename.get(citation_index)

            if file_name:
                local_file_path = os.path.normpath(os.path.join(self.file_path, file_name))

                if link_text in self.text_to_url_map:
                    link_text = f"{link_text} {len(self.text_to_url_map) + 1}"
                
                # Store the file path
                self.text_to_url_map[link_text] = {"path": local_file_path}

                # Return the HTML link and the local file path in separate inline-block divs
                return (f'<div style="display: inline-block;"><a href="{local_file_path}" style="color:green; text-decoration: underline;" download="{file_name}">{link_text}</a></div>'
                        f'<div style="display: inline-block; color:gray;">{local_file_path}</div>')

        # Replace links in the original text
        updated_text = re.sub(citation_link_pattern, replace_with_clickable_text, text)

        # Remove the original citation lines
        updated_text = re.sub(r'\[\d+\]\s*[^ ]+\.png', '', updated_text)

        return updated_text

    def parse_message(self, message):
        """Parse the message into a list of (is_code, text) tuples."""
        segments = []
        # Split the message on code block delimiters
        parts = message.split("```")

        # Iterate over the parts and determine if they are code blocks
        for i, part in enumerate(parts):
            is_code = i % 2 != 0  # Code blocks are at odd indices
            if is_code:
                # Attempt to find a language identifier at the beginning of the code block
                lines = part.split('\n', 1)
                if len(lines) > 1:  # Check if there's more than one line
                    language, code = lines
                    language = language.strip()  # This is your language identifier, e.g., 'java'
                    segments.append((is_code, code.strip('\n')))  # Append without the language line
                else:
                    # No language line present, just append the code
                    segments.append((is_code, part.strip('\n')))
            else:
                segments.append((is_code, part))
        return segments

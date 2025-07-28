import re
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageProcessor:
    def __init__(self):
        # Hashtags to add to tweets
        self.default_hashtags = ["#FreePalestine", "#Palestine"]
        self.max_tweet_length = 280
        
    def process_message(self, message_data: Dict) -> Dict:
        """Process Telegram message for Twitter posting."""
        processed = {
            'original_id': message_data['id'],
            'date': message_data['date'],
            'text': self._process_text(message_data['text']),
            'media_path': message_data.get('media'),
            'media_type': message_data.get('media_type'),
            'should_post': True
        }
        
        # Check if message should be filtered
        if self._should_filter(message_data):
            processed['should_post'] = False
            logger.info(f"Message {message_data['id']} filtered out")
        
        return processed
    
    def _process_text(self, text: str) -> str:
        """Process text content for Twitter."""
        if not text:
            text = ""
        
        # Clean up text
        text = self._clean_text(text)
        
        # Add hashtags if there's room
        text_with_tags = self._add_hashtags(text)
        
        # Ensure text fits in tweet limit
        if len(text_with_tags) > self.max_tweet_length:
            # Try with just the text
            if len(text) > self.max_tweet_length:
                text = text[:self.max_tweet_length - 3] + "..."
            return text
        
        return text_with_tags
    
    def _clean_text(self, text: str) -> str:
        """Clean text for Twitter posting."""
        # Remove Telegram-specific formatting
        text = re.sub(r'`{3}[\s\S]*?`{3}', '', text)  # Remove code blocks
        text = re.sub(r'`([^`]+)`', r'\1', text)  # Remove inline code
        
        # Convert Telegram links to plain text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _add_hashtags(self, text: str) -> str:
        """Add hashtags to text if space permits."""
        # Check if text already has our hashtags
        existing_tags = re.findall(r'#\w+', text.lower())
        tags_to_add = []
        
        for tag in self.default_hashtags:
            if tag.lower() not in existing_tags:
                tags_to_add.append(tag)
        
        if not tags_to_add:
            return text
        
        # Calculate space needed
        tags_text = " " + " ".join(tags_to_add)
        
        if len(text) + len(tags_text) <= self.max_tweet_length:
            return text + tags_text
        
        return text
    
    def _should_filter(self, message_data: Dict) -> bool:
        """Determine if message should be filtered out."""
        text = message_data.get('text', '').lower()
        
        # Filter out messages with certain keywords
        filter_keywords = ['bot', 'spam', 'advertisement', 'promotion']
        for keyword in filter_keywords:
            if keyword in text:
                return True
        
        # Filter out very short messages without media
        if len(text) < 10 and not message_data.get('media'):
            return True
        
        # Filter out messages that are just links
        if re.match(r'^https?://\S+$', text.strip()):
            return True
        
        return False
    
    def format_thread(self, messages: list) -> list:
        """Format multiple messages as a Twitter thread."""
        thread = []
        
        for i, msg in enumerate(messages):
            processed = self.process_message(msg)
            if processed['should_post']:
                # Add thread numbering if multiple messages
                if len(messages) > 1:
                    processed['text'] = f"({i+1}/{len(messages)}) " + processed['text']
                thread.append(processed)
        
        return thread
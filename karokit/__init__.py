"""
===========================
Karokit Karotter API Wrapper
===========================

https://karotter.com/
Python library for interacting with Karotter without official API keys.
"""

__version__ = "0.1.0"

import asyncio
import os

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from ._captcha import Capsolver
from .bookmark import BookmarkFolder
from .community import Community, CommunityCreator, CommunityMember, CommunityRule
from .errors import *
from .geo import Place
from .group import Group, GroupMessage
from .list import List
from .message import Message
from .notification import Notification
from .streaming import RealtimeStreamingClient, StreamingClient
from .trend import Trend
from .karot import CommunityNote, Karot, Poll, ScheduledKarot
from .user import User
from .utils import build_query
from .client.client import Client

__all__ = [
    "Client",
    "build_query",
    "Karot",
    "User",
    "ScheduledKarot",
    "Poll",
    "CommunityNote",
    "Trend",
    "Message",
    "Group",
    "GroupMessage",
    "StreamingClient",
    "RealtimeStreamingClient",
    "BookmarkFolder",
    "Community",
    "CommunityCreator",
    "CommunityMember",
    "CommunityRule",
    "Place",
    "List",
    "Notification",
    "Capsolver",
]

# Pyrogram - Telegram MTProto API Client Library for Python
# Copyright (C) 2017-2019 Dan Tès <https://github.com/delivrance>
#
# This file is part of Pyrogram.
#
# Pyrogram is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pyrogram is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Pyrogram.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
import base64
import binascii
import inspect
import json
import logging
import math
import mimetypes
import os
import re
import shutil
import struct
import tempfile
import time
from configparser import ConfigParser
from datetime import datetime
from hashlib import sha256, md5
from importlib import import_module
from pathlib import Path
from signal import signal, SIGINT, SIGTERM, SIGABRT
from typing import Union, List

from pyrogram.api import functions, types
from pyrogram.api.core import Object
from pyrogram.client.handlers import DisconnectHandler
from pyrogram.client.handlers.handler import Handler
from pyrogram.client.methods.password.utils import compute_check
from pyrogram.crypto import AES
from pyrogram.errors import (
    PhoneMigrate, NetworkMigrate, PhoneNumberInvalid,
    PhoneNumberUnoccupied, PhoneCodeInvalid, PhoneCodeHashEmpty,
    PhoneCodeExpired, PhoneCodeEmpty, SessionPasswordNeeded,
    PasswordHashInvalid, FloodWait, PeerIdInvalid, FirstnameInvalid, PhoneNumberBanned,
    VolumeLocNotFound, UserMigrate, FileIdInvalid, ChannelPrivate, PhoneNumberOccupied,
    PasswordRecoveryNa, PasswordEmpty
)
from pyrogram.session import Auth, Session
from .ext.utils import ainput
from .ext import utils, Syncer, BaseClient, Dispatcher
from .methods import Methods

log = logging.getLogger(__name__)


class Client(Methods, BaseClient):
    """This class represents a Client, the main mean for interacting with Telegram.
    It exposes bot-like methods for an easy access to the API as well as a simple way to
    invoke every single Telegram API method available.

    Args:
        session_name (``str``):
            Name to uniquely identify a session of either a User or a Bot, e.g.: "my_account". This name will be used
            to save a file to disk that stores details needed for reconnecting without asking again for credentials.
            Note for bots: You can pass a bot token here, but this usage will be deprecated in next releases.
            Use *bot_token* instead.

        api_id (``int``, *optional*):
            The *api_id* part of your Telegram API Key, as integer. E.g.: 12345
            This is an alternative way to pass it if you don't want to use the *config.ini* file.

        api_hash (``str``, *optional*):
            The *api_hash* part of your Telegram API Key, as string. E.g.: "0123456789abcdef0123456789abcdef"
            This is an alternative way to pass it if you don't want to use the *config.ini* file.

        app_version (``str``, *optional*):
            Application version. Defaults to "Pyrogram \U0001f525 vX.Y.Z"
            This is an alternative way to set it if you don't want to use the *config.ini* file.

        device_model (``str``, *optional*):
            Device model. Defaults to *platform.python_implementation() + " " + platform.python_version()*
            This is an alternative way to set it if you don't want to use the *config.ini* file.

        system_version (``str``, *optional*):
            Operating System version. Defaults to *platform.system() + " " + platform.release()*
            This is an alternative way to set it if you don't want to use the *config.ini* file.

        lang_code (``str``, *optional*):
            Code of the language used on the client, in ISO 639-1 standard. Defaults to "en".
            This is an alternative way to set it if you don't want to use the *config.ini* file.

        ipv6 (``bool``, *optional*):
            Pass True to connect to Telegram using IPv6.
            Defaults to False (IPv4).

        proxy (``dict``, *optional*):
            Your SOCKS5 Proxy settings as dict,
            e.g.: *dict(hostname="11.22.33.44", port=1080, username="user", password="pass")*.
            *username* and *password* can be omitted if your proxy doesn't require authorization.
            This is an alternative way to setup a proxy if you don't want to use the *config.ini* file.

        test_mode (``bool``, *optional*):
            Enable or disable log-in to testing servers. Defaults to False.
            Only applicable for new sessions and will be ignored in case previously
            created sessions are loaded.

        phone_number (``str`` | ``callable``, *optional*):
            Pass your phone number as string (with your Country Code prefix included) to avoid entering it manually.
            Or pass a callback function which accepts no arguments and must return the correct phone number as string
            (e.g., "391234567890").
            Only applicable for new sessions.

        phone_code (``str`` | ``callable``, *optional*):
            Pass the phone code as string (for test numbers only) to avoid entering it manually. Or pass a callback
            function which accepts a single positional argument *(phone_number)* and must return the correct phone code
            as string (e.g., "12345").
            Only applicable for new sessions.

        password (``str``, *optional*):
            Pass your Two-Step Verification password as string (if you have one) to avoid entering it manually.
            Or pass a callback function which accepts a single positional argument *(password_hint)* and must return
            the correct password as string (e.g., "password").
            Only applicable for new sessions.

        recovery_code (``callable``, *optional*):
            Pass a callback function which accepts a single positional argument *(email_pattern)* and must return the
            correct password recovery code as string (e.g., "987654").
            Only applicable for new sessions.

        force_sms (``str``, *optional*):
            Pass True to force Telegram sending the authorization code via SMS.
            Only applicable for new sessions.

        first_name (``str``, *optional*):
            Pass a First Name as string to avoid entering it manually. Or pass a callback function which accepts no
            arguments and must return the correct name as string (e.g., "Dan"). It will be used to automatically create
            a new Telegram account in case the phone number you passed is not registered yet.
            Only applicable for new sessions.

        bot_token (``str``, *optional*):
            Pass your Bot API token to create a bot session, e.g.: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
            Only applicable for new sessions.

        last_name (``str``, *optional*):
            Same purpose as *first_name*; pass a Last Name to avoid entering it manually. It can
            be an empty string: "". Only applicable for new sessions.

        workers (``int``, *optional*):
            Number of maximum concurrent workers for handling incoming updates. Defaults to 4.

        workdir (``str``, *optional*):
            Define a custom working directory. The working directory is the location in your filesystem
            where Pyrogram will store your session files. Defaults to "." (current directory).

        config_file (``str``, *optional*):
            Path of the configuration file. Defaults to ./config.ini

        plugins (``dict``, *optional*):
            Your Smart Plugins settings as dict, e.g.: *dict(root="plugins")*.
            This is an alternative way to setup plugins if you don't want to use the *config.ini* file.

        no_updates (``bool``, *optional*):
            Pass True to completely disable incoming updates for the current session.
            When updates are disabled your client can't receive any new message.
            Useful for batch programs that don't need to deal with updates.
            Defaults to False (updates enabled and always received).

        takeout (``bool``, *optional*):
            Pass True to let the client use a takeout session instead of a normal one, implies no_updates.
            Useful for exporting your Telegram data. Methods invoked inside a takeout session (such as get_history,
            download_media, ...) are less prone to throw FloodWait exceptions.
            Only available for users, bots will ignore this parameter.
            Defaults to False (normal session).
    """

    terms_of_service_displayed = False

    def __init__(
        self,
        session_name: str,
        api_id: Union[int, str] = None,
        api_hash: str = None,
        app_version: str = None,
        device_model: str = None,
        system_version: str = None,
        lang_code: str = None,
        ipv6: bool = False,
        proxy: dict = None,
        test_mode: bool = False,
        phone_number: str = None,
        phone_code: Union[str, callable] = None,
        password: str = None,
        recovery_code: callable = None,
        force_sms: bool = False,
        bot_token: str = None,
        first_name: str = None,
        last_name: str = None,
        workers: int = BaseClient.WORKERS,
        workdir: str = BaseClient.WORKDIR,
        config_file: str = BaseClient.CONFIG_FILE,
        plugins: dict = None,
        no_updates: bool = None,
        takeout: bool = None
    ):
        super().__init__()

        self.session_name = session_name
        self.api_id = int(api_id) if api_id else None
        self.api_hash = api_hash
        self.app_version = app_version
        self.device_model = device_model
        self.system_version = system_version
        self.lang_code = lang_code
        self.ipv6 = ipv6
        # TODO: Make code consistent, use underscore for private/protected fields
        self._proxy = proxy
        self.test_mode = test_mode
        self.phone_number = phone_number
        self.phone_code = phone_code
        self.password = password
        self.recovery_code = recovery_code
        self.force_sms = force_sms
        self.bot_token = bot_token
        self.first_name = first_name
        self.last_name = last_name
        self.workers = workers
        self.workdir = workdir
        self.config_file = config_file
        self.plugins = plugins
        self.no_updates = no_updates
        self.takeout = takeout
        self.load_session_hook = None
        self.save_session_hook = None

        self.dispatcher = Dispatcher(self, workers)

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.stop()

    async def __aenter__(self):
        return await self.start()

    async def __aexit__(self, *args):
        await self.stop()

    @property
    def proxy(self):
        return self._proxy

    @proxy.setter
    def proxy(self, value):
        if value is None:
            self._proxy = None
            return

        if self._proxy is None:
            self._proxy = {}

        self._proxy["enabled"] = bool(value.get("enabled", True))
        self._proxy.update(value)

    async def start(self):
        """Use this method to start the Client after creating it.
        Requires no parameters.

        Raises:
            :class:`RPCError <pyrogram.RPCError>` in case of a Telegram RPC error.
            ``ConnectionError`` in case you try to start an already started Client.
        """
        if self.is_started:
            raise ConnectionError("Client has already been started")

        if self.BOT_TOKEN_RE.match(self.session_name):
            self.is_bot = True
            self.bot_token = self.session_name
            self.session_name = self.session_name.split(":")[0]
            log.warning('\nWARNING: You are using a bot token as session name!\n'
                        'This usage will be deprecated soon. Please use a session file name to load '
                        'an existing session and the bot_token argument to create new sessions.\n'
                        'More info: https://docs.pyrogram.ml/start/Setup#bot-authorization\n')

        self.load_config()
        if callable(self.load_session_hook):
            self.load_session_hook(self)
        else:
            self.load_session()
        self.load_plugins()

        self.session = Session(
                self,
                self.dc_id,
                self.auth_key,
                self.api_id.encode('utf-8')
            )

        await self.session.start()
        self.is_started = True

        try:
            if self.user_id is None:
                if self.bot_token is None:
                    self.is_bot = False
                    await self.authorize_user()
                else:
                    self.is_bot = True
                    await self.authorize_bot()

                if callable(self.save_session_hook):
                    self.save_session_hook(self)
                else:
                    self.save_session()

            if not self.is_bot:
                if self.takeout:
                    self.takeout_id = (await self.send(functions.account.InitTakeoutSession())).id
                    log.warning("Takeout session {} initiated".format(self.takeout_id))

                now = time.time()

                if abs(now - self.date) > Client.OFFLINE_SLEEP:
                    self.peers_by_username = {}
                    self.peers_by_phone = {}

                    await self.get_initial_dialogs()
                    await self.get_contacts()
                else:
                    await self.send(functions.messages.GetPinnedDialogs())
                    await self.get_initial_dialogs_chunk()
            else:
                await self.send(functions.updates.GetState())
        except Exception as e:
            self.is_started = False
            await self.session.stop()
            raise e

        self.updates_worker_task = asyncio.ensure_future(self.updates_worker())

        for _ in range(Client.DOWNLOAD_WORKERS):
            self.download_worker_tasks.append(
                asyncio.ensure_future(self.download_worker())
            )

        log.info("Started {} DownloadWorkerTasks".format(Client.DOWNLOAD_WORKERS))

        await self.dispatcher.start()
        await Syncer.add(self)

        mimetypes.init()

        return self

    async def stop(self):
        """Use this method to manually stop the Client.
        Requires no parameters.

        Raises:
            ``ConnectionError`` in case you try to stop an already stopped Client.
        """
        if not self.is_started:
            raise ConnectionError("Client is already stopped")

        if self.takeout_id:
            await self.send(functions.account.FinishTakeoutSession())
            log.warning("Takeout session {} finished".format(self.takeout_id))

        await Syncer.remove(self)
        await self.dispatcher.stop()

        for _ in range(Client.DOWNLOAD_WORKERS):
            self.download_queue.put_nowait(None)

        for task in self.download_worker_tasks:
            await task

        self.download_worker_tasks.clear()

        log.info("Stopped {} DownloadWorkerTasks".format(Client.DOWNLOAD_WORKERS))

        self.updates_queue.put_nowait(None)
        await self.updates_worker_task

        for media_session in self.media_sessions.values():
            await media_session.stop()

        self.media_sessions.clear()

        self.is_started = False
        await self.session.stop()

        return self

    async def restart(self):
        """Use this method to restart the Client.
        Requires no parameters.

        Raises:
            ``ConnectionError`` in case you try to restart a stopped Client.
        """
        await self.stop()
        await self.start()

    async def idle(self, stop_signals: tuple = (SIGINT, SIGTERM, SIGABRT)):
        """Blocks the program execution until one of the signals are received,
        then gently stop the Client by closing the underlying connection.

        Args:
            stop_signals (``tuple``, *optional*):
                Iterable containing signals the signal handler will listen to.
                Defaults to (SIGINT, SIGTERM, SIGABRT).
        """

        def signal_handler(*args):
            log.info("Stop signal received ({}). Exiting...".format(args[0]))
            self.is_idle = False

        for s in stop_signals:
            signal(s, signal_handler)

        self.is_idle = True

        while self.is_idle:
            await asyncio.sleep(1)

        await self.stop()

    def run(self, coroutine=None):
        """Use this method to automatically start and idle a Client.
        If a coroutine is passed as argument this method will start the client, run the coroutine
        until is complete and then stop the client automatically.

        Args:
            coroutine: (``Coroutine``, *optional*):
                Pass a coroutine to run it until is complete.

        Raises:
            :class:`RPCError <pyrogram.RPCError>` in case of a Telegram RPC error.
        """
        run = asyncio.get_event_loop().run_until_complete

        run(self.start())

        run(
            coroutine if inspect.iscoroutine(coroutine)
            else coroutine() if coroutine
            else self.idle()
        )

        if self.is_started:
            run(self.stop())

        return coroutine

    def add_handler(self, handler: Handler, group: int = 0):
        """Use this method to register an update handler.

        You can register multiple handlers, but at most one handler within a group
        will be used for a single update. To handle the same update more than once, register
        your handler using a different group id (lower group id == higher priority).

        Args:
            handler (``Handler``):
                The handler to be registered.

            group (``int``, *optional*):
                The group identifier, defaults to 0.

        Returns:
            A tuple of (handler, group)
        """
        if isinstance(handler, DisconnectHandler):
            self.disconnect_handler = handler.callback
        else:
            self.dispatcher.add_handler(handler, group)

        return handler, group

    def remove_handler(self, handler: Handler, group: int = 0):
        """Removes a previously-added update handler.

        Make sure to provide the right group that the handler was added in. You can use
        the return value of the :meth:`add_handler` method, a tuple of (handler, group), and
        pass it directly.

        Args:
            handler (``Handler``):
                The handler to be removed.

            group (``int``, *optional*):
                The group identifier, defaults to 0.
        """
        if isinstance(handler, DisconnectHandler):
            self.disconnect_handler = None
        else:
            self.dispatcher.remove_handler(handler, group)

    def stop_transmission(self):
        """Use this method to stop downloading or uploading a file.
        Must be called inside a progress callback function.
        """
        raise Client.StopTransmission

    async def authorize_bot(self):
        try:
            r = await self.send(
                functions.auth.ImportBotAuthorization(
                    flags=0,
                    api_id=self.api_id,
                    api_hash=self.api_hash,
                    bot_auth_token=self.bot_token
                )
            )
        except UserMigrate as e:
            await self.session.stop()

            self.dc_id = e.x
            self.auth_key = await Auth(self.dc_id, self.test_mode, self.ipv6, self._proxy).create()

            self.session = Session(
                self,
                self.dc_id,
                self.auth_key
            )

            await self.session.start()
            await self.authorize_bot()
        else:
            self.user_id = r.user.id

            print("Logged in successfully as @{}".format(r.user.username))

    async def authorize_user(self):
        phone_number_invalid_raises = self.phone_number is not None
        phone_code_invalid_raises = self.phone_code is not None
        password_invalid_raises = self.password is not None
        first_name_invalid_raises = self.first_name is not None

        async def default_phone_number_callback():
            while True:
                phone_number = await ainput("Enter phone number: ")
                confirm = await ainput("Is \"{}\" correct? (y/n): ".format(phone_number))

                if confirm in ("y", "1"):
                    return phone_number
                elif confirm in ("n", "2"):
                    continue

        while True:
            self.phone_number = (
                await default_phone_number_callback() if self.phone_number is None
                else str(await self.phone_number()) if callable(self.phone_number)
                else str(self.phone_number)
            )

            self.phone_number = self.phone_number.strip("+")

            try:
                r = await self.send(
                    functions.auth.SendCode(
                        phone_number=self.phone_number,
                        api_id=self.api_id,
                        api_hash=self.api_hash,
                        settings=types.CodeSettings()
                    )
                )
            except (PhoneMigrate, NetworkMigrate) as e:
                await self.session.stop()

                self.dc_id = e.x

                self.auth_key = await Auth(
                    self.dc_id,
                    self.test_mode,
                    self.ipv6,
                    self._proxy
                ).create()

                self.session = Session(
                    self,
                    self.dc_id,
                    self.auth_key
                )

                await self.session.start()
            except (PhoneNumberInvalid, PhoneNumberBanned) as e:
                if phone_number_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE)
                    self.phone_number = None
            except FloodWait as e:
                if phone_number_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE.format(x=e.x))
                    await asyncio.sleep(e.x)
            except Exception as e:
                log.error(e, exc_info=True)
                raise
            else:
                break

        phone_registered = r.phone_registered
        phone_code_hash = r.phone_code_hash
        terms_of_service = r.terms_of_service

        if terms_of_service and not Client.terms_of_service_displayed:
            print("\n" + terms_of_service.text + "\n")
            Client.terms_of_service_displayed = True

        if self.force_sms:
            await self.send(
                functions.auth.ResendCode(
                    phone_number=self.phone_number,
                    phone_code_hash=phone_code_hash
                )
            )

        while True:
            if not phone_registered:
                self.first_name = (
                    await ainput("First name: ") if self.first_name is None
                    else str(await self.first_name()) if callable(self.first_name)
                    else str(self.first_name)
                )

                self.last_name = (
                    await ainput("Last name: ") if self.last_name is None
                    else str(await self.last_name()) if callable(self.last_name)
                    else str(self.last_name)
                )

            self.phone_code = (
                await ainput("Enter phone code: ") if self.phone_code is None
                else str(await self.phone_code(self.phone_number)) if callable(self.phone_code)
                else str(self.phone_code)
            )

            try:
                if phone_registered:
                    try:
                        r = await self.send(
                            functions.auth.SignIn(
                                phone_number=self.phone_number,
                                phone_code_hash=phone_code_hash,
                                phone_code=self.phone_code
                            )
                        )
                    except PhoneNumberUnoccupied:
                        log.warning("Phone number unregistered")
                        phone_registered = False
                        continue
                else:
                    try:
                        r = await self.send(
                            functions.auth.SignUp(
                                phone_number=self.phone_number,
                                phone_code_hash=phone_code_hash,
                                phone_code=self.phone_code,
                                first_name=self.first_name,
                                last_name=self.last_name
                            )
                        )
                    except PhoneNumberOccupied:
                        log.warning("Phone number already registered")
                        phone_registered = True
                        continue
            except (PhoneCodeInvalid, PhoneCodeEmpty, PhoneCodeExpired, PhoneCodeHashEmpty) as e:
                if phone_code_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE)
                    self.phone_code = None
            except FirstnameInvalid as e:
                if first_name_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE)
                    self.first_name = None
            except SessionPasswordNeeded as e:
                print(e.MESSAGE)

                async def default_password_callback(password_hint: str) -> str:
                    print("Hint: {}".format(password_hint))
                    return await ainput("Enter password (empty to recover): ")

                async def default_recovery_callback(email_pattern: str) -> str:
                    print("An e-mail containing the recovery code has been sent to {}".format(email_pattern))
                    return await ainput("Enter password recovery code: ")

                while True:
                    try:
                        r = await self.send(functions.account.GetPassword())

                        self.password = (
                            await default_password_callback(r.hint) if self.password is None
                            else str((await self.password(r.hint)) or "") if callable(self.password)
                            else str(self.password)
                        )

                        if self.password == "":
                            r = await self.send(functions.auth.RequestPasswordRecovery())

                            self.recovery_code = (
                                await default_recovery_callback(r.email_pattern) if self.recovery_code is None
                                else str(await self.recovery_code(r.email_pattern)) if callable(self.recovery_code)
                                else str(self.recovery_code)
                            )

                            r = await self.send(
                                functions.auth.RecoverPassword(
                                    code=self.recovery_code
                                )
                            )
                        else:
                            r = await self.send(
                                functions.auth.CheckPassword(
                                    password=compute_check(r, self.password)
                                )
                            )
                    except (PasswordEmpty, PasswordRecoveryNa, PasswordHashInvalid) as e:
                        if password_invalid_raises:
                            raise
                        else:
                            print(e.MESSAGE)
                            self.password = None
                            self.recovery_code = None
                    except FloodWait as e:
                        if password_invalid_raises:
                            raise
                        else:
                            print(e.MESSAGE.format(x=e.x))
                            await asyncio.sleep(e.x)
                            self.password = None
                            self.recovery_code = None
                    except Exception as e:
                        log.error(e, exc_info=True)
                        raise
                    else:
                        break
                break
            except FloodWait as e:
                if phone_code_invalid_raises or first_name_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE.format(x=e.x))
                    await asyncio.sleep(e.x)
            except Exception as e:
                log.error(e, exc_info=True)
                raise
            else:
                break

        if terms_of_service:
            assert await self.send(
                functions.help.AcceptTermsOfService(
                    id=terms_of_service.id
                )
            )

        self.password = None
        self.user_id = r.user.id

        print("Logged in successfully as {}".format(r.user.first_name))

    def fetch_peers(self, entities: List[Union[types.User,
                                               types.Chat, types.ChatForbidden,
                                               types.Channel, types.ChannelForbidden]]):
        for entity in entities:
            if isinstance(entity, types.User):
                user_id = entity.id

                access_hash = entity.access_hash

                if access_hash is None:
                    continue

                username = entity.username
                phone = entity.phone

                input_peer = types.InputPeerUser(
                    user_id=user_id,
                    access_hash=access_hash
                )

                self.peers_by_id[user_id] = input_peer

                if username is not None:
                    self.peers_by_username[username.lower()] = input_peer

                if phone is not None:
                    self.peers_by_phone[phone] = input_peer

            if isinstance(entity, (types.Chat, types.ChatForbidden)):
                chat_id = entity.id
                peer_id = -chat_id

                input_peer = types.InputPeerChat(
                    chat_id=chat_id
                )

                self.peers_by_id[peer_id] = input_peer

            if isinstance(entity, (types.Channel, types.ChannelForbidden)):
                channel_id = entity.id
                peer_id = int("-100" + str(channel_id))

                access_hash = entity.access_hash

                if access_hash is None:
                    continue

                username = getattr(entity, "username", None)

                input_peer = types.InputPeerChannel(
                    channel_id=channel_id,
                    access_hash=access_hash
                )

                self.peers_by_id[peer_id] = input_peer

                if username is not None:
                    self.peers_by_username[username.lower()] = input_peer

    async def download_worker(self):
        while True:
            media = await self.download_queue.get()

            if media is None:
                break

            temp_file_path = ""
            final_file_path = ""

            try:
                media, file_name, done, progress, progress_args, path = media

                file_id = media.file_id
                size = media.file_size

                directory, file_name = os.path.split(file_name)
                directory = directory or "downloads"

                try:
                    decoded = utils.decode(file_id)
                    fmt = "<iiqqqqi" if len(decoded) > 24 else "<iiqq"
                    unpacked = struct.unpack(fmt, decoded)
                except (AssertionError, binascii.Error, struct.error):
                    raise FileIdInvalid from None
                else:
                    media_type = unpacked[0]
                    dc_id = unpacked[1]
                    id = unpacked[2]
                    access_hash = unpacked[3]
                    volume_id = None
                    secret = None
                    local_id = None

                    if len(decoded) > 24:
                        volume_id = unpacked[4]
                        secret = unpacked[5]
                        local_id = unpacked[6]

                    media_type_str = Client.MEDIA_TYPE_ID.get(media_type, None)

                    if media_type_str is None:
                        raise FileIdInvalid("Unknown media type: {}".format(unpacked[0]))

                file_name = file_name or getattr(media, "file_name", None)

                if not file_name:
                    if media_type == 3:
                        extension = ".ogg"
                    elif media_type in (4, 10, 13):
                        extension = mimetypes.guess_extension(media.mime_type) or ".mp4"
                    elif media_type == 5:
                        extension = mimetypes.guess_extension(media.mime_type) or ".unknown"
                    elif media_type == 8:
                        extension = ".webp"
                    elif media_type == 9:
                        extension = mimetypes.guess_extension(media.mime_type) or ".mp3"
                    elif media_type in (0, 1, 2):
                        extension = ".jpg"
                    else:
                        continue

                    file_name = "{}_{}_{}{}".format(
                        media_type_str,
                        datetime.fromtimestamp(
                            getattr(media, "date", None) or time.time()
                        ).strftime("%Y-%m-%d_%H-%M-%S"),
                        self.rnd_id(),
                        extension
                    )

                temp_file_path = await self.get_file(
                    dc_id=dc_id,
                    id=id,
                    access_hash=access_hash,
                    volume_id=volume_id,
                    local_id=local_id,
                    secret=secret,
                    size=size,
                    progress=progress,
                    progress_args=progress_args
                )

                if temp_file_path:
                    final_file_path = os.path.abspath(re.sub("\\\\", "/", os.path.join(directory, file_name)))
                    os.makedirs(directory, exist_ok=True)
                    shutil.move(temp_file_path, final_file_path)
            except Exception as e:
                log.error(e, exc_info=True)

                try:
                    os.remove(temp_file_path)
                except OSError:
                    pass
            else:
                # TODO: "" or None for faulty download, which is better?
                # os.path methods return "" in case something does not exist, I prefer this.
                # For now let's keep None
                path[0] = final_file_path or None
            finally:
                done.set()

    async def updates_worker(self):
        log.info("UpdatesWorkerTask started")

        while True:
            updates = await self.updates_queue.get()

            if updates is None:
                break

            try:
                if isinstance(updates, (types.Update, types.UpdatesCombined)):
                    self.fetch_peers(updates.users)
                    self.fetch_peers(updates.chats)

                    for update in updates.updates:
                        channel_id = getattr(
                            getattr(
                                getattr(
                                    update, "message", None
                                ), "to_id", None
                            ), "channel_id", None
                        ) or getattr(update, "channel_id", None)

                        pts = getattr(update, "pts", None)
                        pts_count = getattr(update, "pts_count", None)

                        if isinstance(update, types.UpdateChannelTooLong):
                            log.warning(update)

                        if isinstance(update, types.UpdateNewChannelMessage):
                            message = update.message

                            if not isinstance(message, types.MessageEmpty):
                                try:
                                    diff = await self.send(
                                        functions.updates.GetChannelDifference(
                                            channel=await self.resolve_peer(int("-100" + str(channel_id))),
                                            filter=types.ChannelMessagesFilter(
                                                ranges=[types.MessageRange(
                                                    min_id=update.message.id,
                                                    max_id=update.message.id
                                                )]
                                            ),
                                            pts=pts - pts_count,
                                            limit=pts
                                        )
                                    )
                                except ChannelPrivate:
                                    pass
                                else:
                                    if not isinstance(diff, types.updates.ChannelDifferenceEmpty):
                                        updates.users += diff.users
                                        updates.chats += diff.chats

                        if channel_id and pts:
                            if channel_id not in self.channels_pts:
                                self.channels_pts[channel_id] = []

                            if pts in self.channels_pts[channel_id]:
                                continue

                            self.channels_pts[channel_id].append(pts)

                            if len(self.channels_pts[channel_id]) > 50:
                                self.channels_pts[channel_id] = self.channels_pts[channel_id][25:]

                        self.dispatcher.updates_queue.put_nowait((update, updates.users, updates.chats))
                elif isinstance(updates, (types.UpdateShortMessage, types.UpdateShortChatMessage)):
                    diff = await self.send(
                        functions.updates.GetDifference(
                            pts=updates.pts - updates.pts_count,
                            date=updates.date,
                            qts=-1
                        )
                    )

                    if diff.new_messages:
                        self.dispatcher.updates_queue.put_nowait((
                            types.UpdateNewMessage(
                                message=diff.new_messages[0],
                                pts=updates.pts,
                                pts_count=updates.pts_count
                            ),
                            diff.users,
                            diff.chats
                        ))
                    else:
                        self.dispatcher.updates_queue.put_nowait((diff.other_updates[0], [], []))
                elif isinstance(updates, types.UpdateShort):
                    self.dispatcher.updates_queue.put_nowait((updates.update, [], []))
                elif isinstance(updates, types.UpdatesTooLong):
                    log.warning(updates)
            except Exception as e:
                log.error(e, exc_info=True)

        log.info("UpdatesWorkerTask stopped")

    async def send(self,
                   data: Object,
                   retries: int = Session.MAX_RETRIES,
                   timeout: float = Session.WAIT_TIMEOUT):
        """Use this method to send Raw Function queries.

        This method makes possible to manually call every single Telegram API method in a low-level manner.
        Available functions are listed in the :obj:`functions <pyrogram.api.functions>` package and may accept compound
        data types from :obj:`types <pyrogram.api.types>` as well as bare types such as ``int``, ``str``, etc...

        Args:
            data (``Object``):
                The API Schema function filled with proper arguments.

            retries (``int``):
                Number of retries.

            timeout (``float``):
                Timeout in seconds.

        Raises:
            :class:`RPCError <pyrogram.RPCError>` in case of a Telegram RPC error.
        """
        if not self.is_started:
            raise ConnectionError("Client has not been started")

        if self.no_updates:
            data = functions.InvokeWithoutUpdates(query=data)

        if self.takeout_id:
            data = functions.InvokeWithTakeout(takeout_id=self.takeout_id, query=data)

        r = await self.session.send(data, retries, timeout)

        self.fetch_peers(getattr(r, "users", []))
        self.fetch_peers(getattr(r, "chats", []))

        return r

    def load_config(self):
        parser = ConfigParser()
        parser.read(self.config_file)

        if self.api_id and self.api_hash:
            pass
        else:
            if parser.has_section("pyrogram"):
                self.api_id = parser.getint("pyrogram", "api_id")
                self.api_hash = parser.get("pyrogram", "api_hash")
            else:
                raise AttributeError(
                    "No API Key found. "
                    "More info: https://docs.pyrogram.ml/start/ProjectSetup#configuration"
                )

        for option in ["app_version", "device_model", "system_version", "lang_code"]:
            if getattr(self, option):
                pass
            else:
                if parser.has_section("pyrogram"):
                    setattr(self, option, parser.get(
                        "pyrogram",
                        option,
                        fallback=getattr(Client, option.upper())
                    ))
                else:
                    setattr(self, option, getattr(Client, option.upper()))

        if self._proxy:
            self._proxy["enabled"] = bool(self._proxy.get("enabled", True))
        else:
            self._proxy = {}

            if parser.has_section("proxy"):
                self._proxy["enabled"] = parser.getboolean("proxy", "enabled", fallback=True)
                self._proxy["hostname"] = parser.get("proxy", "hostname")
                self._proxy["port"] = parser.getint("proxy", "port")
                self._proxy["username"] = parser.get("proxy", "username", fallback=None) or None
                self._proxy["password"] = parser.get("proxy", "password", fallback=None) or None

        if self.plugins:
            self.plugins["enabled"] = bool(self.plugins.get("enabled", True))
            self.plugins["include"] = "\n".join(self.plugins.get("include", [])) or None
            self.plugins["exclude"] = "\n".join(self.plugins.get("exclude", [])) or None
        else:
            try:
                section = parser["plugins"]

                self.plugins = {
                    "enabled": section.getboolean("enabled", True),
                    "root": section.get("root"),
                    "include": section.get("include") or None,
                    "exclude": section.get("exclude") or None
                }
            except KeyError:
                self.plugins = {}

        if self.plugins:
            for option in ["include", "exclude"]:
                if self.plugins[option] is not None:
                    self.plugins[option] = [
                        (i.split()[0], i.split()[1:] or None)
                        for i in self.plugins[option].strip().split("\n")
                    ]

    async def load_session(self):
        try:
            with open(os.path.join(self.workdir, "{}.session".format(self.session_name)), encoding="utf-8") as f:
                s = json.load(f)
        except FileNotFoundError:
            self.dc_id = 1
            self.date = 0
            self.auth_key = await Auth(self.dc_id, self.test_mode, self.ipv6, self._proxy).create()
        else:
            self.dc_id = s["dc_id"]
            self.test_mode = s["test_mode"]
            self.auth_key = base64.b64decode("".join(s["auth_key"]))
            self.user_id = s["user_id"]
            self.date = s.get("date", 0)
            # TODO: replace default with False once token session name will be deprecated
            self.is_bot = s.get("is_bot", self.is_bot)

            for k, v in s.get("peers_by_id", {}).items():
                self.peers_by_id[int(k)] = utils.get_input_peer(int(k), v)

            for k, v in s.get("peers_by_username", {}).items():
                peer = self.peers_by_id.get(v, None)

                if peer:
                    self.peers_by_username[k] = peer

            for k, v in s.get("peers_by_phone", {}).items():
                peer = self.peers_by_id.get(v, None)

                if peer:
                    self.peers_by_phone[k] = peer

    def load_plugins(self):
        if self.plugins.get("enabled", False):
            root = self.plugins["root"]
            include = self.plugins["include"]
            exclude = self.plugins["exclude"]

            count = 0

            if include is None:
                for path in sorted(Path(root).rglob("*.py")):
                    module_path = '.'.join(path.parent.parts + (path.stem,))
                    module = import_module(module_path)

                    for name in vars(module).keys():
                        # noinspection PyBroadException
                        try:
                            handler, group = getattr(module, name)

                            if isinstance(handler, Handler) and isinstance(group, int):
                                self.add_handler(handler, group)

                                log.info('[LOAD] {}("{}") in group {} from "{}"'.format(
                                    type(handler).__name__, name, group, module_path))

                                count += 1
                        except Exception:
                            pass
            else:
                for path, handlers in include:
                    module_path = root + "." + path
                    warn_non_existent_functions = True

                    try:
                        module = import_module(module_path)
                    except ImportError:
                        log.warning('[LOAD] Ignoring non-existent module "{}"'.format(module_path))
                        continue

                    if "__path__" in dir(module):
                        log.warning('[LOAD] Ignoring namespace "{}"'.format(module_path))
                        continue

                    if handlers is None:
                        handlers = vars(module).keys()
                        warn_non_existent_functions = False

                    for name in handlers:
                        # noinspection PyBroadException
                        try:
                            handler, group = getattr(module, name)

                            if isinstance(handler, Handler) and isinstance(group, int):
                                self.add_handler(handler, group)

                                log.info('[LOAD] {}("{}") in group {} from "{}"'.format(
                                    type(handler).__name__, name, group, module_path))

                                count += 1
                        except Exception:
                            if warn_non_existent_functions:
                                log.warning('[LOAD] Ignoring non-existent function "{}" from "{}"'.format(
                                    name, module_path))

            if exclude is not None:
                for path, handlers in exclude:
                    module_path = root + "." + path
                    warn_non_existent_functions = True

                    try:
                        module = import_module(module_path)
                    except ImportError:
                        log.warning('[UNLOAD] Ignoring non-existent module "{}"'.format(module_path))
                        continue

                    if "__path__" in dir(module):
                        log.warning('[UNLOAD] Ignoring namespace "{}"'.format(module_path))
                        continue

                    if handlers is None:
                        handlers = vars(module).keys()
                        warn_non_existent_functions = False

                    for name in handlers:
                        # noinspection PyBroadException
                        try:
                            handler, group = getattr(module, name)

                            if isinstance(handler, Handler) and isinstance(group, int):
                                self.remove_handler(handler, group)

                                log.info('[UNLOAD] {}("{}") from group {} in "{}"'.format(
                                    type(handler).__name__, name, group, module_path))

                                count -= 1
                        except Exception:
                            if warn_non_existent_functions:
                                log.warning('[UNLOAD] Ignoring non-existent function "{}" from "{}"'.format(
                                    name, module_path))

            if count > 0:
                log.warning('Successfully loaded {} plugin{} from "{}"'.format(count, "s" if count > 1 else "", root))
            else:
                log.warning('No plugin loaded from "{}"'.format(root))

    def save_session(self):
        auth_key = base64.b64encode(self.auth_key).decode()
        auth_key = [auth_key[i: i + 43] for i in range(0, len(auth_key), 43)]

        os.makedirs(self.workdir, exist_ok=True)

        with open(os.path.join(self.workdir, "{}.session".format(self.session_name)), "w", encoding="utf-8") as f:
            json.dump(
                dict(
                    dc_id=self.dc_id,
                    test_mode=self.test_mode,
                    auth_key=auth_key,
                    user_id=self.user_id,
                    date=self.date,
                    is_bot=self.is_bot,
                ),
                f,
                indent=4
            )

    async def get_initial_dialogs_chunk(self,
                                        offset_date: int = 0):
        while True:
            try:
                r = await self.send(
                    functions.messages.GetDialogs(
                        offset_date=offset_date,
                        offset_id=0,
                        offset_peer=types.InputPeerEmpty(),
                        limit=self.DIALOGS_AT_ONCE,
                        hash=0,
                        exclude_pinned=True
                    )
                )
            except FloodWait as e:
                log.warning("get_dialogs flood: waiting {} seconds".format(e.x))
                await asyncio.sleep(e.x)
            else:
                log.info("Total peers: {}".format(len(self.peers_by_id)))
                return r

    async def get_initial_dialogs(self):
        await self.send(functions.messages.GetPinnedDialogs())

        dialogs = await self.get_initial_dialogs_chunk()
        offset_date = utils.get_offset_date(dialogs)

        while len(dialogs.dialogs) == self.DIALOGS_AT_ONCE:
            dialogs = await self.get_initial_dialogs_chunk(offset_date)
            offset_date = utils.get_offset_date(dialogs)

        await self.get_initial_dialogs_chunk()

    async def resolve_peer(self,
                           peer_id: Union[int, str]):
        """Use this method to get the InputPeer of a known peer_id.

        This is a utility method intended to be used **only** when working with Raw Functions (i.e: a Telegram API
        method you wish to use which is not available yet in the Client class as an easy-to-use method), whenever an
        InputPeer type is required.

        Args:
            peer_id (``int`` | ``str``):
                The peer id you want to extract the InputPeer from.
                Can be a direct id (int), a username (str) or a phone number (str).

        Returns:
            On success, the resolved peer id is returned in form of an InputPeer object.

        Raises:
            :class:`RPCError <pyrogram.RPCError>` in case of a Telegram RPC error.
            ``KeyError`` in case the peer doesn't exist in the internal database.
        """
        try:
            return self.peers_by_id[peer_id]
        except KeyError:
            if type(peer_id) is str:
                if peer_id in ("self", "me"):
                    return types.InputPeerSelf()

                peer_id = re.sub(r"[@+\s]", "", peer_id.lower())

                try:
                    int(peer_id)
                except ValueError:
                    if peer_id not in self.peers_by_username:
                        await self.send(functions.contacts.ResolveUsername(username=peer_id
                                                                           )
                                        )

                    return self.peers_by_username[peer_id]
                else:
                    try:
                        return self.peers_by_phone[peer_id]
                    except KeyError:
                        raise PeerIdInvalid

            if peer_id > 0:
                self.fetch_peers(
                    await self.send(
                        functions.users.GetUsers(
                            id=[types.InputUser(user_id=peer_id, access_hash=0)]
                        )
                    )
                )
            else:
                if str(peer_id).startswith("-100"):
                    await self.send(
                        functions.channels.GetChannels(
                            id=[types.InputChannel(channel_id=int(str(peer_id)[4:]), access_hash=0)]
                        )
                    )
                else:
                    await self.send(
                        functions.messages.GetChats(
                            id=[-peer_id]
                        )
                    )

            try:
                return self.peers_by_id[peer_id]
            except KeyError:
                raise PeerIdInvalid

    async def save_file(self,
                        path: str,
                        file_id: int = None,
                        file_part: int = 0,
                        progress: callable = None,
                        progress_args: tuple = ()):
        """Use this method to upload a file onto Telegram servers, without actually sending the message to anyone.

        This is a utility method intended to be used **only** when working with Raw Functions (i.e: a Telegram API
        method you wish to use which is not available yet in the Client class as an easy-to-use method), whenever an
        InputFile type is required.

        Args:
            path (``str``):
                The path of the file you want to upload that exists on your local machine.

            file_id (``int``, *optional*):
                In case a file part expired, pass the file_id and the file_part to retry uploading that specific chunk.

            file_part (``int``, *optional*):
                In case a file part expired, pass the file_id and the file_part to retry uploading that specific chunk.

            progress (``callable``, *optional*):
                Pass a callback function to view the upload progress.
                The function must take *(client, current, total, \*args)* as positional arguments (look at the section
                below for a detailed description).

            progress_args (``tuple``, *optional*):
                Extra custom arguments for the progress callback function. Useful, for example, if you want to pass
                a chat_id and a message_id in order to edit a message with the updated progress.

        Other Parameters:
            client (:obj:`Client <pyrogram.Client>`):
                The Client itself, useful when you want to call other API methods inside the callback function.

            current (``int``):
                The amount of bytes uploaded so far.

            total (``int``):
                The size of the file.

            *args (``tuple``, *optional*):
                Extra custom arguments as defined in the *progress_args* parameter.
                You can either keep *\*args* or add every single extra argument in your function signature.

        Returns:
            On success, the uploaded file is returned in form of an InputFile object.

        Raises:
            :class:`RPCError <pyrogram.RPCError>` in case of a Telegram RPC error.
        """

        async def worker(session):
            while True:
                data = await queue.get()

                if data is None:
                    return

                try:
                    await asyncio.ensure_future(session.send(data))
                except Exception as e:
                    log.error(e)

        part_size = 512 * 1024
        file_size = os.path.getsize(path)

        if file_size == 0:
            raise ValueError("File size equals to 0 B")

        if file_size > 1500 * 1024 * 1024:
            raise ValueError("Telegram doesn't support uploading files bigger than 1500 MiB")

        file_total_parts = int(math.ceil(file_size / part_size))
        is_big = file_size > 10 * 1024 * 1024
        pool_size = 3 if is_big else 1
        workers_count = 4 if is_big else 1
        is_missing_part = file_id is not None
        file_id = file_id or self.rnd_id()
        md5_sum = md5() if not is_big and not is_missing_part else None
        pool = [Session(self, self.dc_id, self.auth_key, is_media=True) for _ in range(pool_size)]
        workers = [asyncio.ensure_future(worker(session)) for session in pool for _ in range(workers_count)]
        queue = asyncio.Queue(16)

        try:
            for session in pool:
                await session.start()

            with open(path, "rb") as f:
                f.seek(part_size * file_part)

                while True:
                    chunk = f.read(part_size)

                    if not chunk:
                        if not is_big:
                            md5_sum = "".join([hex(i)[2:].zfill(2) for i in md5_sum.digest()])
                        break

                    if is_big:
                        rpc = functions.upload.SaveBigFilePart(
                            file_id=file_id,
                            file_part=file_part,
                            file_total_parts=file_total_parts,
                            bytes=chunk
                        )
                    else:
                        rpc = functions.upload.SaveFilePart(
                            file_id=file_id,
                            file_part=file_part,
                            bytes=chunk
                        )

                    await queue.put(rpc)

                    if is_missing_part:
                        return

                    if not is_big:
                        md5_sum.update(chunk)

                    file_part += 1

                    if progress:
                        await progress(self, min(file_part * part_size, file_size), file_size, *progress_args)
        except Client.StopTransmission:
            raise
        except Exception as e:
            log.error(e, exc_info=True)
        else:
            if is_big:
                return types.InputFileBig(
                    id=file_id,
                    parts=file_total_parts,
                    name=os.path.basename(path),

                )
            else:
                return types.InputFile(
                    id=file_id,
                    parts=file_total_parts,
                    name=os.path.basename(path),
                    md5_checksum=md5_sum
                )
        finally:
            for _ in workers:
                await queue.put(None)

            await asyncio.gather(*workers)

            for session in pool:
                await session.stop()

    async def get_file(self,
                       dc_id: int,
                       id: int = None,
                       access_hash: int = None,
                       volume_id: int = None,
                       local_id: int = None,
                       secret: int = None,

                       size: int = None,
                       progress: callable = None,
                       progress_args: tuple = ()) -> str:
        with await self.media_sessions_lock:
            session = self.media_sessions.get(dc_id, None)

            if session is None:
                if dc_id != self.dc_id:
                    exported_auth = await self.send(
                        functions.auth.ExportAuthorization(
                            dc_id=dc_id
                        )
                    )

                    session = Session(
                        self,
                        dc_id,
                        await Auth(dc_id, self.test_mode, self.ipv6, self._proxy).create(),
                        is_media=True
                    )

                    await session.start()

                    self.media_sessions[dc_id] = session

                    await session.send(
                        functions.auth.ImportAuthorization(
                            id=exported_auth.id,
                            bytes=exported_auth.bytes
                        )
                    )
                else:
                    session = Session(
                        self,
                        dc_id,
                        self.auth_key,
                        is_media=True
                    )

                    await session.start()

                    self.media_sessions[dc_id] = session

        if volume_id:  # Photos are accessed by volume_id, local_id, secret
            location = types.InputFileLocation(
                volume_id=volume_id,
                local_id=local_id,
                secret=secret,
                file_reference=b""
            )
        else:  # Any other file can be more easily accessed by id and access_hash
            location = types.InputDocumentFileLocation(
                id=id,
                access_hash=access_hash,
                file_reference=b""
            )

        limit = 1024 * 1024
        offset = 0
        file_name = ""

        try:
            r = await session.send(
                functions.upload.GetFile(
                    location=location,
                    offset=offset,
                    limit=limit
                )
            )

            if isinstance(r, types.upload.File):
                with tempfile.NamedTemporaryFile("wb", delete=False) as f:
                    file_name = f.name

                    while True:
                        chunk = r.bytes

                        if not chunk:
                            break

                        f.write(chunk)

                        offset += limit

                        if progress:
                            await progress(self, min(offset, size) if size != 0 else offset, size, *progress_args)

                        r = await session.send(
                            functions.upload.GetFile(
                                location=location,
                                offset=offset,
                                limit=limit
                            )
                        )

            elif isinstance(r, types.upload.FileCdnRedirect):
                with await self.media_sessions_lock:
                    cdn_session = self.media_sessions.get(r.dc_id, None)

                    if cdn_session is None:
                        cdn_session = Session(
                            self,
                            r.dc_id,
                            await Auth(r.dc_id, self.test_mode, self.ipv6, self._proxy).create(),
                            is_media=True,
                            is_cdn=True
                        )

                        await cdn_session.start()

                        self.media_sessions[r.dc_id] = cdn_session

                try:
                    with tempfile.NamedTemporaryFile("wb", delete=False) as f:
                        file_name = f.name

                        while True:
                            r2 = await cdn_session.send(
                                functions.upload.GetCdnFile(
                                    file_token=r.file_token,
                                    offset=offset,
                                    limit=limit
                                )
                            )

                            if isinstance(r2, types.upload.CdnFileReuploadNeeded):
                                try:
                                    await session.send(
                                        functions.upload.ReuploadCdnFile(
                                            file_token=r.file_token,
                                            request_token=r2.request_token
                                        )
                                    )
                                except VolumeLocNotFound:
                                    break
                                else:
                                    continue

                            chunk = r2.bytes

                            # https://core.telegram.org/cdn#decrypting-files
                            decrypted_chunk = AES.ctr256_decrypt(
                                chunk,
                                r.encryption_key,
                                bytearray(
                                    r.encryption_iv[:-4]
                                    + (offset // 16).to_bytes(4, "big")
                                )
                            )

                            hashes = await session.send(
                                functions.upload.GetCdnFileHashes(
                                    file_token=r.file_token,
                                    offset=offset
                                )
                            )

                            # https://core.telegram.org/cdn#verifying-files
                            for i, h in enumerate(hashes):
                                cdn_chunk = decrypted_chunk[h.limit * i: h.limit * (i + 1)]
                                assert h.hash == sha256(cdn_chunk).digest(), "Invalid CDN hash part {}".format(i)

                            f.write(decrypted_chunk)

                            offset += limit

                            if progress:
                                await progress(self, min(offset, size) if size != 0 else offset, size, *progress_args)

                            if len(chunk) < limit:
                                break
                except Exception as e:
                    raise e
        except Exception as e:
            if not isinstance(e, Client.StopTransmission):
                log.error(e, exc_info=True)

            try:
                os.remove(file_name)
            except OSError:
                pass

            return ""
        else:
            return file_name

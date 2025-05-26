#!/usr/bin/env python3

# Slixmpp: The Slick XMPP Library
# Copyright (C) 2010  Nathanael C. Fritz
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

import logging
import email.parser
from email.policy import default
import sys
import configparser
from textwrap import dedent
from pathlib import Path
from argparse import ArgumentParser, RawTextHelpFormatter

import asyncio
import slixmpp


class SendMsgBot(slixmpp.ClientXMPP):
    """
    A basic sendmail replacement for sending stuff over xmpp. It even supports group chats (XEM-0045).
    """

    def __init__(self, jid, password, message):
        if jid is None or password is None or message is None:
            raise Exception(f"No none args allowed ({jid}/{password}/{message})")

        slixmpp.ClientXMPP.__init__(self, jid, password)

        self._parse_msg(msg)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)

    def _parse_msg(self, msg):
        """parse our message, recipients, nickname, ... from the email message object"""
        self.recipients = [
            (
                (
                    parts[1]
                    if len(parts := a.username.split("/", maxsplit=1)) == 2
                    else None
                ),
                slixmpp.JID(f"{parts[0]}@{a.domain}"),
            )
            for a in msg["to"].addresses
        ]

        self.nickname = msg["from"]
        self.message = f"*Subject*: {msg['Subject']}\n{msg.get_content()}"

    async def start(self, event):
        """
        Process the session_start event.
        """
        await self.get_roster()
        self.send_presence()

        # iterate over all recipients and send the respective message
        for mtype, recipient in self.recipients:
            if mtype == "groupchat":
                await self.plugin["xep_0045"].join_muc_wait(recipient, self.nickname)

            self.send_message(mto=recipient, mbody=self.message, mtype=mtype)

        self.disconnect()


def parse_stdin_input():
    # read the incoming message, we need to lstrip empty lines for the parser to work
    msg_str = sys.stdin.read().lstrip()
    msg = email.parser.Parser(policy=default).parsestr(msg_str)
    return msg


if __name__ == "__main__":
    # Setup the command line arguments.
    parser = ArgumentParser(
        description=dedent(SendMsgBot.__doc__),
        formatter_class=RawTextHelpFormatter,
        epilog=dedent(
            """
            All information regarding nickname and recipient addresses will be parsed
            from stdin using the Internet Message Format. For example:

              From: bot@home-server
              To: <user@xmpp.me>, <group/groupchat@muc.xmpp.me>
              Subject: Huston, we got a problem

              The mainframe is down.

            The nickname for groupchats (muc / XEM-0045) will be assigned using the
            `from` field. Recipients are specified under `To` with the addition that
            groupchats must marked using the format `username/groupchat@domain`.

            An alternative to specifying the login and password of the xmpp account
            as arguments, one can use a configuration file. By default this file is located
            at `/etc/xmpp/sendxmpp.ini` and it follows the following syntax:

              [account]
              jid = bot@xmpp.bot
              password = botpassword
        """
        ),
    )

    # Output verbosity options.
    parser.add_argument(
        "-q",
        "--quiet",
        help="set logging to ERROR",
        action="store_const",
        dest="loglevel",
        const=logging.ERROR,
        default=logging.INFO,
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="set logging to DEBUG",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )

    parser.add_argument(
        "-C",
        "--config-file",
        help="alternative config file location",
        default="/etc/xmpp/sendxmpp.ini",
    )

    # JID and password options.
    parser.add_argument("--jid", dest="jid", help="JID to use")
    parser.add_argument("--password", dest="password", help="password to use")

    parser.add_argument(
        "-t",
        help=(
            "Read message for recipients (required).\n"
            "One can specify message type (e.g. groupchat) using"
            "`username/mtype@domain`\nin the `to` field."
        ),
        required=True,
        action="store_true",
    )

    args, unknown = parser.parse_known_args()
    # Setup logging.
    logging.basicConfig(level=args.loglevel, format="%(levelname)-8s %(message)s")

    logging.info(f"Ignoring args {unknown}")

    user_jid = args.jid
    user_password = args.password

    # parse the sendxmpp.ini file
    if Path(args.config_file).is_file():
        config = configparser.ConfigParser()
        config.read(args.config_file)
        user_jid = config["account"]["jid"]
        user_password = config["account"]["password"]
    else:
        logging.warning(f"Config file `{args.config_file}` does not exist")

    # read mail from stdin
    msg = parse_stdin_input()

    # Setup the EchoBot and register plugins. Note that while plugins may
    # have interdependencies, the order in which you register them does
    # not matter.
    xmpp = SendMsgBot(user_jid, user_password, msg)
    xmpp.register_plugin("xep_0030")  # Service Discovery
    xmpp.register_plugin("xep_0199")  # XMPP Ping
    xmpp.register_plugin("xep_0045")  # XMPP MUC

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect()
    asyncio.get_event_loop().run_until_complete(xmpp.disconnected)

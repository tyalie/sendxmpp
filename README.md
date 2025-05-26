# sendxmpp - a xmpp sendmail replacement

When monitoring a server, a lot of Linux tools rely on sendmail to send status
reports to the sys admin (👀 Debians `unattended-upgrades`). Integrating some
other means of communication can either require a lot of changes to random
tools or be a bit dirty by e.g. replacing the command that is most often used
for that purpose, which is exactly what this tool is for.

All calls to sendmail will instead be sent over xmpp in a nicely formatted
manner. The tool will also abuse the mail syntax so that the to and from
address will specify which person or MUCs will be addressed and which nickname
should be used.

## Usage

The script assumes that recipient addresses and such can be parsed from stdin.
So the `-t` argument is required (see sendmail man-page).

The syntax for a message follows the Internet Message Format, e.g.

```mail
From: bot@home-server
To: <user@xmpp.me>, <group/groupchat@muc.xmpp.me>
Subject: Huston, we got a problem

The mainframe is down.
```

This message will be sent to the group chat (MUC / XEM-0045)
`group@muc.xmpp.me` and to the jid `user@xmpp.me`. Generally one can specify
the message type in the recipient address using the syntax
`username/message-type@domain`.

## Installation

The following steps are needed for it to act as an sendmail replacement:
1. download the repo somewhere
2. make sure everything from `requirements.txt` is accessible from python run by root
3. (optional) uninstall your sendmail provider
4. copy or link script to `/usr/sbin/sendmail` using `cp sendxmpp.py /usr/sbin/sendmail`

### Configuration

One can deploy a configuration file in `/etc/xmpp/sendxmpp.ini` with the following content:

```ini
[account]
jid = JID@DOMAIN
password = THEPWD
```

## Example
From bash

```bash
$ ./sendmail.py -t << MESSAGE_END
To: <sysadmin/groupchat@muc.xmpp.me>
From: hypervisor@home
Subject: status update

nothing out of the ordinary
MESSAGE_END
```

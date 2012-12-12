#! /usr/bin/env python
#
# espeak.py
# Use espeak, part of Make Your Own Sugar Activities Book Examples.
# Copyright (C) 2010  James D. Simmons
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import re
import subprocess

PITCH_MAX = 99
RATE_MAX = 99
PITCH_DEFAULT = PITCH_MAX/2
RATE_DEFAULT = RATE_MAX/3

def speak(text, rate=RATE_DEFAULT, pitch=PITCH_DEFAULT, voice="default"):

    # espeak uses 80 to 370
    rate = 80 + (370-80) * int(rate) / 100

    subprocess.call(["espeak", "-p", str(pitch),
                     "-s", str(rate), "-v", voice,  text],
                    stdout=subprocess.PIPE)

def voices():
    out = []
    result = subprocess.Popen(["espeak", "--voices"], stdout=subprocess.PIPE) \
             .communicate()[0]

    for line in result.split('\n'):
        m = re.match(r'\s*\d+\s+([\w-]+)\s+([MF])\s+([\w_-]+)\s+(.+)', line)
        if not m:
            continue
        language, gender, name, stuff = m.groups()
        if stuff.startswith('mb/') or \
               name in ('en-rhotic','english_rp','english_wmids'):
            # these voices don't produce sound
            continue
        out.append((language, name))

    return out

def main():
    print voices()
    speak("I'm afraid I can't do that, Dave.")
    speak("Your mother was a hamster, and your father smelled of elderberries!",  30,  60,  "fr")

if __name__ == "__main__":
    main()

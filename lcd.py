#!/usr/bin/python3

# TODO [feature]     volume and song number in nowplaying screen
# TODO [aestetic]    send to display method is not clean, find a foolproof way to update or refresh whole screen.
# TODO [aestetic]    implement scroll with library option, something like scroll_left()/scroll_right...
# TODO [performance] also turn off display instead of only turn off backlight
# TODO [performance] dont write to display if backlight is off


try:
    import os,sys
    from Adafruit_CharLCD import Adafruit_CharLCD
    import RPi.GPIO as GPIO
    from time import sleep
    from time import time
    import mpd
    import os, sys
    from itertools import cycle
    import threading
    import inspect
    import re
    from time import strftime
    from xbmcjson import XBMC, PLAYER_VIDEO
    # For Kodi
    import json
    from urllib.request import Request, urlopen
    import wifi
    import socket
    import netifaces
except ImportError as e:
     print('Error: One or more libraries are not installed!\nRun: /usr/bin/pip3 install <packagename>')
     print('Error:', e)
     exit()


class StoppableThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_flag = threading.Event()
                                                                                                                                                                     
                                                                                                                                                                     
    def stop(self):
        if self.isAlive() == True:
            self.stop_flag.set()
                                                                                                                                                                     
                                                                                                                                                                     
    def stopped(self):
        return self.stop_flag.is_set()



class Log(object):
    def __init__(self, logfile=False, level='debug', display=True, maxlength=20):
        self.logfile = logfile
        self.display = display
        self.level = level
        self.maxlength = maxlength

        self.colors = { 'red'    : '\033[31m',
                        'white'  : '\033[37m',
                        'gray'   : '\033[0m',
                        'orange' : '\033[33m',
                        'blue'   : '\033[34m',
                        'green'  : '\033[32m',
                        'reset'  : '\033[0m' }

        self.colors_levels = { 'info'    : 'white',
                               'error'   : 'red',
                               'debug'   : 'gray',
                               'warning' : 'orange' }

        self.custom_highlights = {}


    def choose_show(self, level):
        """ Decide if a message should be shown based on configured message level """
        if self.level == 'error' and (level == 'debug' or level == 'warning' or level == 'info'):
            return False
        if self.level == 'warning' and (level =='debug' or level == 'info'):
            return False
        if self.level == 'info' and (level == 'debug'):
            return False
        return True


    def create_message(self, level, module, message):
        # TODO: Add feature to detect lists/dicts and print them out nicely
        if self.choose_show(level):
            message = self.detect_type(message)
            module_justified = module.ljust(self.maxlength)
            level_justified = level.ljust(7)
            time = strftime("%H:%M:%S")

            if self.display:
                print("{0} {1} {2} {3}".format(module_justified,
                                               self.colors[self.colors_levels[level]],
                                               self.custom_highlight(message, self.colors[self.colors_levels[level]]),
                                               self.colors['reset']))

            if self.logfile:
                self.write_to_file("{0} {1}{2}{3}\n".format(strftime("%Y-%m-%d %H:%M:%S"),
                                                            level_justified,
                                                            module_justified,
                                                            message))


    def detect_type(self, message):
        """ Detect whether message is list or dict """
        if type(message) == list:
            message = ' , '.join(message)
        elif type(message) == dict:
            message_out = ''
            for k,v in message.items():
                message_out = "{0}\n{1} : {2}".format(message_out,k,v)
            message = message_out
        return message


    def create_file(self):
        """ Create a file if it doesn't exist """
        try:
            with open(self.logfile) as f: pass
        except IOError as e:
            try:
                FILE = open(self.logfile, 'w')
                FILE.close()
            except IOError as e:
                print('WARNING ... Couldn\'t create file \'%s\' Not writing logs!'%self.logfile)
                return False
        return True


    def write_to_file(self, message):
        if self.create_file():
            try:
                FILE = open(self.logfile, 'a')
                FILE.write(message)
                FILE.close()
            except:
                print('Failed to write to logfile')


    def custom_highlight(self, message, reset_color):
        if message:
            for string, color in self.custom_highlights.items():
                message = re.sub( string, self.colors[color] + string + reset_color, message)
        return message


    def color(self, string, color):
        """ Callable method to add a custom highlight eg. ( log.color('what_to_highlight', 'color_to_use') ) """
        self.custom_highlights[string] = color


    def info(self, message):
        self.create_message('info', inspect.stack()[1][3], message)


    def debug(self, message):
        self.create_message('debug', inspect.stack()[1][3], message)


    def warning(self, message):
        self.create_message('warning', inspect.stack()[1][3], message)


    def error(self, message):
        self.create_message('error', inspect.stack()[1][3], message)


    def red(self, message):
        self.create_message('info', inspect.stack()[1][3], message)


    def blue(self, message):
        self.create_message('info', inspect.stack()[1][3], message)


    def green(self, message):
        self.create_message('info', inspect.stack()[1][3], message)


    def orange(self, message):
        self.create_message('info', inspect.stack()[1][3], message)



class MPDHandler(object):
    def __init__(self, host="localhost", port=6600):
        self.host = host
        self.port = port


    def start_mpd(self):
        try:
            self.mpd = mpd.MPDClient()
            self.mpd.connect(self.host, self.port)
            self.mpd.timeout = 10
            log.info("Connected to MPD on port 6600")
            return True
        except:
            log.error("Failed to connect to MPD on {0}:{1}".format(self.host, self.port))
            return False


    def idle(self):
        return self.mpd.idle()


    def noidle(self):
        result = self.mpd.noidle()


    def check_connection(self):
        # Check if connection to MPD is still OK and reconnect when necessary
        if not self.get_status():
            if not self.start_mpd():
                return False
        return True


    def get_current_artist(self):
        try:
            if "artist" in self.mpd.currentsong(): 
                return self.mpd.currentsong()["artist"]
            elif "name" in self.mpd.currentsong(): 
                return self.mpd.currentsong()["name"]
        except:
               pass
        log.error("Failed to get current artist")
        return "Unknown"


    def get_current_title(self):
        try:
            if "title" in self.mpd.currentsong():
                return self.mpd.currentsong()["title"]
        except:
               pass
        log.error("Failed to get current title")
        return "Unknown"


    def get_current_album(self):
        try:
            if "album" in self.mpd.currentsong():
                return self.mpd.currentsong()["album"]
        except:
               pass
        log.error("Failed to get current album")
        return "Unknown"


    def get_playlist(self):
        try:
            return self.mpd.playlistinfo()
        except:
            log.error("Failed to get playlist")
            return False


    def get_playlist_length(self, playlist):
        if playlist:
            return len(playlist)
        log.error("Failed to get playlist length")
        return False
        

    def get_current_songid(self):
        try:
            cur = self.mpd.currentsong()
            return int(cur["pos"])
        except:
            log.error("Failed to get current songid")
            return False


    def get_pos_in_playlist(self, playlist, songid):
        pos = 0
        for song in playlist:
            if not int(song['pos']) == int(songid):
                pos += 1
            else:
                return pos
        log.error("Songid not found in playlist")
        return False


    def get_status(self):
        # Return state (paused, playing, stopped)                                    
        try:                                                                         
            return self.mpd.status()                                               
        except:                                                                      
            log.error("Failed to get MPD state")                                         
            return False


    def get_volume(self):
        try:
            return self.mpd.status()["volume"]
        except:
            log.error("Failed to get MPD volume")                                         
            return False


    def get_tag(self, tag):
        try:
            return self.mpd.list(tag)
        except:
            log.error("Failed to get tag {0}".format(tag))
            return False


    def do_find_add(self, tag, what):
        try:
            return self.mpd.findadd(tag, what)
        except:
            log.error("Failed to add {0} to tag {1}".format(what, tag))
            return False


    def get_playlists(self):
        try:
            return self.mpd.listplaylists()
        except:
            log.error("Failed to get playlists")
            return False


    def do_load_playlist(self, playlist):
        try:
            self.mpd.load(playlist)
        except:
            log.error("Failed to load playlist")
            return False


    def is_playing(self):                                                         
        try:
            if self.get_status()['state'] == 'play':
                return True
            else:
                return False
        except:
            return False


    def is_paused(self):                                                         
        try:
            if self.get_status()['state'] == 'pause':
                return True
            else:
                return False
        except:
            log.error("Failed to get paused state")
            return False


    def is_stopped(self):                                                         
        try:
            if self.get_status()['state'] == 'stop':
                return True
            else:
                return False
        except:
            log.error("Failed to get stopped state")
            return False


    def do_play(self):
        try:
            log.debug("play")
            if self.is_stopped():
                self.mpd.play(0)
            else:
                self.mpd.pause(0)
        except:
            log.error("Failed to play MPD")
            return False


    def do_pause(self):
        try:
            self.mpd.pause(1)
            log.debug("pause")
        except:
            log.error("Failed to pause MPD")
            return False


    def do_toggle(self):
        if self.is_stopped():
            self.do_play_id(0)
        elif self.is_paused():
            self.do_play()
        else:
            self.do_pause()


    def do_prev(self):
        try:
            playlist = self.get_playlist()
            songid = self.get_current_songid()
            if playlist and songid:
                if self.get_pos_in_playlist(playlist, songid) == 0:
                    log.error("We are playing the first song on playlist")
                    return False

            log.debug("play previous")
            self.mpd.previous()
        except:
            log.error("Failed to play previous song")
            return False


    def do_next(self):
        try:
            playlist = self.get_playlist()
            songid = self.get_current_songid()
            if playlist and songid:
                if self.get_pos_in_playlist(playlist, songid) == self.get_playlist_length(playlist) -1:
                    log.error("We are playing the last song on playlist")
                    return False
            log.debug("play next")
            self.mpd.next()
        except:
            log.error("Failed to play next song")
            return False


    def do_play_id(self, id):
        try:
            self.mpd.playid(id)
            return True
        except:
            log.error("Failed to play song id")
            return False


    def do_clear_playlist(self):
        try:
            return self.mpd.clear()
        except:
            log.error("Failed to play clear current playlist")
            return False


    def set_vol(self, inc):
        # TODO rewrite these to one method, volume down could be a negative number
        log.debug("Set volume: {}/{}".format(inc, self.get_volume()))
        new_vol = int(self.get_volume()) + inc

        if new_vol >= 100:
            new_vol = 100
        if new_vol <= 0:
            new_vol = 0

        try:
            self.mpd.setvol(new_vol)
            return new_vol
        except:
            log.error("Failed to set volume")
            return False


    def do_update_database(self):
        try:
            return self.mpd.update()
        except:
            log.error("Failed to update MPD database")
            return False



class LCD(object):
    def __init__(self):
        lcd_rs = 18
        lcd_en = 23
        lcd_d4 = 24
        lcd_d5 = 25
        lcd_d6 = 12
        lcd_d7 = 16
        self.lcd_columns = 20
        self.lcd_rows = 4
        lcd_backlight = 4

        self.lcd_led = 20


        #GPIO.setup([lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_backlight], GPIO.OUT)

        GPIO.setup(self.lcd_led, GPIO.OUT)

        self.lcd = Adafruit_CharLCD(lcd_rs, lcd_en, lcd_d4, \
                lcd_d5, lcd_d6, lcd_d7, self.lcd_columns, \
                self.lcd_rows, lcd_backlight)

        self.lcd.show_cursor(False)

        # Dict that holds the current display text
        self.display_content = {}
        for row in range(0, self.lcd_rows):
            self.display_content[row] = ""

        # How many seconds should backlight stay on without user input
        self.lcd_backlight_stay_on = 30

        # Track on/off value of backlight
        self.backlight_state = False

        # How often should the backlight thread check for changes
        self.backlight_delay = 0.5

        # Keep track of time of latest input so we know when to turn backlight on/off
        self.t_last_input = time()



    def send_to_display(self, msg, row=0, col=0, center=False, clear=True, force=False, only_update=False, time=False):
        # TODO reason 4th line is not displayed is because the line for this row is the same so it will not be displayed
        #       solution is force
        if type(msg) == dict:
            for row in lcd.lcd_rows:
                if row in msg:
                    self.lcd.message(msg[row])
                else:
                    self.lcd.message("")
                    
                    

        if not self.display_content[row] == msg or force:
            msg_out = msg

            if clear:
                self.lcd.clear()
                for item in self.display_content:
                    self.display_content[item] = ""


            if center:
                msg_out = msg.center(self.lcd_columns)
                col = 0

            self.lcd.set_cursor(col, row)
            max_length = self.lcd_columns - col
            msg_out = msg_out.ljust(max_length)
            msg_out = msg_out[:max_length]
            self.lcd.message(msg_out)
            self.display_content[row] = msg

        if time:
            sleep(time)



class Helper(object):
    def __init__(self):
        # BUTTONS -----------------------------------------------------
        # Function:         BTN1   A1   GND   B1   GND   A2   B2   BTN2
        # Connector pin:       1    2     3    4     5    6    7      8 
        # RPI GPIO pin:       17   27         22          5    6      4
        # -------------------------------------------------------------

        self.default_state = 0
        #self.buttons = { 19 : "left",
        #                 13 : "right" }
        self.buttons = {}

        # short, long
        self.long_press_buttons = { 4 : [ "select", "back" ],
                                   17 : [ "button2", "button2_long" ] }


        self.encoders = { "enc2" : [ 27, 22 ],
                          "enc1" : [ 5, 6 ] }

        # Time between checks for buttonpresses
        self.scroll_delay = 0.1

        for button in self.buttons:
            GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        for button in self.long_press_buttons:
            GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        for enc in self.encoders:
            for enc_ab in self.encoders[enc]:
                GPIO.setup(enc_ab, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Keep track of time of last input so we know when to dim backlight
        self.t_last_input = time()

        # Which context are we in, eg: mpd, bluetooth etc.
        self.main_menu_opts = ["mpd", "bluetooth", "Kodi Remote", "Wifi Settings", "Reboot", "Shutdown"]
        self.menu_select_char = ">"

        self.mpd_hosts = [ { "host" : "ecobox", 
                             "port" : "6600" } ,
                           { "host" : "localhost",
                             "port" : "6600" } ,
                           { "host" : "eeebox",
                             "port" : "6600" } ]
        #self.mpd_host = "localhost"
        self.mpd_port = 6600
        self.full_block = ( 0b00000,
                       0b00000,
                       0b00000,
                       0b00000,
                       0b00000,
                       0b00000,
                       0b00000,
                       0b00000 )

        self.graph_left_char = "|"
        self.graph_right_char = " "
        self.lock = False

        # TODO create special mode for volume so we can have a special volume screen


    def get_event(self, channel):
        log.info(channel)
        if channel in self.long_press_buttons:
            if self.check_pin_state(channel):
                if self.is_long_press(channel):
                    return self.long_press_buttons[channel][1]
                else:
                    return self.long_press_buttons[channel][0]

        if channel in self.buttons:
            return self.buttons[channel]

        for enc in self.encoders:
            if channel == self.encoders[enc][0]:
                direction = self.get_enc_direction(self.encoders[enc][0], self.encoders[enc][1])
                if direction:
                    return "{0}_{1}".format(enc, direction)

        return False


    def setup_channels(self, func):
        # add rising edge detection on a channel
        for button in self.buttons:
            GPIO.remove_event_detect(button)
            GPIO.add_event_detect(button, GPIO.RISING, callback=func, bouncetime=200)

        for enc in self.encoders:
            GPIO.remove_event_detect(self.encoders[enc][0])
            GPIO.add_event_detect(self.encoders[enc][0], GPIO.FALLING, callback=func, bouncetime=5)

        for button in self.long_press_buttons:
            GPIO.remove_event_detect(button)
            GPIO.add_event_detect(button, GPIO.BOTH, callback=func, bouncetime=200)


    def is_long_press(self, channel, t_delay=.5):
        # Only catch rising edges, then wait for falling edges, measure time in between
        t = time()
        while self.check_pin_state(channel):
            if t + t_delay < time():
                log.debug("long press")
                return True
        log.debug("short press")
        return False


    def get_enc_direction(self, enc_a, enc_b):
        Switch_A = GPIO.input(enc_a)
        Switch_B = GPIO.input(enc_b)
        log.info("a:b  >  {0}:{1}".format(Switch_A, Switch_B))
        """
        A and B are connected through a pull up resistor
        This function gets triggered on the falling edge of A

        Left:
        When falling edge is detected at (1) b=0
        Now wait for A edge to rise again at (2)
        if B=1 then cycle is complete.

        A---1    -----
            |    |
            |    |
            |----2
        B--    -----
          |    |
          |    |
          |----|

        Right:
        When falling edge is detected at (1) b=1
        Now wait for A edge to rise again at (2)
        if B=0 then cycle is complete.

        A--1    -----
           |    |
           |    |
           |----2
        B-----    -----
             |    |
             |    |
             |----|
        """

        if (Switch_A == 0) and (Switch_B == 1):
            while Switch_A == 0:
                Switch_A = GPIO.input(enc_a)
            if GPIO.input(enc_b) == 0:
                log.debug("------>")
                return "up"
            log.error("right:  a:b  >  {0}:{1}".format(Switch_A, Switch_B))

        elif (Switch_A == 0) and (Switch_B == 0):
            while Switch_A == 0:
                Switch_A = GPIO.input(enc_a)
            if GPIO.input(enc_b) == 1:
                log.debug("<------")
                return "down"
            log.error("left:  a:b  >  {0}:{1}".format(Switch_A, Switch_B))
        else:
            log.error("a:b  >  {0}:{1}".format(Switch_A, Switch_B))

        return False


    def check_pin_state_rotary(self, pin):
        if GPIO.input(pin):
            log.debug("PIN {0} is on".format(pin))
            return True
        return False


    def get_graphbar(self, value, length, char_left="|", char_right="."):
        graphbar1 = ''
        graphbar2 = ''
        level = int(value) / 100 * length

        for i in range(0, int(level)):
            graphbar1 = graphbar1 + self.graph_left_char
        for i in range((int(level)), length):
            graphbar2 = graphbar2 + self.graph_right_char

        return "{0}{1}".format(graphbar1, graphbar2)


    def check_pin_state(self, pin):
        if not GPIO.input(pin):
            #log.debug("PIN {0} is on".format(pin))
            return True
        return False



class Menu(object):
    # TODO crashes when less than 4 lines
    def __init__(self, opts, helper, pos=0, n_lines=2, horizontal=False):
        self.h = helper
        self.opts = opts
        self.pos = pos
        self.n_lines = n_lines
        self.result = False
        self.stop = False
        self.horizontal=horizontal
        self.pos_display = 1
        if len(self.opts) < n_lines:
            for x in range(0, (n_lines-len(self.opts))):
                self.opts.append("")


    def get_prev(self, amount=1):
        ret = []
        position = self.pos
        for line in range(0,amount):
            position -= 1
            ret.append(self.opts[position])
        return reversed(ret)
            

    def get_next(self, amount=1):
        # When horizontal, the list wraps when returning
        ret = []
        position = self.pos
        for line in range(0,amount):
            if (position+1) > len(self.opts)-1:
                position = 0
            else:
                position += 1
            log.debug(position)
            log.debug(self.opts[position])
            ret.append(self.opts[position])
        return ret

            
    def is_even(self, x):
        if x % 2 == 0:
            return True
        return False


    def handle_event(self, channel):
        lcd.t_last_input = time()
        # When backlight is off, turn on backlight and skip input
        if not lcd.backlight_state: return
        event = self.h.get_event(channel)
        log.debug(event)

        if event == "enc1_up":
            self.move_up()
            self.show_menu()

        elif event == "enc1_down":
            self.move_down()
            self.show_menu()

        elif event == "select":
            self.result = [self.opts[self.pos], self.pos]
            log.debug("selected: {0}".format(self.opts[self.pos]))

        elif event == "back":
            self.stop = True


    def move_up(self):
        while True:
            # if not first
            if self.pos > 1:
                # decrease position
                self.pos -= 1

                # if position on te display is bigger than the second line
                if self.pos_display > 2:
                    # decrease position on display
                    self.pos_display -= 1

            # if position in opts is going to the first opt
            elif self.pos == 1:
                # decrease position
                self.pos -= 1

                # go to the first line on display
                self.pos_display = 1

            # if position going to be negative, wrap to last opt
            else:
                # wrap position to max index in opts
                self.pos = len(self.opts) -1
                # go to last line on display
                self.pos_display = self.n_lines

            if self.opts[self.pos]:
                return True


    def move_down(self):
        while True:
            # if not last
            if self.pos < len(self.opts) -2:
                # increase position
                self.pos += 1

                # if position on te display is smaller than the forelast line
                if self.pos_display < self.n_lines -1:
                    # increase position on display
                    self.pos_display += 1

            # if position in opts is going to the last opt
            elif self.pos == len(self.opts) -2:
                # increase position
                self.pos += 1

                # go to the last line on display
                self.pos_display = self.n_lines

            # if position going to be negative, wrap to last opt
            else:
                # wrap position to max index in opts
                self.pos = 0
                # go to last line on display
                self.pos_display = 1

            if self.opts[self.pos]:
                return True


    def show_menu(self):
        if self.horizontal:
            self.show_menu_horizontal()
            return

        n_leading = self.pos_display -1
        n_trailing = self.n_lines - self.pos_display

        leading_lines = self.get_prev(n_leading)
        trailing_lines = self.get_next(n_trailing)

        lines = []
        lcd.send_to_display("", clear=True)
        for line in leading_lines:
            lines.append(" {0}".format(line))
        lines.append("{0}{1}".format(self.h.menu_select_char, self.opts[self.pos]))
        for line in trailing_lines:
            lines.append(" {0}".format(line))

        row = 0
        for line in lines:
            lcd.send_to_display(line, row=row, clear=False)
            row += 1
            

    def show_menu_horizontal(self):
        if self.is_even(self.n_lines):
            n_leading = int((self.n_lines / 2) -1)
            n_trailing = int((self.n_lines / 2))
        else:
            n_leading = int((self.n_lines -1) /2)
            n_trailing = int((self.n_lines -1) /2)

        log.info(n_leading)
        log.info(n_trailing)
        leading_lines = self.get_prev(n_leading)
        trailing_lines = self.get_next(n_trailing)

        out = ""
        for line in leading_lines:
            out += line
        out += "[{0}]".format(self.opts[self.pos])
        for line in trailing_lines:
            out += line

        lcd.send_to_display(out, row=1, clear=False)


    def run(self):
        self.h.setup_channels(self.handle_event)
        self.first_run = True

        if self.horizontal: self.n_lines = self.n_lines - 2

        while True:
            if self.stop:
                break

            if self.result:
                return self.result

            if self.first_run:
                self.show_menu()
                self.first_run = False

            sleep(0.1)
        return False, False
            


class Scroller(object):
    # everytime scroll method is called it will scroll one step
    def __init__(self, text, helper, row=0, spaces=5, delay=0.5):
        self.h = helper
        self.columns = lcd.lcd_columns
        # What happens if text is shorter than lcd size
        text = text.ljust(len(text) + spaces)
        self.text_cycle = cycle(text)
        self.move_further = len(text) - self.columns
        self.row = row
        self.scroll_delay = delay
        self.last_time = time()
        self.first = True


    def scroll(self):
        if (time() - self.last_time) > self.scroll_delay or self.first:
            self.first = False
            out = ""
            for x in range(0, self.columns):
                out = out + next(self.text_cycle)
            for x in range(0, self.move_further + 1):
                next(self.text_cycle)
            lcd.send_to_display(out, self.row, clear=False) 
            self.last_time = time()



class WifiMode(object):
    def __init__(self, helper):
        self.h = helper
        self.stopped = False


    def get_user_input(self):
        lcd.send_to_display("")
        out = ""
        allowed_chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        menu = Menu(list(allowed_chars), self.h, n_lines=lcd.lcd_columns, horizontal=True)
        result,pos = menu.run()
        while result:
            out += result
            lcd.send_to_display(out, row=2, clear=False, center=True)
            menu = Menu(list(allowed_chars), self.h, pos=pos, n_lines=lcd.lcd_columns, horizontal=True)
            result,pos = menu.run()

        log.info(out)
        if out:
            menu = Menu(["Save", "Cancel"], self.h, n_lines=lcd.lcd_rows)
            if menu.run()[0] == "Save":
                return out
        return False

        # TODO wlan0 is down sometimes and should be up

    def get_networks(self):
        try:
            nets =  wifi.Cell.all("wlan0")
        except wifi.exceptions.ConnectionError as e:
            log.error("Failed to scan for list of networks, Connection error")
            log.error(e)
            return False
        except wifi.exceptions.InterfaceError as e:
            log.error("Failed to scan for list of networks, Interface is down")
            log.error(e)
            return False
        except:
            log.error("Failed to scan for list of networks")
            return False

        # You can itter an itterator only once so we put everything in a list
        if not nets:
            return False

        networks = []
        for net in nets:
            networks.append(net)

        return networks


    def list_activate_scheme(self):
        scheme = self.select_scheme()
        if scheme:
            log.debug("Activating profile: {0}".format(scheme.name))
            if self.activate_scheme(scheme):
                return True
        return False


    def activate_scheme(self, scheme):
        lcd.send_to_display("Activating scheme", row=1, center=True)
        lcd.send_to_display(scheme.name, row=2, center=True, time=4, clear=False)
        try:
            scheme.activate()
            lcd.send_to_display("Activated scheme", row=1, center=True)
            lcd.send_to_display(scheme.name, row=2, center=True, time=4, clear=False)
            return True
        except:
            log.error("Failed to connect to scheme: {0}".format(scheme.name))
            lcd.send_to_display("Failed to activate", row=1, center=True)
            lcd.send_to_display(scheme.name, row=2, center=True, time=4, clear=False)
            return False


    def connect_to_available(self):
        networks = self.get_networks()
        schemes = self.get_schemes()

        if not schemes:
            log.error("No schemes configured!")
            lcd.send_to_display("No schemes configured", row=1, center=True, time=4)
            return False

        if not networks:
            log.error("No networks available")
            lcd.send_to_display("No networks", row=1, center=True)
            lcd.send_to_display("available", row=2, center=True, time=4, clear=False)
            return False

        networks = sorted(networks, key=lambda x: x.quality, reverse=True)

        for network in networks:
            for scheme in schemes:
                if network.ssid == scheme.name:
                    log.debug("Connecting to: {0}".format(network.ssid))
                    #lcd.send_to_display("Connecting to", row=1, center=True)
                    #lcd.send_to_display(scheme.name, row=2, clear=False, center=True)

                    if self.activate_scheme(scheme):
                        log.debug("Connected to: {0}".format(scheme.name))
                        #lcd.send_to_display("Connected to", row=1, center=True)
                        #lcd.send_to_display(scheme.name, row=2, clear=False, center=True, time=4)
                        return True

                    else:
                        log.error("Failed to connect to: {0}".format(scheme.name))
                        #lcd.send_to_display("Failed to connect to", row=1, center=True)
                        #lcd.send_to_display(scheme.name, row=2, clear=False, center=True, time=4)
                        return False

        log.error("No known networks available")
        lcd.send_to_display("No known networks available", row=1, center=True, time=4)
        return False
        

    def select_scheme(self):
        schemes = []
        for scheme in wifi.Scheme.all():
            schemes.append(scheme.name)

        if schemes:
            menu = Menu(schemes, self.h, n_lines=lcd.lcd_rows)
            result,x = menu.run()
        if result:
            for scheme in wifi.Scheme.all():
                if scheme.name == result:
                    print(scheme.name, result)
                    return scheme
        return False


    def get_schemes(self):
        return wifi.Scheme.all()


    def new_scheme(self):
        # TODO double names
        network = self.choose_ssid()
        if not network:
            return False

        password = self.get_user_input()
        if password:
            log.debug("Creating scheme for {0} {1} {2}".format("wlan0", network, password))
            scheme = wifi.Scheme.for_cell("wlan0", network.ssid, network, password)
            scheme.save()
            return True
        return False


    def get_hostname(self):
        return socket.gethostname()


    def delete_scheme(self):
        scheme = self.select_scheme()
        if scheme:
            log.debug("Deleting profile: {0}".format(scheme.name))

            try:
                scheme.delete()
                lcd.send_to_display("Deleted", row=1, center=True)
                lcd.send_to_display(scheme.name, row=2, center=True, time=4, clear=False)
                return True
            except:
                log.error("Failed to delete profile: {0}".format(scheme.name))
                return False
        return False


    def choose_ssid(self):
        networks = self.get_networks()
        if not networks:
            lcd.send_to_display("Failed to scan for", row=1, center=True)
            lcd.send_to_display("networks", row=2, center=True, time=4, clear=False)
            return False

        opts = []
        for network in networks:
            q,t = network.quality.split("/")
            quality = 100 / int(t) * int(q)
            if network.encrypted:
                opts.append("{0}% {1} {2}".format(int(quality), network.encryption_type, network.ssid))
            else:
                opts.append("{0}% OPEN {1}".format(int(quality), network.ssid))

        menu = Menu(sorted(opts, reverse=True), self.h, n_lines=lcd.lcd_rows)
        ssid,x = menu.run()

        if ssid:
            ssid = ssid.split()[2]

            for network in networks:
                if network.ssid == ssid:
                    return network
        return False


    def menu(self):
        # TODO Create thread that checks for connection and activates a profile
        opts = ["Connect", "Status", "Activate Profile", "New Profile", "List Profiles", "Delete Profile"]
        menu = Menu(opts, self.h, n_lines=lcd.lcd_rows)
        selected,x = menu.run()
        if not selected:
            return False

        if selected == "Connect":
            self.connect_to_available()
        elif selected == "New Profile":
            self.new_scheme()
        elif selected == "List Profiles":
            self.select_scheme()
        elif selected == "Status":
            self.status()
        elif selected == "Activate Profile":
            self.list_activate_scheme()
        elif selected == "Delete Profile":
            self.delete_scheme()
        return True
        

    def get_ip(self, adapter):
        # Each of the numbers refers to a particular address family.
        # In this case, we have three address families listed; on my system,
        # 18 is AF_LINK (which means the link layer interface, e.g. Ethernet),
        # 2  is AF_INET (normal Internet addresses),
        # 30 is AF_INET6 (IPv6).

        if adapter in netifaces.interfaces():
            addresses = netifaces.ifaddresses(adapter)
            try:
                af_inet_addresses = addresses[netifaces.AF_INET]
                print("Internet is connected:", adapter, af_inet_addresses)
                return af_inet_addresses[0]["addr"]
            except:
                return False

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
            #return socket.gethostbyname(socket.gethostname())
        except:
            log.error("Failed to get ip")
            return False


    def status(self):
        adapters = [ "eth0", "wlan0" ]
        opts = []
        for adapter in adapters:
            ip = self.get_ip(adapter)
            if ip:
                opts.append("{0}: {1}".format(adapter, self.get_ip(adapter)))
            else:
                opts.append("{0}: disconnected".format(adapter))
        opts.append("Host: {0}".format(self.get_hostname()))
        menu = Menu(opts, self.h, n_lines=lcd.lcd_rows)
        menu.run()


    def activate(self):
        while True:
            if not self.menu():
                return False



class MainMenu(object):
    def __init__(self):
        self.h = Helper()


    def run(self):
        os.system('sudo ifconfig wlan0 up')
        #wifi_mode = WifiMode(self.h)
        #if not wifi_mode.connect_to_available():
        #    wifi_mode.activate()

        while True:
            menu = Menu(self.h.main_menu_opts, self.h, pos=self.h.default_state, n_lines=lcd.lcd_rows)
            result, x = menu.run()
            log.info(result)

            if result == "mpd":
                mpd_mode = MPDMode(self.h)
                mpd_mode.activate()
            elif result == "Kodi Remote":
                kodi_mode = KodiMode(self.h)
                kodi_mode.activate()
            elif result == "Wifi Settings":
                wifi_mode = WifiMode(self.h)
                wifi_mode.activate()
            elif result == "Shutdown":
                lcd.send_to_display("Shutting down ...", row=1, center=True)
                os.system("halt")
            elif result == "Reboot":
                lcd.send_to_display("Rebooting ...", row=1, center=True)
                os.system("reboot")
        backlight_thread.stop()



class MPDEventThread(StoppableThread):
    def __init__(self, helper):
        self.h = helper
        StoppableThread.__init__(self)
        self.mpd_handler2 = MPDHandler(host=self.h.mpd_host, port=self.h.mpd_port)
        self.mpd_handler2.start_mpd()
        self.h.event_player = False
        self.h.event_mixer = False


    def loop(self):
        event = self.mpd_handler2.idle()
        if "player" in event:
            self.h.event_player = True
        if "mixer" in event:
            self.h.event_mixer = True


    def run(self):
        while not self.stopped():
            self.loop()



class MPDMode():
    def __init__(self, helper, playlist=False):
        # TODO also disconnect from mpd
        # You can specify an alternative playlist to work with, eg: in radio mode
        self.playlist = playlist
        self.h = helper
        self.mpd_handler = MPDHandler(host=self.h.mpd_hosts[0]["host"], port=self.h.mpd_hosts[0]["port"])
        self.mpd_handler.start_mpd()
        self.last_title = False
        self.enter_menu = False
        self.enter_volume_up = False
        self.enter_volume_down = False
        self.volume_mode = VolumeMode(self.mpd_handler, self.h)

        # Starts a event check thread and fills some vars in mpd_handler to check for events
        #self.mpd_event_thread = MPDEventThread(self.h).start()
        self.stop = False


    def update_lcd(self):
        # It is sending stuff to lcd very often which is not a problem because it filters out if it's the same
        # but there are a lot of calls to mpd
        artist = self.mpd_handler.get_current_artist()
        title  = self.mpd_handler.get_current_title()

        if self.mpd_handler.is_stopped():
            lcd.send_to_display("[Stopped]", row=2, center=True, clear=True)
            return

        lcd.send_to_display(artist, row=1, center=True)

        # If title is bigger than display, create a scrolling object everytime the songtitle changes and call the scroll() method
        if len(title) > lcd.lcd_columns:
            if self.last_title == title:
                self.scroller.scroll()
            else:
                self.scroller = Scroller(title, self.h, row=2)
                self.last_title = title
        else:
            lcd.send_to_display(title, row=2, center=True, clear=False)

        if self.mpd_handler.is_paused():
            lcd.send_to_display("[Paused]", center=True, row=3, clear=False, force=True)
        else:
            lcd.send_to_display("", center=True, row=3, clear=False)


    def browse_tag(self, tag):
        items = self.mpd_handler.get_tag(tag)
        if not items:
            return False

        menu = Menu(items, self.h, pos=0, n_lines=lcd.lcd_rows)
        selected,x = menu.run()

        if not selected:
            return False

        self.mpd_handler.do_clear_playlist()
        self.mpd_handler.do_find_add(tag, selected)
        self.mpd_handler.do_play()
        

    def radio(self):
        self.mpd_handler.do_clear_playlist()
        playlist = self.mpd_handler.do_load_playlist("radio")
        self.browse_playlist()


    def menu(self):
        opts = [ "Browse Playlist", \
                      "Browse Artists", \
                      "Browse Albums", \
                      "Browse Songs", \
                      "Radio", \
                      "Set Server", \
                      "Update Database" ]

        menu = Menu(opts, self.h, pos=0, n_lines=lcd.lcd_rows)
        selected,x = menu.run()
        if not selected:
            return False

        if selected == "Browse Artists":
            self.browse_tag("artist")
        if selected == "Browse Albums":
            self.browse_tag("album")
        if selected == "Browse Songs":
            self.browse_tag("title")
        elif selected == "Browse Playlist":
            self.browse_playlist()
        elif selected == "Set Server":
            self.set_server()
        elif selected == "Radio":
            self.radio()
        elif selected == "Update Database":
            lcd.send_to_display("Updating Database", row=1, center=True, time=3)
            self.mpd_handler.do_update_database()


    def set_server(self):
        items = []
        for item in self.h.mpd_hosts:
            items.append("{0}:{1}".format(item["host"], item["port"]))

        menu = Menu(items, self.h, pos=0, n_lines=lcd.lcd_rows)
        selected,x = menu.run()

        if not selected:
            return False

        selected = selected.split(":")

        self.mpd_handler = MPDHandler(host=selected[0], port=selected[1])
        self.mpd_handler.start_mpd()


    def browse_playlist(self):
        # Use the menu to choose a song from the playlist.
        playlist_obj = self.mpd_handler.get_playlist()
        if not playlist_obj:
            log.error("no playlist")
            return False
        playlist = {}
        cur_id = self.mpd_handler.get_current_songid()
        if not cur_id:
            cur_id = 0

        for item in playlist_obj:
            if "name" in item.keys():
                playlist[item["id"]] = item["name"]
            elif "title" in item.keys():
                playlist[item["id"]] = item["title"]
            elif "file" in item.keys():
                playlist[item["id"]] = item["file"]
            else:
                playlist[item["id"]] = item["Unknown"]

        playlist_values = []
        for item in sorted(playlist):
            playlist_values.append(playlist[item])

        menu = Menu(playlist_values, self.h, pos=cur_id, n_lines=lcd.lcd_rows)
        selected,x = menu.run()

        for item in sorted(playlist):
            if playlist[item] == selected:
                self.mpd_handler.do_play_id(item)
                return True
        return False


    def handle_event(self, channel):
        # When backlight is off, turn on backlight and skip input
        lcd.t_last_input = time()
        if not lcd.backlight_state: return

        event = self.h.get_event(channel)

        if event == "select":
            self.mpd_handler.do_toggle()

        elif event == "enc2_up":
            self.enter_volume_up = True

        elif event == "enc2_down":
            self.enter_volume_down = True

        elif event == "back":
            self.stop = True

        elif event == "enc1_up" or event == "enc1_down":
            self.enter_menu = True


    def activate(self):
        log.info("MPD mode active")
        
        # Do the callback setup the first time and everytime we need to get back to the default state
        self.setup = True
        self.update_display = True

        while not self.stop:
            if not self.mpd_handler.check_connection():
                
                lcd.send_to_display("Error connecting", row=0, center=True)
                lcd.send_to_display("To MPD", row=1, center=True, clear=False)
                lcd.send_to_display("{0}:{1}".format(self.mpd_handler.host,self.mpd_handler.port), row=2, center=True, clear=False)
                self.update_display = False
                #log.error("Failed to connect to mpd on: {0}:{1}".format(self.mpd_handler.host,self.mpd_handler.port))
            else:
                self.update_display = True

            if self.setup:
                self.h.setup_channels(self.handle_event)
                self.setup = False

            # We can not change the callbacks from a function triggered by a callback
            # So we make the loop listen to a variable
            if self.enter_menu:
                self.menu()
                self.enter_menu = False
                self.setup = True

            if self.enter_volume_up:
                self.volume_mode.run(5)
                self.setup = True
                self.enter_volume_up = False

            if self.enter_volume_down:
                self.volume_mode.run(-5)
                self.setup = True
                self.enter_volume_down = False

            if self.update_display:
                self.update_lcd()

            sleep(0.2)

        log.info("MPD mode stopped")



class KodiMode():
    def __init__(self, helper, playlist=False):
        self.h = helper
        self.stopped = False
        self.kodi_host = "localhost"
        self.kodi_port = "8080"


    def handle_event(self, channel):
        # When backlight is off, turn on backlight and skip input
        lcd.t_last_input = time()
        if not lcd.backlight_state: return

        event = self.h.get_event(channel)

        if event:
            lcd.send_to_display("Sent command", row=1, center=True)
            lcd.send_to_display(event, row=2, center=True, clear=False)

        if event == "select":
            #self.send_to_kodi("Player.PlayPause")
            self.send_to_kodi("Input.Select")

        elif event == "back":
            self.send_to_kodi("Input.Back")

        elif event == "button2":
            pass

        elif event == "button2_long":
            self.stopped = True

        elif event == "enc2_up":
            self.send_to_kodi("Input.Up")

        elif event == "enc2_down":
            self.send_to_kodi("Input.Down")

        elif event == "enc1_up":
            self.send_to_kodi("Input.Left")

        elif event == "enc1_down":
            self.send_to_kodi("Input.Right")


    def send_to_kodi(self, command):
        headers = { 'Content-Type': 'application/json' }
        url = "http://{0}:{1}/jsonrpc".format(self.kodi_host, self.kodi_port)
        data = { "jsonrpc": "2.0", "method": command, "id": 1}

        json_data = json.dumps(data)
        post_data = json_data.encode('utf-8')
        request = Request(url, post_data, headers)
        try:
            result = urlopen(request)
            return True
        except:
            log.error("Failed to send command to Kodi")
            return False


    def is_connected(self):
        try:
            self.kodi.JSONRPC.Ping()
            return True
        except:
            log.error("Failed to connect to Kodi")
            return False


    def activate(self):
        log.info("KODI mode active")
        
        # Do the callback setup the first time and everytime we need to get back to the default state
        self.setup = True

        while not self.stopped:
            if self.setup:
                self.h.setup_channels(self.handle_event)
                self.setup = False

            sleep(1)

        log.info("MPD mode stopped")



class VolumeMode(object):
    def __init__(self, mpd_handler, helper):
        self.mpd_handler = mpd_handler
        self.h = helper


    def handle_event(self, channel):
        # When backlight is off, turn on backlight and skip input
        lcd.t_last_input = time()
        if not lcd.backlight_state: return

        event = self.h.get_event(channel)

        if event == "enc2_up":
            self.set_vol(-5)

        elif event == "enc2_down":
            self.set_vol(5)


    def set_vol(self, volume):
        volume = self.mpd_handler.set_vol(volume)
        if volume:
            graph = self.h.get_graphbar(volume, lcd.lcd_columns-2)
            lcd.send_to_display("Volume", row=1, center=True, force=True)
            lcd.send_to_display("[{0}]".format(graph), row=2, clear=False, force=True)
        else:
            lcd.send_to_display("Failed to set volume", row=1, center=True)


    def run(self, volume):
        self.h.setup_channels(self.handle_event)
        stopped = False
        self.set_vol(volume)

        while not stopped:
            if time() - lcd.t_last_input > 2:
                stopped = True

            sleep(0.1)



class BacklightThread(StoppableThread):
    def __init__(self):
        StoppableThread.__init__(self)
        lcd.backlight_state = False


    def backlight_on(self):
        if not lcd.backlight_state:
            GPIO.output(lcd.lcd_led, GPIO.HIGH)
            lcd.backlight_state = True
            log.debug("Backlight turn on")


    def backlight_off(self):
        if lcd.backlight_state:
            GPIO.output(lcd.lcd_led, GPIO.LOW)
            lcd.backlight_state = False
            log.debug("Backlight turn off")


    def loop(self):
        if (time() - lcd.t_last_input) > lcd.lcd_backlight_stay_on:
            self.backlight_off()
        else:
            self.backlight_on()


    def run(self):
        self.backlight_on()

        while not self.stopped():
            self.loop()
            sleep(lcd.backlight_delay)



class MPDVolumeThread(MPDHandler, StoppableThread):
    # TODO use idle() to wait for volume changes in mixer
    def __init__(self, mpd_handler):
        StoppableThread.__init__(self)
        self.volume_state = False
        self.mpd_handler = mpd_handler


    def loop(self):
        volume = self.mpd_handler.get_volume()
        if volume:
            if not volume == self.volume_state:
                log.debug("MPDVolumeThread is changing volume: {0} : {1}".format(volume, self.volume_state))
                self.mpd_handler.set_volume()
                self.volume_state = volume


    def run(self):
        log.debug("Started volume thread")
        while not self.stopped():
            self.loop()
            sleep(0.5)


log = Log()
lcd = LCD()

# Start backlight thread
backlight_thread = BacklightThread().start()

GPIO.setmode(GPIO.BCM)
main_menu = MainMenu()
main_menu.run()

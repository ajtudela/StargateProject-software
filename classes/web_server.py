import os
import json
import threading
from time import sleep
import urllib.parse
import collections
import platform
from http.server import SimpleHTTPRequestHandler

class StargateWebServer(SimpleHTTPRequestHandler):

    #Overload SimpleHTTPRequestHandler.log_message() to suppress logs from printing to console
    # *** Comment this out for debugging!! ***
    # def log_message(self, format, *args):
    #     pass

    def parse_GET_vars(self):
        qs = {}
        path = self.path
        if '?' in path:
            path, tmp = path.split('?', 1)
            qs = urllib.parse.parse_qs(tmp)
        return path, qs

    def do_GET(self):
        try:
            request_path, get_vars = self.parse_GET_vars()

            if request_path == '/get':
                entity = get_vars.get('entity')[0]

                if ( entity == "standard_gates"):
                    content = json.dumps( self.stargate.addrManager.getBook().get_standard_gates() )

                elif( entity == "fan_gates" ):
                    content = json.dumps( self.stargate.addrManager.getBook().get_fan_gates() )

                elif( entity == "all_gates" ):
                    all_addr = self.stargate.addrManager.getBook().get_all_nonlocal_addresses()
                    ordered_dict = collections.OrderedDict(sorted(all_addr.items()))
                    content = json.dumps( ordered_dict )

                elif( entity == "local_address" ):
                    content = json.dumps( self.stargate.addrManager.getBook().get_local_address() )

                elif( entity == "status" ):
                    data = {
                        "address_buffer_outgoing":  self.stargate.address_buffer_outgoing,
                        "locked_chevrons_outgoing": self.stargate.locked_chevrons_outgoing,
                        "address_buffer_incoming":  self.stargate.address_buffer_incoming,
                        "locked_chevrons_incoming": self.stargate.locked_chevrons_incoming,
                        "wormhole_active":          self.stargate.wormhole,
                        "black_hole_connected":     self.stargate.black_hole,
                        "connected_planet":         self.stargate.connected_planet_name,
                        "wormhole_open_time":       self.stargate.wh.open_time,
                        "wormhole_max_time":        self.stargate.wh.wormhole_max_time,
                        "wormhole_time_till_close": self.stargate.wh.get_time_remaining()
                    }
                    content = json.dumps( data )

                elif( entity == "info" ):
                    data = {
                        "local_stargate_address":         self.stargate.addrManager.getBook().get_local_address(),
                        "local_stargate_address_string":  self.stargate.addrManager.getBook().get_local_address_string(),
                        "subspace_public_key":            self.stargate.subspace.get_public_key(),
                        "subspace_ip_address":            self.stargate.subspace.get_subspace_ip(True),
                        "lan_ip_address":                 self.stargate.subspace.get_lan_ip(),
                        "software_version":               str(self.stargate.swUpdater.get_current_version()),
                        "python_version":                 platform.python_version(),
                        "internet_available":             self.stargate.netTools.has_internet_access(),
                        "subspace_available":             self.stargate.subspace.is_online(),
                        "standard_gate_count":            len(self.stargate.addrManager.getBook().get_standard_gates()),
                        "fan_gate_count":                 len(self.stargate.addrManager.getBook().get_fan_gates()),
                        "dialer_mode":                    self.stargate.dialer.type
                    }
                    content = json.dumps( data )

                elif( entity == "symbols_ddslick" ):
                    data = {
                        "symbols": self.stargate.symbolManager.get_all_ddslick()
                    }
                    content = json.dumps( data )

                self.send_response(200)
                self.send_header("Content-type", "text/json")
                self.end_headers()
                self.wfile.write(content.encode())

            else:
                # Unhandled request: send a 404
                self.send_response(404)
                self.end_headers()

            return
        except:

            raise # *** Un-comment for debugging!! ***

            # Encountered an exception: send a 500
            self.send_response(500)
            self.end_headers()

    def do_POST(self):
        #print('POST PATH: {}'.format(self.path))
        if self.path == '/shutdown':
            self.stargate.wormhole = False
            sleep(5)
            self.send_response(200, 'OK')
            os.system('systemctl poweroff')
            return

        if self.path == '/reboot':
            self.stargate.wormhole = False
            sleep(5)
            self.send_response(200, 'OK')
            os.system('systemctl reboot')
            return

        content_len = int(self.headers.get('content-length', 0))
        body = self.rfile.read(content_len)
        data = json.loads(body)
        #print('POST DATA: {}'.format(data))

        if self.path == '/update':
            if data['action'] == "chevron_cycle":
                self.stargate.chevrons.get(int(data['chevron_number'])).cycle_outgoing()

            elif data['action'] == "all_leds_off":
                self.stargate.chevrons.all_off()
                self.stargate.wormhole = False

            elif data['action'] == "chevron_led_on":
                self.stargate.chevrons.all_lights_on()

            elif data['action'] == "wormhole_on":
                self.stargate.wormhole = True

            elif data['action'] == "wormhole_off":
                self.stargate.wormhole = False

            elif data['action'] == "symbol_forward":
                self.stargate.ring.move( 33, self.stargate.ring.forwardDirection ) # Steps, Direction
                self.stargate.ring.release()

            elif data['action'] == "symbol_backward":
                self.stargate.ring.move( 33, self.stargate.ring.backwardDirection ) # Steps, Direction
                self.stargate.ring.release()

            elif data['action'] == "volume_down":
                self.stargate.audio.volume_down()

            elif data['action'] == "volume_up":
                self.stargate.audio.volume_up()

            elif data['action'] == "sim_incoming":
                if ( not self.stargate.wormhole ): # If we don't already have an established wormhole
                    # Get the loopback address and dial it
                    for symbol_number in self.stargate.addrManager.addressBook.get_local_loopback_address():
                        self.stargate.address_buffer_incoming.append(symbol_number)

                    self.stargate.address_buffer_incoming.append(7) # Point of origin
                    self.stargate.centre_button_incoming = True

            elif data['action'] == "set_local_stargate_address":
                continue_to_save = True
                # Parse the address
                try:
                    address = [ data['S1'], data['S2'], data['S3'], data['S4'], data['S5'], data['S6'] ]
                except Exception as e:
                    data = { "success": False, "error": "Required fields missing or invalid request" }
                    continue_to_save = False

                # Validate that this is an acceptable address
                if continue_to_save:
                    verify_avail, error, entry = self.stargate.addrManager.verify_address_available(address)
                    if verify_avail == "VERIFY_OWNED":
                        # This address is in use by a fan gate, but someone might be (re)configuring their own gate.
                        try:
                            if (data['owner_confirmed']):
                                pass # Valid, continue to save
                            else:
                                data = { "success": False, "error": error }
                                continue_to_save = False
                        except Exception as e:
                            data = { "success": False, "extend": "owner_unconfirmed", "error": "This address is in use by a Fan Gate - \"{}\"".format(entry['name']) }
                            continue_to_save = False
                    elif verify_avail == False:
                        # This address is in use by a standard gate
                        data = { "success": False, "error": error }
                        continue_to_save = False
                    else:
                        pass # Address not in use, clear to proceed

                # Store the address:
                if continue_to_save:
                    # TODO: Error checking
                    self.stargate.addrManager.getBook().set_local_address(address)
                    data = { "success": True, "message": "There are no conflicts with your chosen address.<br><br>Local Address Saved." }

                self.send_json_response(data)
                return

            elif data['action'] == "set_subspace_ip":
                print("Setting Subspace IP Address")

            elif data['action'] == "subspace_up":
                print("Subspace UP")

            elif data['action'] == "subspace_down":
                print("Subspace DOWN")

        elif self.path == '/dhd_press':
            symbol_number = int(data['symbol'])

            if symbol_number > 0:
                self.stargate.keyboard.queue_symbol(symbol_number)
            elif symbol_number == 0:
                self.stargate.fan_gate_online_status = False #TODO: This isn't necessarily true.
                self.stargate.keyboard.queue_center_button()

        elif self.path == '/incoming_press':
            symbol_number = int(data['symbol'])

            if symbol_number > 0:
                self.stargate.address_buffer_incoming.append(symbol_number)
            elif symbol_number == 0:
                self.stargate.centre_button_incoming = True


        self.send_response(200, 'OK')
        self.end_headers()

    def send_json_response(self, data):
        content = json.dumps( data )
        self.send_response(200)
        self.send_header("Content-type", "text/json")
        self.end_headers()
        self.wfile.write(content.encode())
        return

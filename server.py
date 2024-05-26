# Tshegofatso Kgole
# Aphiwe Mkhwanazi
# Joshua Britz 


import socket 
import errno
from threading import Thread, Event, Lock

####################  class definitions  ########################

class Client():
    # a class that holds client information but not the actual socket

    def __init__(self, name, address):
        # constructor variable 
        self.address    = address     # the client ip address
        self.name       = name        # the name or alias used to identify clients in chats
        self.__status   = "available" # the client's current availability status. One of three states available, unavailable or inchat.

    # getter and setters for status, since status is a private variable.
    def set_status_available(self):     self.__status = "available"
    def set_status_unavailable(self):   self.__status = "unavailable"
    def set_status_inchat(self):        self.__status = "inchat"
    def get_status(self) -> str:        return self.__status
    
    # equality overide for search functionality
    def __eq__(self, other_client) -> bool:
        return self.name == other_client.name or self.address == other_client.address
    
    def __str__(self) -> str:
        return f"{self.name}, {self.address}, {self.get_status()}"
    
class Client_list():

    # class that acts as a wrapper on a list of clients and a list of their message handlers.
    # both lists are modified and read in a thread safe and atomic way using python Locks

    def __init__(self) -> None:
        # init list of Client objets and a lock
        self.client_objs = []
        self.client_objs_LOCK = Lock()
        
        # init list of client_message_handler objets and a lock
        self.message_handlers_objs = []
        self.message_handlers_objs_LOCK = Lock()

        # used for iterable implantation
        self.iterator_index = 0

    def add_Client(self, new_client: Client, new_client_socket: socket.socket):
        # adds client to list

        # first gets lock and appends Client object.
        with self.client_objs_LOCK:
            self.client_objs.append(new_client)

        # inits a message handler (that runs in its own thread). Then starts message handler.
        message_handler_obj = client_message_handler(new_client_socket, new_client.name)
        message_handler_obj.start()

        # gets lock and appends message handling thread.
        with self.message_handlers_objs_LOCK:
            self.message_handlers_objs.append(message_handler_obj)

    def change_status_inchat(self, this_client: Client):
        
        with self.client_objs_LOCK:        
        # then looks for client matching argument and deletes it
            for client in self.client_objs:
                if client == this_client:
                    client.set_status_inchat()
    
    def change_status_available(self, this_client: Client):
        with self.client_objs_LOCK:        
        # then looks for client matching argument and deletes it
            for client in self.client_objs:
                if client == this_client:
                    client.set_status_available()
    
    
    def change_status_unavailable(self, this_client: Client):
        with self.client_objs_LOCK:        
        # then looks for client matching argument and deletes it
            for client in self.client_objs:
                if client == this_client:
                    client.set_status_unavailable()

    def remove_client(self, this_client: Client):
        # removes this_client from both internal lists

        # gets lock for client objects list
        with self.client_objs_LOCK:        
            # then looks for client matching argument and deletes it
            for client in self.client_objs:
                if client == this_client:
                    self.client_objs.remove(client)

        # gets lock for message handler object list
        with self.message_handlers_objs_LOCK:
            # first kills the thread and then removes it from the list 
            for client_thread in self.message_handlers_objs:
                if client.name == client_thread.name:
                    client_thread.kill()
                    self.message_handlers_objs.remove(client_thread)

        return

    def get_client_details(self, client: Client) -> Client:
        # returns the Client object for the queried. Matches either name or address.

        with self.client_objs_LOCK:
            for client_in_list in self.client_objs:
                if client == client_in_list:
                    return client_in_list

    def is_unique_name(self, name: str) -> bool:
        # checks whether this name is already used in the client's list.
        
        output = False
        
        with self.client_objs_LOCK:
            for client in self.client_objs:
                if name == client.name:
                    print(name, client.name)
                    output = True
                    break

        return output

    def send_msg_to(self, other_client: Client, message: bytes):
        # sends a byte encoded message to specified client in list.

        with self.message_handlers_objs_LOCK:
            for msg_handler in self.message_handlers_objs:
                if msg_handler.name == other_client.name:
                    msg_handler.socket.send(message)

    def __len__(self):
        # for the length of the Client_List. len()
        return self.client_objs.__len__()

    def __getitem__(self, item):
        # for array syntax so Client_List[i] works.
        return self.client_objs.__getitem__(item)

    def __iter__(self):
        # makes class iterable so for client in Client_List: works 
        return self.client_objs.__iter__()

    def __next__(self):
        # makes class iterable so for client in Client_List: works
        
        self.iterator_index += 1

        if self.iterator_index < len(self.client_objs):
            return self.client_objs[self.iterator_index]

        raise StopIteration

    def __del__(self):
        # goes through and kills all threads in list.

        with self.message_handlers_objs_LOCK:
            for thread in self.message_handlers_objs:
                thread.kill()

class client_message_handler(Thread):

    # message-handling-thread class that responds to messages from one client

    def __init__(self, socket:socket.socket, name):
        super(client_message_handler, self).__init__()
        
        self._listening = Event() # internal atomic bool for thread start/stop
        self.socket = socket      # this client's socket object
        self.name = name          # the client identifier for this respective thread.

    def kill(self):
        # used to stop while loop in run() method
        self._listening.clear()
        
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except socket.error:
            # if the socket wasn't initialized or the socket was already closed by the client.
            pass

    def run(self):
        # runs when the thread is activated by .start()
        self._listening.set()
        
        with self.socket:
            try:
                self.socket.send(f"\nWelcome {self.name}. enter HELP to get a list of available commands".encode())

                while self._listening.is_set():
                    # get message from client
                    message = self.socket.recv(1024).decode()

                    # check to make sure the msg is not None (closed connection) and not and empty string
                    if message != None and message != "":
                        # echo the message
                        print(f"{self.name}: \"{message}\"")
                        # split the string into a list. makes things easier to handle
                        message = message.split(": ")
                        
                        # send the message list to a switchboard style function to respond based on commands.
                        self.switchboard(message)

            except socket.error as err:
                print(f"got a socket error in {self.name} client message handling thread\n{err}")                
                CLIENT_LIST.remove_client(Client(self.name, ""))

            finally:
                self.kill()

    def switchboard(self, message: list):
        ### Switch board ###
                        
        # these if/elif statements act as a "switchboard" and execute specific actions
        # depending on keywords and arguments received from the client.

        if message[0].strip() == "RMV_USR":
            # remove this user from clients list. does not need an argument
            print(f"removing {self.name} from clients list.")
            CLIENT_LIST.remove_client(Client(self.name, ""))
            
        elif message[0].strip() == "GET_USRS":
            # sends a list of all current users. does not need an argument
            print(f"sending {self.name} a list of clients.")
            self.send_clients()

        elif message[0].strip() == "HELP":
            # sends a list of available commands to the client
            print(f"sending {self.name} a list of commands")
            self.send_commands()

        elif message[0].strip() == "CHG_STATUS":
            # changes status of this client
            self.change_status(message)
        
        elif message[0].strip() == "CHAT":
            # establishes a UDP peer to peer chat between two clients on the clients
            self.establish_chat(message)
        
        elif message[0].strip() == "CHAT_RPLY":
            # response from a chat request. notify
            if len(message) > 1:

                if message[1].strip() == "YES":
                    other_client_name = message[2].strip()
                    CLIENT_LIST.change_status_inchat(Client(self.name, ""))
                    CLIENT_LIST.change_status_inchat(Client(other_client_name, ""))

                    this_client_ip = message[3].strip()
                    this_client_port = message[4].strip()
                    CLIENT_LIST.send_msg_to(Client(other_client_name, ""),
                                            f"CHAT_RPLY: YES: {this_client_ip}: {this_client_port}".encode())

                elif message[1].strip() == "NO":

                    # self.socket.send(b"CHAT_RPLY: NO")
                    said_yes_to = message[2].strip()
                    CLIENT_LIST.send_msg_to(Client(said_yes_to, ""), "CHAT_RPLY: NO".encode())
                else:
                    print("idk")  
                    #this is in case user sends a command the server does not support

        else:
            print(f"received an unsupported command, sending {self.name} a list of commands")
            self.socket.send(b"Please enter a supported command")
            self.send_commands()


    def establish_chat(self, message: list):
        print(message)
        if len(message) < 1:
                # no user name entered
                self.socket.send(b"You did not enter another username. Enter GET_USRS: to get a list of available users.")
                return

        other_client = Client(message[1].strip(), "")

        print(f"establishing a peer to peer chat between {self.name} and {other_client.name}")
        
        if other_client not in CLIENT_LIST: 
            # not a valid client 
            self.socket.send(f"{other_client.name} is not the name of one of our users. Enter GET_USRS: to get a list of available users.".encode())
            return
        
        if other_client.name == self.name:
            self.socket.send(b"Please enter another username. You cannot chat to yourself.")
            return

        # now that we know we have a valid other user we'll try and establish a chat.

        other_client = CLIENT_LIST.get_client_details(other_client)

        random_port  = int(message[3].strip())
        peer_addr    = (message[2], random_port)

        if other_client.get_status() == "unavail":
            self.socket.send(f"{other_client.name} is currently unavailable. Please try again later.".encode())
            return
        
        elif other_client.get_status() == "inchat":
            self.socket.send(f"{other_client.name} is currently in another chat. Please try again later.".encode())
            return

        CLIENT_LIST.send_msg_to(other_client, f"CHAT_RQST: {self.name}: {peer_addr[0]}: {peer_addr[1]}".encode())

    def send_commands(self):
     
        self.socket.send(b"\nAll the Supported Commands\n")
        self.socket.send(b"NEW_USR: username \t\t ---> creates a new user with specified username.\n")
        self.socket.send(b"RMV_USR: \t\t\t ---> removes you from the list of users.\n")
        self.socket.send(b"CHG_STATUS: avail or unavail \t ---> changes your user status to available or unavailable.\n")
        self.socket.send(b"GET_USRS: \t\t\t ---> shows a list of all users.\n")
        self.socket.send(b"CHAT: username \t\t\t ---> requests a chat session with specified username.\n")
        self.socket.send(b"HELP:  \t\t\t\t ---> shows a list of available commands.\n")



    def send_clients(self):
        self.socket.send(b"\nName\t| Address\t\t| Status\n")
        self.socket.send(b"--------+-----------------------+------------------\n")
        
        # get lock
        with CLIENT_LIST.client_objs_LOCK:
            
            if len(CLIENT_LIST) >= 1:
                for client in CLIENT_LIST:
                    if Client(self.name, "") == client:
                        self.socket.send(f"{client.name}\t| {client.address}\t| {client.get_status()} <-- YOU\n".encode())

                    elif client.get_status() == "unavailable":
                        self.socket.send(f"{client.name}\t| -------------------\t| {client.get_status()}\n".encode())

                    else:
                        self.socket.send(f"{client.name}\t| {client.address}\t| {client.get_status()}\n".encode())
            else:
                self.socket.sendto(b"There's no one here. Create a new user using NEW_USR: Name\n")
            return

    def change_status(self, message: list):

        if len(message) < 1:
            # no user name entered
            self.socket.send(b"Please enter a new status. Either \"avail\" orr \"unavail.\"\n")
            return

        new_status = message[1].strip()

        if new_status == "avail" or new_status == "unavail" or new_status == "inchat":
            print(f"changing {self.name}'s status to {new_status}")

            if   new_status == "avail":     CLIENT_LIST.change_status_available(Client(self.name, ""))
            elif new_status == "unavail":   CLIENT_LIST.change_status_unavailable(Client(self.name, ""))
            elif new_status == "inchat":    CLIENT_LIST.change_status_inchat(Client(self.name, ""))
            self.socket.send(f"Status has been updated to {new_status}".encode())
    

        else:
            self.socket.send(b"Please enter a new status. Either \"avail\" orr \"unavail.\"\n")

        return

###########################  main  ###############################

SERVER_ADDR = ("localhost", 33311)
CLIENT_LIST = Client_list()

def main():

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as SERVER:

        try:
            SERVER.bind(SERVER_ADDR)
            SERVER.listen()
            print(f"server running on {SERVER_ADDR}")

        except socket.error as err:
            print(f"could not bind to specified port. :(\n{err}")
            exit()

        try:
            while True:
                client_sock, client_addr = SERVER.accept()

                # expecting a NEW_USR: username where username is unique
                message = client_sock.recv(1024).decode()

                if message.startswith("NEW_USR:"):
                    message = message.split(": ")
                    client_name = message[1].strip()

                    if Client(client_name, client_addr) not in CLIENT_LIST:
                        print(f"new user added {client_name} on address {client_addr}")
                        CLIENT_LIST.add_Client(Client(client_name, client_addr), client_sock)

                    else:
                        client_sock.send(f"The username \"{client_name}\" is already taken. Please choose another.".encode())
                        continue
                
                else:
                    # might do something else too
                    client_sock.send(b"Please use NEW_USR: username to continue.")
                    continue

        except socket.error as err:
            print(f"got a socket error in main thread\n{err}")
        
        finally:
            SERVER.shutdown(socket.SHUT_RDWR)
            SERVER.close()
            print("server closing...")
            exit()

if __name__ == "__main__":
    main()
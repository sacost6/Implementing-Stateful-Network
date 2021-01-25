"""
war card game client and server
"""
import asyncio
from collections import namedtuple
from enum import Enum
import logging
import random
import socket
import socketserver
import threading
import sys

"""
Namedtuples work like classes, but are much more lightweight so they end
up being faster. It would be a good idea to keep objects in each of these
for each game which contain the game's state, for instance things like the
socket, the cards given, the cards still available, etc.
"""
Game = namedtuple("Game", ["p1", "p2"])
# Use asyncio queue to temporarily block competing threads
queue = asyncio.Queue()
# Contain a list of players
PlayerList = []

class Command(Enum):
    """
    The byte values sent as the first byte of any message in the war protocol.
    """
    WANTGAME = 0
    GAMESTART = 1
    PLAYCARD = 2
    PLAYRESULT = 3


class Result(Enum):
    """
    The byte values sent as the payload byte of a PLAYRESULT message.
    """
    WIN = 0
    DRAW = 1
    LOSE = 2

def kill_game(game):
    """
    TODO: If either client sends a bad message, immediately nuke the game.
    """
    pass

def compare_cards(card1, card2):
    """
    TODO: Given an integer card representation, return -1 for card1 < card2,
    0 for card1 = card2, and 1 for card1 > card2
    """

    if (card1 % 13) < (card2 % 13):
        return -1
    elif (card1 % 13) > (card2 % 13):
        return 1
    else:
        return 0

def deal_cards():
    """
    TODO: Randomize a deck of cards (list of ints 0..51), and return two
    26 card "hands."
    """

    cards = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20 , 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

    random.shuffle(cards)
    return (cards[:26], cards[26:])



async def play_game(players):
    player1 = players[0]
    player2 = players[1]

    start_playerone = await player1[0].readexactly(2)
    start_playertwo = await player2[0].readexactly(2)
    start_playerone = int.from_bytes(start_playerone, "big")
    start_playertwo = int.from_bytes(start_playertwo, "big")

    logging.info("Both players have started their game")

    # check if valid start command if not ensd game
    if start_playerone != 0 or start_playertwo != 0:
        logging.info("Killing the game")
        var = player1[1].close
        var2 = player2[1].close
        return

    cards = deal_cards()
    deck1 = [1] + cards[0]
    deck2 = [1] + cards[1]
    deck1 = bytes(deck1)
    deck2 = bytes(deck2)
    player1[1].write(deck1)
    player2[1].write(deck2)
    # Let each player make one move for every card in their deck for
    # 26 moves in total
    for pair in range(26):
        first_move = await player1[0].readexactly(2)
        second_move = await player2[0].readexactly(2)

        firstcommand = first_move[0]
        secondcommand = second_move[0]


        if firstcommand != 2 or secondcommand != 2:
            logging.info("Killing the game")
            player1[1].close
            player2[1].close

        # compare moves and return the win/lose command for this play
        # Player 1 wins and player 2 loses this round
        card1 = first_move[1]
        card2 = second_move[1]
        result = compare_cards(card1, card2)
        if result == 1:
            msg1 = bytes([3,0])
            msg2 = bytes([3,2])
            player1[1].write(msg1)
            player2[1].write(msg2)
        # Player 2 wins and player 1 loses this round
        elif result == -1:
            msg1 = bytes([3,2])
            msg2 = bytes([3,0])
            player1[1].write(msg1)
            player2[1].write(msg2)
        # There was a draw so send same message to both
        else:
            msg1 = bytes([3,1])
            msg2 = bytes([3,1])
            player1[1].write(msg1)
            player2[1].write(msg2)

    logging.info("End of game")
    var = player1[1].close
    var2 = player2[1].close



# This function will hold on client until two clients are available to play
# and will only run a game when two clients are connected.
async def get_client(r, w):
    # Check if the queue is empty first if it is then add current client to it
    if r is None or w is None:
        pass

    if queue.empty():
        p = (r, w)
        await queue.put(p)
        logging.info(" Waiting for one more client... ")
    # Check if there is one player in the queue already to be able to start game
    else:
        first_client = await queue.get()
        second_client = (r, w)
        PlayerList.append(first_client)
        PlayerList.append(second_client)
        players = (first_client, second_client)
        await play_game(players)
        logging.info(" Two clients are connected, beginning game")



def serve_game(host, port):
    """
    TODO: Open a socket for listening for new connections on host:port, and
    perform the war protocol to serve a game of war between each client.
    This function should run forever, continually serving clients.
    """
    if port < 0 or port > 65536:
        return

    loop = asyncio.get_event_loop()
    # Start coroutine here to start server
    coroutine = asyncio.start_server(get_client, host, port, loop=loop)
    server = loop.run_until_complete(coroutine)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

async def limit_client(host, port, loop, sem):
    """
    Limit the number of clients currently executing.
    You do not need to change this function.
    """
    async with sem:
        return await client(host, port, loop)

async def client(host, port, loop):
    """
    Run an individual client on a given event loop.
    You do not need to change this function.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port, loop=loop)
        # send want game
        writer.write(b"\0\0")
        card_msg = await reader.readexactly(27)
        myscore = 0
        for card in card_msg[1:]:
            writer.write(bytes([Command.PLAYCARD.value, card]))
            result = await reader.readexactly(2)
            if result[1] == Result.WIN.value:
                myscore += 1
            elif result[1] == Result.LOSE.value:
                myscore -= 1
        if myscore > 0:
            result = "won"
        elif myscore < 0:
            result = "lost"
        else:
            result = "drew"
        logging.debug("Game complete, I %s", result)
        writer.close()
        return 1
    except ConnectionResetError:
        logging.error("ConnectionResetError")
        return 0
    except asyncio.streams.IncompleteReadError:
        logging.error("asyncio.streams.IncompleteReadError")
        return 0
    except OSError:
        logging.error("OSError")
        return 0

def main(args):
    """
    launch a client/server
    """
    host = args[1]
    port = int(args[2])
    if args[0] == "server":
        try:
            # your server should serve clients until the user presses ctrl+c
            serve_game(host, port)
        except KeyboardInterrupt:
            pass
        return
    else:
        loop = asyncio.get_event_loop()

    if args[0] == "client":
        loop.run_until_complete(client(host, port, loop))
    elif args[0] == "clients":
        sem = asyncio.Semaphore(1000)
        num_clients = int(args[3])
        clients = [limit_client(host, port, loop, sem)
                   for x in range(num_clients)]
        async def run_all_clients():
            """
            use `as_completed` to spawn all clients simultaneously
            and collect their results in arbitrary order.
            """
            completed_clients = 0
            for client_result in asyncio.as_completed(clients):
                completed_clients += await client_result
            return completed_clients
        res = loop.run_until_complete(
            asyncio.Task(run_all_clients(), loop=loop))
        logging.info("%d completed clients", res)

    loop.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main(sys.argv[1:])


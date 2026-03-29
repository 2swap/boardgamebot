import discord

import games.connect4 as connect4
import games.snort as snort
import games.othello as othello
import games.gomoku as gomoku
import games.hextictactoe as hextictactoe
import games.hex as hex
import games.grort as grort

import os
from elo_manager import elo_manager
import random
from emojis import emojis
import asyncio

# TODO make challenges timeout after a certain amount of time
# TODO implement Go

with open('../bot.token', 'r') as f:
    TOKEN = f.read().strip()

intents = discord.Intents.default()
intents.message_content= True
intents.members = True

client = discord.Client(intents = intents)

class Handler:
    def __init__(self):
        self.id_game_dict = {}
        self.timeout_tasks = {}

    async def handle_checkmark_reaction(self, reaction, user, reacted_entry):
        owner = reacted_entry.get("owner")

        (player1, player2) = (owner, user) if random.random() < 0.5 else (user, owner)
        class_type = None
        if reacted_entry["game_type"] == "connect4":
            class_type = connect4.Connect4Game
        elif reacted_entry["game_type"] == "snort":
            class_type = snort.SnortGame
        elif reacted_entry["game_type"] == "othello":
            class_type = othello.OthelloGame
        elif reacted_entry["game_type"] == "go":
            class_type = go.GoGame
        elif reacted_entry["game_type"] == "gomoku":
            class_type = gomoku.GomokuGame
        elif reacted_entry["game_type"] == "hex":
            class_type = hex.HexGame
        elif reacted_entry["game_type"] == "hextictactoe":
            class_type = hextictactoe.HexTicTacToeGame
        elif reacted_entry["game_type"] == "grort":
            class_type = grort.GrortGame
        new_game = class_type(player1, player2, reacted_entry["settings"])

        print(f"Starting new game between {player1.name} and {player2.name} with settings: {reacted_entry['settings']}")
        # remove the open challenge mapping and delete the challenge message
        del self.id_game_dict[reaction.message.id]
        await reaction.message.delete()

        # send the new game message and set up timeout
        message_id = await new_game.send_game_message(reaction.message.channel)
        self.id_game_dict[message_id] = new_game
        task = asyncio.create_task(self._start_timeout(message_id, new_game, reaction.message.channel))
        self.timeout_tasks[message_id] = task
        print(f"Game started!")

    async def process_legal_move(self, message, reacted_game, move):
        # cancel timeout for this message since it's being acted on
        if message.id in self.timeout_tasks:
            try:
                self.timeout_tasks[message.id].cancel()
            except Exception:
                pass
            del self.timeout_tasks[message.id]

        del self.id_game_dict[message.id]
        await message.delete()
        reacted_game.make_move(move)

        reacted_game.resolve_outcome()
        if(reacted_game.outcome != None):
            await reacted_game.send_gameend_message(message.channel)
            return

        reacted_game.switch_turns()
        message_id = await reacted_game.send_game_message(message.channel)
        self.id_game_dict[message_id] = reacted_game
        # start timeout for new message
        task = asyncio.create_task(self._start_timeout(message_id, reacted_game, message.channel))
        self.timeout_tasks[message_id] = task

    async def handle_reaction(self, reaction, user):
        if user == client.user:
            return
        try:
            reacted_entry = self.id_game_dict[reaction.message.id]

            # If this is an open challenge, allow anyone except the owner to join by reacting
            if isinstance(reacted_entry, dict) and reacted_entry.get("open_challenge", False):
                await self.handle_checkmark_reaction(reaction, user, reacted_entry)

        # exception is thrown when a message not containing a game is reacted to
        # nothing will happen since the reaction must have been added to a non-game message
        except Exception as excep:
            pass

    async def send_help_message(self, channel):
        available_games = []
        for filename in os.listdir("games"):
            if filename.endswith(".py"):
                available_games.append(filename[:-3])
        await channel.send(f"Start a game with \"!gamename\". For example, \"!connect4\" opens an invitation to a Connect 4 game.\nAvailable games: {', '.join(available_games)}\nUse \"!help gamename\" for the rules of the game.")

    async def send_game_rules(self, channel, game_name):
        game_classes = {
            "connect4": connect4.Connect4Game,
            "snort": snort.SnortGame,
            "othello": othello.OthelloGame,
            "gomoku": gomoku.GomokuGame,
            "hex": hex.HexGame,
            "hextictactoe": hextictactoe.HexTicTacToeGame,
            "grort": grort.GrortGame,
        }
        game_class = game_classes.get(game_name)
        if game_class is None:
            await channel.send(f"Unknown game: \"{game_name}\". Use !help to see available games.")
            return
        rules = game_class.get_rules()
        if not rules:
            await channel.send(f"No rules available for {game_name}.")
            return
        await channel.send(f"**{game_name} rules:** {rules}")

    async def handle_message(self, message):
        if message.author == client.user:
            return

        message_content = message.content.lower()

        if len(message_content) > 0 and message_content[0] != "!":
            await self.handle_potential_move(message)

        if len(message_content) == 0 or message_content[0] != "!":
            return
        if message_content == "!":
            return

        print("Received command: " + message_content + " from user: " + message.author.name)

        command = message_content[1:].split()[0]
        arguments = message_content.split()[1:]

        if command == "help":
            if arguments:
                await self.send_game_rules(message.channel, arguments[0])
            else:
                await self.send_help_message(message.channel)
        elif command == "leaderboard":
            await message.channel.send(elo_manager.get_leaderboard())
        else:
            # post an open challenge anyone can join by reacting
            module = None
            if command == "connect4":
                module = connect4
            elif command == "snort":
                module = snort
            elif command == "othello":
                module = othello
            elif command == "go":
                module = go
            elif command == "gomoku":
                module = gomoku
            elif command == "hextictactoe":
                module = hextictactoe
            elif command == "hex":
                module = hex
            elif command == "grort":
                module = grort
            else:
                await self.send_help_message(message.channel)
                return
            game_type = command
            (success, settings, failure_message) = module.parse_settings(arguments)
            if not success:
                await message.channel.send(failure_message)
                return

            settings_str = module.get_settings_string(settings)
            content = f"Open {game_type} challenge from {message.author.mention}! React with ✅ to join. Settings: {settings_str}"
            print(f"Posting open {game_type} challenge from user: {message.author.name} with settings: {settings_str}")
            open_msg = await message.channel.send(content)

            try:
                await open_msg.add_reaction("✅")
            except Exception:
                pass

            # store open challenge metadata
            self_entry = {
                "open_challenge": True,
                "owner": message.author,
                "game_type": game_type,
                "settings": settings,
            }
            self.id_game_dict[open_msg.id] = self_entry

    async def handle_potential_move(self, message):
        message_content = message.content.lower()

        if message_content in ["forfeit", "resign", "quit"]:
            for game_id in self.id_game_dict:
                entry = self.id_game_dict[game_id]
                if isinstance(entry, dict):
                    continue
                if entry.get_player_to_move() != message.author:
                    continue
                game = entry
                del self.id_game_dict[game_id]
                game.forfeit(message.author)
                replied_message = await message.channel.fetch_message(game_id)
                await game.send_gameend_message(message.channel)
                await replied_message.delete()
                
                return

        # Find a game for which it's the author's turn.
        game = None
        replied_message_id = None
        for game_id in self.id_game_dict:
            entry = self.id_game_dict[game_id]
            if isinstance(entry, dict):
                continue
            if entry.get_player_to_move() != message.author:
                continue
            if entry.is_formatted_move(message_content):
                if entry.is_legal_move(message_content):
                    game = entry
                    replied_message_id = game_id
                    break
                else:
                    await message.channel.send(f"{message.author.mention}, that is not a legal move. {game.get_move_format_instructions()}")
                    return
        if not game: # no game found
            return
        replied_message = await message.channel.fetch_message(replied_message_id)
        await self.process_legal_move(replied_message, game, message_content)

    async def _start_timeout(self, message_id, game, channel):
        try:
            await asyncio.sleep(90)
            player_turn = game.get_player_to_move()
            # if the timeout task hasn't been cancelled by a move being made, then warn the player
            if not (message_id in self.id_game_dict):
                return
            
            await channel.send(f"{player_turn.mention}, you have 20 seconds to make a move before you forfeit the game!")
            await asyncio.sleep(20)
            
            if not (message_id in self.id_game_dict):
                return

            # Forfeit the game.
            del self.id_game_dict[message_id]
            game.forfeit(player_turn)
            await game.send_gameend_message(channel)
        except Exception:
            pass

handler = Handler();

@client.event
async def on_message(message):
    await handler.handle_message(message)

@client.event
async def on_reaction_add(reaction, user):
    await handler.handle_reaction(reaction, user)

client.run(TOKEN)

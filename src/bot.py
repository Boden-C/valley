import csv
from io import StringIO
import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import utils

# Load the token from the .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Create the bot
intents = discord.Intents.all()
# intents.messages = True  # Enable to read messages in guilds
# intents.members = True  # Enable to read members in guilds
# intents.reactions = True  # Enable to monitor reactions
# intents.guilds = True  # Enable to monitor guilds
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# On bot connecting to Discord
@client.event
async def on_ready():
    print(f'{client.user} has started')
    try:
        await tree.sync()
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# /get <channel | role> <category:string | contains:string>
@tree.command(name="get", description="Get channels or roles based on a category or name.")
@app_commands.describe(
    item_type="'channel or 'role' or 'members'",
    filter_type="'category' then value or 'contains' then value or 'all''",
    filter_value="The value for the category or substring filter."
)
async def get(interaction: discord.Interaction, item_type: str, filter_type: str, filter_value: str):
    guild = interaction.guild

    # Check if the command is run in a guild
    if guild is None:
        await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
        return

    # Defer the interaction to give more time for processing
    await interaction.response.defer()

    if item_type == "channel":
        if filter_type == "category":
            category = discord.utils.get(guild.categories, name=filter_value)
            if category:
                channels = sorted(category.channels, key=lambda c: c.position)
                channel_list = [f"{category.name} -> `#{channel.name}`" for channel in channels]
                await interaction.followup.send(f"Channels in category {filter_value}:\n```{'\n'.join(channel_list)}```")
            else:
                await interaction.followup.send(f"Category '{filter_value}' not found.")
        elif filter_type == "contains":
            category_channels = {}
            for channel in sorted(guild.channels, key=lambda c: c.position):
                if filter_value in channel.name:
                    category_name = channel.category.name if channel.category else "No Category"
                    if category_name not in category_channels:
                        category_channels[category_name] = []
                    category_channels[category_name].append(f"{channel.name}")

            output = []
            for category, channels in category_channels.items():
                output.append(f"{category}\n```" + '\n'.join(channels) + "```")

            if output:
                await interaction.followup.send('\n'.join(output))
            else:
                await interaction.followup.send(f"No channels found containing '{filter_value}'.")
                
    elif item_type == "role":
        bot_member = guild.get_member(client.user.id)
        bot_role = bot_member.top_role

        roles_below_bot = [role for role in guild.roles if role.position < bot_role.position]
        if (filter_type != "all"):
            roles_below_bot = [role for role in roles_below_bot if filter_value in role.name]
        roles_below_bot = sorted(roles_below_bot, key=lambda r: r.position)

        if roles_below_bot:
            output = StringIO()
            writer = csv.writer(output)
            for role in roles_below_bot:
                members = [member.name for member in role.members]
                writer.writerow([role.name] + members)
            output.seek(0)

            file = discord.File(StringIO(output.getvalue()), filename="roles_below_bot.csv")
            await interaction.followup.send("Here are the roles below the bot:", file=file)
        else:
            await interaction.followup.send("No roles found below the bot's role with the specified filter.")
            
    elif item_type == "members":
        if filter_type == "role":
            role = discord.utils.get(guild.roles, name=filter_value)
            if role:
                members = {member.name:member.id for member in role.members}
                await interaction.followup.send("\n".join(f"{name} {user_id}" for name, user_id in {member.name: member.id for member in role.members}.items()))
            else:
                await interaction.followup.send(f"Role '{filter_value}' not found.")
        elif filter_type == "contains":
            members = {member.name:member.id for member in guild.members if filter_value in member.name}
            if members:
                await interaction.followup.send("\n".join(f"{name} {user_id}" for name, user_id in {member.name: member.id for member in role.members}.items()))
            else:
                await interaction.followup.send(f"No members found with name containing '{filter_value}'.")
        elif filter_type == "all":
            members = {member.name:member.id for member in guild.members}
            await interaction.followup.send("\n".join(f"{name} {user_id}" for name, user_id in {member.name: member.id for member in role.members}.items()))
        else:
            await interaction.followup.send("Invalid filter type. Use 'role' or 'contains'.")
    else:
        await interaction.followup.send("Invalid item type. Use 'channel' or 'role'.")


# /addrole <roleName:string> <memberName:string>
@tree.command(name="addrole", description="Add a role to a member.")
@app_commands.describe(role_name="The name of the role to add.", member_name="The name of the member to add the role to.")
async def addRole(interaction: discord.Interaction, role_name: str, member_name: str):
    guild = interaction.guild

    # Check if the command is run in a guild
    if guild is None:
        await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
        return

    # Defer the interaction to give more time for processing
    await interaction.response.defer()

    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        await interaction.followup.send(f"Role '{role_name}' not found.")
        return

    member = discord.utils.get(guild.members, name=member_name)
    if member is None:
        await interaction.followup.send(f"Member '{member_name}' not found.")
        return

    try:
        await member.add_roles(role)
        await interaction.followup.send(f"Role '{role_name}' added to member '{member_name}'.")
    except discord.Forbidden:
        await interaction.followup.send(f"Bot lacks the required permissions to add roles.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")




# Create the /role command
@tree.command(name="role", description="Reorder roles based on a message ID")
@app_commands.describe(message_id="The ID of the message containing the ordered list of roles")
async def role(interaction: discord.Interaction, message_id: str):
    guild = interaction.guild
    
    # Fetch the message by ID
    try:
        message = await interaction.channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.response.send_message("Message not found.", ephemeral=True)
        return
    
    new_positions = message.content.splitlines()  # Assuming each role name is on a new line

    # Get roles below the bot
    bot_member = guild.get_member(client.user.id)
    bot_role = bot_member.top_role
    original_positions = [role for role in guild.roles if role.position < bot_role.position]

    # Create any missing roles
    for role_name in new_positions:
        if not discord.utils.get(guild.roles, name=role_name):
            await guild.create_role(name=role_name)

    # Fetch the updated roles list after creating missing roles
    updated_roles = [role for role in guild.roles if role.position < bot_role.position]

    # Map role names to their objects
    role_map = {role.name: role for role in updated_roles}

    # Create the final positions list with the roles that need to be moved
    final_positions = [role_map[role_name] for role_name in new_positions if role_name in role_map]

    # Reorder roles
    try:
        # Update the role positions
        await guild.edit_role_positions(positions={role: index + 1 for index, role in enumerate(final_positions)})
        await interaction.response.send_message("Roles have been reordered successfully.")
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to reorder roles.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
        
        
        
# Create the /assign command
@tree.command(name="assign", description="Assign roles to users based on a CSV-formatted message")
@app_commands.describe(message_id="The ID of the message containing the CSV of roles and users")
async def assign(interaction: discord.Interaction, message_id: str):
    guild = interaction.guild
    
    # Fetch the message by ID
    try:
        message = await interaction.channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.response.send_message("Message not found.", ephemeral=True)
        return
    
    csv_content = message.content

    # Parse the CSV content
    csv_reader = csv.reader(StringIO(csv_content))
    
    for row in csv_reader:
        if len(row) < 2:
            continue  # Skip any rows that don't have at least one role and one user
        
        role_name = row[0]
        user_identifiers = row[1:]
        
        # Find or create the role
        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            role = await guild.create_role(name=role_name)

        # Get the list of members who should have this role
        members_to_have_role = set()

        for user_identifier in user_identifiers:
            user = None
            
            if user_identifier.startswith("<@") and user_identifier.endswith(">"):
                # It's a mention
                user_id = int(user_identifier[2:-1].replace('!', ''))  # Remove mention formatting
                user = guild.get_member(user_id)
            else:
                # Search by username (new Discord username system without discriminator)
                user = discord.utils.find(lambda m: m.name == user_identifier, guild.members)
            
            if user:
                members_to_have_role.add(user)

        # Remove the role from members who shouldn't have it
        for member in role.members:
            if member not in members_to_have_role:
                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    await interaction.response.send_message(f"Failed to remove {role_name} from {member.display_name}: Insufficient permissions.", ephemeral=True)
                except discord.HTTPException as e:
                    await interaction.response.send_message(f"Failed to remove {role_name} from {member.display_name}: {str(e)}", ephemeral=True)

        # Assign the role to the members who should have it
        for member in members_to_have_role:
            if role not in member.roles:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    await interaction.response.send_message(f"Failed to assign {role_name} to {member.display_name}: Insufficient permissions.", ephemeral=True)
                except discord.HTTPException as e:
                    await interaction.response.send_message(f"Failed to assign {role_name} to {member.display_name}: {str(e)}", ephemeral=True)
    
    await interaction.response.send_message("Roles have been updated successfully.")


@tree.command(name="channel", description="Reorganize or create channels in a category based on a list.")
@app_commands.describe(
    category="The category to reorganize.",
    message_id="The ID of the message containing the list of channel names."
)
async def channel(interaction: discord.Interaction, category: str, message_id: str):
    guild = interaction.guild

    # Check if the command is run in a guild
    if guild is None:
        await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
        return

    # Fetch the category
    category_obj = discord.utils.get(guild.categories, name=category)
    if category_obj is None:
        await interaction.response.send_message(f"Category '{category}' not found.", ephemeral=True)
        return

    try:
        # Convert message_id to an integer if needed (since fetch_message expects an integer)
        message_id = int(message_id)
        message = await interaction.channel.fetch_message(message_id)
        channel_list = message.content.splitlines()  # Split message into channel names list

        # Track existing and missing channels
        existing_channels = {channel.name: channel for channel in category_obj.channels}
        new_channels = []

        # Reorder existing channels and track new channels
        for index, channel_name in enumerate(channel_list):
            if channel_name in existing_channels:
                # Reorder existing channels
                await existing_channels[channel_name].edit(position=index)
            else:
                # Track new channels to be created
                new_channels.append(channel_name)

        # Create new channels and position them
        for index, channel_name in enumerate(channel_list):
            if channel_name in new_channels:
                new_channel = await guild.create_text_channel(channel_name, category=category_obj)
                await new_channel.edit(position=index)

        await interaction.response.send_message(f"Channels in category '{category}' have been reorganized.", ephemeral=True)

    except discord.NotFound:
        await interaction.response.send_message(f"Message with ID {message_id} not found.", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("Invalid message ID format. Please provide a valid message ID.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

# /rename <messageID:string>
@tree.command(name="rename", description="Rename channels and roles based on message content.")
@app_commands.describe(message_id="The ID of the message containing the old and new names for renaming.")
async def rename(interaction: discord.Interaction, message_id: str):
    guild = interaction.guild
    try:
        # Defer the interaction response to allow time for the renaming process
        await interaction.response.defer()

        # Convert message_id to an integer if needed (since fetch_message expects an integer)
        message_id = int(message_id)
        message = await interaction.channel.fetch_message(message_id)
        lines = message.content.splitlines()  # Split message into lines
        renamed_items = []  # To keep track of renamed channels and roles

        for line in lines:
            if ',' in line:
                old_name, new_name = line.split(',', 1)  # Split into old and new names

                # Rename channels
                for channel in guild.channels:
                    if channel.name.strip() == old_name.strip():
                        await channel.edit(name=new_name.strip())
                        renamed_items.append(f"Channel '{old_name.strip()}' -> '{new_name.strip()}'")

                # Rename roles
                for role in guild.roles:
                    if role.name.strip() == old_name.strip():
                        await role.edit(name=new_name.strip())
                        renamed_items.append(f"Role '{old_name.strip()}' -> '{new_name.strip()}'")

        if renamed_items:
            await interaction.followup.send(f"Renamed the following items:\n" + "\n".join(renamed_items))
        else:
            await interaction.followup.send(f"No matching channels or roles found to rename.")

    except discord.Forbidden:
        await interaction.followup.send("Bot lacks the required permissions to rename channels or roles.")
    except discord.NotFound:
        await interaction.followup.send(f"Message with ID {message_id} not found.")
    except ValueError:
        await interaction.followup.send("Invalid message ID format. Please provide a valid message ID.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")

# Define the /send slash command
@tree.command(name="send", description="Send a literal string to a specific channel")
@app_commands.describe(channel_id="The ID of the channel to send the message to", message="The message to send (leave blank for a default message)")
async def send(interaction: discord.Interaction, channel_id: str, message: str = None):
    
    class_channel_mapping = {
        'ecs-2390✎ryan': 0,
        'cs-3162✎cole': 0,
        'cs-3162✎srivastava': 0,
        'cs-3345✎all': 0,
        'cs-3354✎narayanasami': 0,
        'cs-3354✎paulk': 0,
        'cs-3377✎all': 0,
        'cs-4141✎becker': 0,
        'cs-4337✎davis': 0,
        'cs-4341✎degroot': 0,
        'cs-4341✎hamdy': 0,
        'cs-4347✎omer': 0,
        'cs-4348✎gupta': 0,
        'cs-4349✎darbari': 0,
        'cs-4365✎all': 0,
        'cs-4384✎all': 0,
        'cs-4390✎all': 0,
        'math-2418✎all': 0,
        'cs-3334✎cankaya': 0,
        'cs-3345✎erbatur': 0,
        'cs-3345✎hamdy': 0,
        'cs-3354✎maweu': 0,
        'cs-3377✎belkoura': 0,
        'cs-3377✎satpute': 0,
        'cs-4341✎wang': 0,
        'cs-4347✎cankaya': 0,
        'cs-4347✎solanki': 0,
        'cs-4348✎kim-khah-mukherjee': 0,
        'cs-4348✎salazar': 0,
        'cs-4349✎chitturi': 0,
        'cs-4349✎erbatur': 0,
        'cs-4365✎guo': 0,
        'cs-4365✎nguyen-chung-ng': 0,
        'cs-4375✎yang': 0,
        'cs-4384✎huynh': 0,
        'cs-4384✎ntafos': 0,
        'cs-4390✎ding': 0,
        'cs-4390✎haas-saadatfar': 0,
        'cs-4392✎feng': 0,
        'cs-4485✎razo': 0,
        'ecs-2390✎montgomery': 0,
        'govt-2305✎all': 0
    }
    
    # Try to get the channel by its ID
    try:
        channels = await interaction.guild.fetch_channels()
        
        output_channel = client.get_channel(int(channel_id))
        if output_channel is None:
            await interaction.response.send_message("Channel not found.", ephemeral=True)
            return

        # Map each class/professor name to the corresponding channel ID
        for class_name in class_channel_mapping.keys():
            for channel in channels:
                if channel.name == class_name:
                    class_channel_mapping[class_name] = channel.id
                    break  # Stop searching once a match is found

        # Check if the message is blank, if so, use the default message
        if not message:
            message = f"""
            """

        # Send the message to the specified channel
        await output_channel.send(message)
        await interaction.response.send_message(f"Message sent to <#{channel_id}>", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)


# /help command
@tree.command(name="help", description="Provides help information about the bot's commands.")
async def help(interaction: discord.Interaction):
    help_text = """
    **Bot Commands:**
    - `/get <channel | role> <category:string | contains:string>`: Get channels or roles based on a category or name pattern.
    - `/rename <messageID:int>`: Rename channels and roles based on message content.
    - `/help`: Display this help message.
    """
    await interaction.response.send_message(help_text)

# Run the bot
client.run(TOKEN)

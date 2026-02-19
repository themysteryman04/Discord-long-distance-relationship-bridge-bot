import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import config
import database
import datetime
import random
import asyncio
import subprocess
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import ai_manager 
from zoneinfo import ZoneInfo
from discord.ext import tasks

# =========================================
# 1. SETUP & CONFIGURATION
# =========================================
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Global variable for Section 10 (Moments Game)
active_snaps = {} 

# =========================================
# 2. REMINDER SYSTEM LOGIC (Backend)
# =========================================

async def schedule_nagging_jobs(bot, event_time, task, channel_id, mention_text):
    """
    Schedules 5 separate alerts: 
    - 60 mins before
    - 45 mins before
    - 30 mins before
    - 15 mins before
    - ON TIME (0 mins)
    """
    intervals = [60, 45, 30, 15, 0]
    
    for minutes in intervals:
        run_time = event_time - datetime.timedelta(minutes=minutes)
        
        # Only schedule if the time hasn't passed yet
        if run_time > datetime.datetime.now(ZoneInfo("Asia/Kuala_Lumpur")):
            bot.scheduler.add_job(
                send_reminder_alert, 
                'date', 
                run_date=run_time, 
                args=[channel_id, mention_text, task, minutes]
            )

async def send_reminder_alert(channel_id, mention_text, task, minutes_left):
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    if minutes_left == 0:
        embed = discord.Embed(
            title="🚨 IT IS TIME! 🚨",
            description=f"**Event:** {task}\n\n{mention_text}, go do it now!",
            color=discord.Color.red()
        )
        await channel.send(content=mention_text, embed=embed)
    else:
        embed = discord.Embed(
            title=f"⏰ Upcoming Event: {minutes_left} mins",
            description=f"**Event:** {task}",
            color=discord.Color.orange()
        )
        await channel.send(content=mention_text, embed=embed)

# =========================================
# 3. DAILY QUESTION SYSTEM
# =========================================

class AnswerModal(discord.ui.Modal, title='Today\'s Question'):
    answer = discord.ui.TextInput(
        label='Your Answer', 
        style=discord.TextStyle.paragraph,
        placeholder="Type here...",
        min_length=2
    )

    def __init__(self, question_id, view_instance):
        super().__init__()
        self.question_id = question_id
        self.view_instance = view_instance

    async def on_submit(self, interaction: discord.Interaction):
        await database.save_answer(
            self.question_id, 
            interaction.user.id, 
            interaction.user.display_name, 
            self.answer.value
        )
        await interaction.response.send_message("✅ Answer saved! Waiting for your partner...", ephemeral=True)
        await self.view_instance.check_reveal(interaction.channel)

class QuestionView(discord.ui.View):
    def __init__(self, question_id=None):
        super().__init__(timeout=None)
        self.question_id = question_id

    @discord.ui.button(label="✍️ Answer Secretly", style=discord.ButtonStyle.blurple, custom_id="ans_btn")
    async def answer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Extract question_id from message or use stored one
        question_id = self.question_id
        if not question_id and interaction.message:
            # Try to extract from embed footer
            for embed in interaction.message.embeds:
                if embed.footer and embed.footer.text:
                    question_id = embed.footer.text.split("ID: ")[-1] if "ID: " in embed.footer.text else None
        
        if not question_id:
            await interaction.response.send_message("❌ Question ID not found. Please try again.", ephemeral=True)
            return
        await interaction.response.send_modal(AnswerModal(question_id, self))

    async def check_reveal(self, channel):
        answers = await database.get_answers(self.question_id)
        if len(answers) >= 2:
            embed = discord.Embed(
                title="✨ Answers Revealed!", 
                description="The Daily Question has been answered by both.",
                color=discord.Color.gold()
            )
            for user, content in answers:
                embed.add_field(name=f"👤 {user}", value=f"💬 {content}", inline=False)
            await channel.send(embed=embed)
            self.stop()

async def send_daily_question():
    target_channel = bot.get_channel(config.CHANNELS["daily_question"])
    
    if not target_channel:
        print("❌ Error: Daily Question Channel not found.")
        return

    malaysia_time = datetime.datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
    q_id = malaysia_time.strftime("%Y-%m-%d_%H-%M-%S")
    
    # Updated to handle potential AI errors gracefully
    try:
        question_text = await ai_manager.get_ai_question()
    except Exception as e:
        print(f"Daily Question Error: {e}")
        question_text = "**What is one thing you are grateful for today?**"

    embed = discord.Embed(
        title="💖 Daily Question", 
        description=question_text, 
        color=discord.Color.from_rgb(255, 105, 180)
    )
    embed.set_footer(text=f"Both partners must answer to reveal. ID: {q_id}")

    await target_channel.send(embed=embed, view=QuestionView(q_id))
    print(f"✅ Daily Question posted for {q_id}")

# =========================================
# 4. BOUNTY SYSTEM (Escrow Logic)
# =========================================

class ApprovalView(discord.ui.View):
    def __init__(self, reward, employer_id, worker_id):
        super().__init__(timeout=None)
        self.reward = reward
        self.employer_id = employer_id
        self.worker_id = worker_id

    @discord.ui.button(label="✅ Approve & Pay", style=discord.ButtonStyle.success, custom_id="approve_pay")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.employer_id:
            await interaction.response.send_message("❌ You are the worker! You must wait for approval.", ephemeral=True)
            return

        await database.add_money(self.worker_id, self.reward)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_field_at(0, name="Status", value=f"💰 PAID to <@{self.worker_id}>")
        
        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.followup.send(f"💸 Transaction Complete! <@{self.worker_id}> has received {self.reward} Us-Bucks.")

    @discord.ui.button(label="❌ Reject (Not Done)", style=discord.ButtonStyle.danger, custom_id="reject_work")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.employer_id:
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.orange()
        embed.set_field_at(0, name="Status", value=f"⚠️ Rejected. Back to work, <@{self.worker_id}>!")
        
        await interaction.response.edit_message(embed=embed, view=InProgressView(self.reward, self.employer_id, self.worker_id))

class InProgressView(discord.ui.View):
    def __init__(self, reward, employer_id, worker_id):
        super().__init__(timeout=None)
        self.reward = reward
        self.employer_id = employer_id
        self.worker_id = worker_id

    @discord.ui.button(label="📩 Submit for Approval", style=discord.ButtonStyle.primary, custom_id="submit_work")
    async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.worker_id:
            await interaction.response.send_message("❌ This isn't your job!", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.gold()
        embed.set_field_at(0, name="Status", value=f"⏳ Pending Approval from <@{self.employer_id}>")
        
        await interaction.response.edit_message(embed=embed, view=ApprovalView(self.reward, self.employer_id, self.worker_id))
        await interaction.followup.send(f"<@{self.employer_id}>, please review the work!", ephemeral=False)

    @discord.ui.button(label="🏳️ I Give Up (Unclaim)", style=discord.ButtonStyle.secondary, custom_id="forfeit_job")
    async def forfeit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.worker_id:
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.blue()
        embed.set_field_at(0, name="Status", value="🟢 OPEN")
        
        await interaction.response.edit_message(embed=embed, view=BountyView(self.reward, self.employer_id))

    @discord.ui.button(label="🗑️ Force Cancel (Refund)", style=discord.ButtonStyle.danger, custom_id="force_cancel")
    async def force_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.employer_id:
            await interaction.response.send_message("❌ Only the Employer can cancel.", ephemeral=True)
            return

        await database.add_money(self.employer_id, self.reward)
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_field_at(0, name="Status", value="❌ CANCELLED (Refunded)")
        
        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.followup.send("💰 Bounty cancelled. Money refunded.", ephemeral=True)

class BountyView(discord.ui.View):
    def __init__(self, reward, employer_id):
        super().__init__(timeout=None)
        self.reward = reward
        self.employer_id = employer_id

    @discord.ui.button(label="🙋‍♂️ I'll do it!", style=discord.ButtonStyle.success, custom_id="claim_bounty")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.employer_id:
            await interaction.response.send_message("❌ You can't claim your own bounty!", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.orange()
        embed.set_field_at(0, name="Status", value=f"🚧 In Progress by {interaction.user.mention}")
        
        await interaction.response.edit_message(embed=embed, view=InProgressView(self.reward, self.employer_id, interaction.user.id))

    @discord.ui.button(label="🗑️ Cancel & Refund", style=discord.ButtonStyle.danger, custom_id="cancel_open_bounty")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.employer_id:
            return

        await database.add_money(self.employer_id, self.reward)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_field_at(0, name="Status", value="❌ CANCELLED (Refunded)")
        
        await interaction.response.edit_message(embed=embed, view=None)

@bot.command()
async def bounty(ctx, reward: int, *, task: str):
    target_channel = bot.get_channel(config.CHANNELS["bounty_board"])
    if not target_channel:
        await ctx.send("❌ Error: Channel ID not set.")
        return
    if reward <= 0:
        await ctx.send("❌ Reward must be positive.")
        return

    if await database.purchase_item(ctx.author.id, reward):
        embed = discord.Embed(
            title="📜 WANTED: Task Assistance",
            description=f"**Task:** {task}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Status", value="🟢 OPEN")
        embed.add_field(name="Reward", value=f"💰 {reward} Us-Bucks")
        embed.set_footer(text=f"Employer: {ctx.author.display_name}")

        await target_channel.send(embed=embed, view=BountyView(reward, ctx.author.id))
        await ctx.message.delete()
        await ctx.send(f"✅ Bounty posted! **{reward} Us-Bucks** held in escrow.", delete_after=5)
    else:
        await ctx.send(f"💸 **Insufficient Funds!** You need {reward} Us-Bucks.")

# =========================================
# 5. DECISION ROOM (AI POWERED)
# =========================================

class DecisionView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=None)
        self.options = options

    @discord.ui.button(label="🎲 Spin the Wheel", style=discord.ButtonStyle.primary, custom_id="bot_pick")
    async def pick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        choice = random.choice(self.options)
        
        await interaction.response.send_message(
            f"🎰 The Wheel spins... and lands on:\n# 🎉 **{choice}** 🎉", 
            ephemeral=False
        )

async def create_poll(ctx, question, options):
    target_channel = bot.get_channel(config.CHANNELS["decision_room"])
    if not target_channel:
        await ctx.send("❌ Error: 'decision_room' ID not found.")
        return

    emojis = ["1️⃣", "2️⃣", "3️⃣"]
    
    description_text = ""
    for i, option in enumerate(options):
        description_text += f"{emojis[i]} **{option}**\n\n"

    embed = discord.Embed(
        title=f"🤖 {question}",
        description=description_text,
        color=discord.Color.teal()
    )
    embed.set_footer(text="Vote with reactions, or click Spin to decide randomly.")

    msg = await target_channel.send(embed=embed, view=DecisionView(options))
    
    for i in range(len(options)):
        await msg.add_reaction(emojis[i])
            
    if ctx.channel.id != target_channel.id:
        await ctx.send(f"✅ Poll created in {target_channel.mention}!", delete_after=3)
    else:
        await ctx.message.delete()

# --- AI COMMANDS ---
@bot.command()
async def food(ctx, *, criteria="Surprise us"):
    await ctx.send(f"🍳 *Chef Bot is thinking about: {criteria}...*", delete_after=4)
    options = await ai_manager.get_choices("Food/Meal", criteria)
    await create_poll(ctx, f"Food Plan: {criteria}", options)

@bot.command()
async def movie(ctx, *, genre="Any Genre"):
    await ctx.send(f"🎬 *Checking the box office for {genre}...*", delete_after=4)
    options = await ai_manager.get_choices("Movie", f"Genre/Vibe: {genre}. specific movie titles")
    await create_poll(ctx, f"Movie Night: {genre}", options)

@bot.command()
async def date(ctx, *, vibe="Any type"):
    await ctx.send(f"🌹 *Brainstorming date ideas for: {vibe}...*", delete_after=4)
    options = await ai_manager.get_choices(
        "Date Idea", 
        f"User Preference: {vibe}. Keep it romantic/fun. STRICTLY NO ALCOHOL."
    )
    await create_poll(ctx, f"Date Night: {vibe}", options)

@bot.command()
async def book(ctx, *, criteria="Any Genre"):
    await ctx.send(f"📚 *Scanning the library for: {criteria}...*", delete_after=4)
    options = await ai_manager.get_choices(
        "Book", 
        f"Genre/Topic: {criteria}. Specific book titles with authors."
    )
    await create_poll(ctx, f"Book Recommendation: {criteria}", options)

@bot.command()
async def tv(ctx, *, criteria="Any Genre"):
    await ctx.send(f"📺 *Browsing streaming services for: {criteria}...*", delete_after=4)
    options = await ai_manager.get_choices(
        "TV Show", 
        f"Genre/Vibe: {criteria}. Specific series titles."
    )
    await create_poll(ctx, f"TV Show Night: {criteria}", options)

@bot.command()
async def decide(ctx, question: str, *options):
    if len(options) < 2:
        await ctx.send("❌ I need at least 2 options!")
        return
    await create_poll(ctx, question, options)

# =========================================
# 6. REMINDER & PING COMMANDS
# =========================================

async def process_reminder(ctx, raw_args, is_public_ping):
    now_malaysia = datetime.datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
    now_str = now_malaysia.strftime("%Y-%m-%d %H:%M:%S")

    await ctx.send("⏳ *Setting alarms...*", delete_after=3)
    extracted_time = await ai_manager.extract_datetime(raw_args, now_str)

    if not extracted_time or "None" in extracted_time:
        await ctx.send("❌ I couldn't understand the time. Try format: `tomorrow at 5pm` or `in 2 hours`.")
        return

    try:
        event_time = datetime.datetime.strptime(extracted_time, "%Y-%m-%d %H:%M:%S")
        event_time = event_time.replace(tzinfo=ZoneInfo("Asia/Kuala_Lumpur"))
    except ValueError:
        await ctx.send("❌ Internal Date Error.")
        return

    if event_time < now_malaysia:
        await ctx.send("❌ That time has already passed!")
        return

    if is_public_ping:
        mention = "@everyone" 
        color = discord.Color.red()
        title = "📢 PUBLIC ANNOUNCEMENT"
    else:
        mention = ctx.author.mention
        color = discord.Color.blue()
        title = "🔔 Personal Reminder"

    task_description = raw_args
    await schedule_nagging_jobs(bot, event_time, task_description, ctx.channel.id, mention)

    embed = discord.Embed(
        title=title,
        description=f"**Event:** {task_description}\n**Time:** {event_time.strftime('%I:%M %p (%d %b)')}",
        color=color
    )
    embed.add_field(name="📅 Schedule", value="I will remind you at: 60m, 45m, 30m, 15m, and 0m marks.")
    embed.set_footer(text=f"Set by {ctx.author.display_name}")

    await ctx.send(embed=embed)

@bot.command()
async def remind(ctx, *, args):
    await process_reminder(ctx, args, is_public_ping=False)

@bot.command()
async def ping(ctx, *, args):
    await process_reminder(ctx, args, is_public_ping=True)

# =========================================
# 7. ECONOMY (The Persistent Shop)
# =========================================

class BuyModal(discord.ui.Modal, title='Purchase Item'):
    item_id = discord.ui.TextInput(
        label='Item ID',
        placeholder='e.g. 1, 2, or 3',
        min_length=1,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        i_id = self.item_id.value.strip()
        item = config.SHOP_ITEMS.get(i_id)
        
        if not item:
            await interaction.response.send_message("❌ Item ID not found!", ephemeral=True)
            return

        success = await database.purchase_item(interaction.user.id, item['cost'])
        
        if not success:
            await interaction.response.send_message("💸 **Insufficient Funds!** Answer more daily questions.", ephemeral=True)
            return

        # Success Logic
        await interaction.response.defer() 

        # 1. Send Receipt
        receipt_embed = discord.Embed(
            description=f"🎉 {interaction.user.mention} just bought **{item['name']}** for {item['cost']} Us-Bucks!",
            color=discord.Color.gold()
        )
        await interaction.channel.send(embed=receipt_embed)

        # 2. Reset the Menu (Delete old, send new)
        try:
            await interaction.message.delete()
        except:
            pass 
        await send_shop_menu(interaction.channel)


class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛒 Buy Item", style=discord.ButtonStyle.success, custom_id="shop_buy_btn")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BuyModal())

    @discord.ui.button(label="💰 Check Wallet", style=discord.ButtonStyle.secondary, custom_id="shop_wallet_btn")
    async def wallet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        balance = await database.get_balance(interaction.user.id)
        await interaction.response.send_message(f"💳 Your Balance: **{balance} Us-Bucks**", ephemeral=True)


async def send_shop_menu(channel):
    """Helper function to generate the shop interface"""
    # Updated Title per request
    embed = discord.Embed(
        title="🛍️ Shop",
        description="Click **Buy Item** and enter the ID of the reward you want.",
        color=discord.Color.purple()
    )
    
    for item_id, details in config.SHOP_ITEMS.items():
        embed.add_field(
            name=f"ID: {item_id} | {details['name']}",
            value=f"🏷️ **{details['cost']} Us-Bucks**",
            inline=False
        )
    
    await channel.send(embed=embed, view=ShopView())


@bot.command()
async def shop(ctx):
    """Resets the shop menu. Run this inside the shop channel."""
    target_id = config.CHANNELS.get("shop")
    if ctx.channel.id != target_id:
        return

    # Purge old messages to keep it clean
    try:
        await ctx.channel.purge(limit=10)
    except:
        pass
    
    await send_shop_menu(ctx.channel)

# =========================================
# 8. WIKI OF US (Memory System)
# =========================================

@bot.command()
async def remember(ctx, key: str, *, value: str = None):
    # Check if in wiki channel
    wiki_channel_id = config.CHANNELS.get("wiki_of_us")
    if ctx.channel.id != wiki_channel_id:
        await ctx.send(f"❌ This command only works in <#{wiki_channel_id}>")
        return
    
    # 1. Check for attachments
    attachment_data = None
    if ctx.message.attachments:
        # Store "ChannelID|MessageID"
        attachment_data = f"{ctx.channel.id}|{ctx.message.id}"

    if value:
        value = value.strip('"').strip("'")

    if not value and not attachment_data:
        await ctx.send("❌ You need to provide text or an image!")
        return

    # 2. Save IDs to Database
    await database.set_wiki_entry(key.lower(), value, attachment_data, ctx.author.display_name)

    await ctx.message.add_reaction("✅")
    # DO NOT delete the user's message! The bot needs it to exist to fetch the image later.


@bot.command()
async def wiki(ctx):
    """Shows a unified list of all memories: wiki entries, snaps, and logs."""
    # Check if in wiki channel
    wiki_channel_id = config.CHANNELS.get("wiki_of_us")
    if ctx.channel.id != wiki_channel_id:
        await ctx.send(f"❌ This command only works in <#{wiki_channel_id}>")
        return
    
    keys = await database.get_all_wiki_keys()
    moments = await database.get_all_moments()
    
    if not keys and not moments:
        await ctx.send("The Wiki is empty! Use `!remember \"key\" \"value\"` to add something or `!snap`/`!log` to capture moments.")
        return

    # Create unified list
    all_items = []
    
    # Add wiki entries
    for key in keys:
        all_items.append(("📝", key, "memory"))
    
    # Add moments
    for user_id, caption, _, timestamp, source in moments:
        source_emoji = "⚡" if source == "SNAP" else "📝"
        all_items.append((source_emoji, caption, "moment"))
    
    # Sort by type then alphabetically
    all_items.sort(key=lambda x: (x[2], x[1]))
    
    # Build embed with paginated list
    embed = discord.Embed(
        title="📚 The Wiki of Us - Complete Index",
        description=f"**Total items:** {len(all_items)} (Memories + Moments)\n\nUse `!get <name or caption>` to view details.",
        color=discord.Color.blue()
    )
    
    # Create list string
    list_str = ""
    for emoji, name, item_type in all_items:
        list_str += f"{emoji} **{name}**\n"
    
    # If list is too long, truncate
    if len(list_str) > 1024:
        list_str = list_str[:1000] + "\n*...and more*"
    
    embed.add_field(
        name="All Memories & Moments",
        value=list_str if list_str else "*(empty)*",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def get(ctx, *, key: str):
    # Check if in wiki channel
    wiki_channel_id = config.CHANNELS.get("wiki_of_us")
    if ctx.channel.id != wiki_channel_id:
        await ctx.send(f"❌ This command only works in <#{wiki_channel_id}>")
        return
    
    search_key = key.strip('"').strip("'").lower()
    
    # First, try to find a wiki entry
    wiki_entry = await database.get_wiki_entry(search_key)
    
    if wiki_entry:
        # Found a wiki entry
        content, attachment_data = wiki_entry
        image_url = None

        # Dynamic Refresh Logic for wiki attachments
        if attachment_data:
            try:
                c_id, m_id = attachment_data.split('|')
                channel = bot.get_channel(int(c_id))
                if channel:
                    msg = await channel.fetch_message(int(m_id))
                    if msg.attachments:
                        image_url = msg.attachments[0].url
            except Exception:
                image_url = None

        embed = discord.Embed(
            title=f"📝 {search_key.title()}",
            description=content if content else "",
            color=discord.Color.green()
        )
        
        if image_url:
            embed.set_image(url=image_url)
        elif attachment_data: 
            embed.set_footer(text="⚠️ Image not found (Original message was deleted?)")

        try:
            await ctx.author.send(embed=embed)
            await ctx.message.add_reaction("📩")
        except discord.Forbidden:
            await ctx.send("❌ Enable DMs!")
        return
    
    # If no wiki entry, try to find a moment by caption
    moment = await database.get_moment_by_caption(search_key)
    
    if moment:
        # Found a moment
        user_id, caption, attachment_data, timestamp, source = moment
        image_url = None
        
        # Get image URL for moment
        if attachment_data:
            try:
                c_id, m_id = attachment_data.split('|')
                channel = bot.get_channel(int(c_id))
                if channel:
                    msg = await channel.fetch_message(int(m_id))
                    if msg.attachments:
                        image_url = msg.attachments[0].url
            except Exception:
                image_url = None
        
        source_label = "⚡ SNAP CHALLENGE" if source == "SNAP" else "📝 MANUAL LOG"
        embed = discord.Embed(
            title=f"📸 {caption}",
            description=f"**Type:** {source_label}\n📅 {timestamp}\n👤 <@{user_id}>",
            color=discord.Color.purple()
        )
        
        if image_url:
            embed.set_image(url=image_url)
        else:
            embed.set_footer(text="⚠️ Image not found (Original message was deleted?)")
        
        try:
            await ctx.author.send(embed=embed)
            await ctx.message.add_reaction("📸")
        except discord.Forbidden:
            await ctx.send("❌ Enable DMs!")
        return
    
    # Not found in either wiki or moments
    await ctx.send(f"❌ Not found: **{search_key}**\n\nSearches both wiki entries and moment captions.")


# =========================================
# 9. TRUTH OR DARE (Simplified)
# =========================================

class DareVerifyView(discord.ui.View):
    def __init__(self, dare_id=None, challenger_id=None, victim_id=None, reward=None):
        super().__init__(timeout=None)
        self.dare_id = dare_id
        self.challenger_id = challenger_id
        self.victim_id = victim_id
        self.reward = reward

    @discord.ui.button(label="💰 Verify & Pay", style=discord.ButtonStyle.success, custom_id="tod_verify")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Extract dare data from footer if None (after restart)
        if self.dare_id is None and interaction.message:
            for embed in interaction.message.embeds:
                if embed.footer and "DARE:" in embed.footer.text:
                    parts = embed.footer.text.split(" | ")
                    if len(parts) >= 4:
                        self.dare_id = parts[0].replace("DARE: ", "")
                        self.challenger_id = int(parts[1])
                        self.victim_id = int(parts[2])
                        self.reward = int(parts[3])
                    break
        
        # AI/Bot challenges (ID 0) are auto-approved if user says they did it
        if self.challenger_id != 0 and interaction.user.id != self.challenger_id:
            await interaction.response.send_message("❌ Only the Challenger can approve payment!", ephemeral=True)
            return

        await database.add_money(self.victim_id, self.reward)
        await database.update_dare_status(self.dare_id, "COMPLETED")

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_field_at(0, name="Status", value=f"🎉 **COMPLETED!** Paid {self.reward} Us-Bucks.")
        
        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.followup.send(f"💸 Cha-ching! <@{self.victim_id}> earned **{self.reward}** Us-Bucks!")

    @discord.ui.button(label="❌ Not Done Yet", style=discord.ButtonStyle.danger, custom_id="tod_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Extract dare data from footer if None (after restart)
        if self.dare_id is None and interaction.message:
            for embed in interaction.message.embeds:
                if embed.footer and "DARE:" in embed.footer.text:
                    parts = embed.footer.text.split(" | ")
                    if len(parts) >= 4:
                        self.dare_id = parts[0].replace("DARE: ", "")
                        self.challenger_id = int(parts[1])
                        self.victim_id = int(parts[2])
                        self.reward = int(parts[3])
                    break
        
        if self.challenger_id != 0 and interaction.user.id != self.challenger_id:
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.orange()
        embed.set_field_at(0, name="Status", value=f"🚧 **IN PROGRESS** (Proof Rejected)")
        
        # Send it back to the 'Active' state so they can try again
        await interaction.response.edit_message(embed=embed, view=DareActiveView(self.dare_id, self.challenger_id, self.victim_id, self.reward))
        await interaction.followup.send(f"⚠️ <@{self.victim_id}>, that didn't count! Try again.", ephemeral=False)

class DareActiveView(discord.ui.View):
    def __init__(self, dare_id=None, challenger_id=None, victim_id=None, reward=None):
        super().__init__(timeout=None)
        self.dare_id = dare_id
        self.challenger_id = challenger_id
        self.victim_id = victim_id
        self.reward = reward

    @discord.ui.button(label="✅ I Did It (Mark Done)", style=discord.ButtonStyle.primary, custom_id="tod_done")
    async def done_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Extract dare data from footer if None (after restart)
        if self.dare_id is None and interaction.message:
            for embed in interaction.message.embeds:
                if embed.footer and "DARE:" in embed.footer.text:
                    parts = embed.footer.text.split(" | ")
                    if len(parts) >= 4:
                        self.dare_id = parts[0].replace("DARE: ", "")
                        self.challenger_id = int(parts[1])
                        self.victim_id = int(parts[2])
                        self.reward = int(parts[3])
                    break
        
        if interaction.user.id != self.victim_id:
            await interaction.response.send_message("❌ You aren't the one doing this dare!", ephemeral=True)
            return

        await database.update_dare_status(self.dare_id, "WAITING_APPROVAL")
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.gold()
        embed.set_field_at(0, name="Status", value=f"⏳ **WAITING REVIEW** from <@{self.challenger_id}>")
        
        # Switch to Verify View
        await interaction.response.edit_message(embed=embed, view=DareVerifyView(self.dare_id, self.challenger_id, self.victim_id, self.reward))
        
        # Ping the challenger
        if self.challenger_id != 0:
            await interaction.followup.send(f"🔔 <@{self.challenger_id}>, please verify the dare!", ephemeral=False)
        else:
            # Auto-approve if it was a Bot Dare
            await self.approve_bot_dare(interaction)

    async def approve_bot_dare(self, interaction):
        # Special helper to auto-complete bot dares
        await database.add_money(self.victim_id, self.reward)
        await database.update_dare_status(self.dare_id, "COMPLETED")
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_field_at(0, name="Status", value=f"🎉 **COMPLETED!** (Bot Approved)")
        await interaction.edit_original_response(embed=embed, view=None)
        await interaction.followup.send(f"🤖 Bot says: Good job! Sent you {self.reward} Us-Bucks.")

class DarePendingView(discord.ui.View):
    def __init__(self, dare_id=None, challenger_id=None, reward=None):
        super().__init__(timeout=None)
        self.dare_id = dare_id
        self.challenger_id = challenger_id
        self.reward = reward

    @discord.ui.button(label="😈 I Accept", style=discord.ButtonStyle.success, custom_id="tod_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Extract dare data from footer if None (after restart)
        if self.dare_id is None and interaction.message:
            for embed in interaction.message.embeds:
                if embed.footer and "DARE:" in embed.footer.text:
                    parts = embed.footer.text.split(" | ")
                    if len(parts) >= 4:
                        self.dare_id = parts[0].replace("DARE: ", "")
                        self.challenger_id = int(parts[1])
                        self.reward = int(parts[3])
                    break
        
        if self.challenger_id != 0 and interaction.user.id == self.challenger_id:
            await interaction.response.send_message("❌ You can't accept your own dare!", ephemeral=True)
            return

        await database.update_dare_status(self.dare_id, "IN_PROGRESS", victim_id=interaction.user.id)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.orange()
        embed.set_field_at(0, name="Status", value=f"🚧 **IN PROGRESS** by {interaction.user.mention}")
        embed.set_footer(text=f"DARE: {self.dare_id} | {self.challenger_id} | {interaction.user.id} | {self.reward}")
        
        await interaction.response.edit_message(embed=embed, view=DareActiveView(self.dare_id, self.challenger_id, interaction.user.id, self.reward))

@bot.command()
async def dare(ctx):
    """Manually start a dare for your partner."""
    # Modified to catch AI errors without crashing
    try:
        task, price = await ai_manager.get_ai_dare()
    except Exception as e:
        print(f"Manual Dare Error: {e}")
        task, price = "Hold a plank for 45 seconds.", 30

    dare_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    await database.create_dare(dare_id, ctx.author.id, task, price)
    
    embed = discord.Embed(
        title="🔥 New Dare!",
        description=f"## **{task}**\n\n💰 **Reward:** {price} Us-Bucks",
        color=discord.Color.dark_magenta()
    )
    embed.add_field(name="Status", value="🟡 Waiting for a victim...")
    embed.set_footer(text=f"DARE: {dare_id} | {ctx.author.id} | 0 | {price}")
    
    await ctx.send(embed=embed, view=DarePendingView(dare_id, ctx.author.id, price))


# =========================================
# 10. MOMENTS (The BeReal Game - Multi-User)
# =========================================

async def trigger_snap_for_user(user_id):
    """Called by scheduler 3x a day per person."""
    channel_id = config.CHANNELS.get("moments")
    channel = bot.get_channel(channel_id)
    
    if not channel: return

    # 1. Set Deadline (15 mins)
    now = datetime.datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
    deadline = now + datetime.timedelta(minutes=15)
    
    # 2. Activate Game for THIS user only
    global active_snaps
    active_snaps[user_id] = deadline
    
    # 3. Send Alert
    await channel.send(
        f"📸 **SNAP TIME!** <@{user_id}>\n"
        f"⚠️ **What are you doing right now?**\n"
        f"Reply with `!snap <caption >` and a photo within **15 minutes**!"
    )

async def save_moment_logic(ctx, caption, source, reward):
    """
    Helper to save photo and pay user.
    Returns TRUE if successful, FALSE if failed (no photo).
    """
    if not ctx.message.attachments:
        await ctx.send("❌ You forgot the photo! Attach an image to your command.")
        return False

    # Save Data
    attachment_data = f"{ctx.channel.id}|{ctx.message.id}"
    timestamp = datetime.datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y-%m-%d %H:%M:%S")
    
    await database.add_moment(ctx.author.id, caption, attachment_data, timestamp, source)
    await database.add_money(ctx.author.id, reward)
    
    embed = discord.Embed(
        description=f"✅ **Memory Saved!**\n💰 Earned **{reward} Us-Bucks**.",
        color=discord.Color.green()
    )
    if source == 'SNAP':
        embed.title = "⚡ SNAP CHALLENGE COMPLETE!"
        embed.color = discord.Color.gold()
        
    await ctx.send(embed=embed)
    return True

@bot.command()
async def snap(ctx, *, caption: str = "Just vibing"):
    """Participate in YOUR active Snap Challenge."""
    global active_snaps
    
    # 1. Check if user has an active deadline
    deadline = active_snaps.get(ctx.author.id)
    
    if not deadline:
        await ctx.send("❌ You haven't been challenged right now! Use `!log` to save a manual memory.")
        return

    # 2. Check Time
    now = datetime.datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
    if now > deadline:
        await ctx.send("⏰ **Too late!** The 15-minute window closed. Use `!log` instead.")
        del active_snaps[ctx.author.id] # Cleanup expired entry
        return

    # 3. Attempt to Save (Pass the result back)
    success = await save_moment_logic(ctx, caption, "SNAP", 50)
    
    # 4. Only remove from active list if they actually succeeded
    if success:
        del active_snaps[ctx.author.id]
@bot.command()
async def log(ctx, *, caption: str = "Memory Log"):
    """Manually add a photo anytime."""
    await save_moment_logic(ctx, caption, "LOG", 5) 

@bot.command()
async def flashback(ctx):
    """Shows a random photo from the past."""
    row = await database.get_random_moment()
    if not row:
        await ctx.send("📭 No memories found yet!")
        return
        
    user_id, caption, attachment_data, timestamp, source = row
    
    image_url = None
    if attachment_data:
        try:
            c_id, m_id = attachment_data.split('|')
            channel = bot.get_channel(int(c_id))
            msg = await channel.fetch_message(int(m_id))
            if msg.attachments:
                image_url = msg.attachments[0].url
        except:
            image_url = None

    embed = discord.Embed(
        title="🕰️ Flashback",
        description=f"**{caption}**\n📅 {timestamp}\n👤 Captured by <@{user_id}>",
        color=discord.Color.blue()
    )
    if image_url:
        embed.set_image(url=image_url)
    else:
        embed.set_footer(text="⚠️ Image lost (Message deleted?)")
        
    await ctx.send(embed=embed)

@bot.command()
async def moments(ctx):
    """Browse all captured moments from snaps and logs."""
    # Check if in wiki channel
    wiki_channel_id = config.CHANNELS.get("wiki_of_us")
    if ctx.channel.id != wiki_channel_id:
        await ctx.send(f"❌ This command only works in <#{wiki_channel_id}>")
        return
    
    all_moments = await database.get_all_moments()
    
    if not all_moments:
        await ctx.send("📭 No captured moments yet! Use `!snap` or `!log` to start capturing memories.")
        return
    
    # Create a paginated view (show 3 moments per page with full details)
    moments_per_page = 3
    total_pages = (len(all_moments) + moments_per_page - 1) // moments_per_page
    
    class MomentsView(discord.ui.View):
        def __init__(self, moments_list, page=0):
            super().__init__()
            self.moments_list = moments_list
            self.current_page = page
            self.total_pages = (len(moments_list) + moments_per_page - 1) // moments_per_page
            self.update_buttons()
        
        def update_buttons(self):
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = self.current_page >= self.total_pages - 1
        
        @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.blurple)
        async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                self.update_buttons()
                await self.show_page(interaction)
        
        @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.blurple)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < self.total_pages - 1:
                self.current_page += 1
                self.update_buttons()
                await self.show_page(interaction)
        
        async def show_page(self, interaction: discord.Interaction):
            start_idx = self.current_page * moments_per_page
            end_idx = min(start_idx + moments_per_page, len(self.moments_list))
            page_moments = self.moments_list[start_idx:end_idx]
            
            embed = discord.Embed(
                title="📸 All Captured Moments",
                description=f"Page {self.current_page + 1} of {self.total_pages} • Total: {len(self.moments_list)} moments",
                color=discord.Color.purple()
            )
            
            for i, moment in enumerate(page_moments, start=start_idx + 1):
                user_id, caption, attachment_data, timestamp, source = moment
                
                source_emoji = "⚡ SNAP CHALLENGE" if source == "SNAP" else "📝 MANUAL LOG"
                moment_info = f"**Type:** {source_emoji}\n📅 **{timestamp}**\n👤 <@{user_id}>"
                embed.add_field(
                    name=f"✨ {caption}",
                    value=moment_info,
                    inline=False
                )
            
            await interaction.response.edit_message(embed=embed, view=self)
    
    # Show first page
    view = MomentsView(all_moments)
    start_idx = 0
    end_idx = min(moments_per_page, len(all_moments))
    page_moments = all_moments[start_idx:end_idx]
    
    embed = discord.Embed(
        title="📸 All Captured Moments",
        description=f"Page 1 of {total_pages} • Total: {len(all_moments)} moments",
        color=discord.Color.purple()
    )
    
    for i, moment in enumerate(page_moments, start=1):
        user_id, caption, attachment_data, timestamp, source = moment
        
        source_emoji = "⚡ SNAP CHALLENGE" if source == "SNAP" else "📝 MANUAL LOG"
        moment_info = f"**Type:** {source_emoji}\n📅 **{timestamp}**\n👤 <@{user_id}>"
        embed.add_field(
            name=f"✨ {caption}",
            value=moment_info,
            inline=False
        )
    
    await ctx.send(embed=embed, view=view)


# =========================================
# 11. AUDIO CAPSULE (Voice Operating System)
# =========================================

# --- DELIVER LOGIC ---
async def deliver_capsule_job(capsule_id, sender_id, attachment_data, reason):
    """
    Fetches the hidden file from Debug Logs and RE-UPLOADS it.
    This ensures it appears as a playable audio file, not a link.
    """
    target_channel_id = config.CHANNELS.get("audio_capsule")
    target_channel = bot.get_channel(target_channel_id)
    if not target_channel: return

    # 1. Fetch the original file from storage (Debug Logs)
    audio_file = None
    try:
        # attachment_data is stored as "ChannelID|MessageID"
        c_id, m_id = attachment_data.split('|')
        source_channel = bot.get_channel(int(c_id))
        source_msg = await source_channel.fetch_message(int(m_id))
        
        if source_msg.attachments:
            # We convert it back to a file object to re-upload
            audio_file = await source_msg.attachments[0].to_file()
            
    except Exception as e:
        print(f"❌ Error retrieving capsule file: {e}")
        await target_channel.send(f"⚠️ **Error:** Capsule from <@{sender_id}> got lost in the mail (Source message deleted).")
        return

    # 2. Mark as 'ARCHIVED' so it shows in mixtape later
    await database.mark_capsule_delivered(capsule_id)

    # 3. Create the delivery note
    embed = discord.Embed(
        title="🔊 Incoming Audio Capsule!",
        description=f"**From:** <@{sender_id}>\n**Type:** {reason}",
        color=discord.Color.teal()
    )
    
    # 4. Send the embed AND the file together
    await target_channel.send(content=f"🔔 <@{sender_id}> sent this for you!", embed=embed, file=audio_file)


# --- MENUS AND BUTTONS ---
class LabelModal(discord.ui.Modal, title='Label This Capsule'):
    tag = discord.ui.TextInput(
        label='Open When...', 
        placeholder='sad, bored, lonely, angry, happy...',
        min_length=2, max_length=20
    )

    def __init__(self, sender_id, attachment_data):
        super().__init__()
        self.sender_id = sender_id
        self.attachment_data = attachment_data

    async def on_submit(self, interaction: discord.Interaction):
        # Save as "OPEN_WHEN" - No scheduler needed. It waits in DB.
        label = self.tag.value.lower().strip()
        await database.add_capsule(self.sender_id, self.attachment_data, label, None, "OPEN_WHEN")
        
        await interaction.response.send_message(
            f"🏷️ **Saved!** Your partner can listen by typing `!need {label}`.", 
            ephemeral=True
        )

class CapsuleTypeView(discord.ui.View):
    def __init__(self, sender_id, attachment_data):
        super().__init__(timeout=None)
        self.sender_id = sender_id
        self.attachment_data = attachment_data

    @discord.ui.button(label="🎲 Surprise (1-3 Days)", style=discord.ButtonStyle.primary)
    async def random_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Calculate Random Time
        minutes = random.randint(60, 4320) # 1h to 72h
        deliver_time = datetime.datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + datetime.timedelta(minutes=minutes)
        
        # 2. Save & Schedule
        c_id = await database.add_capsule(self.sender_id, self.attachment_data, "random", deliver_time.strftime("%Y-%m-%d %H:%M:%S"), "PENDING")
        
        bot.scheduler.add_job(
            deliver_capsule_job, 'date', run_date=deliver_time,
            args=[c_id, self.sender_id, self.attachment_data, "🎲 Surprise Delivery"]
        )
        await interaction.response.send_message(f"🤐 **Buried!** Will surface in {minutes//60} hours.", ephemeral=True)

    @discord.ui.button(label="☀️ First Light (Morning)", style=discord.ButtonStyle.success)
    async def morning_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Find Partner's Timezone
        partner_tz = None
        for p in config.PLAYERS:
            if p["id"] != self.sender_id: # Find the OTHER person
                partner_tz = ZoneInfo(p["tz"])
                break
        
        if not partner_tz: partner_tz = ZoneInfo("Asia/Kuala_Lumpur") # Fallback

        # 2. Calculate next 7 AM
        now_partner = datetime.datetime.now(partner_tz)
        next_morning = now_partner.replace(hour=7, minute=0, second=0)
        if next_morning < now_partner:
            next_morning += datetime.timedelta(days=1) # Move to tomorrow if 7 AM passed
        
        # 3. Save & Schedule
        c_id = await database.add_capsule(self.sender_id, self.attachment_data, "morning", next_morning.strftime("%Y-%m-%d %H:%M:%S"), "PENDING")
        
        bot.scheduler.add_job(
            deliver_capsule_job, 'date', run_date=next_morning,
            args=[c_id, self.sender_id, self.attachment_data, "☀️ Good Morning"]
        )
        await interaction.response.send_message(f"🌅 **Scheduled!** Delivery at 7:00 AM their time.", ephemeral=True)

    @discord.ui.button(label="🏷️ 'Open When...' Label", style=discord.ButtonStyle.secondary)
    async def label_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LabelModal(self.sender_id, self.attachment_data))

# --- COMMANDS ---

@bot.command()
async def need(ctx, *, emotion: str):
    """Retrieves an 'Open When' capsule: !need sad"""
    row = await database.get_open_when_capsule(emotion.lower())
    
    if not row:
        await ctx.send(f"💔 No capsules found for **'{emotion}'**. Maybe ask your partner to record one?")
        return

    c_id, sender_id, attachment_data = row
    
    # Deliver it
    await deliver_capsule_job(c_id, sender_id, attachment_data, f"🏷️ Open When You're {emotion.title()}")

@bot.command()
async def mixtape(ctx):
    """Shows history of delivered capsules."""
    rows = await database.get_mixtape_list()
    if not rows:
        await ctx.send("📭 Mixtape is empty!")
        return

    desc = ""
    for sender, label, date in rows:
        desc += f"• **{label.upper()}** from <@{sender}> ({date[:10]})\n"
        
    embed = discord.Embed(title="📼 The Mixtape", description=desc, color=discord.Color.purple())
    await ctx.send(embed=embed)

# --- LISTENER ---
@bot.event
async def on_message(message):
    await bot.process_commands(message) # Important!

    # Only watch #audio-capsule
    if message.channel.id != config.CHANNELS.get("audio_capsule"):
        return
    
    if message.author.bot: return

    # Detect Audio
    if message.attachments:
        att = message.attachments[0]
        if att.content_type and "audio" in att.content_type:
            
            # 1. SECURE THE FILE (Backup to Debug Channel)
            debug_channel = bot.get_channel(config.CHANNELS.get("debug_logs"))
            if debug_channel:
                backup = await debug_channel.send(f"💾 Audio Backup ({message.author.name})", file=await att.to_file())
                
                # STORE ID "ChannelID|MessageID"
                attachment_data = f"{debug_channel.id}|{backup.id}"
                
                # 2. DELETE ORIGINAL (Hide it)
                await message.delete()
                
                # 3. ASK USER WHAT TO DO
                try:
                    await message.author.send(
                        "🎙️ **Capsule Secured!** How should I deliver this?", 
                        view=CapsuleTypeView(message.author.id, attachment_data)
                    )
                except:
                    # Fallback if DMs closed
                    await message.channel.send(
                        f"{message.author.mention}, enable DMs to set the delivery time!",
                        delete_after=10
                    )



# =========================================
# 12. LIVE DASHBOARD (The Stats Board)
# =========================================

@tasks.loop(minutes=1) 
async def update_dashboard():
    """Updates the pinned stats board every 1 min."""
    channel_id = config.CHANNELS.get("live_stats")
    
    # 1. Fetch channel safely
    channel = bot.get_channel(channel_id)
    if not channel: return

    # 2. Wrap the entire update logic in try/except to prevent 500 crashes
    try:
        # --- A. CLOCKS ---
        tz_husb = ZoneInfo("Asia/Kuala_Lumpur") 
        tz_wife = ZoneInfo("Africa/Lusaka") 
        
        time_husb = datetime.datetime.now(tz_husb).strftime("%I:%M %p")
        time_wife = datetime.datetime.now(tz_wife).strftime("%I:%M %p")
        
        # --- B. COUNTERS ---
        now = datetime.datetime.now()
        try:
            start_date = datetime.datetime.strptime(config.DATES["relationship_start"], "%Y-%m-%d")
            days_together = (now - start_date).days
        except:
            days_together = "0"

        try:
            last_seen_date = datetime.datetime.strptime(config.DATES["last_seen"], "%Y-%m-%d")
            days_apart = (now - last_seen_date).days
        except:
            days_apart = "0"

        # --- C. DATABASE STATS ---
        today_str = datetime.datetime.now(tz_husb).strftime("%Y-%m-%d")
        stats = await database.get_dashboard_stats(today_str)

        # Format Question Status
        q_count = stats['daily_q_count']
        if q_count == 2:
            q_status = "✅ Completed by both"
        elif q_count == 1:
            q_status = "⏳ Waiting for partner"
        else:
            q_status = "❌ Not started yet"

        # --- D. BUILD EMBED ---
        embed = discord.Embed(title="📊 Relationship Control Center", color=discord.Color.dark_teal())
        
        # Row 1: Clocks
        embed.add_field(name="🇲🇾 Husband", value=f"**{time_husb}**", inline=True)
        embed.add_field(name="🇿🇲 Wife", value=f"**{time_wife}**", inline=True)
        
        # Row 2: The Counters
        embed.add_field(
            name="⏳ Timeline", 
            value=f"❤️ **{days_together}** Days Together\n💔 **{days_apart}** Days Apart", 
            inline=False
        )
        
        # Row 3: Action Items
        action_text = (
            f"🔥 **{stats['active_dares']}** Active Dares\n"
            f"📜 **{stats['open_bounties']}** Open Bounties\n"
            f"❓ Daily Question: **{q_status}**"
        )
        embed.add_field(name="⚡ Pending Actions", value=action_text, inline=False)

        # Row 4: Buried Treasure
        embed.add_field(
            name="🏴‍☠️ Buried Treasure", 
            value=f"🎙️ **{stats['buried_capsules']}** Audio Capsules Hidden", 
            inline=False
        )
        
        embed.set_footer(text=f"Auto-updates every 1 min • Last: {datetime.datetime.now(tz_husb).strftime('%H:%M')}")

        # --- E. EDIT OR SEND (Safely) ---
        # We only try to read the last 5 messages to find the bot's own post
        try:
            history = [msg async for msg in channel.history(limit=5)]
            last_bot_msg = None
            for msg in history:
                if msg.author == bot.user:
                    last_bot_msg = msg
                    break
                    
            if last_bot_msg:
                await last_bot_msg.edit(content=None, embed=embed)
            else:
                await channel.send(embed=embed)
        except Exception as e:
            # If Discord 500s here, just skip this update
            print(f"⚠️ Dashboard Discord Error: {e}")
            pass

    except Exception as e:
        print(f"⚠️ Dashboard Logic Error: {e}")


# =========================================
# 13. WATCH PARTY (Sync Timer)
# =========================================

class WatchPartyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.ready_users = set()

    @discord.ui.button(label="🍿 I'm Ready!", style=discord.ButtonStyle.success)
    async def ready_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.ready_users.add(interaction.user.id)
        
        # Update the embed to show who is ready
        embed = interaction.message.embeds[0]
        desc = f"**Waiting for:**\n"
        
        # Check who is missing (Logic assumes 2 players from config)
        missing = []
        for p in config.PLAYERS:
            if p["id"] not in self.ready_users:
                missing.append(f"<@{p['id']}>")
        
        if missing:
            embed.description = f"**Waiting for:** {', '.join(missing)} to grab popcorn..."
            embed.color = discord.Color.orange()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # BOTH READY! START COUNTDOWN
            embed.description = "✅ **EVERYONE READY!** Starting countdown..."
            embed.color = discord.Color.green()
            await interaction.response.edit_message(embed=embed, view=None)
            
            # The Countdown Animation
            msg = interaction.message
            for i in range(5, 0, -1):
                await msg.channel.send(f"# {i}...")
                await asyncio.sleep(1)
            
            await msg.channel.send("# ▶️ PLAY NOW!")
            await msg.channel.send("Enjoy the movie! 🎬")

@bot.command()
async def watch(ctx, *, title="Mystery Movie"):
    """Starts a sync countdown lobby."""
    target_id = config.CHANNELS.get("watch_party")
    if ctx.channel.id != target_id: return

    embed = discord.Embed(
        title=f"🎬 Movie Night: {title}",
        description="Get your snacks and pause the movie at **0:00**.\nClick the button when you are paused and ready.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=WatchPartyView())


# =========================================
# 14. SYSTEM BACKUPS (Safety Net)
# =========================================

async def backup_database_job():
    """Triggers a remote Postgres dump from Heroku and uploads it to Discord."""
    channel_id = config.CHANNELS.get("database_backup")
    channel = bot.get_channel(channel_id)
    
    if not channel: 
        print("⚠️ Backup Failed: Channel not found.")
        return

    timestamp = datetime.datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y-%m-%d_%H-%M")
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("⚠️ Backup Failed: DATABASE_URL not found.")
        return

    print("⏳ Starting remote Postgres backup...")
    try:
        filename = f"/tmp/backup_{timestamp}.dump"
        
        subprocess.run(f"pg_dump {db_url} -F c -f {filename}", shell=True, check=True)
        
        if os.path.exists(filename):
            file = discord.File(filename, filename=f"heroku_backup_{timestamp}.dump")
            
            embed = discord.Embed(title="☁️ Cloud Database Backup", color=discord.Color.light_grey())
            embed.add_field(name="Time", value=timestamp)
            embed.set_footer(text="Restore using: pg_restore -d <db_url> <file>")
            
            await channel.send(embed=embed, file=file)
            print("✅ Postgres backup uploaded successfully.")
        else:
            print("❌ Backup Failed: Dump file was not created.")

    except Exception as e:
        print(f"❌ Backup Error: {e}")

@bot.command()
async def backup(ctx):
    """Manually trigger a backup right now."""
    await ctx.send("⏳ **Running manual cloud backup...**")
    await backup_database_job()
    await ctx.send("✅ Done! Check the backup channel.")

# =========================================
# 15. START MENU (The Manual)
# =========================================

async def setup_start_menu():
    """Wipes #start-here and posts the fresh manual."""
    channel_id = config.CHANNELS.get("start_here")
    channel = bot.get_channel(channel_id)
    
    if not channel: return

    try:
        await channel.purge(limit=10)
    except:
        pass

    embed = discord.Embed(
        title="🏠 Welcome to Our Digital Home",
        description=(
            "This isn't just a server; it's our **Relationship Operating System**.\n"
            "Since we are miles apart, this space helps us stay in sync, manage tasks, and keep memories alive.\n\n"
            "👇 **SYSTEM MANUAL** 👇"
        ),
        color=discord.Color.from_rgb(47, 49, 54) # Dark Grey/Clean
    )

    # --- Connection Modules ---
    embed.add_field(
        name="❤️ Connection Modules",
        value=(
            "**#daily-question**\n"
            "• **What:** Every morning at 9 AM, the AI asks a Deep, Spicy, or Silly question.\n"
            "• **How:** Click '✍️ Answer Secretly'. Answers are hidden until we both reply!\n"
            "• **Status:** Check `#live-stats` to see pending answers.\n\n"
            
            "**#moments (Our 'BeReal')**\n"
            "• **What:** Random pings 3x/day. 15 mins to reply with a photo.\n"
            "• `!snap <caption>` → Reply to a challenge (attach photo). [⚡ SNAP CHALLENGE]\n"
            "• `!log <caption>` → Log a memory manually anytime. [📝 MANUAL LOG]\n"
            "• `!flashback` → See a random photo from the past.\n\n"
            
            "**#audio-capsule (Time Travel Voice Notes)**\n"
            "• **What:** Send voice notes for the future.\n"
            "• **How:** Upload a mic recording. The bot hides it immediately.\n"
            "• **Options:** Morning (7 AM), Random (1-3 days), or 'Open When...'\n"
            "• `!need <emotion>` → Retrieve a hidden capsule (e.g., `!need sad`).\n"
            "• `!mixtape` → See delivery history."
        ),
        inline=False
    )

    # --- Arcade & Economy ---
    embed.add_field(
        name="🕹️ Arcade & Economy",
        value=(
            "**#truth-or-dare**\n"
            "• **What:** Risk it for the biscuit. Earn Us-Bucks.\n"
            "• `!dare` → Generate a new AI dare.\n"
            "• **Process:** Accept -> Do it -> Mark Done -> Partner Approves -> Get Paid.\n\n"
            
            "**#watch-party**\n"
            "• **What:** Sync movie start times perfectly.\n"
            "• `!watch <Movie Name>` → Creates a lobby. Countdown starts when both are Ready.\n\n"
            
            "**#shop**\n"
            "• **What:** Spend your hard-earned 'Us-Bucks'.\n"
            "• `!shop` → Resets the menu.\n"
            "• **Buying:** Click 'Buy Item' and enter the ID."
        ),
        inline=False
    )

    # --- Utility & Tools ---
    embed.add_field(
        name="🛠️ Utility & Tools",
        value=(
            "**#bounty-board**\n"
            "• **What:** Outsource tasks. Money held in escrow.\n"
            "• `!bounty <amount> <task>` → e.g., `!bounty 500 Call the internet company`\n\n"
            
            "**#decision-room (AI Mediator)**\n"
            "• `!food <craving>` → Suggests 3 recipes/meals.\n"
            "• `!movie <genre>` → Suggests 3 movies.\n"
            "• `!date <vibe>` → Suggests 3 date ideas.\n"
            "• `!decide <Q> <Opt1> <Opt2>` → Runs a poll.\n\n"
            
            "**#wiki-of-us (Shared Memory Bank)**\n"
            "• **What:** Store & search all memories in one place.\n"
            "• `!remember \"<key>\" \"<value>\"` → Save text or photo.\n"
            "• `!get <key>` → Retrieve a specific memory.\n"
            "• `!wiki` → List all memories + recent moments preview.\n"
            "• `!moments` → Browse all captured SNAP & LOG moments with pagination.\n\n"
            
            "**#reminder-room**\n"
            "• **What:** Alarms that nag us (1h, 30m, 15m warnings).\n"
            "• `!remind <time>` → Private (Blue).\n"
            "• `!ping <time>` → Public @everyone (Red).\n"
            "• **Ex:** `!ping tomorrow at 8pm`"
        ),
        inline=False
    )

    embed.set_footer(text="System Online • Relationship OS v1.0")
    
    await channel.send(embed=embed)


# =========================================
# 16. STARTUP & SCHEDULER
# =========================================

async def trigger_random_dare():
    """Helper function called by the scheduler at 6 PM"""
    channel_id = config.CHANNELS.get("truth_or_dare")
    channel = bot.get_channel(channel_id)
    
    if not channel:
        print("⚠️ Scheduler Error: 'truth_or_dare' channel ID not found.")
        return

    # Critical fix: Try to get dare, fallback if AI crashes/times out
    try:
        task, price = await ai_manager.get_ai_dare()
    except Exception as e:
        print(f"⚠️ Scheduler AI Error: {e}")
        task, price = "Send a voice note singing a song of your choice.", 50

    dare_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    await database.create_dare(dare_id, 0, task, price) 
    
    embed = discord.Embed(
        title="🎲 Random Daily Dare!",
        description=f"## **{task}**\n\nWho is brave enough?",
        color=discord.Color.random()
    )
    embed.add_field(name="Reward", value=f"💰 {price} Us-Bucks")
    embed.set_footer(text=f"DARE: {dare_id} | 0 | 0 | {price}")
    
    await channel.send(embed=embed, view=DarePendingView(dare_id, 0, price))

async def schedule_todays_snaps():
    """
    Runs every day at 9 AM (Malaysia Time) AND on Startup.
    Calculates the 3 snap times for each user based on THEIR local timezone.
    """
    if not config.PLAYERS:
        print("⚠️ No PLAYERS found in config.py.")
        return

    print("📅 Scheduling Daily Snaps (Multi-Timezone)...")
    
    for player in config.PLAYERS:
        p_id = player["id"]
        p_tz_str = player["tz"]
        
        try:
            p_tz = ZoneInfo(p_tz_str)
            now_local = datetime.datetime.now(p_tz)
            
            # Define 10 AM to 10 PM window in user's local time
            start_window = now_local.replace(hour=10, minute=0, second=0, microsecond=0)
            end_window = now_local.replace(hour=22, minute=0, second=0, microsecond=0)
            
            if now_local > end_window:
                continue # Day is over for them

            # Calculate total seconds in the window
            total_seconds = int((end_window - start_window).total_seconds())
            
            # Pick 3 unique random offsets
            random_offsets = sorted(random.sample(range(0, total_seconds), 3))
            
            for offset in random_offsets:
                run_time = start_window + datetime.timedelta(seconds=offset)
                
                # Only schedule if time is in the future
                if run_time > now_local:
                    bot.scheduler.add_job(
                        trigger_snap_for_user, 
                        'date', 
                        run_date=run_time,
                        args=[p_id]
                    )
                    print(f"   -> Scheduled for {p_id} at {run_time.strftime('%H:%M')} ({p_tz_str})")
                    
        except Exception as e:
            print(f"❌ Error scheduling for {p_id}: {e}")

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    
    # --- CRITICAL FIX: PREVENT DUPLICATE TASKS ON RECONNECT ---
    # If the bot reconnects (common on Heroku), this prevents re-scheduling everything 50 times.
    if hasattr(bot, 'tasks_initialized') and bot.tasks_initialized:
        print("🔄 Reconnected (Skipping task setup)")
        return

    # --- INITIALIZATION START ---
    await database.init_db()
    bot.add_view(ShopView())
    bot.add_view(QuestionView(None))  # Persistent view for daily questions
    bot.add_view(DarePendingView(None, None, None))  # Persistent view for dare challenges
    bot.add_view(DareActiveView(None, None, None, None))  # Persistent view for active dares
    bot.add_view(DareVerifyView(None, None, None, None))  # Persistent view for dare verification
    bot.scheduler = AsyncIOScheduler()
    
    # 1. Daily Question (9 AM MYT)
    bot.scheduler.add_job(
        send_daily_question, 
        'cron', 
        hour=9, 
        minute=0, 
        timezone=ZoneInfo("Asia/Kuala_Lumpur")
    )
    
    # 2. Daily Random Dare (6 PM MYT)
    bot.scheduler.add_job(
        trigger_random_dare, 
        'cron', 
        hour=18, 
        minute=0, 
        timezone=ZoneInfo("Asia/Kuala_Lumpur")
    )

    # 3. Multi-Snap Planner (BeReal) - Run once now, and schedule for future midnights
    await schedule_todays_snaps()
    bot.scheduler.add_job(
        schedule_todays_snaps, 
        'cron', 
        hour=0, 
        minute=0, 
        timezone=datetime.timezone.utc
    )

    # 4. Restore Pending Audio Capsules
    pending_caps = await database.get_pending_capsules()
    print(f"💾 Restoring {len(pending_caps)} pending Audio Capsules...")
    
    for cap in pending_caps:
        c_id, sender_id, attachment_data, deliver_at_str = cap
        try:
            deliver_time = datetime.datetime.strptime(deliver_at_str, "%Y-%m-%d %H:%M:%S")
            deliver_time = deliver_time.replace(tzinfo=ZoneInfo("Asia/Kuala_Lumpur"))
            
            now = datetime.datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
            
            # If missed, send in 10 seconds. If future, schedule normally.
            run_date = max(now + datetime.timedelta(seconds=10), deliver_time)
            
            print(f"   -> Capsule {c_id} restored for {run_date}")
            bot.scheduler.add_job(
                deliver_capsule_job, 
                'date', 
                run_date=run_date,
                args=[c_id, sender_id, attachment_data, "Restored Delivery"]
            )
        except Exception as e:
            print(f"❌ Failed to restore capsule {c_id}: {e}")

    # 5. Start Dashboard Loop
    if not update_dashboard.is_running():
        update_dashboard.start()
        print("📊 Dashboard Loop Started")

    # 6. Auto-Backup (Every 12 Hours)
    bot.scheduler.add_job(
        backup_database_job, 
        'interval', 
        hours=12,
        timezone=ZoneInfo("Asia/Kuala_Lumpur")
    )

    # 7. Setup Start Menu
    await setup_start_menu()
    
    bot.scheduler.start()
    
    # Mark tasks as initialized so we don't do this again until a hard restart
    bot.tasks_initialized = True
    
    debug_channel = bot.get_channel(config.CHANNELS.get("debug_logs"))
    if debug_channel:
        await debug_channel.send(f"🤖 **EchoBot REBOOTED** | Anti-Spam Active | Heartbeat Secured")

@bot.command()
async def test_q(ctx):
    await send_daily_question()
    await ctx.send("✅ Manual Question trigger sent.")

@bot.command()
async def test_dare(ctx):
    await trigger_random_dare()
    await ctx.send("✅ Manual Random Dare trigger sent.")

@bot.command()
async def test_snap(ctx):
    """Forces a snap for the command sender immediately."""
    await trigger_snap_for_user(ctx.author.id)

@bot.command()
async def update(ctx):
    """Forces the dashboard to update immediately."""
    await update_dashboard()
    await ctx.send("✅ Dashboard updated!", delete_after=3)

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
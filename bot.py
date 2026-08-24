"""
Discord Bot - Thông báo khi có người vào kênh thoại
=====================================================
Chức năng:
1. Khi có người tham gia vào một kênh thoại đang được theo dõi,
   bot sẽ nhắn tin riêng (DM) cho MỘT người dùng được chỉ định với nội dung:
   "có người cần hỗ trợ ở phòng trò chuyện"
2. Bảng điều khiển (Control Panel) ngay trong Discord để:
   - Thêm / Xóa ID kênh thoại cần theo dõi
   - Đặt người nhận thông báo (bằng ID hoặc mention)
   - Xem danh sách cấu hình hiện tại

Chạy: python bot.py
Yêu cầu: file .env chứa DISCORD_TOKEN=xxxx (xem .env.example)
"""

import json
import logging
import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# ----------------------------------------------------------------------------
# Cấu hình cơ bản
# ----------------------------------------------------------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

CONFIG_PATH = Path(__file__).parent / "config.json"
NOTIFY_MESSAGE = "có người cần hỗ trợ ở phòng trò chuyện"

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("voice-notify-bot")

intents = discord.Intents.default()
intents.voice_states = True   # bắt buộc để nhận sự kiện vào/ra kênh thoại
intents.members = True        # để lấy thông tin thành viên / DM chính xác
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ----------------------------------------------------------------------------
# Lưu trữ cấu hình (đơn giản bằng file JSON, theo từng server/guild)
# Cấu trúc:
# {
#   "<guild_id>": {
#       "notify_user_id": 123456789012345678,
#       "voice_channels": [111111111111111111, 222222222222222222]
#   }
# }
# ----------------------------------------------------------------------------
def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_guild_config(guild_id: int) -> dict:
    data = load_config()
    return data.get(str(guild_id), {"notify_user_id": None, "voice_channels": []})


def update_guild_config(guild_id: int, guild_cfg: dict) -> None:
    data = load_config()
    data[str(guild_id)] = guild_cfg
    save_config(data)


# ----------------------------------------------------------------------------
# Sự kiện: có người thay đổi trạng thái thoại (vào/ra/chuyển kênh)
# ----------------------------------------------------------------------------
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot:
        return  # bỏ qua chính các bot khác

    # Chỉ xử lý khi người dùng THỰC SỰ vào một kênh mới (không phải rời hoặc mute/unmute)
    joined_new_channel = after.channel is not None and before.channel != after.channel
    if not joined_new_channel:
        return

    guild_cfg = get_guild_config(member.guild.id)
    tracked_channels = guild_cfg.get("voice_channels", [])
    notify_user_id = guild_cfg.get("notify_user_id")

    if after.channel.id not in tracked_channels:
        return  # kênh này không nằm trong danh sách theo dõi

    if not notify_user_id:
        log.warning(f"Chưa đặt người nhận thông báo cho server {member.guild.name}")
        return

    notify_user = member.guild.get_member(notify_user_id) or await bot.fetch_user(notify_user_id)
    if notify_user is None:
        log.warning(f"Không tìm thấy người dùng có ID {notify_user_id}")
        return

    try:
        embed = discord.Embed(
            description=f"📢 {NOTIFY_MESSAGE}",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Người vào phòng", value=member.mention, inline=True)
        embed.add_field(name="Kênh thoại", value=after.channel.mention, inline=True)
        embed.set_footer(text=member.guild.name)
        await notify_user.send(embed=embed)
        log.info(f"Đã gửi thông báo cho {notify_user} vì {member} vào kênh {after.channel.name}")
    except discord.Forbidden:
        log.warning(f"Không thể DM cho {notify_user} (người dùng chặn DM hoặc không chung server).")


# ----------------------------------------------------------------------------
# Bảng điều khiển (Control Panel) - dùng nút bấm + form (Modal)
# ----------------------------------------------------------------------------
class AddChannelModal(discord.ui.Modal, title="Thêm kênh thoại cần theo dõi"):
    channel_id = discord.ui.TextInput(
        label="ID kênh thoại",
        placeholder="Ví dụ: 123456789012345678",
        required=True,
    )

    def __init__(self, guild: discord.Guild):
        super().__init__()
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cid = int(self.channel_id.value.strip())
        except ValueError:
            await interaction.response.send_message("⚠️ ID kênh không hợp lệ (phải là số).", ephemeral=True)
            return

        channel = self.guild.get_channel(cid)
        if channel is None or not isinstance(channel, discord.VoiceChannel):
            await interaction.response.send_message(
                "⚠️ Không tìm thấy kênh thoại nào với ID đó trong server này.", ephemeral=True
            )
            return

        cfg = get_guild_config(self.guild.id)
        if cid in cfg["voice_channels"]:
            await interaction.response.send_message(f"ℹ️ Kênh **{channel.name}** đã có trong danh sách rồi.", ephemeral=True)
            return

        cfg["voice_channels"].append(cid)
        update_guild_config(self.guild.id, cfg)
        await interaction.response.send_message(f"✅ Đã thêm kênh **{channel.name}** vào danh sách theo dõi.", ephemeral=True)


class RemoveChannelModal(discord.ui.Modal, title="Xóa kênh thoại khỏi danh sách"):
    channel_id = discord.ui.TextInput(
        label="ID kênh thoại cần xóa",
        placeholder="Ví dụ: 123456789012345678",
        required=True,
    )

    def __init__(self, guild: discord.Guild):
        super().__init__()
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cid = int(self.channel_id.value.strip())
        except ValueError:
            await interaction.response.send_message("⚠️ ID kênh không hợp lệ (phải là số).", ephemeral=True)
            return

        cfg = get_guild_config(self.guild.id)
        if cid not in cfg["voice_channels"]:
            await interaction.response.send_message("⚠️ Kênh này không có trong danh sách.", ephemeral=True)
            return

        cfg["voice_channels"].remove(cid)
        update_guild_config(self.guild.id, cfg)
        await interaction.response.send_message("✅ Đã xóa kênh khỏi danh sách theo dõi.", ephemeral=True)


class SetNotifyUserModal(discord.ui.Modal, title="Đặt người nhận thông báo"):
    user_id = discord.ui.TextInput(
        label="ID người dùng được chỉ định",
        placeholder="Ví dụ: 123456789012345678",
        required=True,
    )

    def __init__(self, guild: discord.Guild):
        super().__init__()
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value.strip())
        except ValueError:
            await interaction.response.send_message("⚠️ ID người dùng không hợp lệ (phải là số).", ephemeral=True)
            return

        member = self.guild.get_member(uid)
        if member is None:
            await interaction.response.send_message(
                "⚠️ Không tìm thấy thành viên nào với ID đó trong server này.", ephemeral=True
            )
            return

        cfg = get_guild_config(self.guild.id)
        cfg["notify_user_id"] = uid
        update_guild_config(self.guild.id, cfg)
        await interaction.response.send_message(f"✅ Đã đặt **{member.display_name}** là người nhận thông báo.", ephemeral=True)


class ControlPanelView(discord.ui.View):
    """Bảng điều khiển: các nút bấm để quản lý cấu hình."""

    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        self.guild = guild

    @discord.ui.button(label="➕ Thêm kênh", style=discord.ButtonStyle.success)
    async def add_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddChannelModal(self.guild))

    @discord.ui.button(label="➖ Xóa kênh", style=discord.ButtonStyle.danger)
    async def remove_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveChannelModal(self.guild))

    @discord.ui.button(label="👤 Đặt người nhận", style=discord.ButtonStyle.primary)
    async def set_notify_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetNotifyUserModal(self.guild))

    @discord.ui.button(label="📋 Xem danh sách", style=discord.ButtonStyle.secondary)
    async def view_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_status_embed(self.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)


def build_status_embed(guild: discord.Guild) -> discord.Embed:
    cfg = get_guild_config(guild.id)
    notify_user_id = cfg.get("notify_user_id")
    channels = cfg.get("voice_channels", [])

    embed = discord.Embed(title="🎛️ Bảng điều khiển - Thông báo kênh thoại", color=discord.Color.blurple())

    if notify_user_id:
        member = guild.get_member(notify_user_id)
        embed.add_field(
            name="Người nhận thông báo",
            value=member.mention if member else f"`{notify_user_id}` (không tìm thấy trong server)",
            inline=False,
        )
    else:
        embed.add_field(name="Người nhận thông báo", value="⚠️ Chưa được đặt", inline=False)

    if channels:
        lines = []
        for cid in channels:
            ch = guild.get_channel(cid)
            lines.append(f"• {ch.mention if ch else f'`{cid}` (không tìm thấy)'}")
        embed.add_field(name=f"Kênh thoại đang theo dõi ({len(channels)})", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="Kênh thoại đang theo dõi", value="Chưa có kênh nào.", inline=False)

    embed.set_footer(text="Dùng các nút bên dưới để chỉnh sửa cấu hình.")
    return embed


# ----------------------------------------------------------------------------
# Slash command để mở bảng điều khiển
# ----------------------------------------------------------------------------
@bot.tree.command(name="panel", description="Mở bảng điều khiển thông báo kênh thoại")
@app_commands.checks.has_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    embed = build_status_embed(interaction.guild)
    view = ControlPanelView(interaction.guild)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@panel.error
async def panel_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "⚠️ Bạn cần quyền **Administrator** để mở bảng điều khiển.", ephemeral=True
        )
    else:
        log.exception("Lỗi trong lệnh /panel", exc_info=error)
        await interaction.response.send_message("⚠️ Đã xảy ra lỗi không xác định.", ephemeral=True)


# ----------------------------------------------------------------------------
# Sự kiện khởi động
# ----------------------------------------------------------------------------
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        log.info(f"Đã đồng bộ {len(synced)} slash command(s).")
    except Exception as e:
        log.exception("Lỗi khi đồng bộ slash commands", exc_info=e)
    log.info(f"Bot đã đăng nhập với tên {bot.user} (ID: {bot.user.id})")
    log.info("Dùng lệnh /panel trong server để mở bảng điều khiển.")


# ----------------------------------------------------------------------------
# Chạy bot
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit(
            "❌ Không tìm thấy DISCORD_TOKEN. Hãy tạo file .env (xem .env.example) và điền token của bot vào."
        )
    bot.run(TOKEN)

# Bot Discord - Thông báo kênh thoại

Bot theo dõi các kênh thoại được chỉ định. Khi có người vào một trong các kênh đó,
bot sẽ nhắn tin riêng (DM) cho **một người dùng duy nhất được chỉ định** với nội dung:

> có người cần hỗ trợ ở phòng trò chuyện

Bot có bảng điều khiển ngay trong Discord (lệnh `/panel`) để thêm/xóa kênh thoại
cần theo dõi và đặt người nhận thông báo — không cần sửa code.

## 1. Tạo bot trên Discord Developer Portal

1. Vào https://discord.com/developers/applications → **New Application**.
2. Vào tab **Bot** → **Add Bot** → copy **Token** (giữ bí mật).
3. Trong tab **Bot**, bật 2 quyền (Privileged Gateway Intents):
   - **SERVER MEMBERS INTENT**
   - Không cần Message Content Intent (bot không đọc tin nhắn kênh chữ)
4. Vào tab **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `View Channels`, `Send Messages` (để DM cần không có quyền đặc biệt, chỉ cần bot và user chung server)
5. Dùng URL tạo ra để mời bot vào server của bạn.

## 2. Cài đặt

```bash
pip install -r requirements.txt
```

Tạo file `.env` (copy từ `.env.example`) và điền token:

```
DISCORD_TOKEN=token_bot_của_bạn
```

## 3. Chạy bot

```bash
python bot.py
```

## 4. Sử dụng

1. Trong server Discord, gõ lệnh `/panel` (cần quyền Administrator).
2. Bảng điều khiển hiện ra với các nút:
   - **➕ Thêm kênh**: nhập ID kênh thoại cần theo dõi.
   - **➖ Xóa kênh**: nhập ID kênh thoại cần xóa khỏi danh sách.
   - **👤 Đặt người nhận**: nhập ID người dùng sẽ nhận thông báo DM.
   - **📋 Xem danh sách**: xem cấu hình hiện tại.
3. Cách lấy ID kênh/người dùng: Bật **Developer Mode** trong Discord
   (Cài đặt → Nâng cao → Chế độ nhà phát triển), sau đó chuột phải vào
   kênh/người dùng → **Copy ID**.

## Lưu ý quan trọng

- Người dùng được chỉ định phải **cùng server** với bot để bot DM được
  (trừ khi họ cũng chung 1 server khác với bot).
- Nếu người nhận **chặn DM từ thành viên server** hoặc chặn bot, bot sẽ
  không gửi được tin nhắn — điều này sẽ được ghi log ra console.
- Cấu hình được lưu trong file `config.json`, tự động tạo theo từng server (guild).
- Bot chỉ thông báo khi có người **mới vào** kênh (không thông báo khi
  họ rời đi hoặc chỉ tắt/mở mic).

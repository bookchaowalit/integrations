# Brave Bookmarks Integration

ระบบนี้ดูแล bookmark จากไฟล์โปรไฟล์ Brave ในเครื่องตามลำดับ:

```text
Brave Bookmarks JSON → data/lake landing + Bronze Parquet → SQLite search projection
                         ↘ deterministic folder/subfolder organization
AI/user discovery → private proposal inbox → review/approve → Brave (เมื่อปิด browser)
```

การนำเข้าเข้า lake/SQLite เป็น idempotent และเก็บประวัติ bookmark ที่หายจาก
snapshot ล่าสุดเป็น `is_active = 0` การเขียนกลับเข้า Brave เป็นอีก boundary หนึ่ง:
ต้องผ่าน proposal ที่อนุมัติแล้ว, ต้องปิด Brave, ตรวจ hash ก่อนเขียน และสร้าง backup
ก่อน atomic replacement เสมอ

คุณไม่ต้องรันคำสั่งเองในชีวิตประจำวัน: AI ใช้ MCP tool
`manage_brave_bookmark_proposals` เพื่อรับเว็บที่คุณสั่งเก็บ และ cron
`brave_bookmarks_maintenance` จะ sync/จัดหมวดหมู่ทุก 4 ชั่วโมง


แผนผังกลุ่มที่ใช้บน Bookmark Bar อยู่ที่
[`docs/references/BRAVE-BOOKMARKS.md`](../../docs/references/BRAVE-BOOKMARKS.md)

## ใช้งาน

```bash
# ตรวจจำนวนก่อนเขียนจริง
task bookmarks:sync -- --dry-run --json

# นำเข้าและอัปเดต projection
task bookmarks:sync -- --json

# ค้นหาจากข้อมูลที่เก็บไว้แล้ว โดยไม่อ่านไฟล์ Brave สด
task bookmarks:sync -- --search "openai"

# preview/จัดกลุ่ม Bookmark Bar (ต้องปิด Brave ก่อน --apply)
task bookmarks:organize -- --json
task bookmarks:organize -- --apply --json

# สร้างรายการเว็บที่ AI/user พบใหม่ (ยังไม่เขียนเข้า Brave)
task bookmarks:propose -- \
  --url "https://example.com" \
  --title "Example knowledge source" \
  --folder "04 - Learning/Business & Systems" \
  --source-kind ai_discovery

# ดูและอนุมัติ proposal
task bookmarks:review -- --json
task bookmarks:review -- --approve <proposal-id> --json

# apply proposal + จัดโฟลเดอร์ + sync projection (ต้องปิด Brave)
task bookmarks:apply -- --json

# preview maintenance หรือรัน auto เมื่อ Brave ปิด
task bookmarks:maintain -- --json
task bookmarks:auto -- --json
```

ค่าเริ่มต้นอ่านทุก profile ใต้:
`~/.config/BraveSoftware/Brave-Browser/*/Bookmarks`

ถ้าต้องการชี้ path อื่น ใช้ `--bookmarks-root` ได้ เช่นในการทดสอบหรือโปรไฟล์
แยก ระบบเก็บ URL และชื่อไว้ใน SQLite เพื่อค้นหา ส่วน JSON ต้นฉบับและ Bronze
Parquet อยู่ใน `data/lake/` ซึ่งเป็น directory ที่ไม่ commit เข้า Git

## ตรวจสถานะ

```bash
task bookmarks:sync -- --search "" --json
```

ข้อมูล run ถูกบันทึกใน `data_pipeline_runs` ด้วย `pipeline_name=brave_bookmarks`
และ projection อยู่ในตาราง `browser_bookmarks`.

## AI discovery contract

เมื่อ AI พบเว็บไซต์หรือเว็บแอปที่มีประโยชน์และผู้ใช้สั่งให้เก็บ ให้เรียก MCP tool
`manage_brave_bookmark_proposals` ด้วย `action=propose` (หรือใช้
`bookmarks:propose` เป็น CLI fallback) พร้อม
`title`, `url`, `folder` และ `source-kind` ที่สั้นและตรวจสอบได้ ห้ามส่ง raw chat,
credential, token หรือ query URL ที่มี secret เข้า proposal ระบบจะไม่ตามเว็บหรือ
เพิ่ม bookmark จากการกล่าวถึง URL เฉย ๆ; ต้องมีการ approve ก่อน write-back
เพื่อป้องกัน prompt injection, tracking URL และ bookmark ที่ไม่ตั้งใจ

บนเครื่องนี้ scheduled job `brave_bookmarks_maintenance` เปิดใช้งานแล้วที่ทุก 4 ชั่วโมง
และติดตั้ง targeted crontab แล้ว job จะ sync lake/SQLite ทุก รอบ และ apply เฉพาะ
organization/proposal ที่ผ่านเงื่อนไขขณะ Brave ปิด หาก Brave เปิดอยู่จะข้าม browser
write และรอรอบถัดไป การเปิดใช้งานเป็นค่า local runtime ไม่ฝังข้อมูลส่วนตัวลง Git

คำสั่งด้านล่างเป็นขั้นตอนดูแลระบบสำหรับการย้ายเครื่องหรือปิด/เปิด job เท่านั้น
ผู้ใช้ไม่ต้องรันเป็นงานประจำ:

```bash
task bookmarks:auto-enable -- --json
task cron:install-job -- brave_bookmarks_maintenance
```

ปิดได้ด้วย `task bookmarks:auto-disable -- --json` และลบ
entry ของ Solo Empire จาก crontab ได้ด้วย `task cron:install`
หลังตรวจรายการ active jobs อีกครั้ง

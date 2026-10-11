---
title: Landing Page Integration Guide
aliases: [CLI Integration, Portfolio Integration]
tags: [guide, integration, cli, landing-page, portfolio]
created: 2026-01-06
updated: 2026-06-08
description: วิธีเชื่อม Solo Empire CLI กับ Landing Page
parent: ARCHITECTURE
related: [README, CLI Tools, Database]
---

# Landing Page Integration Guide

> **Parent:** [[ARCHITECTURE]]
> **Related:** [[README]], [[CLI Tools]], [[Database]]

---

## 🎯 ภาพรวม

```
┌─────────────────┐         ┌─────────────────┐
│  Landing Page   │         │  Local Machine  │
│   (Vercel)      │         │                 │
│                 │         │  SQLite DB      │
│  Next.js App    │ ◄────── │  CLI Tools      │
│                 │  build  │  (data export)  │
└─────────────────┘         └─────────────────┘
```

---

## 🔧 Setup

### 1. Export Data via CLI

ใช้ CLI tools เพื่อ export ข้อมูลจาก database:

```bash
cd /path/to/operating-hub  # hub root

# Export profile data
npx tsx infra/cli.ts profile --format json > ../landing-page/data/profile.json

# Export skills
npx tsx infra/cli.ts skills --format json > ../landing-page/data/skills.json

# Export assets/projects
npx tsx infra/cli.ts assets --format json > ../landing-page/data/assets.json
```

### 2. Import Data ใน Landing Page

ไฟล์ JSON ที่ export ไว้จะถูก import ในหน้า landing page:

```bash
# ข้อมูลอยู่ที่
# /path/to/landing-page/data/*.json
```

### 3. Usage ใน Landing Page

#### ตัวอย่าง: แสดง Profile ในหน้า About

```tsx
// src/app/about/page.tsx
import profileData from '@/data/profile.json';

export default function AboutPage() {
  const { profile, socialLinks } = profileData;

  return (
    <div>
      <h1>{profile.name}</h1>
      <p>{profile.title}</p>
      <p>{profile.bio}</p>

      <div>
        {socialLinks.map((link: any) => (
          <a key={link.id} href={link.url}>
            {link.platform}
          </a>
        ))}
      </div>
    </div>
  );
}
```

#### ตัวอย่าง: แสดง Skills ในหน้า Portfolio

```tsx
// src/app/portfolio/page.tsx
import skillsData from '@/data/skills.json';

export default function PortfolioPage() {
  const { skills } = skillsData;

  return (
    <div>
      <h1>My Skills</h1>
      <div className="grid grid-cols-2 gap-4">
        {skills.map((skill: any) => (
          <div key={skill.id} className="p-4 border rounded">
            <h3>{skill.name}</h3>
            <div className="w-full bg-gray-200 rounded">
              <div
                className="bg-blue-500 rounded"
                style={{ width: `${skill.progress_percent}%` }}
              />
            </div>
            <span>{skill.progress_percent}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

#### ตัวอย่าง: แสดง Assets/Projects

```tsx
// src/app/projects/page.tsx
import assetsData from '@/data/assets.json';

export default function ProjectsPage() {
  const { assets } = assetsData;

  return (
    <div>
      <h1>My Projects</h1>
      <div className="grid grid-cols-3 gap-6">
        {assets.map((asset: any) => (
          <div key={asset.id} className="p-6 border rounded-lg">
            <h3>{asset.name}</h3>
            <p>{asset.description}</p>
            <span className="badge">{asset.type}</span>
            {asset.url && <a href={asset.url}>View →</a>}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 🔄 Data Flow

### Option 1: Build-Time Data Export (แนะนำ)

Export ข้อมูลจาก CLI ก่อน build landing page:

```bash
# Export ข้อมูลทั้งหมด
cd /path/to/operating-hub  # hub root
npx tsx infra/cli.ts export --all --format json --output ../landing-page/data/

# Build landing page ด้วยข้อมูลล่าสุด
cd /path/to/landing-page
npm run build
```

**ข้อดี:**
- ✅ SEO friendly
- ✅ เร็ว (static data at build time)
- ✅ ไม่ต้อง loading state

**ข้อเสีย:**
- ❌ ต้อง export + rebuild ทุกครั้งที่ data เปลี่ยน

### Option 2: Direct Database Query

อ่านข้อมูลจาก SQLite database โดยตรง:

```tsx
// src/lib/db.ts
import Database from 'better-sqlite3';

// Prefer an explicit path from the environment
const db = new Database(process.env.OPERATIONAL_DB_PATH);

export function getProfile() {
  return db.prepare('SELECT * FROM profile LIMIT 1').get();
}

export function getSkills() {
  return db.prepare('SELECT * FROM skills WHERE status = ?').all('proficient');
}
```

**ข้อดี:**
- ✅ Data always fresh
- ✅ ไม่ต้อง export แยก

**ข้อเสีย:**
- ❌ ต้อง access database ได้จาก build environment
- ❌ ไม่เหมาะสำหรับ Vercel deployment

---

## 🔒 Security

### Database Access

Database file ควรอยู่ใน local machine เท่านั้น ไม่ expose ออกภายนอก:

```bash
# ตรวจสอบว่า database ไม่ถูก commit
echo "*.db" >> .gitignore

# ตั้ง permissions (path relative to monorepo root)
chmod 600 "$OPERATIONAL_DB_PATH"
```

### Data Export Safety

เมื่อ export ข้อมูลเป็น JSON สำหรับ landing page:

```bash
# อย่า export ข้อมูล sensitive (email, tokens, etc.)
npx tsx infra/cli.ts export --public-only --format json --output ../landing-page/data/
```

---

## 📊 Monitoring

### Data Freshness Check

ตรวจสอบว่าข้อมูลใน landing page เป็นปัจจุบัน:

```bash
# ตรวจสอบ last modified ของ database
ls -la "$OPERATIONAL_DB_PATH"

# เปรียบเทียบกับ exported JSON
ls -la /path/to/landing-page/data/*.json
```

### Build Logging

เพิ่ม logging ใน build script:

```bash
#!/bin/bash
# Optional automation
set -e

echo "[$(date)] Exporting data from Solo Empire CLI..."
cd /path/to/operating-hub  # hub root
npx tsx infra/cli.ts export --all --format json --output ../landing-page/data/

echo "[$(date)] Data exported. Building landing page..."
cd /path/to/landing-page
npm run build

echo "[$(date)] Deploy complete."
```

---

## 🚀 Deployment

### Update Landing Page Data

```bash
# Export ข้อมูลล่าสุดจาก CLI
cd /path/to/operating-hub  # hub root
npx tsx infra/cli.ts export --all --format json --output ../landing-page/data/

# Commit และ push ข้อมูลใหม่
cd /path/to/landing-page
git add data/
git commit -m "Update data from Solo Empire CLI"
git push

# Vercel จะ auto-deploy เมื่อ push
```

### Automated Updates (Optional)

ตั้ง cron job เพื่ออัพเดทข้อมูลอัตโนมัติ:

```bash
# No updater script currently exists in Solo Empire. Run the export commands
# above manually, or create a dedicated script under infra/scripts/ before
# adding a cron entry.
```

---

## 📚 Examples

ดูตัวอย่างการใช้งานจริงได้ที่:
- [[CLI Tools]] - 35 CLI commands for data access
- [[Database]] - SQLite schema and queries
- [[ARCHITECTURE]] - System architecture

---

**Last updated:** 2026-06-08

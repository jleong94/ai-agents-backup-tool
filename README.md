# AI Agents Backup & Transfer Tool

Move your **Claude Code**, **Hermes Agent**, and **OpenClaw** data — sessions, memory, skills, and config — to a new computer without losing anything. Windows, macOS, and Linux.

**Languages:** [English](#english) · [Bahasa Melayu](#bahasa-melayu) · [简体中文](#简体中文)

```
ai-agents-backup-tool/
├── backup_transfer_tool.py   # the tool (Python, standard library only)
├── run.bat                   # Windows launcher
├── run.sh                    # Linux / macOS launcher
└── README.md
```

---

## English

### Why
Moving to a new PC risks losing the data these AI agents keep locally: chat sessions, long-term memory, custom skills, and configuration. This tool backs up exactly that data, skips the multi-gigabyte files that regenerate on their own, and restores it safely on the new machine.

### What it backs up
- **Claude Code** — `~/.claude` (sessions, memory, tasks, plugins, credentials) and `~/.claude.json` (MCP servers + per-project config)
- **Hermes Agent** — the `hermes` folder in local app data and `~/.hermes` (memories, sessions, skills, kanban, `state.db`, `config.yaml`, `.env`, `SOUL.md`, auth)
- **OpenClaw** — best-effort paths (automatically skipped if not installed)

### What it skips (large + auto-regenerated)
- Hermes runtime/source (`hermes-agent`, ~2 GB) and `bin`
- Installers (`*-setup.exe`), model/provider caches (`*_cache.json`), caches, logs, and stale `*.lock` / `*.pid` files
- Claude Desktop's Electron cache (a different app; can be ~11 GB)

A full backup is typically well under 100 MB.

### What it does NOT do
- It does **not** back up your project source code — keep that in Git.
- Credentials/tokens are copied for convenience, but some are machine-bound; you might still need to sign in again on the new PC.

### Requirements
- Python 3.8 or newer. The launchers install it automatically if it is missing.

### Quick start
- **Windows:** double-click **`run.bat`**
- **macOS / Linux:** run `./run.sh` from a terminal
- **Or run directly:** `python backup_transfer_tool.py`

### Commands
```
python backup_transfer_tool.py            # interactive menu
python backup_transfer_tool.py backup  [DEST_DIR]
python backup_transfer_tool.py list    [SRC_DIR]
python backup_transfer_tool.py restore [SRC_DIR] [--dry-run] [--yes]
```
Default backup location: `~/Desktop/AI_Agents_Backup`.

### Moving to a new PC
1. **Old PC** — run a backup (quit Claude Code & Hermes first — see below). A `backup_<timestamp>` folder is created.
2. Copy that folder to the **new PC** (USB, cloud, or network share).
3. **New PC** — run restore and point it at the copied folder. Restore re-anchors paths to the new machine automatically, even if the username is different.

### Before you back up
Quit Claude Code and Hermes first, so their live databases (`state.db`, `kanban.db`) are copied in a consistent state.

### Safety
- **Backup only copies.** Your original files are never moved or deleted.
- **Restore asks first.** You must type `YES` to proceed; `--dry-run` previews the plan without changing anything.
- **Restore never deletes.** Any existing folder is renamed to `*.pre-restore-<timestamp>` before the backup is copied in, so the previous version is always recoverable.

### Where the data lives
| App | Windows | macOS | Linux |
|-----|---------|-------|-------|
| Claude Code | `~/.claude`, `~/.claude.json` | same | same |
| Hermes Agent | `%LOCALAPPDATA%\hermes`, `~/.hermes` | `~/Library/Application Support/hermes`, `~/.hermes` | `~/.config/hermes`, `~/.hermes` |

---

## Bahasa Melayu

### Kenapa
Bertukar ke PC baharu berisiko kehilangan data yang disimpan secara setempat oleh ejen AI ini: sesi perbualan, memori jangka panjang, kemahiran tersuai, dan konfigurasi. Alat ini menyandarkan data tersebut, melangkau fail bersaiz gigabait yang boleh dijana semula dengan sendiri, dan memulihkannya dengan selamat pada mesin baharu.

### Apa yang disandarkan
- **Claude Code** — `~/.claude` (sesi, memori, tugasan, plugin, maklumat kelayakan) dan `~/.claude.json` (pelayan MCP + konfigurasi setiap projek)
- **Hermes Agent** — folder `hermes` dalam data aplikasi setempat dan `~/.hermes` (memori, sesi, kemahiran, kanban, `state.db`, `config.yaml`, `.env`, `SOUL.md`, auth)
- **OpenClaw** — laluan anggaran (dilangkau secara automatik jika tidak dipasang)

### Apa yang dilangkau (besar + dijana semula automatik)
- Runtime/sumber Hermes (`hermes-agent`, ~2 GB) dan `bin`
- Pemasang (`*-setup.exe`), cache model/pembekal (`*_cache.json`), cache, log, dan fail `*.lock` / `*.pid` yang lama
- Cache Electron Claude Desktop (aplikasi berbeza; boleh mencecah ~11 GB)

Sandaran penuh biasanya jauh di bawah 100 MB.

### Apa yang TIDAK dilakukan
- Ia **tidak** menyandarkan kod sumber projek anda — simpan itu dalam Git.
- Maklumat kelayakan/token disalin untuk kemudahan, tetapi sebahagiannya terikat pada mesin; anda mungkin masih perlu log masuk semula pada PC baharu.

### Keperluan
- Python 3.8 atau lebih baharu. Pelancar akan memasangnya secara automatik jika tiada.

### Mula pantas
- **Windows:** klik dua kali **`run.bat`**
- **macOS / Linux:** jalankan `./run.sh` dari terminal
- **Atau jalankan terus:** `python backup_transfer_tool.py`

### Arahan
```
python backup_transfer_tool.py            # menu interaktif
python backup_transfer_tool.py backup  [DEST_DIR]
python backup_transfer_tool.py list    [SRC_DIR]
python backup_transfer_tool.py restore [SRC_DIR] [--dry-run] [--yes]
```
Lokasi sandaran lalai: `~/Desktop/AI_Agents_Backup`.

### Berpindah ke PC baharu
1. **PC lama** — jalankan sandaran (tutup Claude Code & Hermes dahulu — lihat di bawah). Folder `backup_<cap masa>` akan dicipta.
2. Salin folder itu ke **PC baharu** (USB, awan, atau perkongsian rangkaian).
3. **PC baharu** — jalankan pemulihan dan tudingkannya ke folder yang disalin. Pemulihan menyesuaikan semula laluan ke mesin baharu secara automatik, walaupun nama pengguna berbeza.

### Sebelum anda menyandarkan
Tutup Claude Code dan Hermes dahulu, supaya pangkalan data langsung mereka (`state.db`, `kanban.db`) disalin dalam keadaan yang konsisten.

### Keselamatan
- **Sandaran hanya menyalin.** Fail asal anda tidak pernah dipindah atau dipadam.
- **Pemulihan bertanya dahulu.** Anda mesti taip `YES` untuk teruskan; `--dry-run` memaparkan rancangan tanpa mengubah apa-apa.
- **Pemulihan tidak pernah memadam.** Mana-mana folder sedia ada dinamakan semula kepada `*.pre-restore-<cap masa>` sebelum sandaran disalin masuk, jadi versi terdahulu sentiasa boleh dipulihkan.

### Di mana data disimpan
| Aplikasi | Windows | macOS | Linux |
|----------|---------|-------|-------|
| Claude Code | `~/.claude`, `~/.claude.json` | sama | sama |
| Hermes Agent | `%LOCALAPPDATA%\hermes`, `~/.hermes` | `~/Library/Application Support/hermes`, `~/.hermes` | `~/.config/hermes`, `~/.hermes` |

---

## 简体中文

### 为什么需要它
更换新电脑时，容易丢失这些 AI 智能体保存在本地的数据：对话会话、长期记忆、自定义技能和配置。此工具正是备份这些数据，跳过可自动重新生成的超大文件，并在新机器上安全恢复。

### 备份的内容
- **Claude Code** — `~/.claude`（会话、记忆、任务、插件、凭据）和 `~/.claude.json`（MCP 服务器 + 各项目配置）
- **Hermes Agent** — 本地应用数据中的 `hermes` 文件夹和 `~/.hermes`（记忆、会话、技能、看板、`state.db`、`config.yaml`、`.env`、`SOUL.md`、认证信息）
- **OpenClaw** — 尽力猜测的路径（若未安装则自动跳过）

### 跳过的内容（体积大 + 自动重新生成）
- Hermes 运行时/源码（`hermes-agent`，约 2 GB）和 `bin`
- 安装程序（`*-setup.exe`）、模型/供应商缓存（`*_cache.json`）、缓存、日志，以及过期的 `*.lock` / `*.pid` 文件
- Claude Desktop 的 Electron 缓存（属于另一个应用；可达约 11 GB）

完整备份通常远小于 100 MB。

### 不做的事情
- 它**不会**备份你的项目源代码——请用 Git 管理。
- 凭据/令牌会一并复制以方便使用，但部分与机器绑定；你在新电脑上或许仍需重新登录。

### 环境要求
- Python 3.8 或更高版本。启动脚本会在缺失时自动安装。

### 快速开始
- **Windows：** 双击 **`run.bat`**
- **macOS / Linux：** 在终端中运行 `./run.sh`
- **或直接运行：** `python backup_transfer_tool.py`

### 命令
```
python backup_transfer_tool.py            # 交互式菜单
python backup_transfer_tool.py backup  [DEST_DIR]
python backup_transfer_tool.py list    [SRC_DIR]
python backup_transfer_tool.py restore [SRC_DIR] [--dry-run] [--yes]
```
默认备份位置：`~/Desktop/AI_Agents_Backup`。

### 迁移到新电脑
1. **旧电脑** — 运行备份（请先退出 Claude Code 和 Hermes，见下文）。将生成一个 `backup_<时间戳>` 文件夹。
2. 将该文件夹复制到**新电脑**（U 盘、云盘或网络共享）。
3. **新电脑** — 运行恢复并指向复制过来的文件夹。恢复会自动将路径重新定位到新机器，即使用户名不同也没问题。

### 备份前
请先退出 Claude Code 和 Hermes，使其实时数据库（`state.db`、`kanban.db`）以一致的状态被复制。

### 安全性
- **备份只复制。** 你的原始文件绝不会被移动或删除。
- **恢复会先询问。** 必须输入 `YES` 才会继续；`--dry-run` 仅预览计划而不做任何更改。
- **恢复绝不删除。** 任何已存在的文件夹会先被重命名为 `*.pre-restore-<时间戳>`，然后再复制备份，因此旧版本始终可以恢复。

### 数据存放位置
| 应用 | Windows | macOS | Linux |
|------|---------|-------|-------|
| Claude Code | `~/.claude`、`~/.claude.json` | 相同 | 相同 |
| Hermes Agent | `%LOCALAPPDATA%\hermes`、`~/.hermes` | `~/Library/Application Support/hermes`、`~/.hermes` | `~/.config/hermes`、`~/.hermes` |

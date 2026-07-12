# AI Agents Backup & Transfer Tool

Move your **Claude Code** and **Codex** (OpenAI) data — sessions, memory, skills, plugins, extensions, connectors, settings, and the **Claude Desktop app's per-account conversation history** — to a new computer without losing anything. Windows, macOS, and Linux.

**Languages:** [English](#english) · [Bahasa Melayu](#bahasa-melayu) · [简体中文](#简体中文)

```
ai-agents-backup-tool/
├── backup_transfer_tool.py   # the tool (Python, standard library only)
├── run.bat                   # Windows launcher (double-click)
├── run.sh                    # Linux / macOS launcher
├── run.command               # macOS launcher (Finder double-click)
├── README.md
└── LICENSE                   # MIT
```

---

## English

### Why
Moving to a new PC risks losing the data these AI agents keep locally: chat sessions, long-term memory, custom skills, installed plugins/extensions, connectors, and configuration — plus the Claude Desktop app's Code-tab conversation history, which is stored **per account**. This tool backs up exactly that data, skips the multi-gigabyte files that regenerate on their own, and restores it safely on the new machine.

### What it backs up
- **Claude Code (CLI)** — `~/.claude` (sessions, memory, tasks, installed **plugins** + their **skills**, **settings**, MCP **connectors** + their OAuth tokens) and `~/.claude.json` (MCP servers + per-project config)
- **Codex (OpenAI)** — `~/.codex` (or `$CODEX_HOME`), the single directory **shared by the Codex CLI, the Codex desktop app, and the IDE extension**: `config.toml`, `auth.json`, `history.jsonl`, `sessions/` (date-organized `rollout-*.jsonl`), `skills/`, and the memories/state/goals databases + `sqlite/` index. The installed desktop app bloats this dir with regenerable runtime, so the tool skips that (see below) and keeps just the data. Codex tags local conversations with **no account** (a single `threads` database, single-account `auth.json`), so a restored `~/.codex` shows every local task under **whichever account you sign into** — nothing per-account to reconcile, unlike the Claude Desktop app. (Codex **Cloud** tasks run server-side and are tied to each account in the cloud; they re-sync on login and aren't part of a local backup.)
- **Claude Desktop app** — a curated slice of its data dir (`%APPDATA%\Claude` on Windows, `~/Library/Application Support/Claude` on macOS, `~/.config/Claude` on Linux):
  - **Code-tab conversation history** (`claude-code-sessions/`) — stored **per account**
  - **agent-mode sessions** (`local-agent-mode-sessions/`) — per account
  - **installed extensions** + their settings + the install list
  - **desktop settings & connectors** (`claude_desktop_config.json`, `developer_settings.json`, `cowork-enabled-cli-ops.json`, `git-worktrees.json`, `plan-usage-history.json`)

### What it skips (huge, auto-regenerated, or already in the cloud)
- Codex's regenerable runtime — `plugins/` (~420 MB of binaries + re-downloadable plugins), `.sandbox-bin` (~330 MB of sandbox binaries), `.tmp` (~140 MB), caches, and log databases — plus the desktop app's install dir `%LOCALAPPDATA%\OpenAI` (~670 MB of binaries + runtimes)
- The Claude Desktop app's `vm_bundles/` (~10 GB), its bundled CLI binary + VM runtime, and all Electron caches (`Cache`, `Code Cache`, `GPUCache`, …)
- `config.json` — it holds **machine-bound auth token caches**; restoring it could disrupt sign-in on the new PC (theme/locale reset in seconds)
- The `IndexedDB` web-chat cache — your **regular claude.ai chats are cloud-synced and reappear automatically on login**, so they need no local backup
- Login cookies / device tokens / crash logs

A full backup is typically a few hundred MB (mostly installed extensions). Add `--lean` to drop the ~150 MB extension payload (keeping the install list), for a backup of roughly 100–150 MB.

### Multiple Claude accounts
The desktop app files Code history under `claude-code-sessions/<accountUuid>/<orgUuid>/`, and those UUIDs are **server-side identities — identical on any machine**. So restoring the folders verbatim lands each account's history exactly where the app looks when *that* account signs in.

When a backup contains **2+ accounts**, restore detects them, lists them, and asks how to handle the per-account history:
- **Separate** (default) — each account keeps only its own conversations. Mirrors your original setup.
- **Merge** — every account sees *all* conversations, so whichever account you switch to shows the same full history.

Skip the prompt with `--separate` or `--merge`. Merge is **additive** — it only copies session entries an account is missing, never overwrites, and unions within a shared organization.

### What it does NOT do
- It does **not** back up your project source code — keep that in Git.
- Credentials/tokens are copied for convenience, but some are machine-bound; you might still need to sign in again on the new PC.

### Requirements
- Python 3.8 or newer. The launchers install it automatically if it is missing.

### Quick start
- **Windows:** double-click **`run.bat`**
- **macOS:** double-click **`run.command`** (or `./run.sh` in a terminal)
- **Linux:** run `./run.sh` from a terminal
- **Or run directly:** `python backup_transfer_tool.py`

### Commands
```
python backup_transfer_tool.py                         # interactive menu
python backup_transfer_tool.py backup  [DEST_DIR] [--lean]
python backup_transfer_tool.py list    [SRC_DIR]
python backup_transfer_tool.py restore [SRC_DIR] [--dry-run] [--yes] [--merge|--separate]
```
- `--lean` — skip the ~150 MB installed-extension payload (extensions re-download on next launch).
- `--merge` / `--separate` — choose multi-account behavior without being prompted.
- `--yes` — restore without any prompts: the newest backup is used, and accounts stay *separate* unless `--merge` is given.
- `--dry-run` — preview the restore plan and detected accounts without changing anything.

Default backup location: `~/Desktop/AI_Agents_Backup`.

### Moving to a new PC
1. **Old PC** — run a backup (quit Claude Code, Codex & the Claude Desktop app first — see below). A `backup_<timestamp>` folder is created.
2. Copy that folder to the **new PC** (USB, cloud, or network share).
3. **New PC** — install the Claude Desktop app first, then run restore and point it at the copied folder. Restore re-anchors paths to the new machine automatically, even if the username is different. If the backup has multiple accounts, you'll be asked *separate* or *merge*. Afterwards, sign into each account in the app to see its history.

### Before you back up
Quit Claude Code, the Codex CLI/desktop app, and the Claude Desktop app first, so their session data and live SQLite databases are copied in a consistent state.

### Safety
- **Backup only copies.** Your original files are never moved or deleted.
- **Restore asks first.** You must type `YES` to proceed; `--dry-run` previews the plan (and the accounts it found) without changing anything.
- **Restore never deletes.** Any existing folder is renamed to `*.pre-restore-<timestamp>` before the backup is copied in, so the previous version is always recoverable.
- **Merge is additive.** It only fills in sessions an account is missing — it never overwrites, and each account's originals stay put.

### Where the data lives
| App | Windows | macOS | Linux |
|-----|---------|-------|-------|
| Claude Code (CLI) | `~/.claude`, `~/.claude.json` | same | same |
| Codex (OpenAI) | `~/.codex` | `~/.codex` | `~/.codex` |
| Claude Desktop app | `%APPDATA%\Claude` | `~/Library/Application Support/Claude` | `~/.config/Claude` |

---

## Bahasa Melayu

### Kenapa
Bertukar ke PC baharu berisiko kehilangan data yang disimpan secara setempat oleh ejen AI ini: sesi perbualan, memori jangka panjang, kemahiran tersuai, plugin/sambungan yang dipasang, penyambung, dan konfigurasi — serta sejarah perbualan Code-tab aplikasi Claude Desktop, yang disimpan **mengikut akaun**. Alat ini menyandarkan data tersebut, melangkau fail bersaiz gigabait yang boleh dijana semula dengan sendiri, dan memulihkannya dengan selamat pada mesin baharu.

### Apa yang disandarkan
- **Claude Code (CLI)** — `~/.claude` (sesi, memori, tugasan, **plugin** yang dipasang + **kemahiran**nya, **tetapan**, **penyambung** MCP + token OAuthnya) dan `~/.claude.json` (pelayan MCP + konfigurasi setiap projek)
- **Codex (OpenAI)** — `~/.codex` (atau `$CODEX_HOME`), direktori tunggal yang **dikongsi oleh Codex CLI, aplikasi Codex desktop, dan sambungan IDE**: `config.toml`, `auth.json`, `history.jsonl`, `sessions/` (disusun mengikut tarikh, `rollout-*.jsonl`), `skills/`, dan pangkalan data memories/state/goals + indeks `sqlite/`. Aplikasi desktop yang dipasang membengkakkan direktori ini dengan runtime yang boleh dijana semula, jadi alat ini melangkaunya (lihat di bawah) dan menyimpan datanya sahaja. Codex tidak menanda perbualan setempat dengan **akaun** (satu pangkalan data `threads`, `auth.json` akaun tunggal), jadi `~/.codex` yang dipulihkan memaparkan setiap tugas setempat di bawah **mana-mana akaun yang anda log masuk** — tiada apa-apa per-akaun untuk diselaraskan, tidak seperti aplikasi Claude Desktop. (Tugas **Cloud** Codex berjalan di pelayan dan terikat pada setiap akaun di awan; ia diselaras semula semasa log masuk dan bukan sebahagian daripada sandaran setempat.)
- **Aplikasi Claude Desktop** — sebahagian terpilih daripada folder datanya (`%APPDATA%\Claude` pada Windows, `~/Library/Application Support/Claude` pada macOS, `~/.config/Claude` pada Linux):
  - **Sejarah perbualan Code-tab** (`claude-code-sessions/`) — disimpan **mengikut akaun**
  - **Sesi mod ejen** (`local-agent-mode-sessions/`) — mengikut akaun
  - **Sambungan yang dipasang** + tetapannya + senarai pemasangan
  - **Tetapan & penyambung desktop** (`claude_desktop_config.json`, `developer_settings.json`, `cowork-enabled-cli-ops.json`, `git-worktrees.json`, `plan-usage-history.json`)

### Apa yang dilangkau (besar, dijana semula, atau sudah di awan)
- Runtime Codex yang boleh dijana semula — `plugins/` (~420 MB binari + plugin yang boleh dimuat turun semula), `.sandbox-bin` (~330 MB binari sandbox), `.tmp` (~140 MB), cache, dan pangkalan data log — serta folder pemasangan aplikasi desktop `%LOCALAPPDATA%\OpenAI` (~670 MB binari + runtime)
- `vm_bundles/` aplikasi Claude Desktop (~10 GB), binari CLI terbundelnya + runtime VM, dan semua cache Electron (`Cache`, `Code Cache`, `GPUCache`, …)
- `config.json` — ia menyimpan **cache token auth yang terikat pada mesin**; memulihkannya boleh mengganggu log masuk pada PC baharu (tema/lokal ditetapkan semula dalam beberapa saat)
- Cache sembang web `IndexedDB` — **sembang claude.ai biasa anda diselaraskan ke awan dan muncul semula secara automatik selepas log masuk**, jadi tidak perlu disandarkan setempat
- Kuki log masuk / token peranti / log ranap

Sandaran penuh biasanya beberapa ratus MB (kebanyakannya sambungan yang dipasang). Tambah `--lean` untuk melangkau muatan sambungan ~150 MB (mengekalkan senarai pemasangan), untuk sandaran lebih kurang 100–150 MB.

### Berbilang akaun Claude
Aplikasi desktop memfailkan sejarah Code di bawah `claude-code-sessions/<accountUuid>/<orgUuid>/`, dan UUID tersebut ialah **identiti sisi pelayan — sama pada mana-mana mesin**. Jadi memulihkan folder sebagaimana adanya meletakkan sejarah setiap akaun tepat di tempat aplikasi mencarinya apabila akaun *itu* log masuk.

Apabila sandaran mengandungi **2+ akaun**, pemulihan mengesannya, menyenaraikannya, dan bertanya cara mengendalikan sejarah setiap akaun:
- **Berasingan** (lalai) — setiap akaun mengekalkan hanya perbualannya sendiri. Mencerminkan susunan asal anda.
- **Gabung** — setiap akaun melihat *semua* perbualan, jadi mana-mana akaun yang anda tukar menunjukkan sejarah penuh yang sama.

Langkau gesaan dengan `--separate` atau `--merge`. Gabung bersifat **tambahan** — ia hanya menyalin entri sesi yang tiada pada sesuatu akaun, tidak pernah menimpa, dan mencantumkan dalam organisasi yang dikongsi.

### Apa yang TIDAK dilakukan
- Ia **tidak** menyandarkan kod sumber projek anda — simpan itu dalam Git.
- Maklumat kelayakan/token disalin untuk kemudahan, tetapi sebahagiannya terikat pada mesin; anda mungkin masih perlu log masuk semula pada PC baharu.

### Keperluan
- Python 3.8 atau lebih baharu. Pelancar akan memasangnya secara automatik jika tiada.

### Mula pantas
- **Windows:** klik dua kali **`run.bat`**
- **macOS:** klik dua kali **`run.command`** (atau `./run.sh` dalam terminal)
- **Linux:** jalankan `./run.sh` dari terminal
- **Atau jalankan terus:** `python backup_transfer_tool.py`

### Arahan
```
python backup_transfer_tool.py                         # menu interaktif
python backup_transfer_tool.py backup  [DEST_DIR] [--lean]
python backup_transfer_tool.py list    [SRC_DIR]
python backup_transfer_tool.py restore [SRC_DIR] [--dry-run] [--yes] [--merge|--separate]
```
- `--lean` — langkau muatan sambungan yang dipasang ~150 MB (sambungan dimuat turun semula pada pelancaran seterusnya).
- `--merge` / `--separate` — pilih gelagat berbilang akaun tanpa digesa.
- `--yes` — pulihkan tanpa sebarang gesaan: sandaran terbaharu digunakan, dan akaun kekal *berasingan* melainkan `--merge` diberikan.
- `--dry-run` — pratonton rancangan pemulihan dan akaun yang dikesan tanpa mengubah apa-apa.

Lokasi sandaran lalai: `~/Desktop/AI_Agents_Backup`.

### Berpindah ke PC baharu
1. **PC lama** — jalankan sandaran (tutup Claude Code, Codex & aplikasi Claude Desktop dahulu — lihat di bawah). Folder `backup_<cap masa>` akan dicipta.
2. Salin folder itu ke **PC baharu** (USB, awan, atau perkongsian rangkaian).
3. **PC baharu** — pasang aplikasi Claude Desktop dahulu, kemudian jalankan pemulihan dan tudingkannya ke folder yang disalin. Pemulihan menyesuaikan semula laluan ke mesin baharu secara automatik, walaupun nama pengguna berbeza. Jika sandaran mempunyai berbilang akaun, anda akan ditanya *berasingan* atau *gabung*. Selepas itu, log masuk ke setiap akaun dalam aplikasi untuk melihat sejarahnya.

### Sebelum anda menyandarkan
Tutup Claude Code, Codex CLI/aplikasi desktop, dan aplikasi Claude Desktop dahulu, supaya data sesi dan pangkalan data SQLite langsung mereka disalin dalam keadaan yang konsisten.

### Keselamatan
- **Sandaran hanya menyalin.** Fail asal anda tidak pernah dipindah atau dipadam.
- **Pemulihan bertanya dahulu.** Anda mesti taip `YES` untuk teruskan; `--dry-run` memaparkan rancangan (dan akaun yang ditemuinya) tanpa mengubah apa-apa.
- **Pemulihan tidak pernah memadam.** Mana-mana folder sedia ada dinamakan semula kepada `*.pre-restore-<cap masa>` sebelum sandaran disalin masuk, jadi versi terdahulu sentiasa boleh dipulihkan.
- **Gabung bersifat tambahan.** Ia hanya mengisi sesi yang tiada pada sesuatu akaun — tidak pernah menimpa, dan versi asal setiap akaun kekal.

### Di mana data disimpan
| Aplikasi | Windows | macOS | Linux |
|----------|---------|-------|-------|
| Claude Code (CLI) | `~/.claude`, `~/.claude.json` | sama | sama |
| Codex (OpenAI) | `~/.codex` | `~/.codex` | `~/.codex` |
| Aplikasi Claude Desktop | `%APPDATA%\Claude` | `~/Library/Application Support/Claude` | `~/.config/Claude` |

---

## 简体中文

### 为什么需要它
更换新电脑时，容易丢失这些 AI 智能体保存在本地的数据：对话会话、长期记忆、自定义技能、已安装的插件/扩展、连接器和配置——以及 Claude 桌面应用的 Code 标签页对话历史，这些历史是**按账户**存储的。此工具正是备份这些数据，跳过可自动重新生成的超大文件，并在新机器上安全恢复。

### 备份的内容
- **Claude Code（CLI）** — `~/.claude`（会话、记忆、任务、已安装的**插件**及其**技能**、**设置**、MCP **连接器**及其 OAuth 令牌）和 `~/.claude.json`（MCP 服务器 + 各项目配置）
- **Codex（OpenAI）** — `~/.codex`（或 `$CODEX_HOME`），这是 **Codex CLI、Codex 桌面应用和 IDE 扩展共用的同一个目录**：`config.toml`、`auth.json`、`history.jsonl`、`sessions/`（按日期归档的 `rollout-*.jsonl`）、`skills/`，以及 memories/state/goals 数据库 + `sqlite/` 索引。已安装的桌面应用会用可重新生成的运行时撑大该目录，因此工具会跳过这些（见下文），只保留数据。Codex 不会给本地对话打上**账户**标记（单一 `threads` 数据库、单账户 `auth.json`），因此恢复后的 `~/.codex` 会在**你登录的任何账户下**显示每一个本地任务——没有任何按账户需要协调的内容，这一点与 Claude 桌面应用不同。（Codex **云端**任务在服务器端运行、在云端与各账户绑定；它们在登录时重新同步，不属于本地备份。）
- **Claude 桌面应用** — 其数据目录中精选的一部分（Windows 上为 `%APPDATA%\Claude`，macOS 上为 `~/Library/Application Support/Claude`，Linux 上为 `~/.config/Claude`）：
  - **Code 标签页对话历史**（`claude-code-sessions/`）——**按账户**存储
  - **智能体模式会话**（`local-agent-mode-sessions/`）——按账户
  - **已安装的扩展** + 其设置 + 安装列表
  - **桌面设置与连接器**（`claude_desktop_config.json`、`developer_settings.json`、`cowork-enabled-cli-ops.json`、`git-worktrees.json`、`plan-usage-history.json`）

### 跳过的内容（体积大、自动重新生成，或已在云端）
- Codex 可重新生成的运行时——`plugins/`（约 420 MB 二进制文件 + 可重新下载的插件）、`.sandbox-bin`（约 330 MB 沙盒二进制文件）、`.tmp`（约 140 MB）、缓存和日志数据库——以及桌面应用的安装目录 `%LOCALAPPDATA%\OpenAI`（约 670 MB 二进制文件 + 运行时）
- Claude 桌面应用的 `vm_bundles/`（约 10 GB）、其内置 CLI 二进制文件 + VM 运行时，以及所有 Electron 缓存（`Cache`、`Code Cache`、`GPUCache` 等）
- `config.json`——它保存**与机器绑定的认证令牌缓存**；恢复它可能会干扰新电脑上的登录（主题/语言几秒即可重设）
- `IndexedDB` 网页聊天缓存——你的**常规 claude.ai 聊天会同步到云端，登录后自动重新出现**，因此无需本地备份
- 登录 Cookie / 设备令牌 / 崩溃日志

完整备份通常为几百 MB（主要是已安装的扩展）。加上 `--lean` 可跳过约 150 MB 的扩展负载（保留安装列表），备份约为 100–150 MB。

### 多个 Claude 账户
桌面应用将 Code 历史归档在 `claude-code-sessions/<accountUuid>/<orgUuid>/` 下，而这些 UUID 是**服务器端身份——在任何机器上都相同**。因此原样恢复这些文件夹，会把每个账户的历史正好放到该账户登录时应用查找的位置。

当备份包含 **2 个及以上账户**时，恢复会检测并列出它们，并询问如何处理各账户的历史：
- **分开保留**（默认）——每个账户只保留自己的对话。与你原来的设置一致。
- **合并**——每个账户都能看到*所有*对话，因此无论切换到哪个账户，都显示相同的完整历史。

用 `--separate` 或 `--merge` 跳过提示。合并是**增量式的**——它只复制某账户缺少的会话条目，绝不覆盖，并在同一组织内合并。

### 不做的事情
- 它**不会**备份你的项目源代码——请用 Git 管理。
- 凭据/令牌会一并复制以方便使用，但部分与机器绑定；你在新电脑上或许仍需重新登录。

### 环境要求
- Python 3.8 或更高版本。启动脚本会在缺失时自动安装。

### 快速开始
- **Windows：** 双击 **`run.bat`**
- **macOS：** 双击 **`run.command`**（或在终端中运行 `./run.sh`）
- **Linux：** 在终端中运行 `./run.sh`
- **或直接运行：** `python backup_transfer_tool.py`

### 命令
```
python backup_transfer_tool.py                         # 交互式菜单
python backup_transfer_tool.py backup  [DEST_DIR] [--lean]
python backup_transfer_tool.py list    [SRC_DIR]
python backup_transfer_tool.py restore [SRC_DIR] [--dry-run] [--yes] [--merge|--separate]
```
- `--lean` — 跳过约 150 MB 的已安装扩展负载（扩展将在下次启动时重新下载）。
- `--merge` / `--separate` — 无需提示即可选择多账户行为。
- `--yes` — 不经任何提示直接恢复：使用最新的备份，且除非给出 `--merge`，各账户保持*分开*。
- `--dry-run` — 预览恢复计划和检测到的账户，而不做任何更改。

默认备份位置：`~/Desktop/AI_Agents_Backup`。

### 迁移到新电脑
1. **旧电脑** — 运行备份（请先退出 Claude Code、Codex 和 Claude 桌面应用，见下文）。将生成一个 `backup_<时间戳>` 文件夹。
2. 将该文件夹复制到**新电脑**（U 盘、云盘或网络共享）。
3. **新电脑** — 先安装 Claude 桌面应用，然后运行恢复并指向复制过来的文件夹。恢复会自动将路径重新定位到新机器，即使用户名不同也没问题。如果备份包含多个账户，会询问你选择*分开保留*还是*合并*。之后，在应用中登录各账户即可查看其历史。

### 备份前
请先退出 Claude Code、Codex CLI/桌面应用和 Claude 桌面应用，使其会话数据和实时 SQLite 数据库以一致的状态被复制。

### 安全性
- **备份只复制。** 你的原始文件绝不会被移动或删除。
- **恢复会先询问。** 必须输入 `YES` 才会继续；`--dry-run` 仅预览计划（及其找到的账户）而不做任何更改。
- **恢复绝不删除。** 任何已存在的文件夹会先被重命名为 `*.pre-restore-<时间戳>`，然后再复制备份，因此旧版本始终可以恢复。
- **合并是增量式的。** 它只补齐某账户缺少的会话——绝不覆盖，且每个账户的原始内容都保持不变。

### 数据存放位置
| 应用 | Windows | macOS | Linux |
|------|---------|-------|-------|
| Claude Code（CLI） | `~/.claude`、`~/.claude.json` | 相同 | 相同 |
| Codex（OpenAI） | `~/.codex` | `~/.codex` | `~/.codex` |
| Claude 桌面应用 | `%APPDATA%\Claude` | `~/Library/Application Support/Claude` | `~/.config/Claude` |

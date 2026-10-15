# 飞书资产工作区：部署、授权与密码分享

仅在已选择飞书协作或明确要求飞书部署时读取。复用当前会话已授权的目标、测试范围与身份，不重新询问已回答事项。本文件不授予其他项目的写权限。由当前技能的飞书工作区入口调用；共享表结构、附件与修订约定见 [FEISHU_BASE_LAYOUT](FEISHU_BASE_LAYOUT.md)，剧本发布见 [FEISHU_SCREENPLAY_SYNC](FEISHU_SCREENPLAY_SYNC.md)。

以下接口于 **2026-10-14** 核对官方文档与 CLI 源码，维护基线为 CLI **1.0.98**；执行前以当前版本帮助/schema 再核准。不能用本文件中的旧示例覆盖新版接口事实。

## 1. 发现与独立部署

先检查宿主已有飞书连接器及其实际暴露的工具、登录身份和 Base 能力。已连接且满足读写需求就复用；连接器缺少密码接口时，可补用官方 CLI/API，不因此重建整个环境。

没有适用连接器时，在 Windows 检查 `Get-Command lark-cli` 及项目部署记录中已有的独立CLI路径；未加入PATH不等于未安装。找到后运行该可执行文件的 `--version`、`--help`、`auth status --json --verify`。仅记录版本、身份、有效状态与缺失权限，不打印配置文件、App Secret、访问令牌或完整环境变量。需要保持用户归属时，后续命令显式 `--as user`；不要因默认落到 bot 就创建一份用户看不到的资产库。

CLI、飞书 Skills、凭据是独立环境，不随当前 Skill 打包。CLI 确实缺失且部署在用户授权范围内时，先检查 Node/npm，再把官方包安装到 Skill 目录之外的独立 prefix。以下为通用示例路径；已有部署路径优先复用：

```powershell
node --version
npm --version
$feishuRuntimeRoot = Join-Path $env:LOCALAPPDATA 'CodexTools\feishu-runtime'
npm install --global --prefix "$feishuRuntimeRoot" @larksuite/cli
$feishuCli = Join-Path $feishuRuntimeRoot 'lark-cli.cmd'
& $feishuCli --version
```

后文用 `lark-cli` 简写已解析的CLI；专用prefix未加入PATH时实际用 `& $feishuCli` 调用，不为照抄命令再次全局安装。不要在任何编剧或导演Skill内产生node_modules、运行时依赖或登录配置。

已有 CLI 能完成任务就不升级。官方推荐的一体向导 `npx @larksuite/cli@latest install` 会进入 Skills 安装及配置流程；不要把它当作只安装 CLI 的无副作用替代。不要自动覆盖用户已有飞书 Skills、应用配置或身份。若确需补装官方 Skills，先检查已有目录并只处理所需内容；不要用全量覆盖命令修复单个能力缺口。

安装失败时先区分缺少运行时、命令未进入 PATH、网络下载失败与本机权限问题。可在当前进程重新发现官方安装位置，不为修复命令可见性修改无关系统配置，也不下载来源不明的代理安装器。记录实际采用的可执行文件与版本，后续继续用同一环境，避免 npx 临时副本和全局版本混用。

## 2. 配置与用户授权

先区分缺 CLI、缺应用配置、缺用户登录、缺 scope、缺目标 Base 权限。浏览器能打开链接不证明 API 可用。已有有效配置继续使用；只有确需首次配置或用户选择新应用时才执行：

```powershell
lark-cli config init --help
lark-cli config init --new
```

配置命令可后台运行；Windows 若用 `Start-Process`，用 Hidden 窗口。用户本人在官方浏览器页面完成应用配置和授权，agent 不代点同意、不要求用户把密钥粘贴进聊天。命令输出 `verification_url`、`verification_uri_complete` 或 `console_url` 时，原样展示该 URL，不能重拼 query 或编解码；同时生成 PNG 二维码并展示，URL 在前、二维码在后：

```powershell
lark-cli auth qrcode <原样URL> --output auth/config-qr.png
```

先建好当前项目 cwd 下的 `auth` 目录。二维码和认证临时记录留在本地，不上传到资产总表。不能因为后台进程仍在等待，就报告配置完成。

按待执行 API 的 schema 选择 scope，不默认申请全部业务域。权限设置读写可使用以下精确范围；Base 表/字段/记录/附件操作还要补齐其各自需要的权限：

```powershell
lark-cli auth login --help
lark-cli auth login --scope "docs:permission.setting:read docs:permission.setting:write_only" --no-wait --json
```

采用 split-flow：读取本次返回的 URL 和 device code，展示原始链接及 QR 后交还用户；明确请用户完成后回复。用户回复完成后，agent 再执行：

```powershell
lark-cli auth login --device-code <本次DEVICE_CODE>
lark-cli auth status --json --verify
```

不在用户尚未看到链接时立即阻塞轮询；链接过期就按相同必要范围重新发起，不复用旧 code。缺 scope 时按错误中的范围增量授权。bot scope 缺失应走开发者后台，不用 user OAuth 假装修复。用户/应用具有 API scope 后仍须拥有目标资源 ACL；高级权限 Base 还需检查相应角色和应用权限。

认证与资源校验分开记状态：登录有效只证明身份可用；读取目标成功才证明有读取权限；写入能力依据所需 scope、资源角色及已授权操作结果确认。不要向既有生产记录写入“测试”文本探路。若仅允许独立测试，就新建或使用明确指定的测试表，并在测试记录中标明用途；清理测试资产也沿用用户允许的处理范围。

## 3. 解析目标并验证连接

先用当前 `lark-cli base +url-resolve --url <原始URL> --as user` 解析返回的资源类型与真实ID。已有 `/base/<token>` URL 可识别为 Base 候选；`/wiki/<token>` 先通过当前支持的 `drive +inspect --url` 解包，不能把 wiki token 当作 app_token。保留 table/view 参数但分别存储，实际读取 Base 元数据、数据表和必要字段，确认标题与用户目标相符。解析失败、权限不足或对象类型不符时，不另建同名表冒充已连接。

用户只给 URL + 分享密码时，可用该密码进入浏览器页面；**网页密码不是 API Authorization**。API 仍走当前连接器/CLI 的 OAuth 或应用授权。没有 API 权限时说明具体缺口，继续不依赖云端的规划；需要浏览器处理则按宿主工具能力执行，不能声称已经完成 API 接入。

权限失败优先按错误对应处理：缺 scope 才重新授权；缺资源协作者权限则让所有者为正确身份赋权；租户安全策略或文档密级阻断则保留目标并说明管理员处理入口。不要把三类错误都解释成密码错误，也不要反复创建应用或重试同一写请求。网络超时若无法确定服务端是否已成功，应先只读核查目标，避免重复创建。

新建时用当前 Base 创建工具或 `lark-cli base --help` / 对应 schema，创建用户授权的总表或独立测试表。先检查是否已有可复用目标，记录真实 app_token、URL、身份及用途；不要猜造创建命令或把本地计划当云端成果。表内布局按 [FEISHU_BASE_LAYOUT](FEISHU_BASE_LAYOUT.md) 实施。

## 4. 默认可编辑链接与密码分享

飞书协作的新建或首次接入默认使用“互联网获得链接的人可编辑”（`anyone_editable`），新建总表同时启用密码；已有分享密码沿用。入口已告知这一协作默认，目标与读写范围已获授权时直接落实，不重复询问已明确事项；仅提供链接而授权范围尚不清楚时，先核实缺失的权限变更范围。用户明确只读或保留现状时覆盖默认。修改前读取实际设置，只更新本次链接编辑权限及必要的外部访问开关，复制、下载、协作者管理等其他权限沿用现状。可编辑用于协作者改记录及上传素材/视频，不等于授予所有者或可管理权限，也不替代API身份与scope。

Base 支持密码分享，但只保护组织外链接访问；所有者、内部成员及通过协作者授权的用户无需密码。不能承诺所有访问者都必须输入密码。企业或知识库禁止对外分享时，交由相关管理员处理，不换接口绕过。

新建按 **创建空 Base → 互联网链接可编辑 → 启用密码并确认成功 → 上传资产 → 验证交付** 执行，密码未确认前不上传或分发资产。已有含资产Base先核实其密码与访问设置，沿用有效密码，仅调整已授权的链接编辑档位；用户明确要求保留现有权限时不调整。不能为验证密码随意关闭/重开或轮换既有密码。官方未提供本指南可证明的原子“创建并加密”操作。

当前 CLI typed 公开权限接口是 v1，默认可编辑枚举是 `anyone_editable`：

```powershell
lark-cli schema drive.permission.public.patch
lark-cli drive permission.public patch --params '{"token":"<APP_TOKEN>","type":"bitable"}' --data '{"external_access":true,"link_share_entity":"anyone_editable"}' --as user --dry-run
```

核对预览后执行相同命令并去掉 `--dry-run`。若返回退出码 10/高风险门禁，遵守当前工具要求，展示具体 action、risk、目标和范围；所要求的人类确认满足后，只按 hint 把确认 flag 追加在原 argv 末尾。已获授权按宿主规则判断，不凭技能自行追加新审批。**不能改用 raw API、脚本或另一身份绕过门禁。** v2 的 `external_access_entity:"open"` 只适用于 v2，不能混进上述 v1 body。

官方密码接口明确支持 `type=bitable`。当前 CLI catalog 未提供 password typed command，可用官方 raw API；新版若有专门工具，先核准后优先用它：

```powershell
lark-cli api --help
lark-cli api POST /open-apis/drive/v1/permissions/<APP_TOKEN>/public/password --params '{"type":"bitable"}' --as user --dry-run
lark-cli api POST /open-apis/drive/v1/permissions/<APP_TOKEN>/public/password --params '{"type":"bitable"}' --as user --format json
```

无请求体、不传自定义 `password`；服务器返回生成的密码。当前 raw `api` 没有 `--yes` 参数，不臆造 flag。需要刷新时同 endpoint 使用 PUT，会使旧密码失效，仅在用户要求轮换时执行；自定义指定密码可通过官方分享设置 UI 完成。密码调用成功前不上传资产、不分发链接。失败时记录 pending/failed，按已授权失败处理方案恢复范围；不能以普通公开链接替代完成结果。

## 5. 文件、验证与完成状态

CLI 的 `--file`、`--output`、`@file` 用当前项目 cwd 内相对路径。先读取上传/下载命令帮助；大 JSON 优先 stdin 或相对 JSON 文件，避免 PowerShell 原生命令转义破坏数据。`base +record-upload-attachment` 将文件直接上传并绑定到指定record/field；不要再把返回token通过普通记录更新写进附件字段。读回实际附件token与文件信息后，用于下载、哈希核对及当前文件清单；本地路径、网页 URL 和临时下载链接不能冒充附件。具体上传、下载、记录字段和增量同步模板见布局参考。

封装 CLI JSON 时检查 `ok == true` 或退出码 0；原始 OpenAPI 的 `code == 0` 不等于 CLI 输出契约。只把生成的分享密码交付给获授权用户，不写入普通台账、提示词、同步日志或提交仓库；API token 更不得输出。读回须确认`link_share_entity=anyone_editable`及允许外部访问；用户明确的权限覆盖按其目标验收。权限GET不返回密码开关，不能仅凭可编辑枚举声称密码已验证。记录密码接口成功证据，并在可用的外部访客上下文分别检查密码门禁及实际编辑/上传；所有者读写成功不能代替访客测试，所有者登录页面免密不算失败。无法完成外部验证时如实标记“可编辑设置与密码API已确认，访客读写未验证”。

用户已授权专用真实测试时，在该测试表完成约定读写验证，不把授权扩展到生产表。报告真实 URL、接入身份、上传/读回结果、密码启用与验证状态；授权未完成、只跑 dry-run 或只有本地文件，都不能报告云端完成。

## 官方依据

- [CLI 安装、认证与输出契约](https://github.com/larksuite/cli/blob/main/README.zh.md)；[安装向导源码](https://github.com/larksuite/cli/blob/main/scripts/install-wizard.js)；[Windows 支持](https://github.com/larksuite/cli/blob/main/package.json)。
- [raw API 命令](https://github.com/larksuite/cli/blob/main/cmd/api/api.go)；[Drive typed catalog](https://github.com/larksuite/cli/blob/main/internal/registry/catalog/services/drive.json)。
- [Base 等云文档的密码分享规则](https://www.larksuite.com/hc/en-US/articles/360048487840-password-protect-documents-and-folders-for-sharing)。
- [启用密码](https://open.feishu.cn/document/server-docs/docs/permission/permission-public/permission-public-password/create)；[刷新密码](https://open.feishu.cn/document/server-docs/docs/permission/permission-public/permission-public-password/update)；[读取权限 v2](https://open.feishu.cn/document/server-docs/docs/permission/permission-public/get-2)。官方开放平台规范文档 URL 后加 `.md` 可读取 Markdown 正文。

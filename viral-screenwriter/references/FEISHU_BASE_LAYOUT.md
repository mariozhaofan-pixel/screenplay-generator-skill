# 飞书四表布局与修订合同

仅在飞书工作区创建、结构映射或增补时加载；由当前技能的飞书工作区入口调用；编剧和导演使用同一版本蓝图。本文件与 [JSON 蓝图](../assets/feishu-base-blueprint.json) 定义同一最小布局：一个 Base，项目总览、资产库、段落交付、剧本交付四张表，没有独立同步表。剧本发布与当前版本选择见 [剧本同步合同](FEISHU_SCREENPLAY_SYNC.md)。

## 文件归属与使用入口

| 表 | 主用途与真实附件字段 | 关联访问 |
| --- | --- | --- |
| 项目总览 | `名称`、`总索引md文件` | `当前剧本`为当前采用修订；`剧本历史`、`资产`、`段落`为自动创建的反向关联 |
| 剧本交付 | `名称`、`剧本md文件` | `所属项目`定位同一项目；项目入口的`当前剧本`选择各批当前采用修订 |
| 资产库 | `名称`、`图片资产`、`对应图片生成提示词md文件` | `所属项目`打开总索引；`使用段落`打开对应段落提示词及视频 |
| 段落交付 | `名称`、`对应段落提示词md文件`、`对应提示词的视频上传` | `关联资产`打开图片与生图提示词；`来源剧本`追溯精确采用修订；`所属项目`打开总索引 |

文件在对应实体上保留这些准确字段名。图片、四个 `.md` 文件字段和视频字段都是 `attachment`，不能用本地路径、文本正文或未验证的链接冒充附件。四表的 `名称` 是 `text` 主展示字段，不承担唯一约束。其他字段只服务身份、修订、场景关系与制作协作，具体定义以蓝图为准。

`对应提示词的视频上传` 是用户附件列：只在建字段时创建 schema，建行时省略，后续自动同步也始终省略。不发送 `null`、`[]` 或读回的旧视频值，不上传占位视频，不调用该字段的附件删除或清空。`备注`同样归人工维护。用户上传不代表成片已验收；用户验收状态须有实际依据，不能由脚本默认推进。

首版使用原生附件和记录关联，不依赖 attachment lookup。现有文档没有充分保证附件 lookup 的预览、下载和画廊封面能力；不能宣称不支持，也不能把关键文件访问建立在未验证的行为上。

## 将蓝图转换为实际字段

蓝图是带编排元数据的模板，**整个文件不是 API payload**。`table_ref`、`source_table_ref`、`primary_field`、`views`、`record_contract` 都不能混入字段创建 JSON。

1. 先解析真实 Base 并读取已有表、字段、视图，映射 `projects → 项目总览`、`assets → 资产库`、`segments → 段落交付`、`scripts → 剧本交付` 的真实 ID。同职能现有表可映射，不因名称不同重复创建；同名字段也必须核对类型。
2. 按 `table_order` 创建缺少的四张表。每项 `fields` 是普通字段的 CLI 形状数组，可单独提取给建表 `--fields`，或给已有表的 `+field-create --json`。`名称`为首字段；若建表命令已生成主字段，映射或按实际协议命名，不再创建第二个主字段。已有字段只补缺项。
3. 四表都存在后处理 `deferred_links`：由 `source_table_ref` 找源表 ID；复制 `field` 对象，把其中 `table_ref` 替换为 `link_table: <真实目标表ID>`，再移除 `table_ref`。将转换后的字段对象交给源表 `+field-create`。不能把占位表名或符号引用当成真实 ID。
4. 前三个双向关联自动生成 `项目总览.资产`、`项目总览.段落`、`资产库.使用段落`，不要再手建同名反向列。已有等价关联优先复用。`来源A` 是资产库指向自身的单向关联。新增`剧本交付.所属项目`自动生成`项目总览.剧本历史`；`项目总览.当前剧本`与`段落交付.来源剧本`均为指向剧本交付的单向关联，前者可含各批当前修订，后者绑定本段实际使用的修订。
5. 基础和关联字段全部就绪后再创建/配置视图；保存实际表、字段、视图 ID。新字段或视图在查询中可能短暂不可见；优先使用创建响应中的真实ID，必要时有限退避后只读确认可见，再配置，不因一次`not_found`重复创建。字段批量创建若部分成功，只补失败与未执行项，不能重发全数组。

转换后的关联字段示例，ID 必须来自本次真实读取：

```json
{"name":"关联资产","type":"link","link_table":"<actual_assets_table_id>","bidirectional":true,"bidirectional_link_field_name":"使用段落"}
```

关联 CellValue 是记录引用数组，如 `[{"id":"<actual_asset_revision_record_id>"}]`；单选 CellValue 也是数组，如 `["可用"]`。禁止旧 `field_name`、`property`、数字类型枚举或自行添加 `multiple` 到 link schema。附件通过专用上传命令处理，不作为普通记录值写入。创建普通字段可使用：

```powershell
lark-cli base +field-create --base-token '<base_token>' --table-id '<table_id>' --json '@ordinary-fields.json' --as user
```

`ordinary-fields.json` 只包含需要新增的字段对象或非空数组，路径相对当前工作目录；不是整个蓝图。字段创建/更新前仍以当前宿主 lark-base reference 或 `--help` 核对协议，已有字段更新可能是完整覆盖，不能用本蓝图盲目重置用户选项、描述或样式。

## 身份、修订与当前文件

`项目ID`、`资产ID`、`段落ID`、`剧本ID` 是稳定业务 ID，沿用云端或首次实际分配的值，不从展示名称、段号或本机路径推导。`record_id` 是对应云行 ID；两者都要保存。业务 ID 找实体，完整 `同步键` 找修订行：

| 实体 | 同步键形状 | 行的生命周期 |
| --- | --- | --- |
| 项目 | `project/{项目ID}` | 项目保持一行；`修订ID`表示当前索引修订 |
| 剧本 | `project/{项目ID}/script/{剧本ID}/revision/{修订ID}` | 同一批次/范围稳定剧本ID，每个采用修订独立一行 |
| 资产 | `project/{项目ID}/asset/{资产ID}/revision/{修订ID}` | 同一状态/方向的每个修订独立一行 |
| 段落 | `project/{项目ID}/segment/{段落ID}/revision/{修订ID}` | 每版段落提示词独立一行 |

这些形状用于一致编码，不能把花括号模板作为真实记录值。同键查询结果为零才创建，一条则复用，多条则保留成果并标记冲突。CLI 的 `+record-upsert` 不会按该业务键自动查重。完整查询范围和分页必须覆盖目标项目，不能只看当前视图。

剧本/资产/段落修订发布后，其图片、提示词和精确资产关联不可换版覆写。段落提示词、所绑定资产修订或来源剧本修订变化时，新建段落修订行，旧视频留在旧行，新行用户视频仍省略。预留修订行可补入尚不存在、且与该修订提示词一致的首次产物；已有图片或提示词发生替换则新建修订。状态、负责人和任务ID可随实际进展更新，人工备注不动。

场景 A/B 是不同资产ID、不同修订行，使用同一 `空间组ID`。B 的 `来源A` 指向实际参与生成 B 的 A 修订记录；A 不虚构来源。A 后来改版不自动改绑既有 B。只有 A 时保留 A 并补 B，不能为凑成对重生 A；只有文本规划时保留方向和提示词，图片字段为空。

`当前文件清单` 是 `text` 单元格，值为 JSON 字符串。结构见蓝图 `manifest_json_text_shape`：包含清单版本、当前修订，以及各文件的角色、实际字段ID、修订、file_token、basename、字节大小和 SHA256。项目只允许 `project_index_md`；资产允许 `asset_image/image_prompt_md`；段落只允许 `segment_prompt_md`；剧本只允许 `screenplay_md`。用户视频不进入这个由程序维护的清单。

只在上传返回实际 token 且哈希已计算后登记；没有图片就省略该角色，不能填假 token、空路径或伪造哈希。清单不放凭据、分享密码、临时下载 URL、本机绝对路径或整篇提示词。附件同名不能证明相同，SHA256用于字节查重，不能代替实际看图。

总索引始终归项目行；新版附件追加，旧版保留，写前核对远端基线后再更新当前清单和索引修订。剧本、资产和段落新修订由新行承载，不把多版提示词塞进同一用户视频行。所有写入只提交改变的程序字段，不把整行读回结果写回。

`生产负责人`与`任务ID`用于约定执行者和追踪生成任务，使用可识别文本即可，不伪造人员 open_id。首版同项目约定单一发布者，同表串行写入；普通字段读写不是原子锁，也未证明服务端有唯一约束或 CAS。跨设备读前比较、冲突保留和追加修订不能被描述成“多人并发绝不重复”。

## 视图与附件命令模板

蓝图每个视图的 `create`、`card`、`visible_fields` 分别是对应命令的 JSON 对象，单独提交。`visible_fields` 控制可见性和顺序，要传完整可见名单；系统可能固定主字段在首位。已有视图先读配置，只改本次要求，保留用户布局。

```powershell
lark-cli base +view-create --base-token '<base_token>' --table-id '<assets_table_id>' --json '{"name":"资产画廊","type":"gallery"}' --as user
lark-cli base +view-set-card --base-token '<base_token>' --table-id '<assets_table_id>' --view-id '<view_id>' --json '{"cover_field":"图片资产"}' --as user
lark-cli base +view-set-visible-fields --base-token '<base_token>' --table-id '<segments_table_id>' --view-id '<view_id>' --json '{"visible_fields":["名称","段号","对应段落提示词md文件","对应提示词的视频上传","关联资产","来源剧本","所属项目","状态","生产负责人","任务ID","备注"]}' --as user
```

`+view-create` 使用 `--json`，不猜测 `--name/--view-type` 参数。画廊封面是实际 `图片资产`附件字段；文字锁定和待生图记录允许无封面。主工作台都是 grid，资产另有 gallery，技术键和当前文件清单默认隐藏，不删除字段。

```powershell
lark-cli base +record-upload-attachment --base-token '<base_token>' --table-id '<table_id>' --record-id '<record_id>' --field-id '<allowed_attachment_field_id>' --file './staging/actual-file.md' --as user
lark-cli base +record-download-attachment --base-token '<base_token>' --table-id '<table_id>' --record-id '<record_id>' --file-token '<actual_file_token>' --output './cache/actual-file.md' --as user
```

上传为追加，名字取本地 basename，重复 `--file` 可上传多件。上传前核对哈希与已确认 token；结果未知先重读，不盲目重传。下载精确 token，避免省略 token 后意外拉取整行用户视频；单 token 可输出文件路径，多 token 要输出已有目录。文件路径相对 cwd，绝对本机路径不写入蓝图或记录。

协议依据：宿主 lark-base 的 field-schema / field-create reference；补充核验了官方 CLI [附件上传](https://github.com/larksuite/cli/blob/v1.0.97/shortcuts/base/record_upload_attachment.go)、[附件下载及可见字段](https://pkg.go.dev/github.com/larksuite/cli/shortcuts/base)、[视图创建](https://github.com/larksuite/cli/blob/v1.0.97/shortcuts/base/view_create.go)和[卡片配置](https://github.com/larksuite/cli/blob/v1.0.97/shortcuts/base/view_set_card.go)的 v1.0.97 定义。模板核验不等于云端建成；部署时以真实返回和当批附件/关联验收确认完成。

## 从三表布局增补到四表

读取本项目原Base、项目记录、真实表/字段ID与映射后，只创建缺少的剧本交付表及上述三组关联；已有同职能表先映射。旧三表和record_id保留，不重建总库、不重置原视图/人工字段、不移动或重复上传资产。主键、字段类型不兼容时只处理具体冲突；已有视图只追加本次必要列并保持原有顺序。全部写入读回确认后才将本地schema_version登记为2.0.0。部分迁移失败保存已成功ID，只补未完成项。

旧项目没有剧本附件时，该字段与当前剧本保持空；继续使用用户已提供的有效剧本，不编造旧修订、来源记录或“已同步”状态。编剧可独立创建完整空布局供导演接入，空的资产/段落表不构成开始写剧本的障碍。

# Glossary: Chinese name | id | category

Generated from `tools/i18n_map.json` (`python3 tools/migrate_ids.py --glossary`). Ids are the English
snake_case names used in data, code, saves and effect/condition strings; Chinese appears only in display
fields (`name`, `text`, `body`, ...). The design documents (GDD, DESIGN_NOTES ...) still use the Chinese
names; look them up here. Source tags in notes: `[orig ...]` original game, `[inferred N..]` was
`[推N..]` (inferred, see DESIGN_NOTES), `[user]` was `[用]` (user decision), `[user material]` was
`[用素材]`.

## Name prefixes in effects and conditions

| Chinese | id | category |
|---|---|---|
| 好感. | `favor.` | prefix |
| 旗标. | `flag.` | prefix |
| 状态. | `status.` | prefix |
| 计数. | `count.` | prefix |
| 修正. | `rep_bonus.` | prefix |
| 权重. | `weight.` | prefix |
| 物品. | `item.` | prefix |
| 触发. | `trigger.` | prefix |
| 成功期数. | `job_periods.` | prefix |
| 旬数. | `class_periods.` | prefix |
| 期数. | `road_periods.` | prefix |
| 标签. | `tag.` | prefix |
| 交手次数. | `duels.` | prefix |

## Second segment of `count.<...>`

| Chinese | id | category |
|---|---|---|
| 试镜 | `audition` | counter |
| 试镜拿到 | `audition_won` | counter |
| 上映 | `release` | counter |
| 大卖 | `hit` | counter |
| 扑街 | `flop` | counter |
| 配角 | `support` | counter |
| 违约 | `breach` | counter |
| 被捕 | `arrest` | counter |
| 丑闻 | `scandal` | counter |
| 机遇 | `opportunity` | counter |
| 年度名次 | `annual_rank` | counter |
| 看书旬数 | `book_periods` | counter |
| 没钱上课日 | `broke_class_days` | counter |
| 外出 | `outing` | counter |
| 旬 | `period` | counter |
| 买装备花费 | `gear_spend` | counter |
| 压下丑闻 | `scandal_covered` | counter |
| 遇见 | `met` | counter |
| 主演 | `lead` | counter |
| 受伤 | `injury` | counter |
| 浪漫系大卖 | `romance_hits` | counter |
| 近12月大片大卖 | `big_hits_12m` | counter |
| 亲自上 | `stunt_self` | counter |
| 低成本 | `lowbudget` | counter |
| 有声片部数 | `talkie_count` | counter |

## Base attributes

| Chinese | id | category |
|---|---|---|
| 体力 | `stamina` | attr |
| 教育 | `education` | attr |
| 义气 | `loyalty` | attr |
| 相貌 | `looks` | attr |
| 自律 | `discipline` | attr |
| 犯罪 | `crime` | attr |
| 疲劳 | `fatigue` | attr |
| 名气 | `fame` | attr |
| 金钱 | `money` | attr |

## Skills

| Chinese | id | category |
|---|---|---|
| 打斗 | `fight` | skill |
| 骑马驾驶 | `riding` | skill |
| 胆识 | `nerve` | skill |
| 演技 | `acting` | skill |
| 打扮 | `grooming` | skill |
| 体态 | `physique` | skill |
| 创作 | `writing` | skill |
| 审美 | `taste` | skill |
| 谈吐 | `speech` | skill |
| 谈判 | `negotiation` | skill |
| 人脉 | `connections` | skill |
| 生意 | `business` | skill |

## Roads (reputation)

| Chinese | id | category |
|---|---|---|
| 硬汉 | `tough` | road |
| 情人 | `lover` | road |
| 文化 | `culture` | road |
| 手腕 | `savvy` | road |

## NPCs

| Chinese | id | category |
|---|---|---|
| Sil | `sil` | npc |
| Duv | `duv` | npc |
| 女明星 | `actress` | npc |
| 第四人 | `fourth` | npc |
| 同乡工头 | `foreman` | npc |
| 神父 | `priest` | npc |
| 画家 | `painter` | npc |
| 酒吧老板 | `bar_owner` | npc |
| 片厂老板 | `studio_boss` | npc |
| 编辑 | `editor` | npc |
| 富婆 | `rich_widow` | npc |
| 动作片导演 | `action_director` | npc |

## Film tags

| Chinese | id | category |
|---|---|---|
| 动作冒险 | `action_adventure` | tag |
| 异国情人 | `exotic_lover` | tag |
| 古装 | `costume` | tag |
| 西部 | `western` | tag |
| 犯罪 | `crime` | tag |
| 反派 | `villain` | tag |
| 文艺 | `arthouse` | tag |
| 悲情 | `tragic` | tag |
| 宗教 | `religious` | tag |
| 浪漫 | `romance` | tag |
| 战争 | `war` | tag |
| 歌舞 | `musical` | tag |
| 恐怖 | `horror` | tag |
| 地下片 | `underground` | tag |
| 喜剧 | `comedy` | tag |
| 贵族 | `noble` | tag |

## Tag families

| Chinese | id | category |
|---|---|---|
| 情人系 | `lover_family` | tag_family |
| 动作系 | `action_family` | tag_family |
| 性格系 | `persona_family` | tag_family |
| 艺术系 | `art_family` | tag_family |
| 喜剧贵族系 | `comedy_noble_family` | tag_family |

## Street entries

| Chinese | id | category |
|---|---|---|
| 服装店 | `clothing_store` | street |
| 杂货店 | `general_store` | street |
| 书店 | `bookstore` | street |
| 餐厅 | `restaurant` | street |
| 教堂 | `church` | street |
| 医院 | `hospital` | street |
| 和 Sil 谈话 | `sil_talk` | street |

## Street services

| Chinese | id | category |
|---|---|---|
| 点心 | `dessert` | service |
| 夜总会晚餐 | `nightclub_dinner` | service |
| 牛排 | `steak` | service |
| 捐款 | `donation` | service |
| 诊疗 | `treatment` | service |
| 近况 | `status_hint` | service |
| 劝说 | `persuade` | service |

## Items

| Chinese | id | category |
|---|---|---|
| 旧西装 | `suit_old` | item |
| 定制西装 | `suit_custom` | item |
| 晚礼服 | `evening_gown` | item |
| 白色皮草 | `fur_white` | item |
| 骑装 | `riding_habit` | item |
| 怀表 | `gold_watch` | item |
| 奴隶手镯 | `slave_bracelet` | item |
| 拳套 | `boxing_gloves` | item |
| 舞鞋 | `dance_shoes` | item |
| 化妆箱 | `makeup_case` | item |
| 留声机 | `phonograph` | item |
| 相机 | `camera` | item |
| 打字机 | `typewriter` | item |
| 社交名录 | `social_register` | item |
| 福特车 | `car_ford` | item |
| 跑车 | `car_sports` | item |
| 进口豪车 | `car_luxury` | item |
| 补药 | `tonic` | item |
| 旧书 | `old_book` | item |
| 前辈的装备·硬汉 | `senior_gear_tough` | item |
| 前辈的装备·情人 | `senior_gear_lover` | item |
| 前辈的装备·文化 | `senior_gear_culture` | item |
| 前辈的装备·手腕 | `senior_gear_savvy` | item |

## Indices

| Chinese | id | category |
|---|---|---|
| 生病指数 | `sick_index` | index |
| 失控指数 | `reckless_index` | index |

## Status flags (state.status)

| Chinese | id | category |
|---|---|---|
| 重病 | `very_sick` | status |
| 失控 | `reckless` | status |
| 恋爱 | `in_love` | status |
| 长约 | `long_contract` | status |
| 拍摄旬 | `shooting_period` | status |
| 当月有拍摄 | `shoot_this_month` | status |
| 有未开拍角色 | `has_pending_role` | status |
| 收尾期 | `wrap_up` | status |

## Derived variables

| Chinese | id | category |
|---|---|---|
| 最高声望 | `max_rep` | derived |
| 最高声望所在路 | `top_road` | derived |
| 四路声望极差 | `rep_spread` | derived |
| 药瘾阶段 | `drug_stage` | derived |
| 负债月数 | `debt_months` | derived |
| 最高基础属性 | `top_base_attr` | derived |
| 手腕最高技能 | `top_savvy_skill` | derived |
| 最大工期数 | `max_job_periods` | derived |
| 有声片部数 | `talkie_count` | derived |
| 日期 | `date` | derived |
| 最大标签族 | `top_tag_family` | derived |
| 无法定义 | `undefined` | derived |
| 低成本定型 | `lowbudget_typed` | derived |
| 最常打的工 | `top_job` | derived |
| 最常上的课 | `top_class` | derived |

## Flags (flag.<id>)

| Chinese | id | category |
|---|---|---|
| Duv写剧本 | `duv_writes_script` | flag |
| 丑闻预知 | `scandal_foresight` | flag |
| 亲自上线50 | `stunt_line_50` | flag |
| 会员 | `member` | flag |
| 侍者情报 | `waiter_tip` | flag |
| 保释减半 | `bail_half` | flag |
| 免费压丑闻 | `free_scandal_cover` | flag |
| 入伙 | `joined_crew` | flag |
| 制片人线 | `producer_line` | flag |
| 前辈三档_硬汉 | `senior_tier3_tough` | flag |
| 前辈三档_情人 | `senior_tier3_lover` | flag |
| 前辈三档_文化 | `senior_tier3_culture` | flag |
| 前辈三档_手腕 | `senior_tier3_savvy` | flag |
| 前辈四档_硬汉 | `senior_tier4_tough` | flag |
| 前辈四档_情人 | `senior_tier4_lover` | flag |
| 前辈四档_文化 | `senior_tier4_culture` | flag |
| 前辈四档_手腕 | `senior_tier4_savvy` | flag |
| 口音待触发 | `accent_pending` | flag |
| 口音期 | `accent_period` | flag |
| 同乡挡债 | `fellow_debt_shield` | flag |
| 告密 | `tipoff` | flag |
| 富婆投资 | `widow_invest` | flag |
| 富婆赞助服装 | `widow_outfit_sponsor` | flag |
| 推销员 | `salesman` | flag |
| 支持转型 | `backs_transition` | flag |
| 放消息 | `leak_news` | flag |
| 文凭 | `diploma` | flag |
| 有声片 | `talkies` | flag |
| 有声谈吐线减10 | `talkie_speech_line_minus_10` | flag |
| 柏林邀约 | `berlin_invite` | flag |
| 瓦伦去世 | `valen_dead` | flag |
| 神父作保 | `priest_vouch` | flag |
| 警告 | `warning` | flag |
| 认识导演 | `knows_director` | flag |
| 谈吐进阶上架 | `speech_advanced_on_shelf` | flag |
| 走私 | `smuggling` | flag |
| 送去戒 | `detox_sent` | flag |
| 长约翻倍 | `long_contract_double` | flag |
| 逃兵 | `deserter` | flag |
| 旧人 | `old_friend` | flag |
| 旧客 | `old_client` | flag |
| 旧片 | `old_film` | flag |
| 人情 | `owed_favor` | flag |
| 戒指 | `ring` | flag |
| 船票 | `ship_ticket` | flag |

## Enumerated values

| Chinese | id | category |
|---|---|---|
| 旬初 | `period_start` | enum |
| 月末 | `month_end` | enum |
| 时代 | `era` | enum |
| 工作 | `job` | enum |
| 小咪生日当天 | `birthday` | enum |
| 工期间 | `during_job` | enum |
| 每局一次 | `once_per_game` | enum |
| 每年一次 | `once_per_year` | enum |
| 每季度一次 | `once_per_quarter` | enum |
| 小 | `small` | enum |
| 中 | `medium` | enum |
| 大 | `big` | enum |
| 服装 | `outfit` | enum |
| 配饰 | `accessory` | enum |
| 持有 | `held` | enum |
| 消耗 | `consumable` | enum |
| 感情线 | `romance` | enum |
| 功能 | `function` | enum |
| 男 | `male` | enum |
| 女 | `female` | enum |
| 唯一 | `single` | enum |
| 第一场 | `first` | enum |
| 黑暗 | `dark` | enum |
| 演员 | `actor` | enum |
| 万能 | `all` | enum |
| 排名 | `ranking` | enum |
| 外出 | `outing` | enum |
| 家教 | `tutor` | enum |
| 随机 | `random` | enum |
| 月 | `month` | enum |
| (链事件) | `(chain)` | enum |
| (常驻) | `(resident)` | enum |
| (家教链) | `(tutor_chain)` | enum |
| 家教第 | `tutor_period` | enum |

## Fame tiers

| Chinese | id | category |
|---|---|---|
| 无名 | `unknown` | fame_tier |
| 眼熟 | `familiar` | fame_tier |
| 有名 | `famous` | fame_tier |
| 当红 | `hot` | fame_tier |
| 巨星 | `superstar` | fame_tier |

## Book tiers

| Chinese | id | category |
|---|---|---|
| 入门 | `beginner` | book_tier |
| 进阶 | `advanced` | book_tier |
| 专著 | `monograph` | book_tier |

## Ending categories

| Chinese | id | category |
|---|---|---|
| 黑暗 | `dark` | category |
| 演员 | `actor` | category |
| 万能 | `all` | category |

## Other values

| Chinese | id | category |
|---|---|---|
| 试镜情报 | `audition_intel` | misc |
| 艳遇 | `encounter` | misc |
| 月份 | `month` | misc |
| 年份 | `year` | misc |
| 档次 | `grade` | misc |
| 计数器 | `counters` | misc |
| 标签计数 | `tag_counts` | misc |
| 生病 | `sick` | misc |

## Internal keys and values (state, saves, bots, trace)

| Chinese | id | category |
|---|---|---|
| 手牌 | `hand` | internal |
| 对手手牌 | `rival_hand` | internal |
| 场风 | `style` | internal |
| 轮次 | `round` | internal |
| 历史 | `history` | internal |
| 轮 | `rounds` | internal |
| 对手牌 | `rival_cards` | internal |
| 我的牌 | `my_cards` | internal |
| 拿到 | `won` | internal |
| 落选 | `lost` | internal |
| 上报 | `reported` | internal |
| 纯色 | `mono` | internal |
| 板 | `board` | internal |
| 池 | `pool` | internal |
| 基础场风 | `base_style` | internal |
| 女主 | `lead` | internal |
| 对手规格 | `rival_spec` | internal |
| 本厂 | `house` | internal |
| 有名占位 | `named_placeholder` | internal |
| 占位 | `placeholder` | internal |
| 上过板 | `boarded` | internal |
| 彩蛋 | `easter_egg` | internal |
| 待上板 | `pending_board` | internal |
| 转型 | `transition` | internal |
| 够不着 | `out_of_reach` | internal |
| 道德条款 | `morals` | internal |
| 排除 | `excluded` | internal |
| 资格 | `eligible` | internal |
| 试过 | `tried` | internal |
| 片约 | `film` | internal |
| 配角 | `support` | internal |
| 待拍 | `to_shoot` | internal |
| 被抢 | `stolen` | internal |
| 片 | `films` | internal |
| 锁 | `locks` | internal |
| 拍摄日 | `shoot_days` | internal |
| 成功日 | `ok_days` | internal |
| 表现 | `perf` | internal |
| 待映 | `to_release` | internal |
| 已映 | `released` | internal |
| 违约 | `breached` | internal |
| 非定型 | `untyped` | internal |
| 口音 | `accent` | internal |
| 大卖 | `hit` | internal |
| 扑街 | `flop` | internal |
| 分红 | `dividend` | internal |
| 专练硬汉 | `only_tough` | internal |
| 专练情人 | `only_lover` | internal |
| 专练文化 | `only_culture` | internal |
| 专练手腕 | `only_savvy` | internal |
| 两路（硬汉+情人） | `two_roads` | internal |
| 犯罪线 | `crime_line` | internal |
| 只读书文化 | `books_culture` | internal |
| 乱选 | `random_pick` | internal |
| 月数 | `months_played` | internal |
| 无年度声望 | `no_annual_rep` | internal |
| 年度修正 | `annual_bonus` | internal |
| 拆 | `breakdown` | internal |
| 训练 | `training` | internal |
| 加成 | `gear` | internal |
| 年度 | `annual` | internal |
| 普通声望 | `plain_rep` | internal |
| 买装备 | `gear_buy` | internal |
| 年度名次 | `annual_rank` | internal |
| 品性 | `character` | internal |
| 对象 | `target` | internal |
| 好 | `good` | internal |
| 末次 | `last_fired` | internal |
| 压丑闻年 | `scandal_cover_year` | internal |
| 免费 | `free` | internal |
| 花钱 | `paid` | internal |
| 长约拒绝 | `contract_refused` | internal |
| 上课日 | `class_days` | internal |
| 放消息年 | `leak_year` | internal |
| 版本 | `version` | internal |
| 工作日 | `work_days` | internal |
| 薪水 | `pay` | internal |
| 作废 | `void` | internal |
| 拍摄 | `shooting` | internal |
| Duv教育 | `duv_education` | internal |
| 随机数 | `rng` | internal |
| 种子 | `seed` | internal |
| 混合 | `mixed` | internal |
| 步骤 | `steps` | internal |
| 开局 | `origin` | internal |
| 测试 | `test` | internal |
| 装备 | `equip` | internal |
| 更新指数 | `update_indices` | internal |
| 变量 | `var` | internal |
| 没有 | `none` | internal |
| 一百 | `hundred` | internal |

## Item class / slot values

| Chinese | id | category |
|---|---|---|
| 书 | `book` | class |
| 服装 | `outfit` | class |
| 配饰 | `accessory` | class |
| 持有 | `held` | class |
| 消耗 | `consumable` | class |
| 旬初 | `period_start` | class |
| 月末 | `month_end` | class |
| 时代 | `era` | class |
| 工作 | `job` | class |
| 机遇 | `opportunity` | class |
| 感情线 | `romance` | class |
| 功能 | `function` | class |

## Field names (JSON keys)

| Chinese | id | category |
|---|---|---|
| 说明 | `note` | field |
| 排名 | `ranking` | field |
| 我的分 | `my_score` | field |
| 对手 | `opponents` | field |
| 对手分 | `opponent_score` | field |
| 奖励 | `rewards` | field |
| 名次 | `rank` | field |
| 修正 | `rep_bonus` | field |
| 奖金 | `prize` | field |
| 场合 | `occasions` | field |
| 名字 | `name` | field |
| 路 | `road` | field |
| 条件 | `cond` | field |
| 玩法 | `play` | field |
| 档 | `tier` | field |
| 教育门槛 | `education_gate` | field |
| 技能上限 | `skill_cap` | field |
| 点数 | `points` | field |
| 收益 | `gain` | field |
| 价格 | `price` | field |
| 书 | `books` | field |
| 技能 | `skills` | field |
| 读完事件 | `finish_event` | field |
| 上架 | `on_shelf` | field |
| 开始 | `start` | field |
| 结束 | `end` | field |
| 月 | `month` | field |
| 序号 | `seq` | field |
| 天数 | `days` | field |
| 旬 | `periods` | field |
| 周日 | `sundays` | field |
| 选片板 | `board` | field |
| 打工解锁 | `job_unlocks` | field |
| 时代事件 | `era_events` | field |
| 年度大事 | `annual` | field |
| 对手成长 | `rival_growth` | field |
| 收尾期 | `wrap_up` | field |
| 结局判定 | `ending_check` | field |
| 等级门槛 | `class_steps` | field |
| 等级说明 | `level_note` | field |
| 课 | `classes` | field |
| 学费 | `fee` | field |
| 项 | `stat` | field |
| 各级 | `per_level` | field |
| 每旬效果 | `period_effect` | field |
| 剧情链 | `story_chain` | field |
| 链 | `chain` | field |
| 触发旬数 | `trigger_periods` | field |
| 强制 | `forced` | field |
| 文本 | `body` | field |
| 特殊 | `special` | field |
| 大类 | `category` | field |
| 大类说明 | `category_note` | field |
| 档次线 | `grade_lines` | field |
| 标签族 | `tag_families` | field |
| 标签族说明 | `tag_families_note` | field |
| 结局 | `endings` | field |
| 顺序 | `order` | field |
| 内容 | `content` | field |
| 动态名 | `dynamic_name` | field |
| 归宿 | `destiny` | field |
| 普通 | `ordinary` | field |
| 模式 | `mode` | field |
| 好归宿线 | `good_destiny_line` | field |
| 叠加 | `stacking` | field |
| 评分 | `scoring` | field |
| 总分 | `total` | field |
| 结局分 | `ending_score` | field |
| 品性分 | `character_score` | field |
| 归宿分 | `destiny_score` | field |
| 普通好归宿 | `ordinary_good` | field |
| 评语 | `comment` | field |
| 品性档 | `character_tiers` | field |
| 分 | `score` | field |
| 默认档 | `default_tier` | field |
| 概率 | `prob` | field |
| 频次 | `freq` | field |
| 代码 | `code` | field |
| 月末顺序 | `month_end_order` | field |
| 月末上限 | `month_end_cap` | field |
| 事件 | `event` | field |
| 类 | `class` | field |
| 时机 | `timing` | field |
| 值 | `value` | field |
| 效果 | `effect` | field |
| 来源 | `source` | field |
| 分子 | `numerator` | field |
| 分母 | `denominator` | field |
| 上限 | `max` | field |
| 选项 | `options` | field |
| 文字 | `text` | field |
| 判定 | `check` | field |
| 成功效果 | `success_effect` | field |
| 失败效果 | `fail_effect` | field |
| 分支 | `branches` | field |
| 日期 | `date` | field |
| 线 | `line` | field |
| 遵循概率 | `follow_prob` | field |
| 习惯 | `habit` | field |
| 出牌 | `play_order` | field |
| 情报 | `intel` | field |
| 显示 | `shows` | field |
| 试镜 | `audition` | field |
| 张数 | `cards` | field |
| 赢轮数 | `rounds_to_win` | field |
| 颜色顺序 | `color_order` | field |
| 克制 | `counters` | field |
| 场风百分比 | `style_pct` | field |
| 克制方百分比 | `counter_pct` | field |
| 被克方百分比 | `countered_pct` | field |
| 对手组牌 | `rival_deck` | field |
| 场风系数百分比 | `style_factor_pct` | field |
| 副色 | `second_color` | field |
| 结果 | `result` | field |
| 记住 | `remembered` | field |
| 比分 | `score_line` | field |
| 主色场风加百分点 | `main_style_add_pts` | field |
| 惜败 | `narrow_loss` | field |
| 拍摄旬数减 | `shoot_periods_cut` | field |
| 拍摄旬数最少 | `shoot_periods_min` | field |
| 片酬百分比 | `fee_pct` | field |
| 上映百分比 | `release_pct` | field |
| 演砸 | `botched` | field |
| 上报概率 | `report_prob` | field |
| 上报效果 | `report_effect` | field |
| 好感 | `favor` | field |
| 规则 | `rules` | field |
| 持有上限 | `hold_cap` | field |
| 服装槽 | `outfit_slots` | field |
| 配饰槽 | `accessory_slots` | field |
| 服装加成 | `outfit_bonus` | field |
| 互斥 | `exclusive` | field |
| 物品 | `items` | field |
| 槽 | `slot` | field |
| 出售 | `sellable` | field |
| 互斥组 | `exclusive_group` | field |
| 日薪 | `daily_wage` | field |
| 加薪档 | `raise_tiers` | field |
| 成功线 | `success_lines` | field |
| 每天效果 | `daily_effect` | field |
| 每期效果 | `job_period_effect` | field |
| 每期随机 | `period_random` | field |
| 前置 | `prereq` | field |
| 成功线修正 | `success_line_mods` | field |
| 期数小于 | `periods_below` | field |
| 加成百分比 | `bonus_pct` | field |
| 全勤加成百分比 | `full_attendance_bonus_pct` | field |
| 拒绝 | `refuse` | field |
| 例外 | `except` | field |
| 工 | `jobs` | field |
| 最早时间 | `earliest` | field |
| 加 | `add` | field |
| 曝光 | `exposure` | field |
| 原版形状 | `original_shape` | field |
| 里程碑 | `milestones` | field |
| 名气档顺序 | `fame_tier_order` | field |
| 生活方式 | `lifestyles` | field |
| 月费 | `monthly_cost` | field |
| 月结效果 | `month_end_effect` | field |
| 触发 | `trigger` | field |
| 常驻 | `resident` | field |
| 权重 | `weight` | field |
| 日程本全显示线 | `schedule_full_view_line` | field |
| 日程 | `schedule` | field |
| 地点 | `place` | field |
| 年份 | `years` | field |
| 月份 | `months` | field |
| 认识途径 | `met_via` | field |
| 机遇 | `opportunities` | field |
| 每月概率 | `monthly_prob` | field |
| 剧情 | `story` | field |
| 占月 | `takes_month` | field |
| 问 | `questions` | field |
| 问题 | `question` | field |
| 标签计数 | `tag_counts` | field |
| 旗标 | `flags` | field |
| 旗标说明 | `flag_note` | field |
| 一次性 | `once` | field |
| 花费 | `cost` | field |
| 常在的人 | `residents` | field |
| 随机表 | `random_table` | field |
| 偏向 | `bias` | field |
| 疲劳每天 | `fatigue_per_day` | field |
| 花费按名气档 | `cost_by_fame_tier` | field |
| 休息 | `rests` | field |
| 生病可选 | `sick_allowed` | field |
| 玩家可选 | `player_choice` | field |
| 钱不够 | `if_broke` | field |
| 钱不够改 | `if_broke_switch` | field |
| 作用于 | `applies_to` | field |
| 拍摄违约 | `shoot_breach` | field |
| 片酬 | `fee` | field |
| 名气百分比 | `fame_pct` | field |
| 有名 | `named` | field |
| 在场 | `present` | field |
| 阶段 | `stages` | field |
| 自 | `from` | field |
| 等级 | `levels` | field |
| 名气 | `fame` | field |
| 替换 | `replace` | field |
| 原 | `old` | field |
| 改为 | `new` | field |
| 无名 | `unnamed` | field |
| 档次 | `size` | field |
| 场次 | `rounds` | field |
| 主色等级 | `main_level` | field |
| 基 | `base` | field |
| 涨级月 | `level_up_months` | field |
| 随机 | `random` | field |
| 副色差 | `second_gap` | field |
| 每半年 | `per_half_year` | field |
| 教学 | `tutorial` | field |
| 角色 | `roles` | field |
| 片名 | `film_title` | field |
| 名气门槛 | `fame_gate` | field |
| 场风概率 | `style_probs` | field |
| 看重 | `wants` | field |
| 目标 | `target` | field |
| 标签 | `tags` | field |
| 加分技能 | `bonus_skill` | field |
| 有声 | `talkie` | field |
| 谈吐线 | `speech_line` | field |
| 出现年份 | `years_active` | field |
| 场风规则 | `style_rule` | field |
| 默认 | `defaults` | field |
| 拍摄旬数 | `shoot_periods` | field |
| 每板 | `per_board` | field |
| 人脉多一个中片 | `connections_extra_medium` | field |
| 人脉多一个大片 | `connections_extra_big` | field |
| 试镜次数 | `audition_tries` | field |
| 同角色上板上限 | `same_role_cap` | field |
| 权重上限 | `weight_cap` | field |
| 道德条款犯罪 | `morals_crime` | field |
| 低成本大片门槛加 | `lowbudget_big_gate_add` | field |
| 转型板数 | `transition_boards` | field |
| 瓦伦去世后多一个 | `after_valen_extra` | field |
| 至 | `until` | field |
| 标签审美 | `tag_taste` | field |
| 习惯交手次数 | `habit_duels` | field |
| 习惯人脉 | `habit_connections` | field |
| 排除一色人脉 | `exclude_color_connections` | field |
| 比例 | `ratio` | field |
| 个数 | `count` | field |
| 百分比 | `pct` | field |
| 拍摄 | `shoot` | field |
| 疲劳 | `fatigue` | field |
| 表现下限 | `perf_min` | field |
| 表现上限 | `perf_max` | field |
| 谈判除数 | `negotiation_div` | field |
| 亲自上 | `stunt_self` | field |
| 胆识线 | `nerve_line` | field |
| 胆识线_旗标 | `nerve_line_flag` | field |
| 表现加 | `perf_add` | field |
| 受伤概率 | `injury_prob` | field |
| 受伤效果 | `injury_effect` | field |
| 临时换角 | `swap_role` | field |
| 旬数 | `period_count` | field |
| 上映 | `release` | field |
| 隔月 | `delay_months` | field |
| 基数 | `box_base` | field |
| 契合 | `fit` | field |
| 底 | `floor` | field |
| 系数 | `coef` | field |
| 单项上限百分比 | `item_cap_pct` | field |
| 标签熟悉 | `tag_familiarity` | field |
| 每个 | `per_tag` | field |
| 上限个数 | `cap_count` | field |
| 定型线 | `typed_line` | field |
| 非定型百分比 | `untyped_pct` | field |
| 分红倍数 | `dividend_mult` | field |
| 大卖百分比 | `hit_pct` | field |
| 扑街百分比 | `flop_pct` | field |
| 有声罚百分比 | `talkie_penalty_pct` | field |
| 电台谈吐线减 | `radio_speech_line_cut` | field |
| 低成本 | `lowbudget` | field |
| 增减 | `delta` | field |
| 无法定义种类 | `undefined_kinds` | field |
| 女主好感 | `lead_favor` | field |
| 占位生成 | `placeholder_gen` | field |
| 主色场风 | `main_style` | field |
| 其余场风 | `other_style` | field |
| 看重目标 | `wants_target` | field |
| 标签按主色 | `tags_by_color` | field |
| 大片有名对手 | `big_named_rivals` | field |
| 取前 | `take_top` | field |
| 剧本 | `script` | field |
| 自己写 | `self_written` | field |
| Duv写 | `duv_written` | field |
| 看重百分比 | `wants_pct` | field |
| 合写 | `co_written` | field |
| 好感初值 | `favor_init` | field |
| 开局认识 | `known_at_start` | field |
| 性别 | `gender` | field |
| 身份 | `identity` | field |
| 好感来源 | `favor_sources` | field |
| 归宿条件 | `destiny_cond` | field |
| 原版对应 | `original` | field |
| 教育里程碑 | `education_milestones` | field |
| 好感范围 | `favor_range` | field |
| 义气加成 | `loyalty_bonus` | field |
| 恋爱状态 | `love_state` | field |
| 持续月数 | `duration_months` | field |
| 结束条件 | `end_cond` | field |
| 每月好感 | `monthly_favor` | field |
| 作用线 | `lines` | field |
| 归宿优先 | `destiny_priority` | field |
| 训练范围 | `train_range` | field |
| 初值 | `init` | field |
| 固定用途 | `fixed_use` | field |
| 显示加成 | `display_bonus` | field |
| 属性 | `attr` | field |
| 除 | `div` | field |
| 基础属性 | `attrs` | field |
| 范围 | `range` | field |
| 用途 | `usage` | field |
| 可为负 | `may_be_negative` | field |
| 声望 | `roads` | field |
| 声望规则 | `rep_rules` | field |
| 公式 | `formula` | field |
| 修正值 | `rep_bonus_rule` | field |
| 结局档次线 | `ending_grade_lines` | field |
| 门槛 | `gate` | field |
| 名气档 | `fame_tiers` | field |
| 下限 | `min` | field |
| 名气规则 | `fame_rules` | field |
| 来信数 | `mail_count` | field |
| 月衰减 | `monthly_decay` | field |
| 月衰减百分比 | `monthly_decay_pct` | field |
| 月衰减最少 | `monthly_decay_min` | field |
| 指数 | `indices` | field |
| 状态线 | `status_line` | field |
| 重病线 | `very_sick_line` | field |
| 倒下 | `collapse` | field |
| 隐藏值 | `hidden` | field |
| 合同 | `contract` | field |
| 教育低于 | `education_below` | field |
| 片酬系数百分比 | `fee_coef_pct` | field |
| 免除条件 | `exempt_cond` | field |
| 月薪 | `monthly_pay` | field |
| 本厂角色数 | `house_roles` | field |
| 本厂场风加 | `house_style_add` | field |
| 拒绝后月数 | `refuse_months` | field |
| 折扣 | `discount` | field |
| 人脉每满 | `connections_per` | field |
| 每档减百分比 | `cut_pct_per_step` | field |
| 上限百分比 | `cap_pct` | field |
| 取整 | `rounding` | field |
| 生效 | `applies` | field |
| 入口 | `entries` | field |
| 货架 | `shelf` | field |
| 服务 | `services` | field |
| 限次 | `limit` | field |
| 次数 | `times` | field |
| 合计 | `shared` | field |
| 价格公式 | `price_formula` | field |
| 效果公式 | `effect_formula` | field |
| 生病 | `when_sick` | field |
| 状态 | `status` | field |
| 留空 | `placeholder` | field |
| 金钱 (`stats.json` top level) | `money` | field |
| 档 (`books.json` top level) | `tiers` | field |
| 地点 (`places.json` top level) | `places` | field |
| 强制 (`lifestyle.json` top level) | `forced_note` | field |
| 月 (`calendar.json` top level) | `months` | field |
| 习惯 (`habits.json` top level) | `habits` | field |
| 事件 (`events.json` top level) | `events` | field |
| 事件 (`outing.json` top level) | `events` | field |
| npc (`romance.json` top level) | `npcs` | field |
| 链 (`npc_chains.json` top level) | `chains` | field |
| 大类 (`endings.json` top level) | `categories` | field |

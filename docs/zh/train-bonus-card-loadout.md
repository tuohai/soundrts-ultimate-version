# 训练加成卡牌（Train Bonus Loadout Cards）

战前携带卡可注册 **训练加成**：本局内**第一次**从建筑**完成训练**指定单位时，在照常产出的单位之外，**额外**再生成 n 个同类型单位（不占人口、不另扣资源）。触发后本局不再重复。

英文版：[../en/train-bonus-card-loadout.md](../en/train-bonus-card-loadout.md)

---

## cards.txt 语法

```txt
def card_footman_train_bonus
title 5396
train_bonus footman 3
grant_charges 1
min_rank rank_sergeant
```

| 指令 | 说明 |
|------|------|
| `train_bonus <unit_type> <n>` | **首次**完成训练该单位时，额外生成 n 个（整局每种单位仅触发一次） |

- 与 `spawn` 不同：`spawn` 在进局（或延迟到点）**立即**在起始格附近生成；`train_bonus` 为整局被动，仅在 **第一次** TrainOrder 完成时触发一次。
- 可与 `delay` 组合：整张卡的效果（含训练加成注册）在延迟到点后一并生效。
- 多张卡或重复条目可叠加（同一 `type_name` 累加 n）。
- 单位名按阵营 `equivalent_type` 解析（随机阵营亦正确）。

## 示例

携带 `train_bonus footman 3` 进局后，**第一次**在兵营完成训练步兵（默认产出 1 个）→ 实际获得 **4 个步兵**（1 + 3 加成）。之后再训步兵恢复正常数量。

若第一次训练命令一次产出多个（`can_train` 批量 >1），加成仍只触发**一次**（在第一个单位训练完成时 +3，同批后续单位不再加成）。

## 语音

| TTS | 中文 |
|-----|------|
| 5394 | 训练时额外获得 |
| 5395 | 本局训练时额外获得 |
| 5396 | 步兵训练增员卡 |

## 实现

- 注册：`card_loadout._apply_card_train_bonuses` → `player._loadout_train_bonuses`
- 触发：`TrainOrder.complete` → `apply_train_bonus_for_unit`

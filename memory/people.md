# 用户身边的人（总控维护）

用途：用户提到某人，或仓库、对话里出现某人时，先查这里。
- 写入者：只有总控。
- 来源：
  - 「用户说」= 用户亲口告诉总控，可信度最高；
  - 「网上」= 公开资料，只记和用户相关的部分；
  - 「推断」= 总控从文件或提交记录推出来的，引用前要确认。
- 中文全名不确定时**不要猜**，写「未知」，等用户告诉。
- 新增人物：按下面的格式加一节，并在末尾「待问」里列出不确定的地方。

## 一、身份对照（GitHub / 邮箱 → 人）

| 账号 | 邮箱 | 人 | 依据 |
|---|---|---|---|
| YijieYing | herryying30@gmail.com | 用户本人 | — |
| aytony | github@aytony.cn、opensource@aytony.cn | 安阳 | 用户说（11-02） |
| Weinan Shi、swnhieian、石伟男 | swnhieian@126.com | 石伟男 | 推断：octopus 提交署名、私有 git 服务器域名 brain.shiweinan.com |
| yuchun、yuchun2pcg | yc2pcg@gmail.com | 喻纯 | 用户说（11-02） |
| euxcet、Chengchi Zhou | zcc.qwer@gmail.com | 未知（octopus 提交最多的人，同一个邮箱） | 待问 |
| shenxing | 81379162@qq.com | 未知（octopus；也是 Ear 手机端 NextHCI/octopus-flutter 的主要提交者，11-13 发现） | 待问 |
| chengsx21 | chengsx_thu@163.com | 未知（octopus） | 待问 |
| HPZ07-end、TMM | hdy24@(m)ails.tsinghua.edu.cn | 未知（NatureCalls 队友，两个署名同一人） | 待问 |
| Songyf24 | songyf24@mails.tsinghua.edu.cn | 未知（NatureCalls 队友） | 待问 |
| BIGfeiyu-friend | — | 未知（deepseek_face 仓库主人） | 待问 |

不需要记的提交者：CodexBridge 的 Gan-Xing 等上游维护者、openai/codex 等外部仓库的作者。

## 二、FlyBrain 组（用户实习，项目叫 DigitalFly）

- 机构：岩思类脑（合同在 DigitalFly 目录）。
- 大老板：**李国齐**。
- 本地材料：`~/research/DigitalFly/`；组会 PPT 在 `ppt/10.15/`。

### 李国齐
- 角色：FlyBrain 组的大老板（用户说）。
- 公开资料（网上）：
  - 中科院自动化所研究员，方向是脉冲神经网络、类脑大模型（SpikingBrain「瞬悉」）。
  - 担任尖峰智能实验室主任（陈天桥支持的「发现式智能」）。
  - BrainFuse 论文的资深作者之一。

### 陈白雨（Baiyu Chen）
- 角色：用户眼里组里**最靠谱的学长**。用户的很多研究反馈来自他（用户说）。
- 现状：最近没在做用户这个方向（用户说）。
- 主要工作：BrainFuse（网上）。
  - 论文：arXiv 2601.21407，2026-01。
  - 内容：可微分的生物物理（Hodgkin-Huxley）神经元仿真，并能部署到类脑芯片。
  - 用途：讨论研究、需要靠谱反馈时，用户会想到他。

### 唐元宏
- 角色：老师（「唐老师」）。他给组里分享过果蝇觅食论文，胡瑞的 10.15 PPT 引用了它。
- 果蝇组的老师（用户说，11-02）。网上没查到更多。

### 胡瑞
- 角色：学长。用户评价「不太靠谱」。
- 方向：视觉、嗅觉 → 脑网络 → 参考路径 → VNC 觅食（10.15 PPT）。
- 提议：今年做「能动、能用 connectome 自主决策」的果蝇，冲 Nature。用户认为目标太大，也没有评价标准。
- 评估：DigitalFly session「果蝇主动决策模型可行性评估」（`local_f0c819f4-4403-4f23-a7f0-0fca8708e6f3`，10-23）。

### 侯科宇、曾依璐、田质文
- 组员，10-15 组会各自做了报告（`ppt/10.15/`）。别的都不知道。

## 三、清华 HCI（喻纯、石伟男一线；Ear / octopus）

### 喻纯
- 用户和录音里叫「郁老师」（用户说正字是喻纯）。
- 公开资料（网上）：
  - 清华计算机系副教授，人机交互方向（普适计算实验室，pi.cs.tsinghua.edu.cn）。
  - 做过智能戒指（手势、文本输入）。
- 和用户的交集：
  - 10-27 饭局提到，他的组输入法论文多；他不赞成只读旧论文。
  - NextHCI/octopus 仓库里的 yuchun 就是他（用户说）。

### 石伟男
- 用户和录音里叫「石老师」（用户说正字是石伟男）。
- 公开资料（网上）：清华 HCI 实验室，读博时做输入法、虚拟键盘（如 LaserBoard）。
- 和用户的交集：
  - 10-27 饭局提到，和他讨论过录音分析助手（Ear）。
  - 托管 `octopus-service-person` 仓库（brain.shiweinan.com）。用户在 `~/.octopus/worktrees/person-ear-*` 往里面接入 Ear。
  - 是 NextHCI/octopus 的主要提交者之一。
  - Octopus 的公网 FRP 中继 `vps.shiweinan.com`（注册端口 7000，HTTP 入口 6950）应是他那边运维的。11-14 起 EarRecorder 借用 6950 做加密中继（手机加密、中继只转发密文）。技术上已跑通，但**还没征得同意**，长期使用要先问他。
- 以后若涉及 Ear 和 octopus 的合作，先想到他。

### 安阳（GitHub: aytony）
- 研一（10-27 饭局，`~/research/1027discussion.md`）。
- Ear（Echo-As-Record/Echo-As-Record）的合作者，有提交。

### 陈伟浩
- 喻纯组的博士后（用户说，11-02）。

## 四、课程与其他项目

- **NatureCalls**（软件工程课的合作游戏，HPZ07-end/NatureCalls）：队友 HPZ07-end（=TMM）、Songyf24，中文名未知。
- **deepseek_face**（BIGfeiyu-friend/dsapi-pet-ascii）：仓库主人 BIGfeiyu-friend，身份未知。

- 芯动计划（`~/Projects/XinDong`，TC377 智能车冬令营，2027-01-18～24，12-20 冻结版本）：甘特表里点名的是吴宗桓、廖宇翚、赵丹琪。用户口述的「三个人分五万」里的另外两人是谁，还不确定（11-13 芯动 session 盘点）。

## 五、已排除（不是真人，或者和用户无关）

- 王老师、杨老师、晴晴、一鸣、老赵等：Ear 合成数据里的角色。
- 刘老师：课程材料。罗薇老师：音乐剧社团文档。
- Diyi Yang：UGVR 申请的目标教授，不是身边的人（见 yyj.md 和 outreach）。

## 待问（下次合适时问用户，问完删掉对应行）
- 芯动计划：「三人分五万」是哪三人，五万是劳务报酬还是采购经费。

用户 11-02：没有严格意义上的导师。下面几条「暂时不重要」，不要主动问，除非这些人开始频繁出现：
- euxcet / Chengchi Zhou、shenxing、chengsx21（octopus）是谁。
- NatureCalls 的 HPZ07-end、Songyf24 叫什么。
- BIGfeiyu-friend 是谁。

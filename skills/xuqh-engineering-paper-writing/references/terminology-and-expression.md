# 专业术语与学术表达：从证据到用语

供新手逐步学习、熟手按功能快速调用。本文件自包含；不依赖私人目录、聊天记录或未发表原稿。配套`terminology-core.tsv`有47条精选条目，其中39条来自公开论文，8条为明确标注的匿名教学释义。术语不是研究结论，例句也不能替代数据。

## 调用标签

- 新手：按“先解释物理意义 → 明确指标定义 → 找到同方向原文 → 改写 → 核对边界”的顺序。
- 熟手：使用`[TERM]`、`[PROBLEM]`、`[GAP]`、`[METHOD]`、`[RESULT]`、`[MECHANISM]`、`[COMPARE]`、`[LIMIT]`、`[TRANSITION]`、`[RESPONSE]`定位所需段落。每次只取当前领域和功能相关的2–4条。
- 跨领域：先重建缩写表。CCM在相变热管理中可指close-contact melting，在燃料电池中可指catalyst-coated membrane。

## [TERM] 先解释物理意义，再选择英文

不要把中文词交给翻译器后直接全文替换。先确认对象是性质、通量、速率、阻力、能量还是效率，并用单位检查。

| 要表达什么 | 常用英文与物理意义 | 何时可用；必须防止的混淆 |
|---|---|---|
| 导热系数 | thermal conductivity；单位W/(m·K)，联系热流密度与温度梯度 | 材料物性；不能换成heat-transfer coefficient |
| 总传热系数 | overall heat transfer coefficient；单位W/(m²·K)，按指定换热面积和总温差定义 | 换热器设计；面积与温差基准要一致 [P32 p6 Eq.(19)] |
| 热量/热功率/热流密度 | heat或thermal energy [J]；heat-transfer rate/heat duty [W]；heat flux [W/m²] | 名字、符号、单位成套；Q不自动表示J，需看定义 |
| 总热阻/面积归一化热阻 | ΔT/Q [K/W]；ΔT/q [K·m²/W] | 两者相差面积；公开CCM例子使用后者 [P34 p6 Eq.(5)] |
| 动力黏度/运动黏度 | dynamic viscosity [Pa·s]；kinematic viscosity [m²/s] | 非牛顿材料还需给剪切速率范围，不能只有一个常数 |
| 供热储能效率/往返效率 | useful heat output/electric input；electricity recovered/electricity charged | 都可用百分比，但服务和分子不同；有外部余热或燃料时单列全部输入边界 [P16 p8；P33 p3] |
| 能量效率/火用效率 | energy efficiency评价数量转换；exergy efficiency进一步考虑能质与环境参考态 | 多产品系统必须分别列输入输出和基准态；不能为避免重复而换词 [P33 p3] |
| 压降 | pressure drop；指定两截面的压力差 [Pa] | 负表压变得更负不等于压力数值升高；静压和总压分别比较 |
| 过热度 | superheat；相对于明确相变温度的温差 | 温差百分比不能直接当摄氏温度百分比；始终给参考温度 |

一个具体的定义检查：[P34 p6]中的有效传热系数以热源温度减初始温度定义，面积归一化热阻却以热源温度减熔点定义。因此，两者不能直接互为倒数。应学习“把参考温度写明”，不能只记住某个指标名称。

新建或校准术语卡时，按实际相关性补充中文物理含义、英文术语、符号、单位、定义式、统计域/参考态、适用条件、易混概念和来源定位；只补当前判断需要的字段。局部润色或卡库已有词不必重复填表，先核对一两项关键判断，例如含义是否准确、单位与分母是否一致；只有发现歧义或定义冲突时，再补查相关字段。熟手可直接按标签或精选表核对；新稿中符号、域与分母的定义仍以本研究为准。

## 怎样建立自己的专业语言库

1. 从同方向、同方法、同研究尺度的论文入手；优先读与当前工作最接近的模型、指标定义和结果讨论。不能因为期刊层级高就跨物理过程套词。
2. 先精读3–5篇建立候选表；出现多种定义或用语冲突时扩到10–20篇，比较哪个定义与本研究一致。数量不能代替逐条定位。
3. 对每个候选表达记录“短原句/片段—它完成的写作功能—支撑它的证据—适用边界—自己的抽象结构”。页码按PDF物理页或明确印刷页记录，不混用。
4. 文献gap要更新到写作时点；过去论文写的“still needed”不是当前仍无研究的证明。若尚未核查，先用“本文需要解决的问题”描述，勿声称无人研究。
5. 源论文也可能有错词、量纲错误、条件矛盾或夸张措辞。遇到冲突先停用该条，回查方程、图表与正文；不能因为已发表就收为推荐。
6. 原句只用于理解和追溯。写入新稿的是按自己的证据重建的表达；不得保留原论文数字、样品、条件或没有证据的因果判断。

## [PROBLEM]—[RESPONSE] 按功能改写

以下全部是教学构造。方括号必须换成自己的真实对象、证据与范围；示例本身不宣告任何研究结果。公开例子只展示其组织功能，书目见文末。

| 标签 | 要完成的任务 | 可复用的教学结构 | 需要什么证据/何时降级措辞 |
|---|---|---|---|
| [PROBLEM] 问题 | 从应用约束收敛到可研究的物理问题 | `[Application] requires [response] under [condition], but the coupling between [process A] and [process B] remains unresolved.` | 应用要求和具体瓶颈有依据；unresolved不能替代文献检索 |
| [GAP] 缺口 | 说明已有策略能解决什么、还不能解释什么 | `Although [strategy] improves [property], its effect on [coupled process] must be resolved to predict [response].` | 单物性与综合响应之间有可验证的缺口；参考[P35 p2]的热–流变问题 |
| [METHOD] 方法 | 明确模型求解对象与过程 | `A [steady/transient] model of [system] solves [conservation laws] subject to [assumptions and boundaries].` | 方程、物性、边界、求解过程实际存在；不等于已做实验验证 |
| [METHOD] 依赖链 | 说明多个模型如何传递信息 | `[Model A] determines [input]; [model B] resolves [local process]; [check] evaluates [response].` | 必须有实际输入输出传递；只同时用了两款软件不叫coupled；参考[P28 p3] |
| [RESULT] 定量结果 | 把值、工况、基准放在同一句 | `At [condition], [metric] changes from [baseline] to [value], corresponding to [defined change].` | 数据、单位、误差和百分比分母完整；不写孤立“提高x%” |
| [RESULT] 验证 | 用覆盖范围与偏差表达模型能力 | `The maximum relative deviation in [quantity] from [reference] is [value] over [range].` | 偏差定义、参考数据、工况范围已核对；不要写fully validated |
| [MECHANISM] 中介过程 | 把控制变量与响应连接起来 | `Increasing [control] reduces [intermediate resistance/length], thereby changing [response].` | 有中介量的测试、场分布或尺度分析；仅相关时改用is consistent with/may reflect |
| [MECHANISM] 权衡 | 解释某性质更好但整体表现未更好 | `Although [property A] improves, [opposing process] limits [response] under [condition].` | 先呈现冲突响应，再给局部场或贡献分解；参考[P35 p14] |
| [COMPARE] 公平比较 | 明确哪些变量相同、哪些改变 | `Both cases share [controlled variables] and differ in [tested factor].` | 若同时改变多个因素，写joint influence，不能宣称分离了单因素贡献 |
| [COMPARE] 服务对齐 | 对照相同产出/规模和输入边界 | `The systems are compared at the same [service and scale] with [shared boundary].` | 电/热服务、时长、材料量、成本基年等均检查；参考[P16 p3] |
| [LIMIT] 模型边界 | 公开简化和它不支持的推断 | `[Component] is represented as [model level]; [unresolved process] is therefore excluded.` | 零维热力学模型不能证明局部传热、反应前沿或动力学；参考[P16 p4] |
| [LIMIT] 限定结论 | 将结论附着到测试范围 | `Under the investigated [conditions], [conclusion]; extension to [untested case] remains unresolved.` | 未覆盖的条件不能靠“可能适用”补齐 |
| [TRANSITION] 证据衔接 | 由当前结果引出下一步需要验证的联系 | `[Structural result] motivates a [transport/reaction] analysis of whether [quantity] translates into [response].` | 结构优势与传热/反应收益需分别验证；不要预告尚未得到的结论 |
| [RESPONSE] 说明已改 | 精确对应真实修改位置 | `The revised manuscript clarifies [actual change] in Section [x] and acknowledges [limitation] in Section [y].` | 匿名教学构造；发出回复前逐项对照当前正文。保留、改写、新增分开说 |
| [RESPONSE] 保留不确定性 | 区分现有证据与未测机制 | `Available [evidence] suggests [direction], but cannot determine [untested response]; the contribution remains uncertain.` | 匿名教学构造；不能假称增加了实验或已解决模型误差 |

因果动词按证据选择：

- `is governed by / is limited by`：需要能够识别主导/限制过程的定量、控制或机制证据。
- `results from / can be attributed to`：需要能支撑该因果解释的中介量或对照；不是语气更高级的普通连接词。
- `is consistent with / may reflect`：用于与机制一致但尚不足以排除替代解释的结果。

不要用significant、excellent、obvious、synergistic、robust、unprecedented代替数值、误差、贡献分解和边界。“首次”“最优”“普适”“完全验证”需要相应全面证据；找不到证据就删除或缩小范围。

## 少量公开短片段：学习功能，不复制结论

| 原文短片段 | 公开来源 | 学什么 |
|---|---|---|
| “compared on the same plant scale” | [P16] PDF p3 §2.1 | 先说明比较基准；还须核对服务、边界与成本年份 |
| “kinetics are not taken into account” | [P16] PDF p4 §2.2，原文对象为碳酸化与煅烧 | 明确模型未解析的过程，防止以系统热力学结论代替动力学验证 |
| “thermal conductivity alone cannot determine temperature control performance” | [P35] PDF p14 §4.2.2 | 从单一物性转向流动和传热的耦合响应；具体结论只属于该研究条件 |
| “round-trip efficiency versus LCOE trade-off” | [P33] PDF p3 Optimization method | 将效率与成本分别定义，再讨论权衡，不能用一个泛称performance掩盖两者 |

短片段仅来自公开PDF。未发表工作只贡献匿名教学构造，不包含原稿句子、真实数据、私人定位或修改历史。语言学习不授予把原论文结论移植给自己研究的权利；若新稿引用某论文支撑事实，必须另核对事实本身与该论文是否对应。

## 匿名教学例：结构指标不等于整体性能

设两个多孔催化结构仅在颗粒位置上不同。一个结构可能提供更多直接邻接孔隙的几何面积，但若新增界面位于供给不足区域，积分反应速率不一定更高。该示例为构造，不引用任何实际项目数值或结论。

新手先区分：几何面积m²、单位材料质量面积m²/g、局部反应通量mol/(m²·s)、指定区域总反应速率mol/s。若用参考浓度mol/m³去除总反应速率，结果m³/s仍有量纲。需说明统计域、材料质量分母、供给方向与边界；不能统称电池功率或完整电化学性能。

熟手可用`[COMPARE] + [MECHANISM] + [LIMIT]`：先列共同约束，再以局部供给解释积分响应，最后把结论限制在计算区域与边界内。需要电池层面结论时，补充相应电化学、热、水管理或整电池验证。

## 交稿前最小检查

- 同一概念是否始终使用同一术语；缩写是否跨域重定义？
- 指标分子、分母、单位、面积/体积基准、参考温度与统计域是否一致？
- 每个数字、机制判断和比较是否对应自己的证据与工况？
- 是否把归一化误写为无量纲，把局部积分误写为整体性能？
- 是否用有限指标误差宣称完全验证，用单一物性宣称整体最优？
- 返修中的“新增、改写、澄清、保留”是否与当前稿和真实完成工作一致？

## 公开书目与定位

以下DOI均从本地公开论文PDF中核对；未声称已在线检查链接可达性。页码是PDF物理页。期刊、作者或年代差异可能影响措辞，不能把单篇合作论文中的习惯当成某一位作者的固定风格。

- **P16**. *A calcium looping system powered by renewable electricity for long-term thermochemical energy storage, residential heat supply and carbon capture*. Energy Conversion and Management **276** (2023), 116592. [DOI: 10.1016/j.enconman.2022.116592](https://doi.org/10.1016/j.enconman.2022.116592). 术语与边界：PDF pp2–4、8。
- **P28**. *Multi-level optimization of thermal management systems with compact large-bend configurations in hybrid electric vehicles*. International Communications in Heat and Mass Transfer **164** (2025), 108901. [DOI: 10.1016/j.icheatmasstransfer.2025.108901](https://doi.org/10.1016/j.icheatmasstransfer.2025.108901). 模型链：p3；阻力/气流术语：pp4–6。个别原文单位需独立核对，不作规范照搬。
- **P32**. *Hybrid thermochemical Carnot battery with calcium looping, methane dry reforming, and supercritical carbon dioxide cycle: thermodynamic and techno-economic optimization*. EES Batteries (2026). [DOI: 10.1039/d5eb00225g](https://doi.org/10.1039/d5eb00225g). 摘要：p1；建模边界/换热量纲：pp5–6。
- **P33**. *Carnot battery with thermochemical energy storage and supercritical CO2 power cycle: Thermodynamic and techno-economic characteristics*. The Innovation Energy **3**(2) (2026), 100163. [DOI: 10.59717/j.xinn-energy.2026.100163](https://doi.org/10.59717/j.xinn-energy.2026.100163). 指标功能定义与优化：p3；实际分子分母仍需查目标稿及配套定义，不能只靠名称。
- **P34**. *Experimental study on micro-fin array shapes for enhanced close-contact melting of phase change materials*. Applied Thermal Engineering **301** (2026), 131602. [DOI: 10.1016/j.applthermaleng.2026.131602](https://doi.org/10.1016/j.applthermaleng.2026.131602). 指标定义：p6；机制：pp9–10。本文某结果的压力条件在p10与p1/p15存在小数位差异，引用该数值前需核对，不作为本模块示例数字。
- **P35**. *Numerical and experimental investigation of the thermal–rheological trade-off in close-contact melting of graphene-based composite phase change materials*. Energy **362** (2026), 142250. [DOI: 10.1016/j.energy.2026.142250](https://doi.org/10.1016/j.energy.2026.142250). 流变与假设：pp5–8；导热–排液权衡：p14。原文结论中的fully validated不作为推荐措辞。

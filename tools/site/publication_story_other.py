"""Research narratives for the five companion papers, grounded in their manuscripts."""
def B(ko,en):return {'ko':ko,'en':en}
def block(ko,en,kbody,ebody,ref):return {'title':B(ko,en),'body':B(kbody,ebody),'ref':ref}
D={}

D['velocity-reuse']={
'problem':[
block('문제 제기: 반복적인 action generation이 inference bottleneck이 된다','Problem: iterative action generation becomes an inference bottleneck',
'Flow Matching 기반 VLA는 image·language conditioning이 끝난 뒤에도 여러 Euler step에서 action generator를 반복 호출해 action chunk를 만듭니다. 이 반복 연산이 실제 배포에서 latency를 키우므로, backbone을 줄이는 것과 별개로 action generator 자체의 호출을 줄일 수 있는지를 문제로 잡았습니다.',
'Flow-matching VLAs still evaluate the action generator over multiple Euler steps after image-language conditioning. Because these repeated evaluations contribute substantial deployment latency, the paper asks whether action-generator calls can be reduced independently of backbone acceleration.','§1'),
block('관찰: 생성 step이 달라도 output velocity가 거의 변하지 않는다','Observation: output velocity changes very little across generation steps',
'Training path가 직선이라는 사실만으로 inference 중 velocity가 안정적이라고 가정하지 않았습니다. 먼저 실제 rollout에서 인접 step의 cosine similarity와 norm ratio를 측정했습니다. π0.5는 LIBERO 네 suite 평균에서 adjacent cosine 0.9997, norm ratio 0.9984였고 GR00T-N1.7에서도 높은 유사성을 확인했습니다.',
'A straight training path does not by itself guarantee stable velocity during inference. The paper therefore measures adjacent-step cosine similarity and norm ratio on rollouts first. Across four LIBERO suites, π0.5 reaches 0.9997 adjacent cosine similarity and 0.9984 norm ratio on average, with similarly high stability for GR00T-N1.7.','§2.2 · Table 1'),
block('가설: internal feature가 아니라 최종 output을 재사용해도 되는가?','Hypothesis: can the final output be reused instead of internal features?',
'Architecture-specific intermediate feature를 저장하는 대신, 반복 계산의 최종 output인 velocity 자체를 재사용하는 방향을 택했습니다. 이렇게 하면 모델 내부 구조를 바꾸지 않고도 동일한 pretrained policy에서 재사용 간격 k만으로 계산량과 성공률의 trade-off를 확인할 수 있습니다.',
'Rather than caching architecture-specific intermediate features, the paper reuses the generator’s final velocity output. This keeps the pretrained policy and internal architecture unchanged, leaving the reuse interval k as the main variable for studying the compute–success trade-off.','§1–2.3')],
'method':[
block('왜 주기적 refresh만 바꾸고 Euler update는 그대로 두었는가?','Why change only refresh frequency while retaining Euler updates?',
'재사용 효과만 분리하기 위해 기존 policy와 Euler state update는 유지하고 velocity를 새로 계산하는 시점만 바꿨습니다. 첫 step과 매 k step에서 action generator를 호출하고, 중간 step에서는 직전 velocity로 state를 계속 갱신합니다. N=10, k=5라면 forward pass는 10회에서 2회로 줄지만 generation schedule의 중간 update는 유지됩니다.',
'To isolate reuse itself, the pretrained policy and Euler state updates remain unchanged; only velocity-refresh times change. The action generator is evaluated at the first step and every k steps, while intermediate states continue to update with the held velocity. With N=10 and k=5, forward passes fall from ten to two without removing intermediate solver updates.','§2.3 · Figure 1'),
block('왜 Paired와 Random을 나누었는가?','Why separate Paired and Random protocols?',
'k의 영향과 initial noise 차이를 섞지 않기 위해 Paired에서는 비교 조건의 환경 reset과 초기 action noise를 맞췄습니다. Random에서는 제어 step마다 새 noise를 추출해 실제 추론에 가까운 조건을 확인했습니다. 성공률과 latency를 별도로 측정해 호출 수 감소가 실제 시간 단축과 같은 의미는 아니라는 점도 분리했습니다.',
'Paired evaluation matches environment resets and initial action noise so the effect of k is not confounded by sampling differences. Random evaluation draws fresh noise at each control step to reflect ordinary inference. Task success and latency are measured separately because fewer evaluations do not translate one-to-one into wall-clock speedup.','§3.1–3.3 · Table 2, Table 4')],
'results_intro':B('먼저 “velocity가 실제로 안정적인가?”를 확인하고, 그 관찰을 reuse interval k로 옮겼을 때 성공률과 latency가 어떻게 달라지는지를 순서대로 검증했습니다.','The experiments first verify whether velocity is actually stable, then test how success and latency change when that observation is turned into a reuse interval k.'),
'evidence':[
block('관찰이 실제 output에서 반복되는가?','Does the stability observation persist in actual outputs?',
'π0.5의 adjacent cosine similarity는 0.9997, GR00T-N1.7은 0.9963이었고 adjacent norm ratio도 각각 0.9984, 0.9971이었습니다. 따라서 “인접 step의 output이 유사하다”는 가정이 아니라 측정된 관찰에서 reuse 실험을 시작했습니다.',
'Adjacent cosine similarity is 0.9997 for π0.5 and 0.9963 for GR00T-N1.7; adjacent norm ratios are 0.9984 and 0.9971. Reuse therefore starts from a measured output-stability observation rather than an assumed one.','Table 1'),
block('성공률을 유지하면서 실제 latency도 줄어드는가?','Does measured latency fall while task success remains near baseline?',
'π0.5의 k=10에서 Paired 평균 성공률은 96.4%(k=1: 96.7%), Random은 96.8%(k=1: 96.8%)였고 E2E latency는 330.5 ms에서 118.4 ms로 2.79× 단축됐습니다. GR00T-N1.7의 k=4에서는 평균 성공률 95.8%(k=1: 97.0%), E2E 2.19×를 보고했습니다.',
'For π0.5 at k=10, Paired mean success is 96.4% versus 96.7% at k=1, Random is 96.8% versus 96.8%, and E2E latency falls from 330.5 ms to 118.4 ms (2.79×). GR00T-N1.7 at k=4 reports 95.8% mean success versus 97.0% at k=1 and 2.19× E2E speedup.','Table 2, Table 3, Table 4')],
'caption':B('그림 1. 속도 재사용 방법(π0.5). τ=0에서 초기 velocity를 계산하고 τ가 kδ의 배수일 때만 다시 계산합니다. 중간 step에서도 Euler update는 계속 수행하며 가장 최근 velocity를 재사용합니다.','Figure 1. Velocity reuse for π0.5. Compute velocity at τ=0 and refresh it only when τ is a multiple of kδ. Euler updates continue at intermediate steps using the most recent velocity.'),
'metric_refs':['Table 4 (π0.5 · k=10)','Table 4 (π0.5 · k=10)','Table 2 (π0.5 · LIBERO)']}

D['navila-patch']={
'problem':[
block('문제 제기: 시각 모델의 취약성이 실제 navigation action으로 이어질 수 있다','Problem: visual vulnerability can propagate into navigation actions',
'VLN은 관찰 영상과 언어 지시를 행동으로 연결하므로 시각 입력의 오류가 단순한 인식 실패에 그치지 않고 잘못된 이동과 경로 실패로 이어질 수 있습니다. 특히 실제 환경에 부착 가능한 adversarial patch를 자연어 action 기반 VLA가 어떻게 받아들이는지를 주행 성능으로 평가하는 문제로 정의했습니다.',
'VLN turns visual observations and instructions into actions, so corrupted visual input can propagate beyond recognition error into wrong movement and route failure. The paper studies how a natural-language-action VLA responds to a physically placeable adversarial patch and evaluates the effect through navigation performance.','§1'),
block('왜 pixel-level 정답이 아니라 natural-language action을 공격 목표로 삼았는가?','Why target natural-language actions rather than a pixel-level label?',
'피해자 모델의 출력은 “The next action is …” 형태의 문장이고 keyword parsing을 거쳐 simulator command가 됩니다. 따라서 문장 형식을 깨뜨리는 것보다 parser가 받아들이는 형식을 유지하면서 행동 유형·방향·제어 값을 잘못 생성하게 만드는 것이 navigation 실패와 더 직접적으로 연결됩니다.',
'The victim model outputs sentences such as “The next action is …”, which are converted to simulator commands through keyword parsing. Preserving a parseable format while changing action type, direction, or control value is therefore more directly tied to navigation failure than simply corrupting text form.','§2.1'),
block('왜 adversarial patch인가?','Why an adversarial patch?',
'Imperceptible perturbation과 달리 patch는 환경에 물리적으로 노출될 수 있고 이동 중 여러 시점에서 반복 관찰될 수 있습니다. 그래서 단일 frame 분류 성능이 아니라, patch가 경로 전체의 SR·SPL·NE에 어떤 영향을 주는지 분석했습니다.',
'Unlike imperceptible perturbations, a patch can be physically visible in the environment and repeatedly observed from different viewpoints during navigation. The study therefore measures route-level NE, SR, and SPL rather than only a single-frame prediction change.','§1, §3')],
'method':[
block('Policy는 고정하고 patch만 최적화','Keep the policy fixed and optimize only the patch',
'현재 관찰 1장과 과거 관찰 7장에 동일한 patch를 적용하고, model parameter는 고정한 채 adversarial target action에 대한 loss로 patch만 업데이트합니다. 이렇게 policy fine-tuning과 입력 공격의 효과를 분리했습니다.',
'Apply the same patch to the current observation and seven historical observations, keep model parameters frozen, and update only the patch against the adversarial target action. This isolates the input attack from policy fine-tuning.','§2.2'),
block('왜 EOT와 우상단 위치를 사용했는가?','Why use EOT and an upper-right placement?',
'로봇이 이동하면 patch의 시점과 형태가 달라지므로 rotation·shear를 확률적으로 적용하는 EOT를 사용했습니다. Patch는 장면 구조물을 최대한 가리지 않도록 우상단에 두어, 단순 occlusion보다 학습된 교란의 영향을 분리하려고 했습니다.',
'As the robot moves, patch viewpoint and geometry change, so EOT applies random rotation and shear. The patch is placed in the upper-right to avoid covering major scene structure, helping separate learned perturbation effects from simple occlusion.','§2.2'),
block('왜 changed token과 Stop을 다르게 처리했는가?','Why treat changed tokens and Stop differently?',
'공통 문장 형식과 정답 행동과 동일한 token은 loss에서 제외하고 target action으로 바뀐 token에 학습 신호를 집중했습니다. Stop은 원래 별도 문장 포맷으로 학습되어 “The next action is stop”을 직접 정답으로 주기 어렵기 때문에 move·turn 확률을 억제하는 unlikelihood loss를 추가했습니다.',
'Shared sentence structure and unchanged tokens are excluded from the loss so the signal focuses on tokens that define the adversarial target. Because Stop was trained with a different response format, an additional unlikelihood loss suppresses move and turn probabilities instead of treating “The next action is stop” as an ordinary target.','§2.2 · Equations 1–3')],
'results_intro':B('실험은 공격 효과를 하나의 숫자로만 보여주지 않고, “학습된 patch인가”, “얼마나 큰가”, “얼마나 자주 보이는가”를 각각 분리해 주행 성능 변화를 확인합니다.','The experiments separate three questions—whether the patch is learned, how large it is, and how often it is observed—rather than collapsing attack behavior into one number.'),
'evidence':[
block('학습된 patch가 단순 가림·noise보다 강한가?','Is the learned patch stronger than occlusion or unoptimized noise?',
'R2R-CE에서 baseline SR 54.0%는 Black Patch 51.2%, Gaussian Init. 51.0%로 낮아졌지만 학습된 patch에서는 38.6%까지 하락했습니다. RxR-CE에서도 52.1%에서 39.8%로 줄었습니다. 학습된 target action이 단순한 시각 차단보다 큰 영향을 주는지 비교한 실험입니다.',
'On R2R-CE, baseline SR 54.0% falls to 51.2% with a Black Patch and 51.0% with Gaussian initialization, but to 38.6% with the learned patch. RxR-CE drops from 52.1% to 39.8%. This comparison separates learned target-action effects from simple visual obstruction.','Table 1'),
block('왜 patch 크기를 따로 비교했는가?','Why evaluate patch size separately?',
'입력 384×384에서 38×38(10%)과 57×57(15%)을 비교했습니다. R2R-CE SR은 46.8%와 38.6%, RxR-CE SR은 46.8%와 39.8%였습니다. 크기가 커질수록 공격 효과는 커지지만 탐지 가능성도 높아진다는 trade-off를 보기 위한 실험입니다.',
'The study compares 38×38 (10%) and 57×57 (15%) patches on 384×384 input. R2R-CE SR is 46.8% and 38.6%, while RxR-CE SR is 46.8% and 39.8%. The size study exposes the trade-off between attack effect and detectability.','§3.3 · Table 2'),
block('초기 몇 step만 보여도 경로에 영향이 남는가?','Does brief early exposure leave a route-level effect?',
'초기 10회의 action generation에서만 patch에 노출한 조건에서도 R2R-CE SR은 45.8%, RxR-CE는 46.3%였습니다. 매 frame에 항상 보이지 않아도 초기의 잘못된 행동이 이후 경로에 누적될 수 있는지를 확인한 비교입니다.',
'Even when the patch is visible only during the first ten action-generation steps, SR is 45.8% on R2R-CE and 46.3% on RxR-CE. This tests whether early wrong actions can continue to influence the later route even without persistent exposure.','§3.4 · Table 3')],
'caption':B('그림 1. 적대적 패치 생성과 적대적 공격 수행 과정','Figure 1. Adversarial patch generation and attack procedure.'),
'metric_refs':['Table 1 (R2R-CE)','Table 1 (RxR-CE)','§3.3 · Figure 5']}

D['lift3d-film']={
'problem':[
block('문제 제기: 3D geometry만으로는 과업의 목표를 모두 표현하기 어렵다','Problem: 3D geometry alone does not fully specify task intent',
'로봇 제어에는 공간 이해가 필요하지만, 같은 객체와 공간 구조에서도 어떤 동작을 해야 하는지는 과업의 목표에 따라 달라집니다. Lift3D는 2D foundation model이 point cloud를 처리하도록 3D representation을 학습하지만, task intent를 명시적으로 넣는 구조는 아닙니다.',
'Robot control requires spatial understanding, yet the desired interaction can differ even for the same geometry. Lift3D teaches a 2D foundation model to process point clouds and learn 3D representations, but does not explicitly encode task intent in that representation.','§1–2.2'),
block('가설: language condition을 3D representation 자체에 반영하면 일반화에 도움이 되는가?','Hypothesis: can language conditioning improve generalization by modulating the 3D representation itself?',
'시각 정보만으로 알기 어려운 과업의 목표를 language instruction으로 제공하고, policy head 뒤가 아니라 3D feature가 만들어지는 과정에 반영하는 방향을 선택했습니다. “어디에 있는가”뿐 아니라 “무엇을 해야 하는가”를 representation 단계에서 함께 표현하려는 설계입니다.',
'The paper provides task intent through language and injects it while the 3D feature is being formed rather than only after feature extraction. The goal is to represent not only where things are, but what interaction the task requires.','§1, §2.3'),
block('왜 두 번째 Lift3D stage에 넣었는가?','Why insert language conditioning in Lift3D’s second stage?',
'Lift3D의 첫 단계는 masked image에서 depth를 복원해 implicit 3D representation을 학습하고, 두 번째 단계는 point cloud와 3D positional embedding을 직접 처리해 action prediction feature를 만듭니다. 그래서 실제 explicit 3D feature를 만드는 두 번째 stage를 language conditioning 지점으로 선택했습니다.',
'Lift3D’s first stage reconstructs depth from masked images to learn implicit 3D structure, whereas the second stage directly processes point clouds and 3D positional embeddings to produce features for action prediction. Language conditioning is therefore inserted in the second, explicit-3D stage.','§2.1–2.3')],
'method':[
block('왜 FiLM인가?','Why FiLM?',
'CLIP text encoder의 task description embedding을 MLP 기반 FiLM generator에 넣어 γ와 β를 만들고 H′ = γ ⊙ H + β로 visual hidden state를 조정합니다. 기존 feature를 버리지 않고 task에 따라 scale·shift할 수 있어 language와 visual representation을 직접 연결할 수 있습니다.',
'A task-description embedding from the CLIP text encoder is mapped by an MLP FiLM generator to γ and β, then applied as H′ = γ ⊙ H + β. This directly conditions the visual representation through task-dependent scaling and shifting without replacing the underlying feature pipeline.','§2.3 · Equations 1–2'),
block('왜 매 세 번째 CLIP-ViT block에 적용했는가?','Why apply FiLM every third CLIP-ViT block?',
'원문은 기존 3D representation learning의 안정성을 고려해 FiLM을 모든 block이 아니라 매 세 번째 CLIP-ViT block에 적용했다고 설명합니다. 즉 강한 구조 변경보다 기존 Lift3D 표현을 유지하면서 language signal을 주기적으로 주입하는 선택입니다.',
'The paper states that FiLM is applied to every third CLIP-ViT block to preserve the stability of the existing 3D representation learning process. The design therefore injects language periodically rather than replacing the Lift3D feature pipeline.','§2.3'),
block('왜 지시문을 다시 구체화했는가?','Why revisit instruction specificity?',
'기본 instruction에서 8개 중 7개 과업은 개선됐지만 sweep into는 74%에서 72%로 떨어졌습니다. 과업 목표가 충분히 구체적이지 않다는 가설을 세우고, 객체·동작·공간 관계를 더 명시한 instruction으로 성능이 낮았던 네 과업을 추가 평가했습니다.',
'Basic instructions improve seven of eight tasks, but sweep into falls from 74% to 72%. The paper hypothesizes that the task description underspecifies the goal and reevaluates four weaker tasks with instructions that make the object, action, and spatial relation more explicit.','§3 · Table 1, Table 2')],
'results_intro':B('결과는 “language를 넣었더니 좋아졌다”에서 끝나지 않고, 기본 instruction에서의 전체 경향과 성능이 떨어진 과업을 다시 정의해 확인한 상세 instruction 실험까지 이어집니다.','The results do not stop at “language helps”: they show the overall effect of basic instructions and then revisit underperforming tasks with more explicit instructions.'),
'evidence':[
block('기본 language condition은 전체적으로 도움이 되는가?','Does basic language conditioning help overall?',
'8개 Meta-World 과업 평균은 Lift3D 71.0%에서 Ours 76.3%로 5.3 pp 높아졌고 7개 과업에서 성공률이 상승했습니다. 다만 sweep into는 74%에서 72%로 떨어져, language condition의 내용까지 살펴볼 이유가 생겼습니다.',
'Across eight Meta-World tasks, mean success rises from 71.0% for Lift3D to 76.3% for Ours, with improvements on seven tasks. Sweep into, however, falls from 74% to 72%, motivating a closer look at the content of the language condition.','Table 1'),
block('상세 instruction이 실패 가설을 설명하는가?','Do detailed instructions support the failure hypothesis?',
'Sweep into의 “Sweep a puck into a hole.”을 “Grasp the puck and sweep it into the hole in front of it.”으로 구체화했을 때 성공률은 82%였습니다. Hand insert·push wall·shelf place에서도 상세 instruction이 기본 instruction보다 높았습니다. 이 후속 실험은 language의 존재보다 instruction의 정보량이 중요하다는 점을 확인합니다.',
'For sweep into, replacing “Sweep a puck into a hole.” with “Grasp the puck and sweep it into the hole in front of it.” raises success to 82%. Detailed instructions also improve hand insert, push wall, and shelf place relative to their basic instructions, supporting the importance of instruction content rather than language presence alone.','Table 2')],
'caption':B('그림 1. 언어 조건 기반 3D 표현 학습 구조','Figure 1. Language-conditioned 3D representation learning architecture.'),
'metric_refs':['Table 1 (Meta-World)','Table 1 (Mean success rate)','Table 1 (Basic instructions)']}

D['act-cbam']={
'problem':[
block('문제 제기: 더 많은 시연보다 현재 시각 정보를 더 잘 쓰는 방법이 필요한가?','Problem: can the policy use existing visual information better instead of collecting more demonstrations?',
'ACT는 expert demonstration으로 학습하고 visual encoder도 fine-tuning하지만, 정밀한 insertion에서는 여전히 낮은 성공률을 보였습니다. 그래서 데이터를 더 추가하기 전에, 현재 관찰 영상에서 제어에 중요한 feature를 충분히 활용하고 있는지를 문제로 잡았습니다.',
'ACT learns from expert demonstrations and fine-tunes its visual encoder, yet still shows limited success on precise insertion. Before adding more demonstrations, the paper asks whether the policy is making effective use of control-relevant visual features already present in the observations.','§1'),
block('관찰: 모든 channel과 spatial location이 행동 예측에 똑같이 중요하지 않다','Observation: not every channel and spatial location is equally useful for action prediction',
'정밀 조작에서는 객체의 종류뿐 아니라 위치 관계가 중요합니다. 따라서 visual feature에서 “무엇”이 중요한지와 “어디”가 중요한지를 분리해 강조하는 channel attention과 spatial attention을 결합하는 방향을 선택했습니다.',
'Precise manipulation depends on both feature identity and spatial relation. The design therefore combines channel attention and spatial attention to separately emphasize what matters and where it matters in the visual feature map.','§1–2'),
block('두 번째 문제: 성능을 위해 visual encoder 전체를 다시 학습해야 하는가?','Second question: must the whole visual encoder be retrained to improve control?',
'기존 ACT는 ResNet18 visual encoder를 fine-tuning합니다. 본 연구는 pretrained representation을 유지하면서 학습 가능한 parameter를 줄이기 위해 encoder를 동결하고 소규모 CBAM만 학습하는 adapter 방식을 선택했습니다.',
'Baseline ACT fine-tunes the ResNet18 visual encoder. To preserve pretrained representations while reducing trainable parameters, the paper freezes the visual encoder and trains only the compact CBAM module as an adapter.','§1–2')],
'method':[
block('왜 Channel → Spatial 순서인가?','Why Channel → Spatial attention?',
'CBAM은 먼저 channel attention으로 feature map의 “무엇”을 강조한 뒤, 갱신된 feature에 spatial attention을 적용해 “어디”에 집중할지를 조정합니다. 두 attention을 순차적으로 사용한 구조를 ACT visual encoder 뒤에 연결했습니다.',
'CBAM first applies channel attention to emphasize what is important in the feature map, then applies spatial attention to the updated feature to determine where to focus. This sequential module is attached to ACT’s visual encoder.','§2 · Equations 1–3'),
block('왜 adapter 방식으로 검증했는가?','Why validate it as an adapter?',
'ResNet18은 동결하고 CBAM만 추가 학습하되 policy의 나머지 구성은 기존 학습을 유지합니다. 따라서 성능 향상뿐 아니라 전체 trainable parameter 수가 실제로 줄어드는지도 함께 비교했습니다. “attention을 추가했다”와 “효율적으로 개선했다”를 동시에 검증하려는 설계입니다.',
'ResNet18 is frozen and only CBAM is added as the trainable visual adapter, while the rest of the policy follows the existing training setup. The experiments therefore compare both task success and total trainable parameters, testing efficiency as well as accuracy.','§2–3 · Table 1')],
'results_intro':B('실험은 CBAM 전체만 baseline과 비교하지 않고 Channel-only·Spatial-only를 함께 두어 각 설계 선택이 실제 control success에 어떤 영향을 주는지 분리합니다.','The experiments do not compare only full CBAM against baseline; channel-only and spatial-only variants isolate how each design choice affects control success.'),
'evidence':[
block('어떤 attention이 실제로 도움이 되었는가?','Which attention component actually helps?',
'Transfer Cube에서 ACT 93%, Channel-only 84%, Spatial-only 91%, CBAM 96%였고 Insertion에서는 55%, 52%, 60%, 61%였습니다. Channel만 추가하는 것으로는 개선되지 않았고, Spatial과 두 attention의 순차 결합이 더 나은 결과를 보였습니다.',
'On Transfer Cube, success is 93% for ACT, 84% for channel-only, 91% for spatial-only, and 96% for CBAM; on Insertion it is 55%, 52%, 60%, and 61%. Channel attention alone does not improve the baseline, while spatial attention and the sequential combination perform better.','Table 1'),
block('성능 향상이 parameter efficiency와 함께 나타나는가?','Does the gain come with parameter efficiency?',
'기준 ACT의 trainable parameter는 83.92M, adapter 구성은 72.79M입니다. CBAM은 두 과업에서 가장 높은 성공률을 내면서 학습 가능한 parameter를 11.13M 줄였습니다. 여기서 비교하는 값은 전체 모델 크기가 아니라 trainable parameter 수입니다.',
'Baseline ACT has 83.92M trainable parameters, while the adapter configurations have 72.79M. CBAM achieves the highest success on both tasks while reducing trainable parameters by 11.13M. These are trainable-parameter counts, not total model size.','Table 1')],
'caption':B('그림 1. 전체 구조도','Figure 1. Overall architecture.'),
'metric_refs':['Table 1 (Transfer Cube)','Table 1 (Insertion)','Table 1 (Trainable parameters)']}

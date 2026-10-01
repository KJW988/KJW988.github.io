"""Reasoning behind choices, grounded in each supplied manuscript (no invented experiments)."""
def pair(ko,en): return {'ko':ko,'en':en}
def item(ko,en,kbody,ebody,ref):return {'title':pair(ko,en),'body':pair(kbody,ebody),'ref':ref}
METHODS={
'velocity-reuse':[
item('왜 internal feature가 아니라 output velocity인가?','Why reuse output velocity rather than internal features?',
'기존 training-free 가속은 visual token이나 VLM 연산을 줄이거나 특정 architecture의 feature를 저장하는 경우가 많습니다. 이 연구는 반복 계산의 병목인 action generator에 직접 적용하면서 모델 내부 구조에 대한 의존성을 줄이기 위해 최종 output인 velocity를 선택했습니다. 학습 경로가 직선이라는 사실만으로 추론 trajectory가 직선인 것은 아니므로, 재사용에 앞서 인접 step의 cosine similarity와 norm ratio를 측정했습니다.',
'Existing training-free approaches often reduce visual-token or VLM computation, or cache architecture-specific features. Output velocity targets repeated action-generator evaluations while avoiding dependence on internal representations. A straight training path does not guarantee a straight inference trajectory, so adjacent-step cosine similarity and norm ratios are measured before testing reuse.','§1–2.2 · Table 1'),
item('왜 주기적인 refresh와 기존 Euler update를 유지했는가?','Why use periodic refreshes and retain Euler updates?',
'연산을 생략하는 효과를 분리하기 위해 pretrained policy와 Euler update는 유지하고 velocity를 계산하는 시점만 바꿨습니다. 첫 step과 매 k step에서 새 velocity를 계산하고 중간에는 직전 output을 사용합니다. N=10, k=5이면 action generator의 forward pass는 10회에서 2회가 됩니다. 추가 학습이나 별도 cache 판정 모델 없이 k에 따른 성공률·latency 변화를 비교하는 구성입니다.',
'To isolate the effect of skipped evaluations, the pretrained policy and Euler update remain unchanged; only the velocity-refresh times change. Evaluate at the first step and every k steps, reusing the latest output in between. With N=10 and k=5, AG forward passes fall from ten to two. This makes the success–latency trade-off observable without retraining or an additional cache-decision model.','§2.3 · Figure 1'),
item('왜 Paired와 Random 조건을 나누었는가?','Why separate Paired and Random evaluation?',
'초기 noise가 달라지면 k의 효과와 sampling 차이가 섞일 수 있습니다. Paired에서는 동일한 initial noise를 k별 비교에 사용해 이 변수를 통제하고, Random에서는 매 추론마다 새 noise를 사용해 배포와 가까운 조건을 확인했습니다. 두 조건의 성공률과 action generator·전체 모델 latency를 따로 보고했습니다.',
'Different initial-noise samples can confound the effect of k. Paired evaluation controls this variable by using matched initial noise across reuse intervals; Random evaluation draws fresh noise for each inference call to approximate deployment. Success under these protocols is reported separately, alongside action-generator and whole-model latency.','§3.1–3.3 · Table 2, Table 4')],
'star':[
item('왜 optical flow를 사고 판정 rule이 아닌 후보 단서로 쓰는가?','Why use optical flow as a candidate cue, not an accident rule?',
'CCTV의 appearance는 저조도·날씨·시점에 따라 모호해지고, 갑작스러운 움직임이 모두 사고인 것도 아닙니다. 그래서 MEMFOF에서 얻은 motion anomaly를 사고를 확정하는 규칙 대신 후보 시간 구간과 severity로 정리해 VLM에 전달했습니다. RGB만으로 놓치기 쉬운 움직임을 보조하되 사고 여부와 시점의 판단은 영상 맥락과 함께 수행하게 한 선택입니다.',
'CCTV appearance degrades with lighting, weather and viewpoint, but abrupt motion alone is not always an accident. Motion anomalies extracted with MEMFOF therefore become candidate windows and severity cues rather than hard accident triggers. They direct attention to motion that RGB appearance may obscure while leaving the prediction to the VLM in its video context.','§2.2 · Table 5'),
item('왜 사고 시점을 먼저 찾고 실제로 영상을 자르는가?','Why localize time first and actually trim the video?',
'사고 단서는 긴 영상의 짧고 국소적인 구간에 있습니다. 전체 영상에 예측 시점만 텍스트로 알려주면 무관한 frame은 그대로 남기 때문에, t̂를 먼저 찾고 그 주변 6초 clip을 위치·유형 추론에 공통으로 사용했습니다. Table 3에서 full video의 spatial score는 0.114, 시점 텍스트 추가는 0.095, trimmed video는 0.529였습니다. 이 비교는 이 설정에서 실제 입력 구간을 좁히는 선택을 뒷받침합니다.',
'Accident evidence occupies a brief, localized part of a longer video. Supplying the predicted time as text leaves irrelevant frames in the input, so STAR first estimates t̂ and shares a six-second crop between spatial and type prediction. Table 3 reports spatial scores of 0.114 for full video, 0.095 with time as text and 0.529 for a trimmed clip. This supports narrowing the input in the evaluated setting.','§2.1, §2.3, §3.2 · Table 3'),
item('왜 collision type에는 LoRA를 사용하지 않았는가?','Why omit a collision-type LoRA?',
'합성 학습 데이터에는 class imbalance와 town별 scene bias가 있습니다. 예를 들어 Single 유형은 3.0%이며 두 town에만 등장합니다. 유형 분류가 이런 분포의 shortcut에 과적합할 가능성을 고려해, temporal·spatial localization에는 LoRA를 적용하고 collision type에는 backbone의 zero-shot prior를 유지했습니다. Table 4의 과업별 adapter 비교로 이 선택을 점검했습니다.',
'The synthetic training data contain class imbalance and town-specific scene bias: the Single class accounts for 3.0% and occurs in only two towns. To reduce the risk of fitting such shortcuts, STAR adapts temporal and spatial localization but retains the backbone’s zero-shot prior for collision type. Task-aware adapter comparisons in Table 4 evaluate this choice.','§2.4, §3.2 · Table 1, Table 4')],
'navila-patch':[
item('왜 인식 label이 아니라 natural-language action을 목표로 삼았는가?','Why target natural-language actions instead of recognition labels?',
'NaVILA가 생성한 문장은 keyword parsing을 통해 실제 이동 명령으로 바뀝니다. 따라서 단순히 문장을 깨뜨리는 것보다, parsing 가능한 형식은 유지하면서 잘못된 행동을 생성하는지를 평가하는 편이 navigation 실패와 직접 연결됩니다. 원문에서 정의한 action type·방향·제어 값의 변형을 목표로 하고 policy weight는 고정해, 입력 patch가 행동 예측에 미치는 영향을 분리했습니다.',
'NaVILA’s generated sentences are parsed into movement commands. Preserving a parseable action format while changing the predicted action is therefore more directly connected to navigation failure than merely producing malformed text. The study uses its defined action-type, direction and control-value targets while freezing policy weights to isolate the effect of the input patch.','§2.1–2.2'),
item('왜 EOT와 제한된 입력 영역을 사용했는가?','Why use EOT and a restricted input region?',
'로봇이 이동하면 보이는 patch의 각도와 형태도 달라집니다. EOT(Expectation over Transformation)의 rotation·shear로 이러한 입력 변화를 모사하고, 장면 구조를 가능한 한 가리지 않도록 patch 위치를 우상단으로 정했습니다. 과거 7장과 현재 1장에 같은 규칙을 적용했습니다. 이 실험은 VLN-CE에서 수행한 simulation 평가이며 실물 부착 실험으로 표현하지 않습니다.',
'The observed appearance of a patch changes as the robot moves. Rotation and shear under EOT (Expectation over Transformation) model such input variation. An upper-right placement limits obstruction of scene structure, with the same rule applied to seven historical observations and the current view. These are VLN-CE simulation evaluations, not physical patch-deployment experiments.','§2.2–2.3, §3.1'),
item('왜 변경된 토큰과 Stop의 포맷 차이를 구분했는가?','Why distinguish changed tokens and the Stop format?',
'공통 문장 형식까지 다시 학습하면 잘못된 행동을 유도하려는 신호가 분산될 수 있어, 기존 행동과 달라진 유효 토큰에 손실을 집중했습니다. Stop은 별도의 문장 포맷으로 학습되어 있다는 점을 고려해 unlikelihood loss를 추가했습니다. 이는 일반적인 문장 생성이 아니라 action parsing 구조에 맞춘 목적함수 선택입니다.',
'The objective focuses on tokens that differ from the original action instead of relearning shared sentence structure. Because Stop was trained with a distinct response format, an additional unlikelihood term addresses that mismatch. The objective is thus selected for the action-parsing structure rather than generic text generation.','§2.2 · Equations 1–3'),
item('왜 Black·Gaussian·크기·노출 조건을 각각 비교했는가?','Why compare occlusion, noise, size and exposure separately?',
'Black patch는 가림, Gaussian initialization은 학습하지 않은 noise의 영향을 구분하기 위한 비교 조건입니다. 크기와 노출 조건은 공격 방식의 효과가 전체 관측에 항상 노출되는 가정에만 의존하는지 확인하기 위해 나누었습니다. 15%는 한 변의 근사 비율이며 57×57 patch는 384×384 영상 면적의 약 2.2%입니다. 초기 10회 노출과 주기적 노출도 별도 조건으로 평가했습니다.',
'Black patches control for occlusion, and Gaussian initialization controls for unoptimized noise. Size and exposure studies separately test how much the effect depends on a patch being visible in every observation. “15%” is an approximate side-length ratio: a 57×57 patch covers about 2.2% of a 384×384 image. Initial-ten-step and periodic exposure are evaluated as distinct conditions.','§3.2–3.4 · Table 1, Table 2, Table 3')],
'lift3d-film':[
item('왜 language를 3D feature 학습에 넣었는가?','Why condition 3D feature learning on language?',
'Geometry만으로는 과업의 맥락과 목표를 충분히 알기 어렵습니다. Lift3D의 두 번째 단계가 point cloud를 직접 처리해 action prediction에 필요한 feature를 만드는 과정이므로, 이 단계에 language conditioning을 결합했습니다. 기존의 2D-to-3D 학습 구조를 유지하면서 task intent를 visual representation에 반영하려는 선택입니다.',
'Geometry alone may not convey task context and intent. Lift3D’s second stage directly processes point clouds to produce features for action prediction, making it the chosen place for language conditioning. This retains the existing 2D-to-3D learning pipeline while introducing task intent into the visual representation.','§2.2–2.3'),
item('왜 FiLM이고, 왜 매 세 번째 block인가?','Why FiLM, and why every third block?',
'FiLM은 language embedding에서 얻은 γ와 β로 visual hidden state를 scale·shift하므로, feature를 과업에 맞게 직접 조정할 수 있습니다. CLIP text embedding과 MLP 기반 FiLM generator를 사용하고 기존 3D representation 학습의 안정성을 고려해 매 세 번째 CLIP-ViT block에 적용했습니다.',
'FiLM scales and shifts visual hidden states using language-derived γ and β, directly modulating features for the task. A CLIP text embedding and MLP-based FiLM generator are used at every third CLIP-ViT block to preserve the stability of existing 3D representation learning.','§2.3 · Equations 1–2'),
item('왜 지시문을 다시 구체화했는가?','Why revisit instruction detail?',
'기본 지시문에서는 8개 중 7개 과업이 개선됐지만 sweep into는 74%에서 72%로 떨어졌습니다. 과업 목표가 충분히 구체적이지 않다는 가설을 세워, 성능이 하락했거나 평균보다 낮은 네 과업의 지시문에 객체·동작·공간 관계를 추가했습니다. Sweep into는 82%로 높아졌고, 이 결과를 단순히 FiLM의 유무가 아니라 어떤 language condition을 주느냐가 중요하다는 근거로 사용했습니다.',
'Basic instructions improve seven of eight tasks, but sweep into drops from 74% to 72%. The authors hypothesize that the instruction underspecifies the objective and add object, action and spatial details for four tasks with declining or below-average performance. Sweep into reaches 82%, supporting the importance of the language condition itself rather than only the presence of FiLM.','§3 · Table 1, Table 2')],
'act-cbam':[
item('왜 추가 시연보다 visual attention을 먼저 바꿨는가?','Why change visual attention rather than add demonstrations?',
'Visual encoder를 fine-tuning한 ACT도 정밀한 insertion에서 낮은 성공률을 보였습니다. 입력 영상의 모든 특징이 제어에 똑같이 중요한 것은 아니라는 점에서, 같은 시연 데이터를 유지하면서 유용한 feature와 위치를 더 잘 활용하는 방향을 택했습니다. CBAM의 channel attention과 spatial attention은 각각 무엇과 어디에 집중할지를 조정합니다.',
'ACT still struggles with precise insertion after visual-encoder fine-tuning. Since not every visual feature is equally relevant to control, the study keeps demonstrations fixed and instead improves how the policy uses useful features and locations. CBAM’s channel and spatial attention address what and where to emphasize.','§1–2'),
item('왜 encoder를 동결한 adapter 방식인가?','Why freeze the encoder and train an adapter?',
'전체 visual encoder를 다시 학습하는 비용을 줄이고 pretrained representation을 활용하기 위해 ResNet18을 동결하고 CBAM을 adapter로 학습했습니다. 다른 policy component의 학습은 유지합니다. 따라서 83.92M → 72.79M은 전체 모델 크기가 아니라 학습 가능한 파라미터의 비교입니다.',
'To reduce visual-encoder fine-tuning cost while using pretrained representations, ResNet18 is frozen and CBAM is trained as an adapter. Other policy components remain trainable. The change from 83.92M to 72.79M therefore concerns trainable parameters, not total model size.','§2 · Table 1'),
item('왜 channel-only·spatial-only ablation을 두었는가?','Why include channel-only and spatial-only ablations?',
'두 attention은 서로 다른 기능을 하므로 결합 모듈의 성능만으로 각 구성의 역할을 알 수 없습니다. 같은 두 과업에서 channel-only·spatial-only·순차 결합을 비교했습니다. Channel-only는 두 과업 모두 baseline보다 낮았고, CBAM 결합은 96%·61%로 가장 높았습니다. 구성 요소를 추가했다는 사실보다 실제 제어 성공률로 선택을 검증한 비교입니다.',
'The two attention mechanisms have different roles, so a combined model alone cannot establish their contributions. Channel-only, spatial-only and sequential CBAM are compared on the same two tasks. Channel-only falls below baseline on both, whereas combined CBAM reaches the highest rates, 96% and 61%. This tests the design through control success rather than assuming an added module helps.','§3 · Table 1')]
}
STAR_TABLE_NOTES=[
pair('동일 backbone에서 한 번에 모든 답을 생성하는 방식, multi-turn, STAR를 비교합니다. 값은 원문의 offline evaluation 결과입니다.', 'Compare a single-response baseline, multi-turn and STAR using the same backbone. Values are the paper’s offline evaluation results.'),
pair('예측 시점을 텍스트로 알려주는 것과 실제 입력 영상을 좁히는 것을 분리해 비교합니다.', 'Separate giving the predicted time as text from actually narrowing the input video.'),
pair('Temporal·spatial·collision-type adapter 적용 조합을 비교합니다. 각 행은 원문에 보고된 하나의 구성입니다.', 'Compare the reported temporal, spatial and collision-type adapter configurations.')]

"""English editorial corrections. Never alter titles, Korean copy or result values.

Applied by both the generator and presentation pass so page copy, embedded data,
related-paper summaries and source-based checks see the same English wording.
"""
from __future__ import annotations

REVISIONS = {
    'The same evaluation budget can produce very different robot success rates depending on what is cached. EndCache distinguishes reuse by numerical solver and, for stochastic diffusion, reuses the estimated clean-action endpoint rather than raw noise. Mathematical analysis and closed-loop evaluation examine how output caching reduces calls and inference latency without retraining the policy.':
    'The same number of action-generator calls can yield very different task success rates depending on what is cached. EndCache analyzes output reuse in relation to the numerical solver. For stochastic diffusion, it reuses the estimated clean-action endpoint rather than the noise prediction. Mathematical analysis and closed-loop evaluation examine how output caching reduces calls and inference latency without retraining the policy.',
    'An action generator is evaluated repeatedly within one action chunk. Similar adjacent outputs alone do not establish safe caching: noise, velocity and endpoints enter numerical solvers differently.':
    'An action generator is evaluated repeatedly to produce a single action chunk. Similar outputs at adjacent steps alone do not establish the stability of caching: noise predictions, velocities, and endpoint estimates enter numerical solvers differently.',
    'For deterministic linear-FM Euler integration, blockwise velocity reuse is equivalent to coarse-grid Euler. On a uniform grid with k dividing N, it is native N/k-step inference. This equivalence fails in ancestral samplers that inject fresh noise at each fine step, making the reuse space consequential.':
    'With explicit Euler integration for deterministic linear flow matching, blockwise velocity reuse is equivalent to coarse-grid Euler integration. On a uniform grid where k divides N, it is equivalent to native inference with N/k steps. This equivalence does not hold for ancestral samplers that inject fresh noise at each step, so the choice of cached output matters.',
    'A stale noise prediction is amplified by σ/α = SNR⁻¹ᐟ² when converted to an endpoint. Direct endpoint reuse propagates staleness non-expansively under the stated assumptions. The analysis connects conditional posterior covariance to the endpoint Jacobian, without claiming a universal task-success guarantee.':
    'Error in a cached noise prediction is amplified by σ/α = SNR⁻¹ᐟ² when the prediction is converted to an endpoint estimate. Direct endpoint reuse propagates staleness error non-expansively under the stated assumptions. The analysis relates conditional posterior covariance to the endpoint Jacobian; it does not provide a universal guarantee of task success.',
    'Endpoint–noise success gap': 'Endpoint–noise success-rate gap',
    'π0.5 model-inference speedup': 'π0.5 end-to-end inference speedup',
    'π0.5 whole-model speedup': 'π0.5 end-to-end inference speedup',
    'π0.5 mean success variation': 'π0.5 mean success-rate variation',
    'Original Figure 2. Call schedule and action-generator (AG) latency for π0.5 at k=5. The headline 2.71× is whole-model inference at k=10.':
    'Figure 2 from the paper. Action-generator (AG) call schedule and latency for π0.5 at k=5. The headline 2.71× speedup refers to end-to-end model inference at k=10.',
    'We start from the observation that adjacent flow-matching outputs have highly similar directions and magnitudes. Recomputing velocity at fixed intervals and reusing it between refreshes reduces action-generation latency without retraining. Experiments on π0.5 and GR00T-N1.7 evaluate success and latency separately.':
    'We begin with the observation that velocity outputs at adjacent flow-matching steps have highly similar directions and magnitudes. Recomputing velocity at fixed intervals and reusing it between refreshes reduces action-generation latency without retraining. Experiments on π0.5 and GR00T-N1.7 evaluate task success rates and inference latency separately.',
    'Across four LIBERO suites, π0.5 has mean adjacent cosine similarity 0.9997 and norm ratio 0.9984. GR00T-N1.7 also has high adjacent cosine similarity, averaging 0.9963. These are observations on the tested models and conditions.':
    'Across the four LIBERO suites, π0.5 has a mean cosine similarity of 0.9997 and a mean norm ratio of 0.9984 between adjacent velocity outputs. GR00T-N1.7 also shows high adjacent-step cosine similarity, averaging 0.9963. These observations apply to the evaluated models and conditions.',
    'Evaluate velocity initially and refresh every k steps. Between refreshes, apply Euler updates using the held velocity. N=10 and k=5 reduce calls from ten to two, while intermediate solver-state updates remain.':
    'Compute velocity at the first generation step and refresh it every k steps. Between refreshes, perform Euler updates using the cached velocity. With N=10 and k=5, generator calls decrease from ten to two, while intermediate solver-state updates are retained.',
    'Paired fixes resets and initial action noise for comparisons; Random samples new initial action noise each control step. Success is evaluated across three seeds, with latency profiled on an A6000 using 30 warmups and 100 repetitions.':
    'The Paired protocol uses matched environment resets and initial action noise across compared methods; the Random protocol samples new initial action noise at each control step. Success rates are evaluated across three seeds. Latency is measured on an A6000 GPU using 30 warm-up runs and 100 timed repetitions.',
    'Original Figure 1. Reuse schedule illustration. Use the Table-4 explorer below for the latency and speedup comparison.':
    'Figure 1 from the paper. Velocity-reuse schedule. The results explorer below uses Table 4 for latency and speedup comparisons.',
    'Perturbed inputs pass through visual-language reasoning, natural-language action generation and command parsing. Evaluation measures goal reaching and path efficiency, not just a changed image prediction.':
    'Perturbed inputs pass through vision-language reasoning, natural-language action generation, and command parsing. Evaluation measures goal-reaching success and path efficiency, rather than changes in image predictions alone.',
    'Select a dataset/study and metric. Unmeasured size–exposure combinations are not fabricated.':
    'Select an experiment and metric to compare the reported results. Patch size and exposure conditions are evaluated in separate experiments.',
    'We add a CBAM adapter combining channel and spatial attention to ACT’s visual encoder. Freezing pretrained ResNet18 and training the adapter improves two simulation tasks with fewer trainable parameters and no additional expert demonstrations.':
    'We add a CBAM adapter combining channel and spatial attention to ACT’s visual encoder. Keeping the pretrained ResNet18 encoder frozen and training the adapter improves success rates on two simulated tasks, with fewer trainable parameters and no additional expert demonstrations.',
    '8-task mean · basic instruction': 'Mean across 8 tasks · basic instructions',
    'Mean success difference': 'Mean success-rate improvement',
    'Tasks improved with basic text': 'Tasks improved with basic instructions',
    'Basic descriptions improve seven of eight tasks. After observing a sweep-into regression, four tasks are additionally evaluated with explicit object-and-action instructions. No eight-task detailed-instruction mean is reported.':
    'Basic instructions improve success rates on seven of the eight tasks. After a performance drop on sweep into, four tasks are also evaluated with more detailed instructions specifying objects and actions. The paper does not report an eight-task mean for the detailed-instruction setting.',
    'Select a task to compare baseline, basic and detailed instructions. Unreported detailed conditions are left missing.':
    'Select a task to compare the baseline with basic- and detailed-instruction settings. Detailed-instruction results are shown only for tasks reported in the paper.',
}


def apply_paper_copy(papers: list[dict]) -> None:
    """Update English members of bilingual fields; repeated calls are safe."""
    def visit(value):
        if isinstance(value, dict):
            text = value.get('en')
            if isinstance(text, str) and text in REVISIONS:
                value['en'] = REVISIONS[text]
            for key, child in value.items():
                if key != 'en':
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(papers)

# ScopedAct narrated walkthrough

[Watch or download the video](media/scopedact-walkthrough.mp4) ·
[Transcript](media/scopedact-walkthrough.txt) · [Captions](media/scopedact-walkthrough.srt)

The revised eight-slide walkthrough starts with excessive authority, malicious
instructions in retrieved content, and the difficulty of connecting task activity
across separate records. Research references and their limits are in
[Problem and evidence](PROBLEM_AND_EVIDENCE.md).

The video follows a staging login investigation: access profiles, an actual denied
authentication-configuration request, operator intervention, the activity map,
and a separate run that ended without a repair. Setup commands stay in the
[native setup guide](NATIVE_REVIEW.md), rather than the narration.

This is an edited walkthrough using saved console screenshots, **not a continuous
live recording**. The saved Docker runs retain their historical labels; current
narration calls the corresponding profiles Diagnostic access and Change-proposal
access. No historical outcomes were changed. Native and Docker launchers share the
agent and enforcement code but have different isolation boundaries.

Narration is locally generated male English speech (Kokoro, am_michael), with
normalized volume. Caption timings are approximate. Maintainer-run evaluations
are not independent adoption. All incident data is synthetic; no production
system or real customer data is shown. [Speech tooling](https://github.com/thewh1teagle/kokoro-onnx).

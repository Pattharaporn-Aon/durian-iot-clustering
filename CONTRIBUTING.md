# Contributing

Thank you for your interest in this repository. It contains the analysis code and
data accompanying the manuscript *"A feature-scaling and stability-testing pipeline
for clustering small orchard IoT datasets"* (Thongnim, Piladaeng & Srinil), submitted
to *PeerJ Computer Science*.

Because the repository backs a specific published analysis, contributions are welcome
but are handled a little differently from a general-purpose software project: the
committed outputs in `outputs_analysis/` must continue to match the figures and tables
in the article.

## Ways to contribute

- **Report a problem.** Open a [GitHub Issue](https://github.com/Pattharaporn-Aon/durian-iot-clustering/issues)
  describing what you ran, what you expected, and what happened.
- **Ask a question** about the data, the pipeline, or how to reuse it — also via Issues.
- **Suggest an improvement** to the code, the documentation, or the data dictionary.
- **Reuse the pipeline** on your own dataset. You are encouraged to do so under the
  licence terms below; a citation is appreciated.

## Reporting a bug

Please include:

1. Your operating system and Python version (`python --version`).
2. Your installed package versions (`pip freeze`).
3. The exact command you ran, e.g. `python stability_analysis.py`.
4. The full error message or traceback.
5. What you expected to happen instead.

## Proposing a change

**Please open an issue before opening a pull request.** This lets us agree on the
change before you spend time on it, and lets us check whether it would alter the
published results.

Once the change is agreed:

1. Fork the repository and create a branch from `main`
   (e.g. `fix/vpd-threshold`, `docs/clarify-codebook`).
2. Set up the environment:

   ```bash
   python -m venv venv
   source venv/bin/activate          # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Make your change.
4. Re-run the full pipeline and check the effect on the outputs:

   ```bash
   python durian_analysis.py
   python scaling_comparison.py
   python clustering_models.py
   python stability_analysis.py
   python silhouette_null.py
   ```

5. Inspect `git diff outputs_analysis/`.
   - If the outputs are unchanged, say so in the pull request.
   - If they changed, explain **why** and **which figure or table in the article is
     affected**. Do not silently change a published number.
6. Open a pull request referencing the issue.

## Code conventions

- Python 3.11, standard library plus the packages pinned in `requirements.txt`.
- Keep each script **self-contained**: it reads the raw data files (`PSN.xlsx`, and
  `IoT_Sensor_Hourly.csv` where weather features are needed) and writes its own
  outputs, so the scripts can be run in any order or individually.
- Do not change the shared analysis parameters (`SEED = 0`, `K = 3`, `B = 2000`,
  `EXCLUDE_ZONES = ("C",)`) without raising it in an issue first — they define the
  published results.
- Keep random seeds fixed so runs remain reproducible.
- Follow the existing style: descriptive names, comments where a step encodes a
  methodological decision rather than a mechanical one.

## Changes to the data

The data files (`PSN.xlsx`, `IoT_Sensor_Hourly.csv`, `merged_field_weather.csv`) are
the field record as collected and are **not** modified through pull requests. If you
believe you have found an error in the data, please open an issue describing it; any
correction has to be reconciled with the archived copy on
[OSF](https://osf.io/68fc5/) and, if the article is already published, handled through
the journal.

If you change a column, also update [`DATA_README.md`](DATA_README.md) and
[`CODEBOOK.md`](CODEBOOK.md) in the same pull request.

## Continuous integration

Every push to `main` triggers
[`.github/workflows/run-pipeline.yml`](.github/workflows/run-pipeline.yml), which
installs `requirements.txt`, runs all five scripts and commits the regenerated
`outputs_analysis/` back to the repository. Please make sure the workflow passes on
your branch before requesting a review.

## Licence

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE) for code, and CC-BY 4.0 for data.

## Code of conduct

Participation in this project is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Contact

Pattharaporn Thongnim — Department of Mathematics, Faculty of Science,
Burapha University, Chon Buri, Thailand — <pattharaporn@buu.ac.th>

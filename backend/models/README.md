# Model artifacts

Generated ML artifacts are intentionally not committed to Git.

Run `python train_model.py --data <path-to-log-file> --output models` from `backend/` to build a local artifact set. A valid artifact directory is expected to contain the Keras model, fitted preprocessing objects, threshold calibration data, and `metadata.json` produced by the training pipeline.

Production images and releases must obtain a verified artifact set through the documented build/release workflow rather than relying on developer-local binary files.

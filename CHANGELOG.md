# Changelog

---

## [0.03] - 2026-06-09

### Added

- Some combo boxes and tables are now automatically sorted for better readability.
- Horizontal and vertical units can now be configured independently.
- New **Dynamic Tab** feature with linear interpolation.
- Automatic version checking.

### Changed

- Disabled auto-range when changing color mapping in the 2D Map.
- Updated README documentation.
- Disabled Aspect Ratio locking on polar graphs.

### Fixed

- Fixed an issue when creating a polar region near the end of the dataset that could return a `None` value.
- Fixed a bug where linear regions disappeared after updating preferences.
- Corrected glide ratio calculation errors.
- Corrected the default width of new linear regions in the Polar tab.

---

## [0.02] - 2026-05-11

### Added

- Splash screen displayed during application startup.

### Changed

- Removed or replaced several heavy dependencies.
- Improved error handling when importing IGC files.
- Removed modification confirmation dialogs for aliases and comments.

### Fixed

- Added support for southern and western hemisphere GNSS coordinates.
- Fixed handling of GNSS signal losses occurring during flight.

---

## [0.01] - 2026-05-07

### Added

Initial release of Vector Vario Software, including:

- Import / Export
- Time Series
- Map Explorer
- Polar Analysis
- Skew-T Diagram
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Initial audio downloader with support for Deezer album, track,
  and playlist URLs.
- FLAC download preference with an MP3 fallback converted to FLAC
  using SoX.
- Automatic directory structure:
  `Artist/Year - Album Title/01 - Track Title.flac`.
- Reuse of existing artist and album directories.
- Metadata for title, album, artist, release year, and track number.
- Concurrent processing with up to four worker threads.
- English README with system installation instructions for Arch Linux
  and Ubuntu, virtual environment setup, and ARL file creation.
- Python dependency list in `requirements.txt`.

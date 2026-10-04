# Changelog

All notable changes to this project will be documented in this file.

## 2026-10-04

### Added

- Download available album artwork as a separate 1000 × 1000 JPEG named `Folder.jpg`.
- Preserve existing cover files using an existence check and exclusive file creation.
- Copy album picture IDs into track data for album downloads.

- Artist URL expansion into album and EP downloads.
- Pagination for artist catalog results.
- Filtering of artist releases to `album` and `ep`, excluding singles and unknown release types.
- Duplicate album ID removal within an artist lookup and duplicate URL removal within an invocation.
- HTTP short-link resolution before artist URL detection.

### Changed

- Document cover storage, concurrent requests, and failure limitations.

- Expand artist URLs before submitting work to the download thread pool.
- Update the English README to use `deedl.py` and `deedl.arl` consistently.
- Document artist downloads, release filtering, short links, and mixed URL input.
- Clarify the limitations of short-link resolution and catalog completeness.

## Initial Implementation

### Added

- Album, track, and playlist URL processing.
- FLAC preference with MP3 fallback converted to FLAC using SoX.
- Artist and album directories using `Artist/Year - Album Title/NN - Track Title.flac`.
- Reuse of existing artist and album directories.
- Track metadata for title, album, artist, release year, and track number.
- Processing with up to four worker threads.
- English installation instructions for Arch Linux and Ubuntu, with system packages or a virtual environment.
- ARL session file setup instructions and `requirements.txt`.

The dated release entries document the discussed changes. No version number has been assigned; the current script implementation was not verified from a script attachment.
#!/usr/bin/env python3

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from Crypto.Cipher import Blowfish
from functools import partial
from json import loads as json_decode
from hashlib import md5
from mutagen import File as TagFile
from pathlib import Path
from re import compile as regex
from requests import Session
from subprocess import Popen, DEVNULL, PIPE, STDOUT
from sys import argv, exit
from threading import local as thread_local
from urllib.parse import urlparse

BLOWFISH_IV = b"\x00\x01\x02\x03\x04\x05\x06\x07"
SECRET_DECRYPT = b"g4el58wc0zvf9na1"
BLOCK_SIZE = 2048

DATA_RE = regex(r'({"DATA":{.*}})</script>')

DATE_TAGS = (
    "ORIGINAL_RELEASE_DATE",
    "PHYSICAL_RELEASE_DATE",
    "DIGITAL_RELEASE_DATE",
)

FORMATS = (
    "FLAC",
    "MP3_320",
)

ARTIST_PATH_RE = regex(
    r"^/(?:[a-z]{2}/)?artist/(\d+)(?:/.*)?$"
)

def get_artist_album_urls(session, artist_id):
    endpoint = f"https://api.deezer.com/artist/{artist_id}/albums"
    album_urls = []
    seen_ids = set()
    index = 0

    while True:
        resp = session.get(
            endpoint,
            params={"limit": 100, "index": index},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()

        if error := payload.get("error"):
            raise RuntimeError(
                f"Artist {artist_id}: "
                f"{error.get('message', error)}"
            )

        albums = payload.get("data")
        if not isinstance(albums, list):
            raise RuntimeError(
                f"Artist {artist_id}: invalid album response"
            )

        for album in albums:
            if album.get("record_type") not in {"album", "ep"}:
                continue

            album_id = str(album["id"])

            if album_id in seen_ids:
                continue

            seen_ids.add(album_id)
            album_urls.append(
                f"https://www.deezer.com/de/album/{album_id}"
            )

        if not payload.get("next"):
            break

        if not albums:
            raise RuntimeError(
                f"Artist {artist_id}: empty pagination page"
            )

        index += len(albums)

    print(f"Artist {artist_id}: found {len(album_urls)} releases")
    return album_urls

def resolve_deezer_url(session, url):
    if urlparse(url).hostname != "link.deezer.com":
        return url

    resp = session.get(
        url,
        allow_redirects=True,
        timeout=30,
    )
    resp.raise_for_status()

    resolved_url = resp.url
    hostname = urlparse(resolved_url).hostname

    if hostname not in {"deezer.com", "www.deezer.com"}:
        raise RuntimeError(
            f"Couldn't resolve Deezer short link: "
            f"{url} -> {resolved_url}"
        )

    print(f"Resolved: {url} -> {resolved_url}")
    return resolved_url

def expand_artist_urls(urls):
    expanded = []
    seen_urls = set()

    with Session() as session:
        session.headers["User-Agent"] = (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )

        for url in urls:
            # Resolve short links before checking the resource type.
            url = resolve_deezer_url(session, url)

            parsed = urlparse(url)
            match = ARTIST_PATH_RE.fullmatch(parsed.path)

            if (
                parsed.hostname in {"deezer.com", "www.deezer.com"}
                and match
            ):
                resolved_urls = get_artist_album_urls(
                    session, match.group(1)
                )
            else:
                resolved_urls = [url]

            for resolved_url in resolved_urls:
                if resolved_url not in seen_urls:
                    seen_urls.add(resolved_url)
                    expanded.append(resolved_url)

    return expanded

def main(script, urls):
    if not urls:
        return 0

    arlfile = script.with_suffix(".arl")

    if not arlfile.exists():
        print(f"ARL file '{arlfile}' missing")
        return 1

    if not arlfile.is_file():
        print(f"'{arlfile}' is not a regular file")
        return 1

    arl = arlfile.read_text().strip()

    with Session() as root_session:
        root_session.headers.update({
            "User-Agent": ( "Mozilla/5.0 (X11; Linux x86_64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/68.0.3440.106 Safari/537.36" ),
        })
        root_session.cookies.update({
            "arl": arl,
            "comeback": "1",
        })

        resp = root_session.get(
            "https://www.deezer.com/ajax/gw-light.php",
            params={
                "api_version": "1.0",
                "api_token": "",
                "method": "deezer.getUserData",
            }
        )

        userdata = resp.json().get("results")
        useropts = userdata["USER"]["OPTIONS"]

        if not useropts["web_lossless"] and \
           not useropts["mobile_lossless"]:
            print("account can't download lossless audio")
            return 1

        try:
            urls = expand_artist_urls(urls)
        except (RuntimeError, ValueError, OSError) as exc:
            print(f"Couldn't resolve artist URLs: {exc}")
            return 1

        if not urls:
            print("No albums found")
            return 0

        tlocal = thread_local()

        def get_thread_session():
            try:
                session = tlocal.session
            except AttributeError:
                session = tlocal.session = Session()
                session.headers.update(root_session.headers)
                session.cookies.update(root_session.cookies)
            return session

        with ThreadPoolExecutor(max_workers=4) as pool:
            songs = as_completed(
                pool.submit(
                    get_songs,
                    pool, get_thread_session,
                    useropts["license_token"], url
                )
                for url in urls
            )

            downloads = as_completed(
                pool.submit(
                    download_song,
                    get_thread_session, *song
                )
                for items in songs
                for song in items.result()
            )

            for fut in downloads:
                fut.result()

def a2b(s):
    return s.encode("ascii")

def md5hex(b):
    return a2b(md5(b).hexdigest())

def decrypt(resp, decrypt_key):
    for i,data in enumerate(resp.iter_content(BLOCK_SIZE)):
        # only full blocks and every third is encrypted
        if len(data) == BLOCK_SIZE and i % 3 == 0:
            data = (
                Blowfish
                .new(decrypt_key, Blowfish.MODE_CBC, BLOWFISH_IV)
                .decrypt(data)
            )
        yield data

def set_metadata(filename, song):
    fp = TagFile(filename)
    if title := song.get("SNG_TITLE"):
        fp["title"] = title
    if album := song.get("ALB_TITLE"):
        fp["album"] = album
    for tag in DATE_TAGS:
        if date := song.get(tag):
            fp["date"] = date[:4]
            break
    artists = ", ".join(
        name for artist in song.get("ARTISTS", [])
        if (name := artist.get("ART_NAME", None))
    )
    if artists:
        fp["artist"] = artists
    if tracknum := song.get("TRACK_NUMBER"):
        fp["tracknumber"] = str(int(tracknum))
    fp.save()

def clean_filename(value):
    """Entfernt problematische Zeichen aus Datei- und Ordnernamen."""
    value = str(value).strip()
    for char in '<>:"/\\|?*\x00':
        value = value.replace(char, "_")

    value = "".join(char for char in value if ord(char) >= 32)
    return value.rstrip(". ") or "Unbekannt"


def get_song_filename(song):
    release_year = next(
        (
            str(song[tag]).strip()[:4]
            for tag in DATE_TAGS
            if song.get(tag)
        ),
        "Unbekanntes Jahr",
    )

    artist = clean_filename(
        song.get("ALB_ART_NAME")
        or song.get("ART_NAME")
        or next(
            (
                item["ART_NAME"]
                for item in song.get("ARTISTS", [])
                if item.get("ART_NAME")
            ),
            "Unbekannter Interpret",
        )
    )

    album_title = clean_filename(
        song.get("ALB_TITLE") or "Unbekanntes Album"
    )
    title = clean_filename(
        song.get("SNG_TITLE") or song["SNG_ID"]
    )
    track_number = int(song.get("TRACK_NUMBER") or 0)

    album_dir = (
        Path(artist)
        / f"{clean_filename(release_year)} - {album_title}"
    )
    album_dir.mkdir(parents=True, exist_ok=True)

    return album_dir / f"{track_number:02d} - {title}.flac"

def download_album_cover(session, song, album_dir):
    cover_file = album_dir / "Folder.jpg"

    if cover_file.is_file():
        return

    picture_id = song.get("ALB_PICTURE")
    if not picture_id:
        return

    cover_url = (
        "https://e-cdns-images.dzcdn.net/images/cover/"
        f"{picture_id}/1000x1000-000000-80-0-0.jpg"
    )

    try:
        resp = session.get(cover_url, timeout=30)
        resp.raise_for_status()

        if not resp.headers.get("Content-Type", "").startswith("image/jpeg"):
            print(f"Unexpected cover format: {cover_url}")
            return

        # Exclusive creation prevents concurrent downloads from
        # overwriting a cover created by another worker.
        try:
            with cover_file.open("xb") as fp:
                fp.write(resp.content)
        except FileExistsError:
            return

        print(f"Saved cover: {cover_file}")

    except OSError as exc:
        print(f"Couldn't save cover for {album_dir}: {exc}")

def download_song(get_session, song, fmt, urls):
    session = get_session()
    filename = get_song_filename(song)
    
    download_album_cover(session, song, filename.parent)

    songid_md5 = md5hex(a2b(song["SNG_ID"]))
    decrypt_key = bytes(
        songid_md5[i] ^ songid_md5[i + 16] ^ SECRET_DECRYPT[i]
        for i in range(16)
    )

    print(f"downloading {filename} ({fmt})")

    for url in urls:
        resp = session.get(url["url"], stream=True)
        if resp.status_code != 200:
            continue
        try:
            if fmt == "FLAC":
                with filename.open("wb") as fp:
                    for block in decrypt(resp, decrypt_key):
                        fp.write(block)

            else:
                with Popen(
                    (
                        "sox",
                        # input
                        "-t", "mp3", "-",
                        # output as 24 bit FLAC compression level 0 to stdout
                        "-t", "flac", "-C", "0", filename.resolve(),
                        # normalize to -3 dB
                        "gain", "-n", "-3",
                    ),
                    stdin=PIPE,
                    stderr=STDOUT,
                ) as proc:
                    for block in decrypt(resp, decrypt_key):
                        proc.stdin.write(block)

            set_metadata(filename, song)
        except KeyboardInterrupt:
            filename.unlink(missing_ok=True)
            raise
        except:
            filename.unlink(missing_ok=True)
            continue
        else:
            break

def get_songs(pool, get_session, license_token, url):
    session = get_session()

    if (match := DATA_RE.search(session.get(url).text)) is None:
        print(url, "couldn't find page data")
        return []

    if (pagedata := json_decode(match.group(1))) is None:
        print("invalid page data")
        return []

    res = []
    songs = []

    match pagedata["DATA"]["__TYPE__"]:
        case "album":
            album_artist = pagedata["DATA"].get("ART_NAME")

            for song in pagedata["SONGS"]["data"]:
                if album_artist:
                    song["ALB_ART_NAME"] = album_artist

                if picture_id := pagedata["DATA"].get("ALB_PICTURE"):
                    song["ALB_PICTURE"] = picture_id

                for tag in DATE_TAGS:
                    song[tag] = pagedata["DATA"].get(tag)

                songs.append(song)

        case "playlist":
            for song in pagedata["SONGS"]["data"]:
                print(song['SNG_ID'], song['SNG_TITLE'])
            futs = as_completed(
                pool.submit(
                    get_songs,
                    pool, get_session, license_token,
                    f"https://www.deezer.com/de/track/{song['SNG_ID']}"
                )
                for song in pagedata["SONGS"]["data"]
            )
            for fut in futs:
                res.extend(fut.result())

        case "song":
            songs.append(pagedata["DATA"])

    if not songs:
        return res

    resp = session.post(
        "https://media.deezer.com/v1/get_url",
        json={
            "license_token": license_token,
            "track_tokens": [
                song["TRACK_TOKEN"] for song in songs
            ],
            "media": [{
                "type": "FULL",
                "formats": [
                    { "cipher": "BF_CBC_STRIPE", "format": fmt }
                    for fmt in FORMATS
                ],
            }],
        },
    )
    data = [
        { fmt["format"]: fmt["sources"]
          for fmt in song.get("media", []) }
        for song in resp.json()["data"]
    ]

    for song,urls in zip(songs, data):
        for fmt in FORMATS:
            if sources := urls.get(fmt, None):
                break

        if sources is None:
            print(f"No FLAC or MP3_320 available for song {song['SNG_ID']}")
        else:
            res.append((song, fmt, sources))

    return res

if __name__ == "__main__":
    try:
        exit(main(Path(argv[0]).resolve(), argv[1:]) or 0)
    except KeyboardInterrupt:
        pass

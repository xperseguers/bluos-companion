"""Tests for the media source and the artwork proxy."""

from __future__ import annotations

import base64

import aiohttp
import pytest
from homeassistant.components.media_player import BrowseError
from homeassistant.components.media_source import (
    Unresolvable,
    async_browse_media,
    async_resolve_media,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.bluos_companion.const import DOMAIN

from custom_components.bluos_companion.api import Node
from custom_components.bluos_companion.const import ICONS_URL
from custom_components.bluos_companion.http import (
    async_artwork_url,
    decode_image,
    encode_image,
)
from custom_components.bluos_companion.media_source import (
    TITLES,
    _encode_node,
    menu_label,
)

from .conftest import BASE, SONGS_SECTION, browse_url, calls

ROOT = f"media-source://{DOMAIN}"


def _b64(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode()


def _ids(item) -> list[str]:
    return [child.media_content_id for child in item.children]


def _thumb_path(thumbnail: str) -> str:
    return thumbnail.split("&authSig=")[0]


def _image_of(thumbnail: str) -> str:
    """Return the player image path a proxied thumbnail points to."""
    return decode_image(_thumb_path(thumbnail).split("?path=")[1])


@pytest.mark.usefixtures("init_integration")
async def test_root_lists_players(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Each loaded player is listed."""
    item = await async_browse_media(hass, ROOT)
    assert [child.title for child in item.children] == ["Séjour"]
    assert _ids(item) == [f"{ROOT}/{init_integration.entry_id}"]


async def test_player_menu(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """The player offers the recent albums, the library categories and presets."""
    item = await async_browse_media(hass, f"{ROOT}/{init_integration.entry_id}")
    assert [child.title for child in item.children] == [
        "Recently added",
        "Artists",
        "Albums",
        "Songs",
        "Genres",
        "Playlists",
        "Composers",
        "Presets",
        "Queue",
    ]


async def test_recent_albums(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Recent albums are playable, expandable and have a proxied thumbnail."""
    eid = init_integration.entry_id
    item = await async_browse_media(hass, f"{ROOT}/{eid}/recent")
    first = item.children[0]
    assert first.title == "Definitely Maybe - Oasis"
    assert first.can_play
    assert first.can_expand
    assert first.media_content_id == (
        f"{ROOT}/{eid}/album/{_b64('album=Definitely+Maybe&artist=Oasis')}"
    )
    assert _image_of(first.thumbnail).startswith("/Artwork")
    assert "authSig=" in first.thumbnail


async def test_albums_by_section(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Sections lead to the albums of a letter, which can be played and expanded."""
    eid = init_integration.entry_id
    sections = await async_browse_media(hass, f"{ROOT}/{eid}/albums")
    assert [child.title for child in sections.children] == ["A (84)", "# (36)"]
    assert not sections.children[0].can_play
    assert sections.children[0].can_expand

    albums = await async_browse_media(hass, sections.children[0].media_content_id)
    assert albums.title == "A"
    assert [child.title for child in albums.children] == [
        "À côté du soleil - Cristina Marocco"
    ]
    album = albums.children[0]
    assert (album.media_class, album.can_play, album.can_expand) == ("album", True, True)
    assert _image_of(album.thumbnail).startswith("/Artwork")


@pytest.mark.parametrize(
    ("category", "title", "media_class", "can_play", "can_expand"),
    [
        pytest.param("artists", "A (67)", "directory", False, True, id="artists"),
        pytest.param("genres", "Pop", "genre", False, True, id="genres"),
        pytest.param("playlists", "Relaxing", "playlist", True, True, id="playlists"),
    ],
)
async def test_library_categories(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    category: str,
    title: str,
    media_class: str,
    can_play: bool,
    can_expand: bool,
) -> None:
    """Library categories are browsable, entries without target are hidden."""
    item = await async_browse_media(
        hass, f"{ROOT}/{init_integration.entry_id}/{category}"
    )
    assert len(item.children) == 1
    child = item.children[0]
    assert (child.title, child.media_class, child.can_play, child.can_expand) == (
        title,
        media_class,
        can_play,
        can_expand,
    )


async def test_tracks_have_artist_and_no_thumbnail(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Songs show their artist and album and do not load a cover each."""
    node = Node("section", "A", "1", "songs-a", None, None)
    player_api.get(browse_url("songs-a"), text=SONGS_SECTION)
    item = await async_browse_media(
        hass, f"{ROOT}/{init_integration.entry_id}/node/{_encode_node(node)}"
    )
    track = item.children[0]
    assert track.title == "À 82 ans - Axelle Red • Toujours moi"
    assert (track.can_play, track.can_expand, track.thumbnail) == (True, False, None)


async def test_album_tracks(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """An album lists its tracks, each playable."""
    eid = init_integration.entry_id
    item = await async_browse_media(
        hass, f"{ROOT}/{eid}/album/{_b64('album=21&artist=Adele')}"
    )
    assert item.title == "21"
    assert item.can_play
    assert [child.title for child in item.children] == [
        "1. Rolling In the Deep",
        "5. Set Fire to the Rain",
    ]
    assert all(child.can_play and not child.can_expand for child in item.children)


async def test_presets(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """HTTPS preset images are used as is, others are proxied."""
    eid = init_integration.entry_id
    item = await async_browse_media(hass, f"{ROOT}/{eid}/presets")
    http_preset, https_preset, no_image = item.children
    assert _image_of(http_preset.thumbnail).startswith("http")
    assert https_preset.thumbnail == "https://cdn.example/s58290.png"
    assert no_image.thumbnail is None
    assert [child.media_content_id for child in item.children] == [
        f"{ROOT}/{eid}/preset/{n}" for n in (1, 2, 3)
    ]


@pytest.mark.parametrize(
    "tail",
    [
        pytest.param("unknown", id="unknown-entry"),
        pytest.param("{eid}/nope", id="unknown-item"),
        pytest.param("{eid}/node/!!!", id="bad-identifier"),
        pytest.param("{eid}/node/e30=", id="node-without-key"),
    ],
)
async def test_browse_errors(
    hass: HomeAssistant, init_integration: MockConfigEntry, tail: str
) -> None:
    """Invalid identifiers raise a browse error."""
    with pytest.raises(BrowseError):
        await async_browse_media(
            hass, f"{ROOT}/{tail.format(eid=init_integration.entry_id)}"
        )


async def test_browse_player_failure(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Player errors become browse errors."""
    player_api.clear_requests()
    player_api.get(f"{BASE}/Presets", exc=aiohttp.ClientError)
    with pytest.raises(BrowseError):
        await async_browse_media(hass, f"{ROOT}/{init_integration.entry_id}/presets")


async def test_resolve_is_not_supported(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Library items cannot be turned into a URL."""
    with pytest.raises(Unresolvable, match="select your BluOS player"):
        await async_resolve_media(
            hass, f"{ROOT}/{init_integration.entry_id}/preset/1", "media_player.sejour"
        )


async def test_artwork_proxy(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    """Thumbnails are fetched from the player and served by Home Assistant."""
    eid = init_integration.entry_id
    item = await async_browse_media(hass, f"{ROOT}/{eid}/recent")
    player_api.mock_calls.clear()
    client = await hass_client()

    response = await client.get(item.children[0].thumbnail)

    assert response.status == 200
    assert response.content_type == "image/jpeg"
    assert await response.read() == b"image"
    assert calls(player_api) == [
        (
            "/Artwork",
            {"service": "LocalMusic", "album": "Definitely Maybe", "artist": "Oasis"},
        )
    ]


@pytest.mark.parametrize(
    ("entry_id", "path", "status"),
    [
        pytest.param("{eid}", "relative", 404, id="relative-path"),
        pytest.param("{eid}", "", 404, id="missing-path"),
        pytest.param("unknown", "/Artwork", 404, id="unknown-entry"),
        pytest.param("{eid}", "/Missing", 502, id="player-error"),
    ],
)
async def test_artwork_proxy_errors(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
    entry_id: str,
    path: str,
    status: int,
) -> None:
    """Bad requests and player failures are not proxied."""
    player_api.get(f"{BASE}/Missing", status=404)
    client = await hass_client()
    response = await client.get(
        f"/api/{DOMAIN}/{entry_id.format(eid=init_integration.entry_id)}/artwork",
        params={"path": encode_image(path)},
    )
    assert response.status == status
    assert [call for call in calls(player_api) if call[0] == "/Artwork"] == []


async def test_artwork_proxy_requires_auth(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """Unsigned, unauthenticated requests are refused."""
    client = await hass_client_no_auth()
    response = await client.get(
        f"/api/{DOMAIN}/{init_integration.entry_id}/artwork",
        params={"path": encode_image("/Artwork")},
    )
    assert response.status == 401


async def test_artwork_proxy_signed_url_with_encoded_path(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """A signed URL works for paths holding %XX, + and quotes, as in file names."""
    image = (
        "/Artwork?service=LocalMusic&fn=%2Fmnt%2FKuschel+Rock%2C+Vol.+10"
        "%2FI%27d+Lie+%28And%29.m4a"
    )
    url = async_artwork_url(hass, init_integration.entry_id, image)
    player_api.mock_calls.clear()

    response = await (await hass_client_no_auth()).get(url)

    assert response.status == 200
    assert calls(player_api) == [
        (
            "/Artwork",
            {"service": "LocalMusic", "fn": "/mnt/Kuschel Rock, Vol. 10/I'd Lie (And).m4a"},
        )
    ]


async def test_titles_follow_the_language(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The menu uses the language of Home Assistant."""
    hass.config.language = "fr"
    eid = init_integration.entry_id

    menu = await async_browse_media(hass, f"{ROOT}/{eid}")
    assert [child.title for child in menu.children] == [
        "Nouveautés",
        "Artistes",
        "Albums",
        "Chansons",
        "Genres",
        "Listes de lecture",
        "Compositeurs",
        "Préréglages",
        "File d'attente",
    ]

    songs = await async_browse_media(hass, f"{ROOT}/{eid}/playlists")
    assert songs.title == "Listes de lecture"
    recent = await async_browse_media(hass, f"{ROOT}/{eid}/recent")
    assert recent.title == "Nouveautés"
    presets = await async_browse_media(hass, f"{ROOT}/{eid}/presets")
    assert presets.title == "Préréglages"


async def test_unsupported_language_falls_back_to_english(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Other languages get the English titles."""
    hass.config.language = "de"
    menu = await async_browse_media(hass, f"{ROOT}/{init_integration.entry_id}")
    assert menu.children[0].title == "Recently added"


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        pytest.param(
            "fr",
            ["Albums", "Chansons", "Favoris", "Favoris", "Dossiers", "Radio"],
            id="french",
        ),
        pytest.param(
            "en",
            ["Albums", "Songs", "Favourites", "Favourites", "Folders", "Radio"],
            id="english",
        ),
    ],
)
async def test_player_menu_labels_are_translated(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    language: str,
    expected: list[str],
) -> None:
    """Known labels of the player menus follow the language, others are kept."""
    hass.config.language = language
    player_api.get(
        browse_url("artist-menu"),
        text='''<browse type="menu">
  <item browseKey="albums-key" text="Albums" type="link"></item>
  <item browseKey="songs-key" text="Songs" type="link"></item>
  <item browseKey="fav-key" text="Favourites" type="link"></item>
  <item browseKey="fav2-key" text="Favorites" type="link"></item>
  <item browseKey="folders-key" text="Folders" type="link"></item>
  <item browseKey="radio-key" text="Radio" type="link"></item>
</browse>''',
    )
    player_api.get(browse_url("songs-key"), text=SONGS_SECTION)
    node = Node("artist", "a-ha", "", "artist-menu", None, None)
    item = await async_browse_media(
        hass, f"{ROOT}/{init_integration.entry_id}/node/{_encode_node(node)}"
    )
    assert [child.title for child in item.children] == expected

    songs = await async_browse_media(hass, item.children[1].media_content_id)
    assert songs.title == expected[1]


async def test_album_named_like_a_menu_is_not_translated(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Only menu links are translated, not music called "Songs"."""
    hass.config.language = "fr"
    player_api.get(
        browse_url("artist-albums"),
        text='''<browse type="albums">
  <item browseKey="k" playURL="/Add?playnow=1" text="Songs" text2="Someone" type="album"></item>
</browse>''',
    )
    node = Node("artist", "x", "", "artist-albums", None, None)
    item = await async_browse_media(
        hass, f"{ROOT}/{init_integration.entry_id}/node/{_encode_node(node)}"
    )
    assert item.children[0].title == "Songs - Someone"


async def test_menu_items_have_icons(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Players and categories get a dedicated icon instead of a folder."""
    eid = init_integration.entry_id
    root = await async_browse_media(hass, ROOT)
    assert [child.thumbnail for child in root.children] == [f"{ICONS_URL}/player.svg"]

    menu = await async_browse_media(hass, f"{ROOT}/{eid}")
    assert [child.thumbnail for child in menu.children] == [
        f"{ICONS_URL}/{name}.svg"
        for name in (
            "recently_added",
            "artists",
            "albums",
            "songs",
            "genres",
            "playlists",
            "composers",
            "presets",
            "queue",
        )
    ]


async def test_player_menu_links_have_icons(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Known links below an artist get the icon of their category."""
    player_api.get(
        browse_url("artist-menu"),
        text="""<browse type="menu">
  <item browseKey="a" text="Albums" type="link"></item>
  <item browseKey="f" text="Favorites" type="link"></item>
  <item browseKey="r" text="Radio" type="link"></item>
</browse>""",
    )
    node = Node("artist", "a-ha", "", "artist-menu", None, None)
    item = await async_browse_media(
        hass, f"{ROOT}/{init_integration.entry_id}/node/{_encode_node(node)}"
    )
    assert [child.thumbnail for child in item.children] == [
        f"{ICONS_URL}/albums.svg",
        f"{ICONS_URL}/favourites.svg",
        None,
    ]


@pytest.mark.parametrize(
    ("browse_key", "icon"),
    [("LocalMusic:", "library"), ("Airable:", "radio"), ("Deezer:", None)],
)
def test_source_icons(browse_key: str, icon: str | None) -> None:
    """The player's white glyphs are replaced by our tiles, service logos are kept."""
    node = Node("link", "Library", "", browse_key, None, "/images/x.png")
    assert menu_label(node, {})[1] == (f"{ICONS_URL}/{icon}.svg" if icon else None)


@pytest.mark.parametrize("name", ["player", "library", "radio", *TITLES])
async def test_icons_are_served(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
    name: str,
) -> None:
    """Every icon used by the menus exists and loads without authentication."""
    client = await hass_client_no_auth()
    response = await client.get(f"{ICONS_URL}/{name}.svg")
    assert response.status == 200
    assert response.content_type == "image/svg+xml"


async def test_queue(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """The queue lists its tracks, each playable by position."""
    eid = init_integration.entry_id
    queue = await async_browse_media(hass, f"{ROOT}/{eid}/queue")
    assert [(child.identifier, child.title, child.can_play) for child in queue.children] == [
        (f"{eid}/queue/0", "U Got the Look - Prince", True),
        (f"{eid}/queue/1", "Kiss", True),
    ]
    assert queue.children[0].thumbnail is not None
    assert queue.children[1].thumbnail is None

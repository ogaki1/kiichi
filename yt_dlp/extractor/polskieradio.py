import itertools
import json
import math
import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_unquote,
    compat_urlparse
)
from ..utils import (
    determine_ext,
    extract_attributes,
    ExtractorError,
    InAdvancePagedList,
    int_or_none,
    js_to_json,
    parse_iso8601,
    strip_or_none,
    traverse_obj,
    unified_timestamp,
    unescapeHTML,
    url_or_none,
)


class PolskieRadioBaseExtractor(InfoExtractor):
    def _extract_webpage_player_entries(self, webpage, playlist_id, base_data):
        media_urls = set()

        for data_media in re.findall(r'<[^>]+data-media="?({[^>]+})"?', webpage):
            media = self._parse_json(data_media, playlist_id, transform_source=unescapeHTML, fatal=False)
            if not media.get('file') or not media.get('desc'):
                continue
            media_url = self._proto_relative_url(media['file'])
            if media_url in media_urls:
                continue
            media_urls.add(media_url)
            entry = base_data.copy()
            entry.update({
                'id': compat_str(media['id']),
                'url': media_url,
                'duration': int_or_none(media.get('length')),
                'vcodec': 'none' if media.get('provider') == 'audio' else None,
            })
            entry_title = compat_urllib_parse_unquote(media['desc'])
            if entry_title:
                entry['title'] = entry_title
            yield entry


class PolskieRadioLegacyIE(PolskieRadioBaseExtractor):
    # legacy sites
    IE_NAME = 'polskieradio:legacy'
    _VALID_URL = r'https?://(?:www\.)?polskieradio(?:24)?\.pl/\d+/\d+/[Aa]rtykul/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.polskieradio.pl/8/2382/Artykul/2534482,Zagarysci-Poezja-jak-spoiwo',
        'info_dict': {
            'id': '2534482',
            'title': 'Żagaryści. Poezja jak spoiwo',
            'description': 'md5:f18d95d5dcba747a09b635e21a4c0695',
        },
        'playlist': [{
            'md5': 'd07559829f61d5a93a75755987ded760',
            'info_dict': {
                'id': '2516679',
                'ext': 'mp3',
                'title': 'md5:c6e1234e0b747ad883cb91b7ad06b98c',
                'timestamp': 1592654400,
                'upload_date': '20200620',
                'duration': 1430,
                'thumbnail': r're:^https?://static\.prsa\.pl/images/.*\.jpg$'
            },
        }],
    }, {
        # PR4 audition - other frontend
        'url': 'https://www.polskieradio.pl/10/6071/Artykul/2610977,Poglos-29-pazdziernika-godz-2301',
        'info_dict': {
            'id': '2610977',
            'ext': 'mp3',
            'title': 'Pogłos 29 października godz. 23:01',
        },
    }, {
        'url': 'https://polskieradio24.pl/130/4503/Artykul/2621876,Narusza-nasza-suwerennosc-Publicysci-o-uzaleznieniu-funduszy-UE-od-praworzadnosci',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage, urlh = self._download_webpage_handle(url, playlist_id)
        if PolskieRadioIE.suitable(urlh.url):
            return self.url_result(urlh.url, PolskieRadioIE, playlist_id)

        content = self._search_regex(
            r'(?s)<div[^>]+class="\s*this-article\s*"[^>]*>(.+?)<div[^>]+class="tags"[^>]*>',
            webpage, 'content', default=None)

        timestamp = unified_timestamp(self._html_search_regex(
            r'(?s)<span[^>]+id="datetime2"[^>]*>(.+?)</span>',
            webpage, 'timestamp', default=None))

        thumbnail_url = self._og_search_thumbnail(webpage, default=None)

        title = self._og_search_title(webpage).strip()

        description = strip_or_none(self._og_search_description(webpage, default=None))
        description = description.replace('\xa0', ' ') if description is not None else None

        if not content:
            return {
                'id': playlist_id,
                'url': self._proto_relative_url(
                    self._search_regex(
                        r"source:\s*'(//static\.prsa\.pl/[^']+)'",
                        webpage, 'audition record url')),
                'title': title,
                'description': description,
                'timestamp': timestamp,
                'thumbnail': thumbnail_url,
            }

        entries = self._extract_webpage_player_entries(content, playlist_id, {
            'title': title,
            'timestamp': timestamp,
            'thumbnail': thumbnail_url,
        })

        return self.playlist_result(entries, playlist_id, title, description)


class PolskieRadioIE(InfoExtractor):
    # new next.js sites, excluding radiokierowcow.pl
    _VALID_URL = r'https?://(?:[^/]+\.)?polskieradio(?:24)?\.pl/artykul/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://jedynka.polskieradio.pl/artykul/1587943',
        'info_dict': {
            'id': '1587943',
            'title': 'Prof. Andrzej Nowak: o historii nie da się myśleć beznamiętnie',
            'description': 'md5:12f954edbf3120c5e7075e17bf9fc5c5',
        },
        'playlist': [{
            'md5': '2984ee6ce9046d91fc233bc1a864a09a',
            'info_dict': {
                'id': '7a85d429-5356-4def-a347-925e4ae7406b',
                'ext': 'mp3',
                'title': 'md5:d4623290d4ac983bf924061c75c23a0d',
            },
        }],
    }, {
        'url': 'https://trojka.polskieradio.pl/artykul/1632955',
        'only_matching': True,
    }, {
        # with mp4 video
        'url': 'https://trojka.polskieradio.pl/artykul/1634903',
        'only_matching': True,
    }, {
        'url': 'https://jedynka.polskieradio.pl/artykul/3042436,Polityka-wschodnia-ojca-i-syna-Wladyslawa-Lokietka-i-Kazimierza-Wielkiego',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        article_data = traverse_obj(
            self._search_nextjs_data(webpage, playlist_id), ('props', 'pageProps', 'data', 'articleData'))

        title = strip_or_none(article_data['title'])

        description = strip_or_none(article_data.get('lead'))

        entries = [{
            'url': entry['file'],
            'ext': determine_ext(entry.get('fileName')),
            'id': self._search_regex(
                r'([a-f\d]{8}-(?:[a-f\d]{4}-){3}[a-f\d]{12})', entry['file'], 'entry id'),
            'title': strip_or_none(entry.get('description')) or title,
        } for entry in article_data.get('attachments') or () if entry['fileType'] in ('Audio', )]

        return self.playlist_result(entries, playlist_id, title, description)


class PolskieRadioAuditionIE(InfoExtractor):
    # new next.js sites
    IE_NAME = 'polskieradio:audition'
    _VALID_URL = r'https?://(?:[^/]+\.)?polskieradio\.pl/audycj[ae]/(?P<id>\d+)'
    _TESTS = [{
        # articles, PR1
        'url': 'https://jedynka.polskieradio.pl/audycje/5102',
        'info_dict': {
            'id': '5102',
            'title': 'Historia żywa',
            'thumbnail': r're:https://static\.prsa\.pl/images/.+',
        },
        'playlist_mincount': 38,
    }, {
        # episodes, PR1
        'url': 'https://jedynka.polskieradio.pl/audycje/5769',
        'info_dict': {
            'id': '5769',
            'title': 'AgroFakty',
            'thumbnail': r're:https://static\.prsa\.pl/images/.+',
        },
        'playlist_mincount': 269,
    }, {
        # both episodes and articles, PR3
        'url': 'https://trojka.polskieradio.pl/audycja/8906',
        'info_dict': {
            'id': '8906',
            'title': 'Trójka budzi',
            'thumbnail': r're:https://static\.prsa\.pl/images/.+',
        },
        'playlist_mincount': 722,
    }]

    def _call_lp3(self, path, query, video_id, note):
        return self._download_json(
            f'https://lp3test.polskieradio.pl/{path}', video_id, note,
            query=query, headers={'x-api-key': '9bf6c5a2-a7d0-4980-9ed7-a3f7291f2a81'})

    def _entries(self, playlist_id, has_episodes, has_articles):
        for i in itertools.count(1) if has_episodes else []:
            page = self._call_lp3(
                'AudioArticle/GetListByCategoryId', {
                    'categoryId': playlist_id,
                    'PageSize': 10,
                    'skip': i,
                    'format': 400,
                }, playlist_id, f'Downloading episode list page {i}')
            if not traverse_obj(page, 'data'):
                break
            for episode in page['data']:
                yield {
                    'id': str(episode['id']),
                    'url': episode['file'],
                    'title': episode.get('title'),
                    'duration': int_or_none(episode.get('duration')),
                    'timestamp': parse_iso8601(episode.get('datePublic')),
                }

        for i in itertools.count(1) if has_articles else []:
            page = self._call_lp3(
                'Article/GetListByCategoryId', {
                    'categoryId': playlist_id,
                    'PageSize': 9,
                    'skip': i,
                    'format': 400,
                }, playlist_id, f'Downloading article list page {i}')
            if not traverse_obj(page, 'data'):
                break
            for article in page['data']:
                yield {
                    '_type': 'url_transparent',
                    'ie_key': PolskieRadioIE.ie_key(),
                    'id': str(article['id']),
                    'url': article['url'],
                    'title': article.get('shortTitle'),
                    'description': traverse_obj(article, ('description', 'lead')),
                    'timestamp': parse_iso8601(article.get('datePublic')),
                }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        page_props = traverse_obj(
            self._search_nextjs_data(self._download_webpage(url, playlist_id), playlist_id),
            ('props', 'pageProps', ('data', None)), get_all=False)

        has_episodes = bool(traverse_obj(page_props, 'episodes', 'audios'))
        has_articles = bool(traverse_obj(page_props, 'articles'))

        return self.playlist_result(
            self._entries(playlist_id, has_episodes, has_articles), playlist_id,
            title=traverse_obj(page_props, ('details', 'name')),
            description=traverse_obj(page_props, ('details', 'description', 'lead')),
            thumbnail=traverse_obj(page_props, ('details', 'photo')))


class PolskieRadioCategoryIE(InfoExtractor):
    # legacy sites
    IE_NAME = 'polskieradio:category'
    _VALID_URL = r'https?://(?:www\.)?polskieradio\.pl/\d+(?:,[^/]+)?/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.polskieradio.pl/7/129,Sygnaly-dnia?ref=source',
        'only_matching': True
    }, {
        'url': 'http://www.polskieradio.pl/37,RedakcjaKatolicka/4143,Kierunek-Krakow',
        'info_dict': {
            'id': '4143',
            'title': 'Kierunek Kraków',
        },
        'playlist_mincount': 61
    }, {
        'url': 'http://www.polskieradio.pl/10,czworka/214,muzyka',
        'info_dict': {
            'id': '214',
            'title': 'Muzyka',
        },
        'playlist_mincount': 61
    }, {
        'url': 'http://www.polskieradio.pl/8,Dwojka/196,Publicystyka',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if PolskieRadioLegacyIE.suitable(url) else super().suitable(url)

    def _entries(self, url, page, category_id):
        content = page
        for page_num in itertools.count(2):
            for a_entry, entry_id in re.findall(
                    r'(?s)<article[^>]+>.*?(<a[^>]+href=["\']/\d+/\d+/Artykul/(\d+)[^>]+>).*?</article>',
                    content):
                entry = extract_attributes(a_entry)
                href = entry.get('href')
                if not href:
                    continue
                yield self.url_result(
                    compat_urlparse.urljoin(url, href), PolskieRadioLegacyIE,
                    entry_id, entry.get('title'))
            mobj = re.search(
                r'<div[^>]+class=["\']next["\'][^>]*>\s*<a[^>]+href=(["\'])(?P<url>(?:(?!\1).)+)\1',
                content)
            if not mobj:
                break
            next_url = compat_urlparse.urljoin(url, mobj.group('url'))
            content = self._download_webpage(
                next_url, category_id, 'Downloading page %s' % page_num)

    def _real_extract(self, url):
        category_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, category_id)
        if PolskieRadioAuditionIE.suitable(urlh.url):
            return self.url_result(urlh.url, PolskieRadioAuditionIE, category_id)
        title = self._html_search_regex(
            r'<title>([^<]+) - [^<]+ - [^<]+</title>',
            webpage, 'title', fatal=False)
        return self.playlist_result(
            self._entries(url, webpage, category_id),
            category_id, title)


class PolskieRadioPlayerIE(InfoExtractor):
    IE_NAME = 'polskieradio:player'
    _VALID_URL = r'https?://player\.polskieradio\.pl/anteny/(?P<id>[^/]+)'

    _BASE_URL = 'https://player.polskieradio.pl'
    _PLAYER_URL = 'https://player.polskieradio.pl/main.bundle.js'
    _STATIONS_API_URL = 'https://apipr.polskieradio.pl/api/stacje'

    _TESTS = [{
        'url': 'https://player.polskieradio.pl/anteny/trojka',
        'info_dict': {
            'id': '3',
            'ext': 'm4a',
            'title': 'Trójka',
        },
        'params': {
            'format': 'bestaudio',
            'skip_download': 'endless stream',
        },
    }]

    def _get_channel_list(self, channel_url='no_channel'):
        player_code = self._download_webpage(
            self._PLAYER_URL, channel_url,
            note='Downloading js player')
        channel_list = js_to_json(self._search_regex(
            r';var r="anteny",a=(\[.+?\])},', player_code, 'channel list'))
        return self._parse_json(channel_list, channel_url)

    def _real_extract(self, url):
        channel_url = self._match_id(url)
        channel_list = self._get_channel_list(channel_url)

        channel = next((c for c in channel_list if c.get('url') == channel_url), None)

        if not channel:
            raise ExtractorError('Channel not found')

        station_list = self._download_json(self._STATIONS_API_URL, channel_url,
                                           note='Downloading stream url list',
                                           headers={
                                               'Accept': 'application/json',
                                               'Referer': url,
                                               'Origin': self._BASE_URL,
                                           })
        station = next((s for s in station_list
                        if s.get('Name') == (channel.get('streamName') or channel.get('name'))), None)
        if not station:
            raise ExtractorError('Station not found even though we extracted channel')

        formats = []
        for stream_url in station['Streams']:
            stream_url = self._proto_relative_url(stream_url)
            if stream_url.endswith('/playlist.m3u8'):
                formats.extend(self._extract_m3u8_formats(stream_url, channel_url, live=True))
            elif stream_url.endswith('/manifest.f4m'):
                formats.extend(self._extract_mpd_formats(stream_url, channel_url))
            elif stream_url.endswith('/Manifest'):
                formats.extend(self._extract_ism_formats(stream_url, channel_url))
            else:
                formats.append({
                    'url': stream_url,
                })

        return {
            'id': compat_str(channel['id']),
            'formats': formats,
            'title': channel.get('name') or channel.get('streamName'),
            'display_id': channel_url,
            'thumbnail': f'{self._BASE_URL}/images/{channel_url}-color-logo.png',
            'is_live': True,
        }


class PolskieRadioPodcastBaseExtractor(InfoExtractor):
    _API_BASE = 'https://apipodcasts.polskieradio.pl/api'

    def _parse_episode(self, data):
        return {
            'id': data['guid'],
            'formats': [{
                'url': data['url'],
                'filesize': int_or_none(data.get('fileSize')),
            }],
            'title': data['title'],
            'description': data.get('description'),
            'duration': int_or_none(data.get('length')),
            'timestamp': parse_iso8601(data.get('publishDate')),
            'thumbnail': url_or_none(data.get('image')),
            'series': data.get('podcastTitle'),
            'episode': data['title'],
        }


class PolskieRadioPodcastListIE(PolskieRadioPodcastBaseExtractor):
    IE_NAME = 'polskieradio:podcast:list'
    _VALID_URL = r'https?://podcasty\.polskieradio\.pl/podcast/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://podcasty.polskieradio.pl/podcast/8/',
        'info_dict': {
            'id': '8',
            'title': 'Śniadanie w Trójce',
            'description': 'md5:57abcc27bc4c6a6b25baa3061975b9ef',
            'uploader': 'Beata Michniewicz',
        },
        'playlist_mincount': 714,
    }]
    _PAGE_SIZE = 10

    def _call_api(self, podcast_id, page):
        return self._download_json(
            f'{self._API_BASE}/Podcasts/{podcast_id}/?pageSize={self._PAGE_SIZE}&page={page}',
            podcast_id, f'Downloading page {page}')

    def _real_extract(self, url):
        podcast_id = self._match_id(url)
        data = self._call_api(podcast_id, 1)

        def get_page(page_num):
            page_data = self._call_api(podcast_id, page_num + 1) if page_num else data
            yield from (self._parse_episode(ep) for ep in page_data['items'])

        return {
            '_type': 'playlist',
            'entries': InAdvancePagedList(
                get_page, math.ceil(data['itemCount'] / self._PAGE_SIZE), self._PAGE_SIZE),
            'id': str(data['id']),
            'title': data.get('title'),
            'description': data.get('description'),
            'uploader': data.get('announcer'),
        }


class PolskieRadioPodcastIE(PolskieRadioPodcastBaseExtractor):
    IE_NAME = 'polskieradio:podcast'
    _VALID_URL = r'https?://podcasty\.polskieradio\.pl/track/(?P<id>[a-f\d]{8}(?:-[a-f\d]{4}){4}[a-f\d]{8})'
    _TESTS = [{
        'url': 'https://podcasty.polskieradio.pl/track/6eafe403-cb8f-4756-b896-4455c3713c32',
        'info_dict': {
            'id': '6eafe403-cb8f-4756-b896-4455c3713c32',
            'ext': 'mp3',
            'title': 'Theresa May rezygnuje. Co dalej z brexitem?',
            'description': 'md5:e41c409a29d022b70ef0faa61dbded60',
            'episode': 'Theresa May rezygnuje. Co dalej z brexitem?',
            'duration': 2893,
            'thumbnail': 'https://static.prsa.pl/images/58649376-c8a0-4ba2-a714-78b383285f5f.jpg',
            'series': 'Raport o stanie świata',
        },
    }]

    def _real_extract(self, url):
        podcast_id = self._match_id(url)
        data = self._download_json(
            f'{self._API_BASE}/audio',
            podcast_id, 'Downloading podcast metadata',
            data=json.dumps({
                'guids': [podcast_id],
            }).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
            })
        return self._parse_episode(data[0])


class PolskieRadioRadioKierowcowIE(PolskieRadioBaseExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiokierowcow\.pl/artykul/(?P<id>[0-9]+)'
    IE_NAME = 'polskieradio:kierowcow'

    _TESTS = [{
        'url': 'https://radiokierowcow.pl/artykul/2694529',
        'info_dict': {
            'id': '2694529',
            'title': 'Zielona fala reliktem przeszłości?',
            'description': 'md5:343950a8717c9818fdfd4bd2b8ca9ff2',
        },
        'playlist_count': 3,
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id)
        nextjs_build = self._search_nextjs_data(webpage, media_id)['buildId']
        article = self._download_json(
            f'https://radiokierowcow.pl/_next/data/{nextjs_build}/artykul/{media_id}.json?articleId={media_id}',
            media_id)
        data = article['pageProps']['data']
        title = data['title']
        entries = self._extract_webpage_player_entries(data['content'], media_id, {
            'title': title,
        })

        return {
            '_type': 'playlist',
            'id': media_id,
            'entries': entries,
            'title': title,
            'description': data.get('lead'),
        }

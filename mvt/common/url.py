# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import requests
from typing import Optional
from tld import get_tld

SHORTENER_DOMAINS = [
    "1drv.ms",
    "1link.in",
    "1url.com",
    "2big.at",
    "2pl.us",
    "2tu.us",
    "2ya.com",
    "4url.cc",
    "6url.com",
    "a.gg",
    "a.nf",
    "a2a.me",
    "abbrr.com",
    "adf.ly",
    "adjix.com",
    "alturl.com",
    "atu.ca",
    "b23.ru",
    "bacn.me",
    "bit.do",
    "bit.ly",
    "bkite.com",
    "bloat.me",
    "budurl.com",
    "buff.ly",
    "buk.me",
    "burnurl.com",
    "c-o.in",
    "chilp.it",
    "clck.ru",
    "cli.gs",
    "clickmeter.com",
    "cort.as",
    "cut.ly",
    "cuturl.com",
    "decenturl.com",
    "decenturl.com",
    "dfl8.me",
    "digbig.com",
    "digg.com",
    "doiop.com",
    "dwarfurl.com",
    "dy.fi",
    "easyuri.com",
    "easyurl.net",
    "eepurl.com",
    "esyurl.com",
    "ewerl.com",
    "fa.b",
    "ff.im",
    "fff.to",
    "fhurl.com",
    "fire.to",
    "firsturl.de",
    "flic.kr",
    "fly2.ws",
    "fon.gs",
    "forms.gle",
    "fwd4.me",
    "gl.am",
    "go.9nl.com",
    "go2.me",
    "go2cut.com",
    "goo.gl",
    "goshrink.com",
    "gowat.ch",
    "gri.ms",
    "gurl.es",
    "hellotxt.com",
    "hex.io",
    "hover.com",
    "href.in",
    "ht.ly",
    "htxt.it",
    "hugeurl.com",
    "hurl.it",
    "hurl.me",
    "hurl.ws",
    "icanhaz.com",
    "idek.net",
    "inreply.to",
    "is.gd",
    "iscool.net",
    "iterasi.net",
    "jijr.com",
    "jmp2.net",
    "just.as",
    "kissa.be",
    "kl.am",
    "klck.me",
    "korta.nu",
    "krunchd.com",
    "liip.to",
    "liltext.com",
    "lin.cr",
    "linkbee.com",
    "linkbun.ch",
    "liurl.cn",
    "ln-s.net",
    "ln-s.ru",
    "lnk.gd",
    "lnk.in",
    "lnkd.in",
    "loopt.us",
    "lru.jp",
    "lt.tl",
    "lurl.no",
    "metamark.net",
    "migre.me",
    "minilien.com",
    "miniurl.com",
    "minurl.fr",
    "moourl.com",
    "myurl.in",
    "ne1.net",
    "njx.me",
    "nn.nf",
    "notlong.com",
    "nsfw.in",
    "o-x.fr",
    "om.ly",
    "ow.ly",
    "pd.am",
    "pic.gd",
    "ping.fm",
    "piurl.com",
    "pnt.me",
    "poprl.com",
    "post.ly",
    "posted.at",
    "profile.to",
    "qicute.com",
    "qlnk.net",
    "quip-art.com",
    "rb6.me",
    "redirx.com",
    "ri.ms",
    "rickroll.it",
    "riz.gd",
    "rsmonkey.com",
    "ru.ly",
    "rubyurl.com",
    "s7y.us",
    "safe.mn",
    "sharein.com",
    "sharetabs.com",
    "shorl.com",
    "short.ie",
    "short.to",
    "shortlinks.co.uk",
    "shortna.me",
    "shorturl.com",
    "shoturl.us",
    "shrinkify.com",
    "shrinkster.com",
    "shrt.st",
    "shrten.com",
    "shrunkin.com",
    "shw.me",
    "simurl.com",
    "sn.im",
    "snipr.com",
    "snipurl.com",
    "snurl.com",
    "sp2.ro",
    "spedr.com",
    "sqrl.it",
    "starturl.com",
    "sturly.com",
    "su.pr",
    "t.co",
    "tcrn.ch",
    "thrdl.es",
    "tighturl.com",
    "tiny.cc",
    "tiny.pl",
    "tiny123.com",
    "tinyarro.ws",
    "tinytw.it",
    "tinyuri.ca",
    "tinyurl.com",
    "tinyvid.io",
    "tnij.org",
    "to.ly",
    "togoto.us",
    "tr.im",
    "tr.my",
    "traceurl.com",
    "turo.us",
    "tweetburner.com",
    "twirl.at",
    "twit.ac",
    "twitterpan.com",
    "twitthis.com",
    "twiturl.de",
    "twurl.cc",
    "twurl.nl",
    "u.mavrev.com",
    "u.nu",
    "u6e.de",
    "ub0.cc",
    "updating.me",
    "ur1.ca",
    "url.co.uk",
    "url.ie",
    "url4.eu",
    "urlao.com",
    "urlbrief.com",
    "urlcover.com",
    "urlcut.com",
    "urlenco.de",
    "urlhawk.com",
    "urlkiss.com",
    "urlot.com",
    "urlpire.com",
    "urlx.ie",
    "urlx.org",
    "urlzen.com",
    "virl.com",
    "vl.am",
    "w3t.org",
    "wapurl.co.uk",
    "wipi.es",
    "wp.me",
    "x.co",
    "x.se",
    "xaddr.com",
    "xeeurl.com",
    "xr.com",
    "xrl.in",
    "xrl.us",
    "xurl.jp",
    "xzb.cc",
    "yep.it",
    "yfrog.com",
    "ymlp.com",
    "yweb.com",
    "zi.ma",
    "zi.pe",
    "zipmyurl.com",
    "zz.gd",
]


class URL:

    def __init__(self, url: str) -> None:
        if type(url) == bytes:
            url = url.decode()

        self.url = url
        self.domain = self.get_domain()
        self.top_level = self.get_top_level()
        self.is_shortened = False

    def get_domain(self) -> None:
        """Get the domain from a URL.

        :param url: URL to parse
        :type url: str
        :returns: Domain name extracted from URL
        :rtype: str

        """
        # TODO: Properly handle exception.
        try:
            return get_tld(self.url,
                           as_object=True,
                           fix_protocol=True).parsed_url.netloc.lower().lstrip("www.")
        except Exception:
            return None

    def get_top_level(self) -> None:
        """Get only the top-level domain from a URL.

        :param url: URL to parse
        :type url: str
        :returns: Top-level domain name extracted from URL
        :rtype: str

        """
        # TODO: Properly handle exception.
        try:
            return get_tld(self.url, as_object=True, fix_protocol=True).fld.lower()
        except Exception:
            return None

    def check_if_shortened(self) -> bool:
        """Check if the URL is among list of shortener services.


        :returns: True if the URL is shortened, otherwise False

        :rtype: bool

        """
        if self.domain.lower() in SHORTENER_DOMAINS:
            self.is_shortened = True

        return self.is_shortened

    def unshorten(self) -> Optional[str]:
        """Unshorten the URL by requesting an HTTP HEAD response."""
        res = requests.head(self.url)
        if str(res.status_code).startswith("30"):
            return res.headers["Location"]

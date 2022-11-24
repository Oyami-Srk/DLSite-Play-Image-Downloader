import io
import os
import re
from http.cookiejar import MozillaCookieJar, CookieJar, Cookie
from pathlib import Path

import requests
from PIL import Image

from ImageBuilder import build_image

ziptree_url = "https://play.dl.dlsite.com/content/work/doujin/{RJ_CODE_EX}/{RJ_CODE}/ziptree.json"
product_info_url = "https://www.dlsite.com/maniax/product/info/ajax?product_id={RJ_CODE}"
download_token_url = "https://play.dlsite.com/api/download_token?workno={RJ_CODE}"


# secret
# cookies_txt_file = "cookies-play-dlsite-com.txt"
# cookiejar = MozillaCookieJar(cookies_txt_file)
# cookiejar.load()


class DLSitePlayImageDownloader:
    def __init__(self, rj_code: str, cookie_jar: CookieJar):
        assert rj_code[:2] == "RJ"
        self.RJ_CODE = rj_code
        self.product_info = requests.get(product_info_url.format(RJ_CODE=self.RJ_CODE)).json().popitem()[1]
        self.download_token = requests.get(
            download_token_url.format(RJ_CODE=self.RJ_CODE),
            timeout=10,
            headers={
                "Referer": "https://play.dlsite.com",
                "Host": "play.dlsite.com",
            }, cookies=cookie_jar
        ).json()
        if "status" in self.download_token and self.download_token["status"] == 401:
            raise Exception("Authorized expired. Please use a new cookie.")
        self.URL = self.download_token["url"]
        self.RJ_CODE_EX = re.findall(r"(RJ\d+)/RJ\d+", self.URL)[0]
        self.zip_tree = requests.get(
            ziptree_url.format(RJ_CODE_EX=self.RJ_CODE_EX, RJ_CODE=self.RJ_CODE),
            timeout=10,
            params=self.download_token["params"]
        ).json()

    def get_image(self, hashname: str) -> Image:
        if hashname not in self.zip_tree["playfile"]:
            raise Exception("Hashname not found.")
        file_info = self.zip_tree["playfile"][hashname]
        if file_info["type"] != "image":
            raise Exception("Only support image")
        image_info = file_info["image"]["optimized"]
        assert image_info["crypt"] is True
        width = image_info["width"]
        height = image_info["height"]
        resp = requests.get(self.URL + "/optimized/" + hashname, params=self.download_token["params"])
        assert resp.status_code == 200
        cropped_image = Image.open(io.BytesIO(resp.content))
        return build_image(hashname, cropped_image, width, height)

    def do_walk_tree(self, folder: list[dict], base_dir=""):
        for item in folder:
            if item["type"] == "folder":
                self.do_walk_tree(item["children"], base_dir + "/" + item["path"])
            elif item["type"] == "file":
                filename = item["name"]
                hashname = item["hashname"]
                if self.zip_tree["playfile"][hashname]["type"] == "image":
                    os.makedirs(base_dir, exist_ok=True)
                    if os.path.exists(base_dir + "/" + filename):
                        print(f"{base_dir}/{filename} is already existed")
                        continue
                    img = self.get_image(hashname)
                    with open(base_dir + "/" + filename, "wb") as f:
                        img.save(f)
                        print(f"{f.name} saved.")

    def walk_tree(self, base_dir=""):
        self.do_walk_tree(self.zip_tree["tree"], base_dir)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='DLSite Image Downloader')
    parser.add_argument('rjcode', metavar='RJCODE', type=str)
    parser.add_argument('--path', metavar='PATH', type=Path, default="")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--cookie', metavar='COOKIE.TXT', type=Path)
    group.add_argument('--play-session', metavar='COOKIE.TXT', type=str)

    args = parser.parse_args()

    if args.cookie is None and args.play_session is None:
        print("You should give me your cookie.txt or play-session.")

    jar = MozillaCookieJar()
    if args.cookie is not None:
        jar.load(args.cookie)
    else:
        jar.set_cookie(
            Cookie(0, 'play_session', args.play_session, None, False, 'play.dlsite.com',
                   True, False, '/', False, False, 1669283197, False, None, None, None, False)
        )

    p = Path(args.path)
    rjcode = args.rjcode.upper()
    p = p.joinpath(rjcode)
    p = str(p)
    if re.match(r"^RJ\d+$", rjcode) is None:
        raise Exception("RJCode is illegal")
    downloader = DLSitePlayImageDownloader(rjcode, jar)
    downloader.walk_tree(base_dir=p)

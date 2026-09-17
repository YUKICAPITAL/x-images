"""日記の写真を1枚の画像にして x-images へ上げ、公開URLを返す（YUKI CAPITAL）
使い方: GH_TOKEN=... python3 diary_image.py 2026-09-18 写真1 [写真2 写真3 写真4]
  --dry-run を末尾に付けると、組写真を作るだけで上げない
規定の正本: 01 WORKFLOW「日記の写真」。IFTTT の画像つき投稿は1投稿1枚のため、2〜4枚は1枚に組む。
"""
import sys, os, json, base64, time, hashlib, urllib.request
from PIL import Image, ImageOps
REPO = 'YUKICAPITAL/x-images'
def cover(im, w, h):
    return ImageOps.fit(im, (w, h), method=Image.LANCZOS, centering=(0.5, 0.5))
def build(paths, out):
    ims = [ImageOps.exif_transpose(Image.open(p)).convert('RGB') for p in paths]
    n = len(ims); G = 8; BG = (17, 17, 17)
    if not 1 <= n <= 4: sys.exit('NG: 写真は1〜4枚')
    if n == 1:
        c = ims[0]; c.thumbnail((2048, 2048), Image.LANCZOS)
    elif n == 2:
        W, H = 1600, 1000; cw = (W - G) // 2; c = Image.new('RGB', (W, H), BG)
        c.paste(cover(ims[0], cw, H), (0, 0)); c.paste(cover(ims[1], W - cw - G, H), (cw + G, 0))
    elif n == 3:
        W, H = 1600, 1000; cw = (W - G) // 2; ch = (H - G) // 2; c = Image.new('RGB', (W, H), BG)
        c.paste(cover(ims[0], cw, H), (0, 0))
        c.paste(cover(ims[1], W - cw - G, ch), (cw + G, 0)); c.paste(cover(ims[2], W - cw - G, H - ch - G), (cw + G, ch + G))
    else:
        W = H = 1600; s = (W - G) // 2; c = Image.new('RGB', (W, H), BG)
        for i, im in enumerate(ims): c.paste(cover(im, s, s), ((s + G) * (i % 2), (s + G) * (i // 2)))
    clean = Image.new('RGB', c.size); clean.paste(c)          # 撮影情報・位置情報を持たない新規画像
    q = 90
    while True:
        clean.save(out, 'JPEG', quality=q)
        if os.path.getsize(out) <= 4_500_000 or q <= 60: break
        q -= 10
    if len(Image.open(out).getexif()) != 0: sys.exit('NG: 撮影情報が残っている')
    return n, clean.size, os.path.getsize(out)
def main():
    args = sys.argv[1:]; dry = '--dry-run' in args; args = [a for a in args if a != '--dry-run']
    date, photos = args[0], args[1:]
    out = f'/home/claude/{date}_diary.jpg'
    n, size, nbytes = build(photos, out)
    print(f'組写真: {n}枚 → {size[0]}x{size[1]} {nbytes}bytes 撮影情報0件')
    if dry: return
    tok = os.environ['GH_TOKEN']
    name = f'images/{date}_diary_{time.strftime("%H%M%S")}.jpg'   # 同名の上書きを作らない（配信の古い画像が出るのを防ぐ）
    body = json.dumps({'message': f'diary {date}', 'content': base64.b64encode(open(out, 'rb').read()).decode()}).encode()
    req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/{name}', data=body, method='PUT',
          headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github+json'})
    urllib.request.urlopen(req)
    url = f'https://raw.githubusercontent.com/{REPO}/main/{name}'
    for _ in range(10):
        try:
            got = urllib.request.urlopen(url).read()
            if hashlib.sha256(got).digest() == hashlib.sha256(open(out, 'rb').read()).digest():
                print('公開URL確認: 200・内容一致'); print('PHOTO_URL=' + url); return
        except Exception: pass
        time.sleep(3)
    sys.exit('NG: 公開URLで取得できない。日記は投稿せず本人へ報告する')
if __name__ == '__main__': main()

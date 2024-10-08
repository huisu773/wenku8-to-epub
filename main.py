"""
从wenku8.net下载小说，并按卷/整本转epub
"""
import os
import sys

from PIL import Image

from create_epub import Epub, XML_TITLE_LABEL, XML_PARAGRAPH_LABEL, XML_IMAGE_LABEL
from wenku8 import Wenku8Download

# --------自定义参数------------

# epub存储目录（相对路径/绝对路径）
save_epub_dir = 'epub'
# 每次网络请求后停顿时间，避免封IP
sleep_time = 2
# 是否将插图第一页设为封面，若不设置就默 认使用小说详情页封面
use_divimage_set_cover = True
# 指定wenku8的hostname，可填www.wenku8.net www.wenku8.cc www.wenku8.com
wenku_host = 'www.wenku8.com'
# 反代pic.wenku8.com、app.wenku8.com的hostname：xxxx.xxxx.workers.dev 或 自定义域名
wenkupic_proxy_host = 'wk8-test.jsone.gq'
wenkuapp_proxy_host = None
# ---------------------------


if not os.path.exists(save_epub_dir):
    os.makedirs(save_epub_dir)


def download_volume(book_epub, it, mode_id=0):
    """封装chapter"""
    print('Start making volume:', wk.book['title'], it['volume'])
    for chapter_title, chapter_href in it['chapter']:
        content_title, content_list, image_urls = wk.get_chapter(chapter_href)
        if wk.error_msg:
            print('Error:', wk.error_msg)
            return False

        # 设置HTML格式
        html_body = XML_TITLE_LABEL.format(ct=chapter_title)
        if content_list:
            print('├── Start downloading chapter-text:', chapter_title)
            for p in content_list:
                html_body += XML_PARAGRAPH_LABEL.format(p=p)
            print('│   └── Download chapter-text completed.')
        elif image_urls:
            print('├── Start downloading chapter-image:', chapter_title)
            for img_url in image_urls:
                file_path, file_name, file_base = wk.save_image(img_url)
                if file_name:
                    if use_divimage_set_cover and not book_epub.is_set_cover:  # 将插图的第一张长图作为封面
                        with Image.open(file_path) as img:
                            width, height = img.size
                        if width <= height:
                            book_epub.set_cover(file_path)
                    book_epub.set_images(file_path)
                    html_body += XML_IMAGE_LABEL.format(fb=file_base, fn=file_name)
                print('│   ├──', img_url, '->', file_path, 'success' if file_name else 'fail')
            print('│   └─�� Download chapter-image completed.')
        else:
            print('├── Downloaded empty chapter.')

        # 开始分卷下载 / 整本下载
        book_epub.set_html(chapter_title, html_body, it['volume'] if mode_id == 1 else None)

    if not book_epub.is_set_cover:  # 插图第一张图片未能设置为封面，就把缩略图作为封面
        book_epub.set_cover('src/cover.jpg')
    return True


def whole_book_download():
    """整本下载"""
    book_epub = Epub()
    book_epub.set_metadata(wk.book['title'], author=wk.book['author'], desp=wk.book['description'],
                           publisher=wk.book['publisher'], source_url=wk.book['api']['detail'],
                           tag_list=wk.book['tags'], vol_idx=1,
                           cover_path='src/cover.jpg' if not use_divimage_set_cover else None)

    for it in wk.book['toc']:
        flag = download_volume(book_epub, it, mode_id=1)
        if not flag:
            return
        print('└── Making volume completed.\n')

    book_epub.pack_book(save_epub_dir)
    wk.clear_src()


def volume_by_volume_download():
    """按卷下载，单独下载某一/些卷"""
    print_format([it['volume'] for it in wk.book['toc']])
    volume_idx_list = input('输入要下载的卷索引，下载多卷用空格分割��默认0，逐卷下载）：').split()
    print()
    # 检查输入索引是否合法
    if volume_idx_list and all(map(lambda i: i.isdigit() and (1 <= int(i) <= len(wk.book['toc'])), volume_idx_list)):
        volume_idx_list = sorted(map(int, volume_idx_list))
    elif volume_idx_list == [] or '0' in volume_idx_list:
        volume_idx_list = list(map(lambda i: i + 1, range(len(wk.book['toc']))))
    else:
        print('Error: volume_id is valid.')
        return

    vol_idx = 0
    for it in wk.book['toc']:
        vol_idx += 1
        if vol_idx not in volume_idx_list:
            continue

        wk.image_idx = 0

        book_epub = Epub()
        book_epub.set_metadata(wk.book['title'], it['volume'], author=wk.book['author'], desp=wk.book['description'],
                               publisher=wk.book['publisher'], source_url=wk.book['api']['detail'],
                               tag_list=wk.book['tags'], vol_idx=vol_idx,
                               cover_path='src/cover.jpg' if not use_divimage_set_cover else None)

        flag = download_volume(book_epub, it, mode_id=0)
        if not flag:
            return

        book_epub.pack_book(save_epub_dir)
        print('└── Packing volume completed.\n')
        wk.clear_src()


def print_format(volume_list):
    """格式化打印每卷标题"""
    max_chars_per_line = 55  # 每行的最大字符数
    max_unit_len = max([len(it) for it in volume_list])
    max_ele_per_line_num = max_chars_per_line // (max_unit_len + 4)

    template = "{0:>2d}: {1:{2}<{3}s}\t"

    total_text = ""
    current_line = ""
    current_line_num = 0
    for idx, volume_title in enumerate(volume_list):
        current_line_num += 1
        if current_line_num > max_ele_per_line_num:
            total_text += current_line.rstrip() + '\n'
            current_line_num = 1
            current_line = template.format(idx + 1, volume_title, chr(12288), max_unit_len)  # 使用chr(12288)填充
        else:
            current_line += template.format(idx + 1, volume_title, chr(12288), max_unit_len)

    total_text += current_line
    print(total_text)


if __name__ == '__main__':
    book_ids = [
        114
    ]

    for book_id in book_ids:
        print(f"\nProcessing book ID: {book_id}")
        
        wk = Wenku8Download(str(book_id), wenku_host, wenkupic_proxy_host, wenkuapp_proxy_host)
        if wk.error_msg:
            print('Error:', wk.error_msg)
            continue
        wk.sleep_time = sleep_time  # 设置延迟时间

        print('Light Novel Title:', wk.book['title'], '\n')

        if not wk.book['copyright']:
            print('Note: web copyright is restricted and will be downloaded from APP.\n')

        # 默认使用整本下载模式
        whole_book_download()

        print(f"Finished processing book ID: {book_id}\n")
        print("-" * 50)

    print("All books have been processed.")

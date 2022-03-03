import asyncio
import time
import traceback
import aiohttp
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
import sys

path = "card_full"  # 设置图片的下载路径
path_output = "card_full转换" # 设置图片的转换路径

Path(path).mkdir(parents = True, exist_ok = True) # parents：如果父目录不存在，是否创建父目录。exist_ok：只有在目录不存在时创建目录，目录已存在时不会抛出异常。

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 Edg/97.0.1072.76'
}

proxy = {}
# 若不用代理，将链接清空即可。

def get_urls():
    '''
    图片下载链接获取（同步）
    '''
    global get_urls_msg
    start_time = time.time()
    base = "https://redive.estertion.win/card/full/"
    print('开始进行爬取，请稍后......')
    try:
        resp = requests.get(base, headers = headers, proxies = proxy, timeout=90) # 以get方式请求url，得到响应赋值给resp。proxies = prox添加代理
    except:
        print('网页请求超时，请检查网络连接')
        sys.exit() # 结束程序
    resp.encodin = 'utf-8'
    main_page = BeautifulSoup(resp.text, 'html.parser')
    alist = main_page.find('body').find_all('a')
    urls = [base + a.get('href') for a in alist]
    end_time = time.time()
    use_time = int(end_time - start_time)
    print(f'共爬取到{len(urls)}个文件地址，即将开始下载')
    get_urls_msg = f'\n共爬取到{len(urls)}个文件，爬取用时{use_time}秒'
    time.sleep(3)
    return urls

def changeType(path_input, path_output, img_type = "png"):
    '''
    图片转码
    '''
    start = time.time()

    try:
        path_list = [i for i in Path(path_input).iterdir()]
        # 当路径指向一个目录时，产生该路径下的所有对象的路径。iterdir()返回的是一个生成器，需要循环遍历才能读取
    except FileNotFoundError:
        print(f'文件目录下没有 {path_input} 文件夹，请创建文件夹并将图片放入img文件夹中')
        sys.exit()

    Path(path_output).mkdir(parents = True, exist_ok = True)

    success_num = 0
    error_num = 0
    for file_path in path_list:
        s = Path(file_path).suffix # 目录中最后一个部分的扩展名
        if s in [".webp", ".jfif", ".jpeg", ".png"]:
            imname = Path(file_path).stem # 目录最后一个部分，没有后缀（仅文件名）
            pic = Path(f'{path_output}', f'{imname}.{img_type}') # 拼接路径、文件名与目标后缀
            if not pic.exists():
                try:
                    im = Image.open(file_path) # 获取图片详细属性
                    im.load() # :im.load() 含义:为图像分配内存并从文件中加载它
                    if img_type in ["png", "webp"]:
                        colour = "RGBA"
                    else: 
                        colour = "RGB"
                    im.convert(colour).save(pic, quality = 100) # 保存文件，目标目录中的同名文件会被覆盖
                    # Path(file_path).unlink(missing_ok = True) # 删除源文件，missing_ok = True表示若路径不存在则忽略异常
                    success_num += 1
                    print(f'转换成功{success_num}个：{imname}.{img_type}')
                except:
                    error_num += 1
                    print(f'error! 转换失败{error_num}个：{imname}.{s}')
                    continue
            else:
                print(f'目标文件{imname}.{img_type}已存在，不再进行转换')
        else:
            error_num += 1
            image = Path(file_path).name
            print(f'error! 转换失败{error_num}个，图片格式不受支持：{image}')

    end = time.time()

    print(f'全部转换完成！！！共成功{success_num}个，失败{error_num}个，用时{int(end - start)}秒')
    print(f'文件输出路径：{path_output}')

async def aiodownload(url):
    '''
    图片下载（异步）
    '''
    global success_download, error_download # 必须加全局声明，否则下载计数会出现错误
    success_download = 0
    error_download = 0
    name = url.split("/")[-1] # 拿到url中的最后一个/以后的内容(图片名)
    try:
        if not Path(path, name).exists(): # 文件不存在则进行下载。Path(path, name)拼接路径与文件名
            async with aiohttp.ClientSession(headers = headers) as session: # aiohttp.ClientSession()等价于requests。headers上下都可以放，放一个地方就好
                async with session.get(url) as resp: # session.get()等价于requests.get()。以get方式请求url，得到响应赋值给resp。proxy来指明代理。timeout默认5分钟
                    Path(path, name).write_bytes(await resp.content.read()) # Path.write_bytes(data)，将文件以二进制模式打开，写入二进制data并关闭。一个同名的现存文件将被覆盖。同时该方法完美解决图片出现0kb的bug
                        # resp.content.read()得到字节(二进制)对象，resp.text()得到字符串(文本)对象，resp.json()得到json对象。异步读取文件需要await挂起
                        # resp.content和resp.text只适用于requests.get().content和requests.get().text。resp.json()两种请求方式都一样
                    success_download += 1
                    print(f'图片下载成功{success_download}个：{name}')
        else:
            print(f'文件 {name} 已存在，不再进行下载')
    except:
        error_download += 1
        traceback.print_exc()
        print(f'图片下载失败{error_download}个：{name}')

async def main():
    '''
    主协程对象
    '''
    urls = get_urls() #后续需要调用两次urls，这样做只需调用一次get_urls函数，节省资源
    start = time.time() 
    tasks = [aiodownload(url) for url in urls] # 生成执行任务的列表
    await asyncio.wait(tasks)
    end = time.time()

    print('\n开始进行图片转码...')
    changeType(path, path_output)

    print(get_urls_msg)
    print(f'共下载成功{success_download}个文件，失败{error_download}个，下载用时{int(end - start)}秒\n')
    print('程序将在10秒后结束......')
    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main()) # asyncio.run()，创建事件循环，运行一个协程，关闭事件循环。
# if __name__ == '__main__':的作用
# 一个python文件通常有两种使用方法，第一是作为脚本直接执行，第二是 import 到其他的 python 脚本中被调用（模块重用）执行。
# 因此 if __name__ == 'main': 的作用就是控制这两种情况执行代码的过程，
# 在 if __name__ == 'main': 下的代码只有在第一种情况下（即文件作为脚本直接执行）才会被执行，
# 而 import 到其他脚本中是不会被执行的。
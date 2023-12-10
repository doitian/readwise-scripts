#!/usr/bin/env python3

import fileinput
import json
import utils

# Example:
#
# ```
# Reading Notes | <<银河帝国 - 阿西莫夫>>第二篇 骡
# 2023-01-27 18:58  |  Page No.: 785
# 矫揉做作地喜好各种规矩就是“有系统”，孜孜不倦且兴致勃勃地处理鸡毛蒜皮的公事就是“勤勉”；该做的事优柔寡断就是“谨慎”；不该做的事盲目地坚持到底就是“决心”。
# -------------------
# 第二篇 基地的寻找
# 2023-01-27 18:59  |  Page No.: 1357
# 最无可救药的笨蛋，就是聪明却不自知的人。你知道自己够资格，正是你够资格的原因之一。
# -------------------
# 第十二章 长老阁
# 2023-01-27 19:00  |  Page No.: 2282
# 不论民众在冷静的时候，具有何种人道胸怀，”日主十四冷静地说，“在情绪激动的时候，他们都能被煽动成暴力分子。在各个文化中通通一样
# -------------------
# ```
# https://weread.qq.com/web/reader/43132e60813ab7439g011388kd67323c0227d67d8ab4fb04#2


def collect_highlights(lines):
    last_auto_title = None
    auto_title_level = 1

    article = {
        "title": None,
        "author": None,
        "source_type": "Boox",
        "category": "books",
    }
    result = []
    pending_article = None
    for line in lines:
        line = line.strip()
        if line.startswith("Reading Notes "):
            title_author_section = line.split("<<")[1]
            title_author, section = title_author_section.split(">>")
            title, author = title_author.rsplit(" - ", maxsplit=1)
            article["title"] = title
            article["author"] = author
            if " // " in section:
                auto_title_level = 2
                h1, h2 = section.split(" // ")
                pending_article = article.copy()
                pending_article["text"] = h1
                pending_article["note"] = ".h1"
                result.append(pending_article)
                pending_article = article.copy()
                pending_article["text"] = h2
                pending_article["note"] = ".h2"
                result.append(pending_article)
                last_auto_title = h2
            else:
                pending_article = article.copy()
                pending_article["text"] = section
                pending_article["note"] = ".h1"
                result.append(pending_article)
                last_auto_title = section
            pending_article = article.copy()
        elif "Page No.: " in line:
            if pending_article is None:
                raise RuntimeError("expect pending article")
            if "location" in pending_article:
                raise RuntimeError("expect new pending article: " + line)
            pending_article["location_type"] = "page"
            pending_article["location"] = int(line.split("Page No.: ")[1])
            pending_article["highlighted_at"] = (
                line.split("  |  ")[0].replace(" ", "T") + ":00+08:00"
            )
            for prev_article in reversed(result):
                if "location" in prev_article:
                    break
                prev_article["location_type"] = "page"
                prev_article["location"] = pending_article["location"]
        elif line.startswith("-------------------"):
            if pending_article is None:
                raise RuntimeError("expect pending article")
            result.append(pending_article)
            pending_article = article.copy()
        elif pending_article is not None and "location" in pending_article:
            if "text" in pending_article:
                pending_article["text"] = "\n".join([pending_article["text"], line])
            else:
                pending_article["text"] = line
        elif pending_article is not None:
            section = line.strip()
            if " // " in section:
                h1, h2 = section.split(" // ")
                title_article = article.copy()
                title_article["text"] = h1
                title_article["note"] = ".h1"
                result.append(title_article)
                title_article = article.copy()
                title_article["text"] = h2
                title_article["note"] = ".h2"
                result.append(title_article)
            elif section != last_auto_title:
                last_auto_title = section
                title_article = article.copy()
                title_article["text"] = section
                title_article["note"] = f".h{auto_title_level}"
                result.append(title_article)
        else:
            raise RuntimeError("unexpected line: " + line)

    return result


def main(args):
    dry_run = args[1] == "-n" if len(sys.argv) > 1 else False
    input_args = args[1:] if not dry_run else args[2:]
    highlights = collect_highlights(fileinput.input(input_args))

    if dry_run:
        print(json.dumps(highlights, indent=2, ensure_ascii=False))
        return

    utils.create_highlights(highlights)


if __name__ == "__main__":
    import sys

    main(sys.argv)

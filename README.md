爬取网页标题、图片链接、文章内容
import argparse
import json
import sys
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


class PageParser(HTMLParser):
	def __init__(self, page_url):
		super().__init__(convert_charrefs=True)
		self.page_url = page_url
		self.title_parts = []
		self.content_parts = []
		self.paragraph_parts = []
		self.image_urls = []
		self._in_title = False
		self._content_depth = 0
		self._paragraph_depth = 0
		self._skip_depth = 0
		self._void_tags = {
			"area", "base", "br", "col", "embed", "hr", "img", "input",
			"link", "meta", "param", "source", "track", "wbr",
		}
		self._ignored_tags = {"footer", "form", "header", "nav", "script", "style", "svg"}
		self._block_tags = {
			"address", "article", "blockquote", "div", "h1", "h2", "h3",
			"h4", "h5", "h6", "li", "main", "p", "section", "br",
		}

	def handle_starttag(self, tag, attrs):
		attributes = dict(attrs)

		if self._skip_depth:
			if tag not in self._void_tags:
				self._skip_depth += 1
			return
		if tag in self._ignored_tags:
			self._skip_depth = 1
			return

		if tag == "title":
			self._in_title = True
		if tag in {"article", "main"}:
			self._content_depth += 1
		if tag == "p":
			self._paragraph_depth += 1
		if tag in self._block_tags:
			self._add_separator()

		if tag == "img":
			for attribute in ("src", "data-src", "data-original"):
				image_url = attributes.get(attribute)
				if image_url:
					self._add_image(image_url)
					break
			for candidate in attributes.get("srcset", "").split(","):
				image_url = candidate.strip().split()
				if image_url:
					self._add_image(image_url[0])

	def handle_endtag(self, tag):
		if self._skip_depth:
			if tag not in self._void_tags:
				self._skip_depth -= 1
			return

		if tag == "title":
			self._in_title = False
		if tag in {"article", "main"} and self._content_depth:
			self._content_depth -= 1
		if tag == "p" and self._paragraph_depth:
			self._paragraph_depth -= 1
			self.paragraph_parts.append("\n")
		if tag in self._block_tags:
			self._add_separator()

	def handle_data(self, data):
		if self._skip_depth:
			return
		if self._in_title:
			self.title_parts.append(data)
		if self._content_depth:
			self.content_parts.append(data)
		if self._paragraph_depth:
			self.paragraph_parts.append(data)

	def _add_separator(self):
		if self._content_depth:
			self.content_parts.append("\n")
		if self._paragraph_depth:
			self.paragraph_parts.append("\n")

	def _add_image(self, image_url):
		absolute_url = urljoin(self.page_url, image_url.strip())
		if urlparse(absolute_url).scheme in {"http", "https"} and absolute_url not in self.image_urls:
			self.image_urls.append(absolute_url)

	@staticmethod
	def _clean_text(parts):
		lines = [" ".join(line.split()) for line in "".join(parts).splitlines()]
		return "\n".join(line for line in lines if line).strip()

	def result(self):
		content = self._clean_text(self.content_parts)
		if not content:
			content = self._clean_text(self.paragraph_parts)
		return {
			"title": self._clean_text(self.title_parts),
			"images": self.image_urls,
			"content": content,
		}


def fetch_page(url):
	parsed_url = urlparse(url)
	if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
		raise ValueError("请输入有效的 http 或 https 网页地址")

	request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SimplePageScraper/1.0)"})
	with urlopen(request, timeout=15) as response:
		page_url = response.geturl()
		charset = response.headers.get_content_charset() or "utf-8"
		html = response.read().decode(charset, errors="replace")

	parser = PageParser(page_url)
	parser.feed(html)
	parser.close()
	return parser.result()


def main():
	argument_parser = argparse.ArgumentParser(description="提取网页标题、图片链接和文章内容")
	argument_parser.add_argument("url", help="网页的 http 或 https 地址")
	argument_parser.add_argument("-o", "--output", help="将结果保存为 JSON 文件")
	args = argument_parser.parse_args()

	try:
		result = fetch_page(args.url)
	except (URLError, ValueError, UnicodeError) as error:
		print(f"抓取失败：{error}", file=sys.stderr)
		return 1

	output = json.dumps(result, ensure_ascii=False, indent=2)
	if args.output:
		with open(args.output, "w", encoding="utf-8") as output_file:
			output_file.write(output + "\n")
		print(f"结果已保存到：{args.output}")
	else:
		print(output)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

import re
from bs4 import BeautifulSoup

with open("2021.html", "r") as file:
    html_content = file.read()
html = html_content

def extract_date_str_to_iso(date_str):
    """
    Convert mm/dd/yy to yyyy-mm-dd, e.g. '11/14/22' -> '2022-11-14'.
    Returns None if the string doesn't match or parse.
    """
    match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{2})$', date_str)
    if not match:
        return None
    mm, dd, yy = match.groups()
    # Example rule: '22' => 2022, '99' => 1999, '03' => 2003, etc.
    year = int(yy)
    if year <= 30:
        year += 2000
    else:
        year += 1900
    return f"{year:04d}-{int(mm):02d}-{int(dd):02d}"

def extract_title_and_date(block_div):
    """
    Given a <div> (likely `.fe-block` or `.col`), look for .html-block
    containing <h2> (title) and first <p> (date).
    Returns (title_text, iso_date) or (None, None).
    """
    if not block_div:
        return None, None

    # Sometimes the .html-block is one level down, sometimes the <h2>/<p> might be directly inside.
    html_block = block_div.find("div", class_="sqs-block html-block")
    if not html_block:
        # fallback: maybe the block_div *is* the html block
        html_block = block_div

    # 1) Title from <h2>
    h2_el = html_block.find("h2")
    if not h2_el:
        return None, None
    title = h2_el.get_text(strip=True)

    # 2) Date from the first <p>
    p_el = html_block.find("p")
    if not p_el:
        return None, None
    date_str = p_el.get_text(strip=True)
    iso_date = extract_date_str_to_iso(date_str)
    if not iso_date:
        return None, None

    return title, iso_date

soup = BeautifulSoup(html, "html.parser")
results = []

# 1) Find all divs that match 'video-block sqs-block-video'
video_blocks = soup.find_all("div", class_=["sqs-block", "video-block"])
for vb in video_blocks:
    # 2) Extract the YouTube URL from data-block-json
    block_json = vb.get("data-block-json") or ""
    match_url = re.search(r'"url":"([^"]+)"', block_json)
    if not match_url:
        continue
    youtube_url = match_url.group(1)

    # 3) In fluid-engine, this .video-block is inside a parent .fe-block
    #    The sibling .fe-block might contain the interview text. So let's go up:
    parent_fe_block = vb.find_parent("div", class_=re.compile(r"^fe-block"))
    if not parent_fe_block:
        # If not found, maybe it's the old row/col layout.
        # Then the parent might be .col sqs-col-7, etc. We'll just skip that for now or handle separately.
        continue

    # 4) Look for the parent's siblings that might have .html-block
    #    We'll check both previous and next siblings, in either order.
    #    If no success, we skip.
    siblings = []
    siblings.extend(parent_fe_block.find_previous_siblings("div", class_=re.compile(r"^fe-block")))
    siblings.extend(parent_fe_block.find_next_siblings("div", class_=re.compile(r"^fe-block")))

    found_title = None
    found_date = None
    for sibl in siblings:
        title_text, iso_date = extract_title_and_date(sibl)
        if title_text and iso_date:
            found_title = title_text
            found_date = iso_date
            break

    if not found_title:
        # no date/title found among siblings, skip
        continue

    # 5) Build a final line: "- 2022-11-14: [Indonesian Education Minister](https://youtu.be/...)"
    line = f"- {found_date}: [{found_title}]({youtube_url})"
    results.append(line)

# Print results:
for line in results:
    print(line)
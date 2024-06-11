import requests_html as rh
import os
import subprocess
import requests
import json
from pathlib import Path

# to change language, set the content of "lang" to iso code. Also, please check that it already exist on k8s web
lang = "es"

def generate_directory_pdf(url1, name, s=None):
    # some needed variables...
    mydir = Path(f"tmp/links_{name}")
    mydir.mkdir(parents=True, exist_ok=True)
    final_links_to_download = f"tmp/links_{name}/links_to_download.json"
    url2 = f"https://kubernetes.io/{lang}/docs/{name}"

    s = rh.HTMLSession() if not s else s
    r1 = s.get(url1)
    r2 = s.get(url2)
    html = ""
    anchors1 = r1.html.find('.td-sidebar-link')
    anchors2 = r2.html.find('.td-sidebar-link')
    links_en = [a.absolute_links.pop() for a in anchors1 if a.element.tag == 'a']
    links_es = [a.absolute_links.pop() for a in anchors2 if a.element.tag == 'a']

    links_en_uniq_a_comprobar = []
    for i in links_en:
        if i not in links_en_uniq_a_comprobar:
            links_en_uniq_a_comprobar.append(i)

    links_solo_es_uniq = []
    for i in links_es:
        if i not in links_solo_es_uniq:
            links_solo_es_uniq.append(i)

    links_es_uniq_a_comprobar = []
    links_es_uniq_a_comprobar = [link.replace("kubernetes.io/docs", "kubernetes.io/{lang}/docs") for link in links_en_uniq_a_comprobar]

    def check_url(tocheck):
        try:
            response = requests.get(tocheck, timeout=5)
            if response.status_code == 200:
                return True
            else:
                return False
        except requests.RequestException:
            return False

    checked_links_mixed = []
    for english, spanish in zip(links_en_uniq_a_comprobar, links_es_uniq_a_comprobar):
        if check_url(spanish):
            checked_links_mixed.append(spanish)
        else:
            checked_links_mixed.append(english)

    mixed_links_to_uniq = checked_links_mixed + links_solo_es_uniq
    filtered_mixed_links_for_lambda = []
    for i in mixed_links_to_uniq:
        if i not in filtered_mixed_links_for_lambda:
            filtered_mixed_links_for_lambda.append(i)


    links_post_lambda = filter(lambda href: href.startswith(url1) or href.startswith(url2), filtered_mixed_links_for_lambda)
    links_post_lambda_list = list(links_post_lambda)


    with open(final_links_to_download, 'w') as output_file:
                json.dump(links_post_lambda_list, output_file, indent=4)

    print("Downloading content from links...")
    cwd = os.getcwd()
    for l1 in links_post_lambda_list:
        r2 = s.get(l1)
        div = r2.html.find('.td-content', first=True, clean=True)
        if div:
            html += div.html
        with open("{}/{}.html".format(cwd, name), "wt") as f:
            f.write(html)

    print("generating pdf in " + name )
    subprocess.run(["{}/weasy_print.sh".format(cwd), name])


if __name__ == '__main__':
    s = rh.HTMLSession()
    directories = [\
                   "setup",
                   "concepts",
                   "tasks",
                   "tutorials",
                   "reference",
                   ]
    directories_pairs = [("https://kubernetes.io/docs/{}/".format(n.lower()), n) for n in directories]
    for url1, name in directories_pairs:
        print("Working with the content in url : " + url1)
        generate_directory_pdf(url1, name)

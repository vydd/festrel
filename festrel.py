#!/usr/bin/env python

from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
from trello import TrelloClient

import settings


def extract_dates(movie_details):
    if settings.language == 'en':
        time_split = 'Time'
        price_split = 'Price'
    else:
        time_split = 'Vreme'
        price_split = 'Cena'
    showings = movie_details.find('div', {'class': 'product-projection'})
    dates = showings.find_all('div', {'class': 'date'})
    days = [find_day(d) for d in dates]
    months = [find_month(d) for d in dates]
    pretty_days = [m + ' ' + d for m, d in zip(months, days)]
    time_locs = [t.text for t in showings.find_all('p')]
    times = [t.split(time_split + ': ')[1].split(price_split)[0] for t in time_locs]
    prices = [t.split(price_split + ': ')[1].split('RSD')[0] + 'RSD' for t in time_locs]
    places = [t.replace('Ulaz slobodan', 'Ulaz slobodanRSD').split('RSD')[1] for t in time_locs]
    return [f'{pl}: {d}, {t} ({pr})' for d, t, pl, pr in zip(pretty_days, times, places, prices)]


def find_day(div):
    span = div.find('span')
    if span:
        return span.text
    return div.text.split('.')[0]


def find_month(div):
    span = div.find('span')
    if span:
        return span.next_sibling.capitalize()
    return div.text.split(' ')[1]




def movie_to_dict(movie):
    a = movie.find('a', {'class': 'media-object'})
    link = a.attrs['href']
    img = a.img.attrs['src']
    details = BeautifulSoup(requests.get(f'https://www.fest.rs{link}').text, 'html.parser')
    title = details.find('div', {'page-header'}).find('h2').text
    title_serbian = details.find('h1', {'class': 'row-big-title'}).get_text().strip(' ').strip('\r\n')
    try:
        description = details.find('blockquote').p.get_text().strip(' ').strip('\r\n')
    except:
        description = 'NEMA OPISA'
    properties = details.find('dl', {'class': 'dl-horizontal'})
    prop_names = [p.get_text().strip(':').strip('\r\n') for p in properties.find_all('dt')]
    prop_values = [p.get_text().strip('\r\n') for p in properties.find_all('dd')]
    return {
        'title': title,
        'title_serbian': title_serbian,
        'img': f'https://www.fest.rs{img}',
        'description': description,
        'link': f'https://www.fest.rs{link}',
        'meta': dict(zip(prop_names, prop_values)),
        'showing': extract_dates(details)
    }


def all_movie_htmls(n=1000):
    id = 1102 if settings.language == 'en' else 102
    doc = requests.get(f'https://www.fest.rs/cms/view.php?id={id}'
                       f'&keyword=&date=&products_id=0&product_categories_id=0&product_cinema_id=0'
                       f'&limit={n}&startfrom=0&sortby=nameASC&ascdesc=ASC&submit=next'
                       f'&location_in_text[N]=1&location_in_text[D]=1#first-wrapper')
    return BeautifulSoup(doc.text, 'html.parser').find_all('div', {'class': 'media-article'})


client = TrelloClient(
    api_key=settings.api_key,
    api_secret=settings.api_secret,
    token=settings.token,
    token_secret=settings.api_secret
)
board = client.get_board(settings.board_id)
film_list = board.add_list('Festrel')


def make_trello_description(movie):
    title_serbian = movie['title_serbian']
    title = movie['title']
    link = movie['link']
    description = f'# {title_serbian}\n### {title}\n{link}\n\n---\n'

    description += movie['description']

    description += '\n\n---\n'

    description += '```\n'
    for showing in movie['showing']:
        description += showing + '\n'
    description += '```\n'

    description += '---\n'
    for name, val in movie['meta'].items():
        description += f'- **{name}**: {val}\n'
    return description


def add_to_trello(movie):
    card = film_list.add_card('%s (%s)' % (movie['title_serbian'], movie['title']),
                              desc=make_trello_description(movie), position='bottom')
    card.attach(url=movie['img'])


def add_all():
    print('Downloading movie descriptions...', flush=True)
    movies = all_movie_htmls(1000)
    print('Converting and adding to trello!', flush=True)
    for movie in tqdm(movies):
        add_to_trello(movie_to_dict(movie))


if __name__ == '__main__':
    add_all()

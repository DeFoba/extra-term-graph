from bs4 import BeautifulSoup
import requests, os

with requests.Session() as session:
    main_page = BeautifulSoup(session.get('https://www.ontology-of-designing.ru/issues/').content, 'html.parser')
    tom_links = []

    # Получаем список ссылок всех томов
    print('Получаем все тома: ',end='')
    for tom in main_page.find_all('div', {'class': 'elementor-widget-container'}):
        try:
            link_el = tom.find('a')
            if link_el is None: continue

            if link_el.find_all('img') != []:
                tom_links.append(tom.find('a').get('href'))

        except Exception as e:
            print(e)
    print('Все тома получены.')

    c = 0
    titles_links = []
    print('Получаем все статьи: ',end='')
    for tom_link in tom_links:
        tom_page = BeautifulSoup(session.get(tom_link).content, 'html.parser')
        for p in tom_page.find_all('p'):
            strong = p.find('strong')
            if strong is None: continue

            try:
                title_link = strong.find('a').get('href')

                if title_link is not None and '.pdf' in title_link:
                    titles_links.append(title_link)

            except AttributeError as e: pass

            except Exception as e:
                print(e)
    print('Все статьи получены.')

    print('Сохраняем в папку articles/: ')
    max_links = len(titles_links)
    for idx, link in enumerate(titles_links):
        with open('articles/' + link.split('/')[-1], 'wb') as file:
            file.write(session.get(link).content)
            print(f'\r SAVED: [{idx + 1}/{max_links}]', flush=True, end='')

    print('\nГотово')
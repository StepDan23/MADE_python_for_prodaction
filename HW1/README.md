##Построение инвертированного индекса и сериализация объектов в Python 

* Написано CLI приложение.
* Написан собственный сериализатор поверх библиотеки `struct`

Построение и сериализация инвертированного индекса:

`python3 inverted_index.py build -d one_article_wikipedia.txt -o inv.idx`

Выполнение поисковых запросов:

`python3 inverted_index.py query -i inv.idx -q is often the`

Man на программу:

`python3 inverted_index.py --help`

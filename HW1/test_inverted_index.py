import os

import pytest
from argparse import Namespace
from collections import defaultdict

from inverted_index import InvertedIndex

ONE_ARTICLE_PATH = 'one_article_wikipedia.txt'
_SMALL_INDEX = defaultdict(set, {'TitleOne': {1}, 'TitleTwo': {2},
                                 'TitleThree': {3}, 'word': {1, 3},
                                 'simple': {1},
                                 })


def test_build_value_is_file_descriptor():
    with pytest.raises(ValueError):
        InvertedIndex().build(fd=2)


def test_build_file_descriptor_is_open():
    with pytest.raises(ValueError):
        InvertedIndex().build(fd=open('inverted.index').close())


def test_build_small_index():
    index = InvertedIndex()
    wiki_path = 'small_test.txt'
    with open(wiki_path, 'r') as fd:
        index.build(fd)
    assert index.inverted_index == _SMALL_INDEX, f'wrong build index from {wiki_path}'


def test_add_new_doc_doc_id_not_int_value():
    with pytest.raises(ValueError):
        InvertedIndex().add_new_document('das1', '')


def test_add_new_doc_content_not_str_value():
    with pytest.raises(ValueError):
        InvertedIndex().add_new_document(1, 312)


def test_add_new_doc_one_word():
    doc_id = 1
    content = 'foo'
    foo_index = InvertedIndex()
    foo_index.add_new_document(doc_id, content)
    assert doc_id in foo_index.inverted_index[content], (
        "add a new document with 1 word but couldn't find in built index")


def test_add_new_doc_multi_word():
    doc_id = 23
    word_1 = '  foo   '
    word_2 = ' \t bar\t'
    foo_index = InvertedIndex()
    foo_index.add_new_document(doc_id, word_1 + word_2)
    assert_mes = "add a new document with 2 words and different separators but couldn't find a word in built index"
    assert doc_id in foo_index.inverted_index[word_1.strip()], assert_mes
    assert doc_id in foo_index.inverted_index[word_2.strip()], assert_mes


def test_dump_value_is_file_descriptor():
    with pytest.raises(ValueError):
        InvertedIndex().dump(fd=2)


def test_dump_file_descriptor_is_open():
    with pytest.raises(ValueError):
        InvertedIndex().dump(fd=open('inverted.index', 'w').close())


def test_dump_small_index():
    index = InvertedIndex()
    index.inverted_index = _SMALL_INDEX
    small_index_path = 'small.index'
    index.dump(fd=open(small_index_path, 'wb'))
    assert os.path.getsize(small_index_path) > 0, 'build index with zero size'


def test_word_encode():
    expected_word = 'foo'
    result_word = InvertedIndex().encode_string(expected_word)
    assert result_word != b'', 'encoding simple word return nothing'


def test_word_encode_decode():
    expected_word = 'foo'
    foo_index = InvertedIndex()
    result_word = foo_index.decode_string(foo_index.encode_string(expected_word), 0)[0]
    assert expected_word == result_word, 'wrong decode/encode string to binary string'


def test_word_encode_decode_utf8():
    expected_word = 'слово_второе'
    foo_index = InvertedIndex()
    result_word = foo_index.decode_string(foo_index.encode_string(expected_word), 0)[0]
    assert expected_word == result_word, 'wrong decode/encode string to binary string'


def test_encode_dict():
    expected_dict = {'word': {1, 23, 55}}
    result = InvertedIndex().encode_dict(expected_dict)
    assert result != b'', 'encoding simple dict return nothing'


def test_dict_encode_decode():
    expected_dict = {'word': {1, 23, 55}}
    foo_index = InvertedIndex()
    result_dict = foo_index.decode_dict(foo_index.encode_dict(expected_dict))
    assert expected_dict == result_dict, 'wrong decode/encode dict to binary string'


def test_dict_encode_decode_multi_word():
    expected_dict = {'word': {1, 23, 55}, 'another': {1}}
    foo_index = InvertedIndex()
    result_dict = foo_index.decode_dict(foo_index.encode_dict(expected_dict))
    assert expected_dict == result_dict, 'wrong decode/encode dict to binary string'


def test_load_value_is_file_descriptor():
    with pytest.raises(ValueError):
        InvertedIndex().load(fd=2)


def test_load_file_descriptor_is_open():
    with pytest.raises(ValueError):
        InvertedIndex().load(fd=open('inverted.index', 'r').close())


def test_dump_load_small_index():
    index = InvertedIndex()
    index.inverted_index = _SMALL_INDEX
    small_index_path = 'small.index'
    with open(small_index_path, 'wb') as fd:
        index.dump(fd)
    with open(small_index_path, 'rb') as fd:
        index.load(fd)
    assert index.inverted_index == _SMALL_INDEX, 'dumped and loaded index not the same'


def test_parse_queries_wrong_fd():
    with pytest.raises(ValueError):
        arguments = Namespace(query=None, query_file_utf8=123, query_file_cp1251=None)
        InvertedIndex().parse_queries(arguments)


def test_parse_queries_one_query():
    expected = [['one', 'два', '123']]
    with open('test_one_query.utf8', 'r') as f:
        arguments = Namespace(query=None, query_file_utf8=f, query_file_cp1251=None)
        result = InvertedIndex().parse_queries(arguments)
    assert result == expected, 'wrong parsing query file with one query'


def test_parse_queries_two_query():
    expected = [['foo', 'bar'], ['one', 'два', '123']]
    with open('test_two_queries.cp1251', 'r', encoding='cp1251') as f:
        arguments = Namespace(query=None, query_file_utf8=None, query_file_cp1251=f)
        result = InvertedIndex().parse_queries(arguments)
    assert result == expected, 'wrong parsing query file with two queries'


def test_parse_queries_three_query():
    expected = [['foo', 'bar'], ['one', 'два', '123'], ['один']]
    arguments = Namespace(query=expected, query_file_utf8=None, query_file_cp1251=None)
    result = InvertedIndex().parse_queries(arguments)
    assert result == expected, 'wrong parsing query file with three queries'


def test_empty_query():
    index = InvertedIndex()
    index.inverted_index = defaultdict(set, {'foo': {1, 2, 3}, 'bar': {1}})
    assert index.query([]) == set(), 'find a doc, that not in index'


def test_query_not_in_index():
    index = InvertedIndex()
    index.inverted_index = defaultdict(set, {'foo': {1, 2, 3}, 'bar': {1}})
    assert index.query(['foobar']) == set(), 'find a doc, that not in index'


def test_query_one_doc_in_index():
    index = InvertedIndex()
    index.inverted_index = defaultdict(set, {'foo': {1, 2, 3}, 'bar': {1}, 'foobar': {1, 2}})
    assert index.query(['foo', 'bar']) == {1}, 'didnt find a doc, which present in index'


def test_query_two_docs_in_index():
    index = InvertedIndex()
    index.inverted_index = defaultdict(set, {'foo': {1, 2, 3}, 'bar': {1}, 'foobar': {1, 2}})
    assert index.query(['foo', 'foobar']) == {1, 2}, 'didnt find a two docs, which are present in index'


def test_unicode_query_two_docs_in_index():
    index = InvertedIndex()
    index.inverted_index = defaultdict(set, {'один': {1, 2, 3}, 'bar': {1}, 'два': {1, 2}})
    assert index.query(['один', 'два']) == {1, 2}, 'didnt find a two docs, which are present in index with unicode'


def test_one_article():
    index = InvertedIndex()
    with open(ONE_ARTICLE_PATH, 'r') as fd:
        index.build(fd)
    with open(ONE_ARTICLE_PATH, 'r') as fd:
        article_id, words = fd.readline().split(maxsplit=1)
    words = words.split()
    assert article_id == index.find_articles(words), 'didnt find article in query of all words in article'


@pytest.mark.parametrize('query', [['–700+'], ['Harper'], ['Alistair'],
                                   ['some'], ['organizations,'], ['Anarchism'],
                                   ['à'], ['será']
                                   ])
def test_many_queries_from_one_article(query):
    index = InvertedIndex()
    article_id = '12'
    with open(ONE_ARTICLE_PATH, 'r') as fd:
        index.build(fd)
    assert article_id in index.find_articles(query), 'didnt find article in query in one article'


@pytest.mark.parametrize('query', [['этих'], ['Слов'], ['нет'],
                                   ['в'], ['стетье,']
                                   ])
def test_many_queries_not_in_one_article(query):
    index = InvertedIndex()
    article_id = '12'
    with open(ONE_ARTICLE_PATH, 'r') as fd:
        index.build(fd)
    assert article_id not in index.find_articles(query), 'find article in query that not in one article'

from argparse import ArgumentParser

import pytest
from unittest.mock import patch

from stackoverflow_analytics import WordStatistic, setup_parser

NOT_EXIST_FILEPATH = 'not_exist_filepath'


def total_size_of_dict_of_dict(dictionary):
    all_keys = set()
    for inner_dict in dictionary.values():
        all_keys.update(inner_dict.keys())
    return len(all_keys)


def test_setup_parser_show_help_empty_args():
    parser = ArgumentParser()
    with patch('sys.argv', ['']):
        with pytest.raises(SystemExit):
            setup_parser(parser)


def test_parse_args_raise_file_not_exist():
    parser = ArgumentParser()
    setup_parser(parser)
    sys_args = [f'--questions', NOT_EXIST_FILEPATH,
                f'--stop-words', NOT_EXIST_FILEPATH,
                f'--queries', NOT_EXIST_FILEPATH]

    with patch('sys.argv', [''] + sys_args):
        with pytest.raises(SystemExit):
            parser.parse_args()


@pytest.mark.parametrize('data, expected_len', [
    ('word are are', 2),
    ('word are', 2),
    ('', 0),
])
def test_load_stop_words(data, expected_len):
    statistic = WordStatistic()
    statistic.load_stop_words(data.split())
    cur_len = len(statistic.stop_words)
    assert expected_len == cur_len


@pytest.mark.parametrize('data, expected_len', [
    (['<row PostTypeId="1" CreationDate="2010-11-15T20:09:58.970" Score="1" Title="SQL Server" />'], 1),
    (['<row PostTypeId="1" CreationDate="2010-11-15T20:09:58.970" Score="1" Title="SQL Server" />',
      '<row PostTypeId="2" CreationDate="2010-11-15T20:09:58.970" Score="1" Title="SQL Server" />'], 1),
    (['<row PostTypeId="1" CreationDate="some_year" Score="1" Title="SQL Server" />'], 0),
    ([' PostTypeId="1" CreationDate="2010-11-15T20:09:58.970" Score="1" Title="SQL Server" />'], 0),
    (['<row PostTypeId="1" CreationDate="2010-11-15T20:09:58.970" Title="SQL Server" />'], 0),
    (['<row PostTypeId="1" CreationDate="2010-11-15T20:09:58.970" Score="1" Title="SQL Server"'], 0),
    (['<row PostTypeId="1" CreationDate="time" Score="1" Title="SQL Server'], 0),
])
def test_parse_documents_validation(data, expected_len):
    statistic = WordStatistic()
    cur_len = len(statistic.parse_documents(data))
    assert expected_len == cur_len


@pytest.mark.parametrize('doc_info, expected_year_len, expected_words_len', [
    ([(1999, -2, 'word $word are'),
      (1999, -2, 'another word,word')], 1, 3),
    ([(1999, -2, 'word wOrd woRd'),
      (2000, -2, 'Word word $word')], 2, 1),
])
def test_add_new_document(doc_info, expected_year_len, expected_words_len):
    statistic = WordStatistic()
    for doc_year, doc_score, doc_text in doc_info:
        statistic.add_new_document_to_statistic(doc_year, doc_score, doc_text)
    assert expected_year_len == len(statistic.words_statistic)

    words_count = total_size_of_dict_of_dict(statistic.words_statistic)
    assert expected_words_len == words_count


@pytest.mark.parametrize('doc_year, doc_score, doc_text, expected_total_score', [
    (1999, 10, 'word $word are', 20),
    (1999, 10, 'word $word word', 10),
    (1999, 20, '', 0),
])
def test_add_new_document(doc_year, doc_score, doc_text, expected_total_score):
    statistic = WordStatistic()
    statistic.add_new_document_to_statistic(doc_year, doc_score, doc_text)
    total_score = sum(statistic.words_statistic[doc_year].values())
    assert expected_total_score == total_score


@pytest.mark.parametrize('doc_info, stop_words, expected_words_len', [
    ([(1999, -2, 'word $word are'),
      (1999, -2, 'another word,word')], [], 3),
    ([(1999, -2, 'word $word are'),
      (2000, -2, 'another word,word')], ['word', 'another'], 1),
    ([(1999, -2, 'word wOrd woRd'),
      (2000, -2, 'Word word $word')], ['word'], 0),
])
def test_add_new_document_with_stop_words(doc_info, stop_words, expected_words_len):
    statistic = WordStatistic()
    statistic.load_stop_words(stop_words)
    for doc_year, doc_score, doc_text in doc_info:
        statistic.add_new_document_to_statistic(doc_year, doc_score, doc_text)

    words_count = total_size_of_dict_of_dict(statistic.words_statistic)
    assert expected_words_len == words_count


@pytest.mark.parametrize('queries, expected_queries_len', [
    (['1999,2000,3', '1999,2000,3', '1999,2000,3'], 3),
    (['1999,2000,text', '2000,3', '1999,,3'], 0),
    (['1999,2000,3', '1999,text,3', '1999,2000,3'], 2),
])
def test_add_new_document_with_stop_words(queries, expected_queries_len):
    statistic = WordStatistic()
    valid_queries = statistic.parse_queries(queries)
    assert expected_queries_len == len(valid_queries)


@pytest.mark.parametrize('start_year, end_year, top_n, expected_answer', [
    (2000, 2000, 2, '{"start": 2000, "end": 2000, "top": []}'),
    (2019, 2019, 2, '{"start": 2019, "end": 2019, "top": [["seo", 15], ["better", 10]]}'),
    (2019, 2020, 4,
     '{"start": 2019, "end": 2020, "top": [["better", 30], ["javascript", 20], ["python", 20], ["seo", 15]]}')
])
def test_calculate_statistic(start_year, end_year, top_n, expected_answer):
    doc_info = [(2019, 10, 'Is SEO better better better done with repetition?'),
                (2019, 5, 'What is SEO?'),
                (2020, 20, 'Is Python better than Javascript?')
                ]
    stop_words = ['is', 'than']
    statistic = WordStatistic()
    statistic.load_stop_words(stop_words)
    for doc_year, doc_score, doc_text in doc_info:
        statistic.add_new_document_to_statistic(doc_year, doc_score, doc_text)
    answer = statistic.calculate_statistic(start_year, end_year, top_n)
    assert expected_answer == answer

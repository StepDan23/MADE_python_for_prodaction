import sys
import re
import logging
import logging.config

import json
from collections import defaultdict
from argparse import ArgumentParser, FileType

from lxml import etree
import yaml

LOGGING_CONFIG_FILEPATH = 'logging_conf.yml'
logger = logging.getLogger('stackoverflow_analytics')


class WordStatistic:
    def __init__(self):
        self.words_statistic = defaultdict(lambda: defaultdict(int))
        self.stop_words = set()

    def load_stop_words(self, fd):
        for word in fd:
            self.stop_words.add(word.strip())

    @staticmethod
    def parse_documents(fd):
        valid_documents = []
        for line in fd:
            try:
                tag = etree.fromstring(line)
            except etree.XMLSyntaxError:
                continue
            attributes = tag.attrib
            if ('PostTypeId' in attributes and attributes['PostTypeId'] == '1'
                    and 'CreationDate' in attributes
                    and 'Score' in attributes
                    and 'Title' in attributes):
                try:
                    doc_year = int(attributes['CreationDate'][:4])
                    doc_score = int(attributes['Score'])
                except ValueError:
                    continue
                valid_documents.append((doc_year, doc_score, attributes['Title']))
        return valid_documents

    def add_new_document_to_statistic(self, doc_year, doc_score, doc_text):
        year_dict = self.words_statistic[doc_year]
        doc_words = set(re.findall(r'\w+', doc_text.lower()))
        for word in doc_words:
            if word not in self.stop_words:
                year_dict[word] += doc_score

    @staticmethod
    def parse_queries(fd):
        valid_queries = []
        for line in fd:
            try:
                start_year, end_year, top_n = map(int, line.split(','))
                valid_queries.append((start_year, end_year, top_n))
            except ValueError:
                continue
        return valid_queries

    def calculate_statistic(self, start_year, end_year, top_n):
        logger.debug('got query "%d,%d,%d"' % (start_year, end_year, top_n))
        years_statistic = defaultdict(int)
        for stat_year in range(start_year, end_year + 1):
            for word, word_score in self.words_statistic[stat_year].items():
                years_statistic[word] += word_score

        if len(years_statistic) < top_n:
            logger.warning('not enough data to answer, found %d words out of %d for period "%d,%d"'
                           % (len(years_statistic), top_n, start_year, end_year))

        top_n_words = sorted(years_statistic.items(), key=lambda x: (-x[1], x[0]))[:top_n]
        answer_dict = {"start": start_year,
                       "end": end_year,
                       "top": top_n_words
                       }
        return json.dumps(answer_dict)


def setup_parser(arg_parser):
    if len(sys.argv) == 1:
        arg_parser.print_help()
        sys.exit(1)

    arg_parser.add_argument(
        '--questions',
        help='path to questions dataset file',
        metavar='QUESTIONS_DATASET_FILEPATH',
        type=FileType('r', encoding='utf-8'),
        required=True
    )

    arg_parser.add_argument(
        '--stop-words',
        help='path to stop words file in koi8-r encoding',
        metavar='STOP_WORDS_FILEPATH',
        type=FileType('r', encoding='koi8-r'),
        required=True
    )

    arg_parser.add_argument(
        '--queries',
        help='path to queries file',
        metavar='QUERIES_FILEPATH',
        type=FileType('r'),
        required=True
    )


def setup_logging():
    with open(LOGGING_CONFIG_FILEPATH) as fin:
        logging.config.dictConfig(yaml.safe_load(fin))


if __name__ == '__main__':
    setup_logging()
    parser = ArgumentParser(
        prog='word_analytics',
        description='analyze word popularity in articles by year',
    )
    setup_parser(parser)
    arguments = parser.parse_args()

    statistic = WordStatistic()
    statistic.load_stop_words(arguments.stop_words)
    documents = statistic.parse_documents(arguments.questions)
    for year, score, words in documents:
        statistic.add_new_document_to_statistic(year, score, words)
    logger.info('process XML dataset, ready to serve queries')

    answers = []
    for q_start_year, q_end_year, q_top_n in statistic.parse_queries(arguments.queries):
        answers.append(statistic.calculate_statistic(q_start_year, q_end_year, q_top_n))
    print(*answers, sep='\n')
    logger.info('finish processing queries')

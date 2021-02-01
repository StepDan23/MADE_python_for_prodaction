import sys
from io import TextIOWrapper
from collections import defaultdict
from typing import Tuple, List, TextIO, BinaryIO, DefaultDict

import struct
from argparse import ArgumentParser, FileType, ArgumentTypeError, Namespace

_U_CHAR_SIZE = 1
_U_SHORT_SIZE = 2
_INT_SIZE = 4


class EncodedFileType(FileType):
    def __call__(self, string):
        # the special argument "-" means sys.std{in,out}
        if string == '-':
            if 'r' in self._mode:
                stdin = TextIOWrapper(sys.stdin.buffer, encoding=self._encoding)
                return stdin
            elif 'w' in self._mode:
                stdout = TextIOWrapper(sys.stdout.buffer, encoding=self._encoding)
                return stdout
            else:
                msg = 'argument "-" with mode %r' % self._mode
                raise ValueError(msg)

        # all other arguments are used as file names
        try:
            return open(string, self._mode, self._bufsize, self._encoding, self._errors)
        except OSError as e:
            message = "can't open '%s': %s"
            raise ArgumentTypeError(message % (string, e))


class InvertedIndex:
    def __init__(self):
        self.inverted_index = defaultdict(set)

    def add_new_document(self, doc_id: int, content: str):
        if not isinstance(doc_id, int):
            raise ValueError(f'doc_id must be int, got {type(doc_id)}')
        if not isinstance(content, str):
            raise ValueError(f'content must be string, got {type(doc_id)}')
        words = content.split()
        for word in words:
            self.inverted_index[word].add(doc_id)

    def build(self, fd: TextIO):
        if not hasattr(fd, 'read'):
            raise ValueError(f'expected file descriptor got {type(fd)}')
        for document in fd:
            doc_id, content = document.split(maxsplit=1)
            self.add_new_document(int(doc_id), content)

    @staticmethod
    def encode_string(word: str) -> bytes:
        encoded_word = word.encode()
        binary_str = struct.pack('>B', len(encoded_word))
        binary_str += struct.pack(f'>{len(encoded_word)}s', encoded_word)
        return binary_str

    @staticmethod
    def decode_string(bin_str: bytes, start_ind: int) -> Tuple[str, int]:
        read_bytes = _U_CHAR_SIZE
        str_len = struct.unpack('>B', bin_str[start_ind:start_ind + read_bytes])[0]
        start_ind += read_bytes
        binary_word = struct.unpack(f'>{str_len}s', bin_str[start_ind:start_ind + str_len])[0]
        read_bytes += str_len
        return binary_word.decode(), read_bytes

    def encode_dict(self, conv_dict: DefaultDict[str, set]) -> bytes:
        bin_str = struct.pack('>i', len(conv_dict))
        bin_str += b''.join([self.encode_string(key)
                             + struct.pack('>H', len(docs_set))
                             + b''.join([struct.pack('>H', doc_id) for doc_id in docs_set])
                             for key, docs_set in conv_dict.items()
                             ])
        return bin_str

    def decode_dict(self, bin_str: bytes) -> DefaultDict[str, set]:
        read_dict = defaultdict(set)
        dict_size = struct.unpack('>i', bin_str[:_INT_SIZE])[0]
        read_ind = _INT_SIZE
        for _ in range(dict_size):
            word, read_bytes = self.decode_string(bin_str, read_ind)
            read_ind += read_bytes
            set_size = struct.unpack('>H', bin_str[read_ind:read_ind + _U_SHORT_SIZE])[0]
            read_ind += _U_SHORT_SIZE
            word_set = set()
            for _ in range(set_size):
                word_set.add(struct.unpack('>H', bin_str[read_ind:read_ind + _U_SHORT_SIZE])[0])
                read_ind += _U_SHORT_SIZE
            read_dict[word] = word_set
        return read_dict

    def dump(self, fd: BinaryIO):
        if not hasattr(fd, 'write'):
            raise ValueError(f'expected file descriptor got {type(fd)}')
        bin_dict = self.encode_dict(self.inverted_index)
        fd.write(bin_dict)

    def load(self, fd: BinaryIO):
        if not hasattr(fd, 'read'):
            raise ValueError(f'expected file descriptor got {type(fd)}')
        bin_dict = fd.read()
        self.inverted_index = self.decode_dict(bin_dict)

    @staticmethod
    def parse_queries(args: Namespace):
        if args.query:
            queries = args.query
        else:
            query_fd = args.query_file_utf8 if args.query_file_utf8 else args.query_file_cp1251
            if not hasattr(query_fd, 'read'):
                raise ValueError(f'expected file descriptor got {type(query_fd)}')
            queries = []
            for query_words in query_fd:
                queries.append(query_words.split())
        return queries

    def query(self, words: List[str]) -> set:
        if len(words) == 0:
            return set()
        output = self.inverted_index[words[0]]
        for word in words[1:]:
            output = output.intersection(self.inverted_index[word])
        return output

    def find_articles(self, words):
        answer = ','.join(map(str, self.query(words)))
        return answer


def setup_parser(arg_parser):
    sub_parsers = arg_parser.add_subparsers(help='choose command')
    build_parser = sub_parsers.add_parser(
        'build',
        help='build inverted index and save into hard drive',
    )
    build_parser.add_argument(
        '-d', '--dataset',
        help='path to dataset file',
        metavar='INPUT_DATASET_PATH',
        type=FileType('r'),
    )
    build_parser.add_argument(
        '-o', '--output',
        help='path for saving constructed inverted index',
        metavar='OUTPUT_INDEX_PATH',
        type=FileType('wb'),
    )
    build_parser.set_defaults(command='build')
    query_parser = sub_parsers.add_parser(
        'query',
        help='run queries over inverted document index',
    )
    query_parser.add_argument(
        '-i', '--index',
        help='path to constructed inverted index',
        metavar='INDEX_PATH',
        type=FileType('rb'),
    )
    query_args_group = query_parser.add_mutually_exclusive_group(
        required=True,
    )
    query_args_group.add_argument(
        '-q', '--query',
        help='list of words in documents for search',
        action='append',
        metavar='WORD',
        nargs='+',
    )
    query_file_group = query_args_group.add_mutually_exclusive_group()
    query_file_group.add_argument(
        '--query-file-cp1251',
        help='path to queries file in cp1251 encoding',
        metavar='QUERY_FILE_PATH',
        type=EncodedFileType('r', encoding='cp1251'),
    )
    query_file_group.add_argument(
        '--query-file-utf8',
        help='path to queries file in utf-8 encoding',
        metavar='QUERY_FILE_PATH',
        type=EncodedFileType('r', encoding='utf-8'),
    )
    query_parser.set_defaults(command='query')
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    parser = ArgumentParser(
        prog='inverted_index',
        description='',
    )
    setup_parser(parser)
    arguments = parser.parse_args()
    index = InvertedIndex()

    if arguments.command == 'build':
        index.build(arguments.dataset)
        index.dump(arguments.output)
    elif arguments.command == 'query':
        index.load(arguments.index)
        answers = []
        for query in index.parse_queries(arguments):
            answers.append(index.find_articles(query))
        print(*answers, sep='\n')

import json
import os
import time
from enum import Enum
from typing import IO, BinaryIO, Union
from threading import Event, Thread
import queue

import torch
from git_ai.cmd.ai_repo import AIRepo
from git_ai.cmd.constants import AIRepoConstants
from torch.utils.tensorboard import SummaryWriter

from git_ai.errors.errors import MetricError


class DataTypeEnum(Enum):
    FLOAT = 0
    STRING = 1
    INT = 2
    BOOLEAN = 3

    @classmethod
    def from_string(cls, str):
        if str == 'FLOAT':
            return cls.FLOAT
        elif str == 'STRING':
            return cls.STRING
        elif str == 'INT':
            return cls.INT
        elif str == 'BOOLEAN':
            return cls.BOOLEAN
        else:
            raise MetricError.unknown_data_type_enum(str)

    @classmethod
    def to_string(cls, v):
        if v == DataTypeEnum.FLOAT:
            return 'FLOAT'
        elif v == DataTypeEnum.STRING:
            return 'STRING'
        elif v == DataTypeEnum.INT:
            return 'INT'
        elif v == DataTypeEnum.BOOLEAN:
            return 'BOOLEAN'
        else:
            raise MetricError.unknown_data_type_enum(str(v))


class AsynchFileWriter(Thread):

    def __init__(self) -> None:
        super().__init__()
        self.stop_event = Event()
        self.flush_event = Event()
        self.flush_done_event = Event()
        self.q = queue.Queue()
        self.writer_queue = []
        self.pending_items = {}
        self.start()

    def flush(self):
        self.flush_event.set()
        while not self.stop_event.is_set() and not self.flush_done_event.wait(0.1):
            pass
        if self.flush_done_event.is_set():
            self.flush_done_event.clear()

    def enqueue_write(self, filename, contents):
        self.q.put((filename, contents.to_dict()), block=True)

    def dequeue_writes(self) -> bool:
        """Dequees an items from the process queue and puts it in an internal queue.
        Keeps only the most recent item for each file. Pushes the file to the head
        of the queue if it is already in the queue.

        Returns:
            bool: True if is successful false if it fails
        """
        try:
            while self.q.qsize() > 0:
                filename, item = self.q.get()
                # If the file is already in the queue, put it in the front
                # If it is not, just append it
                if filename in self.writer_queue:
                    self.writer_queue.remove(filename)

                self.writer_queue.append(filename)
                self.pending_items[filename] = item
        except FileNotFoundError:
            return False
        return True

    def __worker_loop(self):
        process_running = self.dequeue_writes()
        if process_running:
            for filename in self.writer_queue:
                try:
                    with open(filename, 'w') as f:
                        json.dump(self.pending_items[filename], f)
                        f.flush()
                except Exception as e:
                    print("Error writing to file %s: %s" % (filename, str(e)))
                    process_running = False
                    break
            self.writer_queue = []
        return process_running

    def run(self):
        running = True
        while not self.stop_event.is_set() and running:
            running = self.__worker_loop()
            if self.flush_event.is_set():
                # Flush the queue
                running = self.__worker_loop()
                self.flush_event.clear()
                self.flush_done_event.set()
            time.sleep(0.1)
        # This is flush
        self.__worker_loop()
        # Something went wrong
        if not running:
            print("File writer failed to write, won't be able to write further.")
            self.stop_event.set()

    def close(self):
        self.flush()
        self.stop_event.set()
        self.join()


class JsonObj(object):
    def __init__(self):
        self.run = True

    def log(self, string):
        print("WORKER %s - %s" % (self.__class__.__name__, string))

    def to_dict(self):
        raise NotImplementedError("Not implemented!")

    @staticmethod
    def get_data_type(value):
        if isinstance(value, str):
            return DataTypeEnum.STRING
        elif isinstance(value, float):
            return DataTypeEnum.FLOAT
        elif isinstance(value, bool):
            return DataTypeEnum.BOOLEAN
        elif isinstance(value, int):
            return DataTypeEnum.INT
        else:
            raise NotImplementedError("Cannot recoginze type of %s" %
                                      str(value))

    @staticmethod
    def format_value(value, data_type):
        if data_type == DataTypeEnum.STRING:
            return value
        elif data_type == DataTypeEnum.FLOAT:
            return "%.03f" % value
        elif data_type == DataTypeEnum.BOOLEAN:
            return "true" if value else "false"
        elif data_type == DataTypeEnum.INT:
            return "%d" % value
        raise NotImplementedError("Cannot recoginize type %s" % str(data_type))

    @staticmethod
    def read_value(str, data_type):
        if data_type == DataTypeEnum.STRING:
            return str
        elif data_type == DataTypeEnum.FLOAT:
            return float(str)
        elif data_type == DataTypeEnum.BOOLEAN:
            return True if str == "true" else False
        elif data_type == DataTypeEnum.INT:
            return int(str)
        raise NotImplementedError("Cannot recoginize type %s" % str(data_type))

    @classmethod
    def from_json(self):
        raise NotImplementedError("Not implemented!")

    @classmethod
    def from_file(cls, filename):
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                return cls.from_json(json.load(f))
        else:
            return None


class Metric(JsonObj):
    def __init__(self, label, value, unit=None, data_type=None):
        super().__init__()
        self.label = label
        self.value = value
        self.unit = unit
        if not data_type:
            self.data_type = self.get_data_type(value)
        else:
            self.data_type = data_type

    def to_dict(self):
        dict = {
            'label': self.label,
            'value': self.format_value(self.value, self.data_type),
            'dataType': DataTypeEnum.to_string(self.data_type)
        }

        if self.unit:
            dict['unit'] = self.unit

        return dict

    @classmethod
    def from_json(cls, json):
        unit = None if ('unit' not in json) else json['unit']
        data_type = DataTypeEnum.from_string(json['dataType'])
        return cls(json['label'], cls.read_value(json['value'], data_type),
                   unit, data_type)


class Hparams(JsonObj):
    def __init__(self):
        super().__init__()
        self.values = []

    def add_metric(self, metric):
        self.values.append(metric)

    def to_dict(self):
        return [v.to_dict() for v in self.values]

    @classmethod
    def from_json(cls, json_f):
        hparams = cls()
        for v in json_f:
            hparams.add_metric(Metric.from_json(v))
        return hparams


class ScalarHeader(JsonObj):
    def __init__(self, title, data_type, x_title=None, unit=None):
        super().__init__()
        self.title = title
        self.x_title = x_title
        self.unit = unit
        self.data_type = data_type

    def to_dict(self):
        dict = {
            'title': self.title,
            'x_title': self.x_title,
            'dataType': DataTypeEnum.to_string(self.data_type)
        }

        if self.unit:
            dict['unit'] = self.unit

        return dict

    @classmethod
    def from_json(cls, json):
        unit = None if ('unit' not in json) else json['unit']
        x_title = None if ('x_title' not in json) else json['x_title']
        data_type = DataTypeEnum.from_string(json['dataType'])
        return cls(json['title'], data_type=data_type, unit=unit,
                   x_title=x_title)


class Scalar(JsonObj):
    def __init__(self, values, data_type):
        super().__init__()
        self.values = values
        self.data_type = data_type

    def add_value(self, value):
        self.values.append(value)

    def to_dict(self):
        return {
            'values': [self.format_value(v, self.data_type)
                       for v in self.values],
            'dataType': DataTypeEnum.to_string(self.data_type)
        }

    @classmethod
    def from_json(cls, json):
        data_type = DataTypeEnum.from_string(json['dataType'])
        values = [cls.read_value(v, data_type) for v in json['values']]
        return cls(values, data_type)


class GitTensorboardSummaryWriter(SummaryWriter, AIRepoConstants):

    def __init__(self, repo: AIRepo, **kwargs):
        self.workdir = repo.workdir
        self._tb_folder = os.path.join(self.workdir, self.GIT_AI_ROOT,
                                       self.TENSORBOARD_FOLDER)

        super().__init__(log_dir=self._tb_folder, **kwargs)
        self.hparams = None
        self.scalars = {}
        self.scalar_headers = {}
        self.async_writer = AsynchFileWriter()

    def add_scalar(self, tag, scalar_value, unit=None,
                   data_type_=None, x_title=None,
                   global_step=None, walltime=None,
                   new_style=False, double_precision=False):
        super().add_scalar(tag, scalar_value, global_step, walltime, new_style,
                           double_precision)

        data_type = (data_type_ if data_type_
                     else JsonObj.get_data_type(scalar_value))

        scalar_filename = self.metric_filename(self.workdir, tag)
        scalar_header_filename = self.metric_filename(
            self.workdir, tag) + '_header'
        if scalar_header_filename not in self.scalar_headers:
            scalar_header = ScalarHeader.from_file(scalar_header_filename)
            if not scalar_header:
                scalar_header = ScalarHeader(
                    title=tag, x_title=x_title, unit=unit, data_type=data_type)
            self.scalar_headers[scalar_header_filename] = scalar_header
        else:
            scalar_header = self.scalar_headers[scalar_header_filename]

        self.async_writer.enqueue_write(scalar_header_filename, scalar_header)

        if scalar_filename not in self.scalars:
            scalar = Scalar.from_file(scalar_filename)
            if not scalar:
                scalar = Scalar(values=[], data_type=data_type)
            self.scalars[scalar_filename] = scalar
        else:
            scalar = self.scalars[scalar_filename]

        scalar.add_value(scalar_value)
        self.async_writer.enqueue_write(scalar_filename, scalar)

    def add_hparams(self, hparam_dict, metric_dict,
                    hparam_unit_dict={}, metric_unit_dict={},
                    hparam_domain_discrete=None, run_name=None):

        all_data = {**hparam_dict, **metric_dict}
        super().add_hparams(all_data, {}, hparam_domain_discrete,
                            run_name)

        if not self.hparams:
            hparams_filename = self.hparam_filename(self.workdir)
            hparams = Hparams.from_file(hparams_filename)
            if not hparams:
                hparams = Hparams()
        else:
            hparams = self.hparams

        for k, v in hparam_dict.items():
            unit = hparam_unit_dict[k] if k in hparam_unit_dict else ""
            hparams.add_metric(Metric(k, v, unit=unit))
        for k, v in metric_dict.items():
            unit = metric_unit_dict[k] if k in metric_unit_dict else ""
            hparams.add_metric(Metric(k, v, unit=unit))

        self.async_writer.enqueue_write(hparams_filename, hparams)

    def save_artifact(self, obj,
                      f: Union[str, os.PathLike, BinaryIO, IO[bytes]]):
        torch.save(obj, self.ARTIFACT_PATH / str(f))

    def add_topology(self, topology):
        with open(self.TOPOLOGY_PATH, 'w') as f:
            f.write(topology)

    def flush(self):
        self.async_writer.flush()
        super().flush()

    def close(self):
        self.flush()
        self.async_writer.close()
        super().close()

import random
from typing import Iterable, Iterator, Optional, Type, Union
from typing_extensions import Self
from dataclasses import dataclass
import math
from git_ai.test.utils.testutils import sample_array


@dataclass(frozen=True)
class Metric:
    label: str
    unit: str
    metric_type: str
    value: Union[str, int, float, bool]

    def __eq__(self, x):
        label_equals = (self.label == x.label)
        if self.metric_type == 'FLOAT':
            value_equals = math.isclose(self.value, x.value, rel_tol=.01)
        elif self.metric_type == 'INT':
            value_equals = self.value == x.value
        elif self.metric_type == 'STRING':
            value_equals = self.value == x.value
        elif self.metric_type == 'BOOLEAN':
            value_equals = self.value == x.value
        else:
            raise Exception("metric type %s unknown" % self.metric_type)
        return label_equals == value_equals

    def format_value(self) -> str:
        if self.metric_type == 'FLOAT':
            return '%.03f' % self.value
        elif self.metric_type == 'INT':
            return "%i" % self.value
        elif self.metric_type == 'STRING':
            return "%s" % self.value
        elif self.metric_type == 'BOOLEAN':
            return str(self.value)
        else:
            raise Exception("metric type %s unknown" % self.metric_type)

    @ staticmethod
    def parse_value(v: str, metric_type: str) -> Union[str, int, float, bool]:
        if metric_type == 'FLOAT':
            return float(v)
        elif metric_type == 'INT':
            return int(v)
        elif metric_type == 'STRING':
            return v
        elif metric_type == 'BOOLEAN':
            return v in ['true', 'True']
        else:
            raise Exception("metric type %s unknown" % metric_type)

    @ classmethod
    def from_json(cls: Type[Self], j: dict) -> Self:
        unit = j['unit'] if 'unit' in j else ''
        return cls(j['label'], unit, j['dataType'],
                   Metric.parse_value(j['value'], j['dataType']))

    def __str__(self) -> str:
        if self.unit:
            return "%s: %s %s" % (self.label, self.format_value(), self.unit)
        else:
            return "%s: %s" % (self.label, self.format_value())

    def __repr__(self) -> str:
        return self.__str__()

    @ classmethod
    def sample_metric(cls: Type[Self], label: str, unit: str, metric_type: str) -> Self:
        """samples a single metric

        Args:
            cls (Type[Self]): class object
            label (str): label of the metric sampled
            metric_type (str): type of the metric sampled

        Returns:
            Self: a metric with a value sampled according to the label
        """
        return Metric(label, unit, metric_type, Metric.__sample_value(metric_type))

    @ staticmethod
    def __sample_value(metric_type: str) -> Union[str, int, float, bool]:
        """samples a single value

        Args:
            metric_type (str): type of the metric to be sampled

        Returns:
            Union[str, int, float, bool]: value sampled
        """
        if metric_type == 'FLOAT':
            value = (random.random()*10)
        elif metric_type == 'INT':
            value = int(random.random()*1000)
        elif metric_type == 'STRING':
            value = random.choice(['ADAM', 'SGD', 'POWER_SGD'])
        elif metric_type == 'BOOLEAN':
            value = random.choice([True, False])
        else:
            raise Exception("metric type %s unknown" % metric_type)
        return value


@ dataclass(frozen=True)
class Plot:
    label: str
    values: list[float]

    def __eq__(self, x):
        return (self.label == x.label and
                all([math.isclose(this, that, rel_tol=.1) for (this, that) in zip(self.values, x.values)]) and
                len(self.values) == len(x.values))

    def format_values(self, vs):
        return ",".join(["%.3f" % v for v in vs])

    @ classmethod
    def from_json(cls: Type[Self], header: dict, values: dict[str, list[str]]) -> Self:
        return cls(header['title'], [float(v) for v in values['values']])

    def __str__(self):
        if len(self.values) <= 6:
            values_str = self.format_values(self.values)
        else:
            values_str = (
                self.format_values(self.values[:3]) + " ... " +
                self.format_values(self.values[-3:])
            )
        return "%s: [%s]" % (self.label, values_str)

    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self):
        for v in self.values:
            yield (self.label, v)

    @ classmethod
    def sample_plot(cls: Type[Self], total_iterations: int, label: str, plot_type: str,
                    scale: float) -> Self:
        """samples a plot object

        Args:
            cls (Type[Self]): class object
            total_iterations (int): number of iterations in the plot
            label (str): label of the plot
            plot_type (str): type of the plot
            scale (float): scale of the plot for varying it during experiments

        Returns:
            Self: plot sampled
        """
        values = [
            Plot.__sample_value(total_iterations, it, plot_type, scale)
            for it in range(total_iterations)
        ]
        return cls(label, values)

    @ staticmethod
    def __sample_value(total_iterations: int, it: int, plot_type: str,
                       scale: float) -> float:
        """samples all values for a plot

        Args:
            total_iterations (int): number of iterations in the plot
            it (int): current interation in the plot
            scale (float): scale of the plot for varying it during experiments

        Returns:
            float: value sampled according to tye plot type
        """
        if plot_type == 'log':
            sampled_value = math.log((it+1)*0.01)*scale
        elif plot_type == 'exponential':
            sampled_value = math.exp((it+1)*0.01)*scale
        elif plot_type == 'inverse_exponential':
            sampled_value = 1/math.exp((it+1)*0.01)*scale
        elif plot_type == 'linear_growth':
            sampled_value = it*scale
        elif plot_type == 'linear_decrease':
            sampled_value = (total_iterations-it)*scale
        else:
            raise Exception('plot type unknown')

        return sampled_value


class DataConstants:
    METRIC_LABELS = [
        ('f1_score', '', 'FLOAT'), ('training_loss', '', 'FLOAT'),
        ('test_loss', '', 'FLOAT'), ('hparams/lr', '', 'FLOAT'),
        ('hparams/batch_size', '', 'FLOAT'), ('hparams/alpha', '', 'FLOAT'),
        ('hparms/beta', '', 'FLOAT'), ('mean_error', '%', 'FLOAT'),
        ('mean_squared_error', '%', 'FLOAT'), ('test_error', '%', 'FLOAT'),
        ('training_error', '%', 'FLOAT'), ('test_accuracy', '%', 'FLOAT'),
        ('hparams/dropout', '%', 'FLOAT'), ('hparams/optimizer', '', 'STRING'),
        ('hparams/shuffle', '', 'BOOLEAN'), ('hparams/epochs', '', 'INT'),
        ('mean_absolute_error', '', 'FLOAT'), ('mrr', '', 'FLOAT'),
        ('dcg', '', 'FLOAT'), ('ndcg', '', 'FLOAT'),
        ('perplexity', '', 'FLOAT'), ('bleu_score', 'score', 'FLOAT'),
        ('psnr', '', 'FLOAT'), ('ssim', '', 'FLOAT'), ('iou', '', 'FLOAT'),
    ]

    PLOT_TYPES = ['log', 'exponential', 'inverse_exponential', 'linear_growth',
                  'linear_decrease']

    PLOT_LABELS = [
        ('test_accuracy', 'iteration',  'FLOAT'),
        ('test_error', 'iteration', 'FLOAT'),
        ('test_loss', 'iteration', 'FLOAT'),
        ('training_accuracy', 'iteration', 'FLOAT'),
        ('training_error', 'iteration', 'FLOAT'),
        ('training_loss', 'iteration', 'FLOAT'),
        ('l1_weight_value', 'iteration', 'FLOAT'),
        ('f1_score', 'iteration', 'FLOAT'),
        ('roc', 'iteration', 'FLOAT'),
        ('mean_absolute_error', 'iteration', 'FLOAT'),
        ('inception_score', 'iteration', 'FLOAT')
    ]

    HEADER = ['id', 'name', 'description', 'forkCount', 'watcherCount',
              'issueCount', 'license', 'pullRequestCount', 'createdAt',
              'updatedAt', 'isFork', 'isPrivate', 'isMirror', 'isArchived',
              'ownerId', 'size', 'isAIRepo', 'dataTypeStr',
              'aiRepositoryTypeStr', 'fileCount', 'layers']

    DATES = ["2017-07-18T21:41:10Z", "2021-10-20T07:09:06Z",
             "2017-03-22T19:15:24Z", "2021-10-17T20:39:19Z",
             "2016-06-07T16:56:31Z", "2021-10-20T13:19:01Z"]


class ExperimentDataGen:
    def __sample_metrics(self, metric_spec: list[str]) -> list[Metric]:
        """samples metrics based on a list of labels provided by the user

        Args:
            metric_spec (list[str]): list of labels

        Returns:
            list[Metric]: a list of values with sampled values
        """
        metric_labels = {
            m: Metric.sample_metric(m, u, t)
            for (m, u, t) in DataConstants.METRIC_LABELS
            if m in metric_spec
        }
        # get labels in the same order as specified
        return [
            metric_labels[k] for k in metric_spec
        ]

    def __sample_plots(self, plot_spec: list[str]) -> list[Plot]:
        """samples a list of plots based on labels provided by the user

        Args:
            plot_spec (list[str]): list of plot labels

        Returns:
            list[Plot]: plots with samples values
        """
        plot_labels = {
            p: Plot.sample_plot(self.epoch_count, p, random.choice(
                DataConstants.PLOT_TYPES), random.random()*.2+.8)
            for (p, _, _) in DataConstants.PLOT_LABELS
            if p in plot_spec
        }

        return [plot_labels[p] for p in plot_spec]

    def __init__(self, epoch_count: int, before_metrics_spec: list[str],
                 after_metrics_spec: list[str], plot_spec: list[str]) -> None:
        """generates an entire experiment

        Args:
            epoch_count (int): number of epochs
            before_metrics_spec (list[str]): metrics to be added before te experiments runs
            after_metrics_spec (list[str]): metrics to be added after te experiments runs
            plot_spec (list[str]): list of plot labels
        """
        self.name = None
        self.epoch_count = epoch_count
        self.before_metrics = self.__sample_metrics(before_metrics_spec)
        self.after_metrics = self.__sample_metrics(after_metrics_spec)
        self.plots = self.__sample_plots(plot_spec)

    def get_before_metrics(self) -> list[Metric]:
        return self.before_metrics

    def get_after_metrics(self) -> list[Metric]:
        return self.after_metrics

    def get_plots(self) -> list[Plot]:
        return self.plots

    def epochs_generator(self) -> Iterator[list[tuple[str, float]]]:
        """iterator for epochs generation

        Yields:
            Iterator[list[tuple[str, float]]]: an iterator that yields with a list of (label, value) for each epoch
        """
        for ps in zip(*self.plots):
            yield list(ps)

    def __str__(self) -> str:
        def indent_v(v) -> str:
            return "  " + str(v)
        return ("\n\nExperiment %s: \nBefore metrics:\n" % self.name +
                "\n".join(map(indent_v, self.before_metrics)) + "\nAfter metrics:\n" +
                "\n".join(map(indent_v, self.after_metrics)) + "\nPlots:\n" +
                "\n".join(map(indent_v, self.plots))
                )

    def __repr__(self) -> str:
        return self.__str__()

    def match_data(self, metrics: dict[str, Metric], plots: dict[str, Plot]) -> bool:
        all_metrics = self.before_metrics + self.after_metrics
        matches = True
        labels = set([m.label for m in all_metrics])
        plot_labels = set([p.label for p in self.plots])

        for m in all_metrics:
            assert m.label in metrics
            assert m == metrics[m.label]

        for m in metrics.keys():
            assert m in labels

        for p in self.plots:
            assert p.label in plots
            assert p == plots[p.label]

        for p in plots.keys():
            assert p in plot_labels


class RepositoryDataGen:
    def __init__(self, experiment_count: int,
                 experiment_epochs: int,
                 mandatory_before_metrics: list[str],
                 mandatory_after_metrics: list[str],
                 mandatory_plots: list[str],
                 optional_before_metrics: list[str],
                 optional_after_metrics: list[str],
                 optional_plots: list[str],
                 seed=42) -> None:
        random.seed(seed)
        self.experiments = [
            ExperimentDataGen(
                epoch_count=experiment_epochs,
                before_metrics_spec=(
                    mandatory_before_metrics + sample_array(optional_before_metrics)),
                after_metrics_spec=(
                    mandatory_after_metrics + sample_array(optional_after_metrics)),
                plot_spec=mandatory_plots + sample_array(optional_plots))
            for it in range(experiment_count)
        ]

    def __iter__(self):
        yield from self.experiments

    def match_data(self, exp: str, metrics: dict[str, Metric], plots: dict[str, Plot]) -> None:
        exp_dict = {e.name: e for e in self.experiments}
        assert (exp in exp_dict)
        exp_dict[exp].match_data(metrics, plots)

    @ classmethod
    def default(cls, experiment_count=5, experiment_epochs=10) -> Self:
        return cls(
            experiment_count=experiment_count,
            experiment_epochs=experiment_epochs,
            mandatory_before_metrics=[
                'f1_score', 'hparams/epochs', 'hparams/optimizer', 'hparams/shuffle'],
            mandatory_after_metrics=['dcg', 'psnr', 'test_loss'],
            mandatory_plots=['test_accuracy', 'test_error'],
            optional_before_metrics=['hparms/beta', 'hparams/dropout'],
            optional_after_metrics=['ssim', 'iou', 'mrr'],
            optional_plots=['training_error', 'training_loss', 'f1_score']
        )

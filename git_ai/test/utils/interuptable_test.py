from pathlib import Path
import sys
from git_ai.cmd.ai_repo.ai_repo import AIRepo
from git_ai.metrics.experiment import Experiment
from git_ai.test.utils.data_gen import RepositoryDataGen
from git_ai.test.utils.setup_repo import SetupRepo


def main():
    data = RepositoryDataGen.default(
        experiment_count=1, experiment_epochs=1000)

    if not sys.argv[1]:
        sys.exit(1)

    with SetupRepo(Path(sys.argv[1]), "interruptable") as (copy, bare, setup):
        ai_repo = AIRepo(copy.workdir)
        ai_repo.init_ai_repo()

        for exp_data in data:
            with Experiment() as exp:
                before_metrics = exp_data.get_before_metrics()
                exp.writer.add_hparams(
                    metric_dict={
                        m.label: m.value for m in before_metrics
                    },
                    hparam_dict={},
                    metric_unit_dict={
                        m.label: m.unit for m in before_metrics
                    })
                exp.checkpoint("experiment start")
                for idx,  epoch in enumerate(exp_data.epochs_generator()):
                    for label, value in epoch:
                        exp.writer.add_scalar(
                            tag=label, scalar_value=value)
                    exp.checkpoint("epoch %d" % idx)
                after_metrics = exp_data.get_after_metrics()
                exp.writer.add_hparams(
                    metric_dict={
                        m.label: m.value for m in after_metrics
                    },
                    hparam_dict={},
                    metric_unit_dict={
                        m.label: m.unit for m in after_metrics
                    })
                exp.checkpoint("final checkpoint")


if __name__ == "__main__":
    main()

REGISTRY = {}

# from .single_run import S
# REGISTRY["episode"] = EpisodeRunner
#
# from .parallel_run import ParallelRunner
# REGISTRY["parallel"] = ParallelRunner

from .merge_run import MergeRunner
REGISTRY["Merge"] = MergeRunner

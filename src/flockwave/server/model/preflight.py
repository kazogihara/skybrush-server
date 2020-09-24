from bidict import bidict
from enum import Enum
from typing import Optional, Union

from flockwave.server.model.metamagic import ModelMeta
from flockwave.spec.schema import get_complex_object_schema

from .utils import enum_to_json


__all__ = ("PreflightCheckInfo",)


class PreflightCheckResult(Enum):
    """Possible outcomes for a single preflight check item."""

    OFF = "off"
    PASS = "pass"
    WARNING = "warning"
    RUNNING = "running"
    SOFT_FAILURE = "softFailure"
    FAILURE = "failure"
    ERROR = "error"


#: Ordering of preflight check results; used when summarizing the results of a
#: preflight checklist into a single result value. Larger values take precedence
#: over smaller ones
_numeric_preflight_check_results = bidict(
    {
        PreflightCheckResult.OFF: 0,
        PreflightCheckResult.PASS: 10,
        PreflightCheckResult.WARNING: 20,
        PreflightCheckResult.RUNNING: 30,
        PreflightCheckResult.SOFT_FAILURE: 40,
        PreflightCheckResult.FAILURE: 50,
        PreflightCheckResult.ERROR: 60,
    }
)


class PreflightCheckItem(metaclass=ModelMeta):
    """Class representing a single item in a detailed preflight check rpeort."""

    class __meta__:
        schema = get_complex_object_schema("preflightCheckItem")
        mappers = {"result": enum_to_json(PreflightCheckResult)}

    def __init__(self, id: str, label: Optional[str] = None):
        self.id = id
        self.label = label
        self.result = PreflightCheckResult.OFF


class PreflightCheckInfo(metaclass=ModelMeta):
    """Class representing the detailed result of the preflight checks on a
    single UAV.
    """

    class __meta__:
        schema = get_complex_object_schema("preflightCheckInfo")
        mappers = {"result": enum_to_json(PreflightCheckResult)}

    def __init__(self):
        self._in_progress = False
        self.result = PreflightCheckResult.OFF
        self.items = []
        self.update_summary()

    def add_item(self, id: str, label: Optional[str] = None) -> None:
        self.items.append(PreflightCheckItem(id=id, label=label))
        self.update_summary()

    def _get_result_from_items(self) -> Union[PreflightCheckResult, bool]:
        """Returns a single preflight check result summary based on the results
        of the individual items, and whether there is at least one check that
        is still running.
        """
        if not self.items:
            return PreflightCheckResult.OFF, False

        running = any(
            item.result is PreflightCheckResult.RUNNING for item in self.items
        )
        result = max(
            _numeric_preflight_check_results.get(item.result, 0) for item in self.items
        )
        return _numeric_preflight_check_results.inverse[result], running

    @property
    def failed(self) -> bool:
        """Returns whether at least one preflight check has failed, including
        "soft" failures that may resolve themselves on their own.
        """
        return self.result in (
            PreflightCheckResult.SOFT_FAILURE,
            PreflightCheckResult.FAILURE,
            PreflightCheckResult.ERROR,
        )

    @property
    def failed_conclusively(self) -> bool:
        """Returns whether the preflight checks failed conclusively, i.e. it is
        unlikely that the problems indicated by the preflight checks would
        resolve themselves without human intervention.
        """
        return self.result in (PreflightCheckResult.FAILURE, PreflightCheckResult.ERROR)

    @property
    def in_progress(self) -> bool:
        """Returns whether the preflight checks are currently in progress (i.e.
        if there is at least one item where the status indicates that it is
        still in progress).
        """
        return self._in_progress

    def update_summary(self) -> None:
        """Updates the summary of this preflight check report based on the
        results of the individual preflight check items.
        """
        self.result, self._in_progress = self._get_result_from_items()
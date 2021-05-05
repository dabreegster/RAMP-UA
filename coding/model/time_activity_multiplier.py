# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core RAMP-UA model.

Created on April 2021 from population_initialisation.py

@authors: nick, Anna for the national up-scaling
"""
import sys
from coding.constants import ColumnNames
import pandas as pd
pd.set_option('display.expand_frame_repr', False)  # Don't wrap lines when displaying DataFrame

class TimeActivityMultiplier:

    """
    A class used to implement the lockdown scenario on the model.
    """

    @staticmethod
    def read_time_activity_multiplier(lockdown_file) -> pd.DataFrame:
        """
        Some times people should spend more time at home than normal. E.g. after lockdown. This function
        reads a file that tells us how much more time should be spent at home on each day.
        :param lockdown_file: Where to read the mobility data from (assume it's within the DATA_DIR).
        :return: A dataframe with 'day' and 'timeout_multiplier' columns
        """
        assert lockdown_file != "", \
            "read_time_activity_multiplier should not have been called if lockdown_file is empty"
        print(f"Reading time activity multiplier data from {lockdown_file}...", )
        time_activity = pd.read_csv(lockdown_file)
        # Cap at 1.0 (it's a curve so some times peaks above 1.0)=
        time_activity["timeout_multiplier"] = time_activity.loc[:, "timeout_multiplier"]. \
            apply(lambda x: 1.0 if x > 1.0 else x)

        return time_activity
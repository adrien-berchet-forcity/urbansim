import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest
from pandas.util import testing as pdt

from .. import lcm


@pytest.fixture
def choosers():
    return pd.DataFrame(
        {'var1': range(5, 10),
         'thing_id': ['a', 'c', 'e', 'g', 'i']})


@pytest.fixture
def alternatives():
    return pd.DataFrame(
        {'var2': range(10, 20),
         'var3': range(20, 30)},
        index=pd.Index([x for x in 'abcdefghij'], name='thing_id'))


def test_unit_choice_uniform(choosers, alternatives):
    probabilities = [1] * len(alternatives)
    choices = lcm.unit_choice(
        choosers.index, alternatives.index, probabilities)
    npt.assert_array_equal(choices.index, choosers.index)
    assert choices.isin(alternatives.index).all()


def test_unit_choice_some_zero(choosers, alternatives):
    probabilities = [0, 1, 0, 1, 1, 0, 1, 0, 0, 1]
    choices = lcm.unit_choice(
        choosers.index, alternatives.index, probabilities)
    npt.assert_array_equal(choices.index, choosers.index)
    npt.assert_array_equal(sorted(choices.values), ['b', 'd', 'e', 'g', 'j'])


def test_unit_choice_not_enough(choosers, alternatives):
    probabilities = [0, 0, 0, 0, 0, 1, 0, 1, 0, 0]
    choices = lcm.unit_choice(
        choosers.index, alternatives.index, probabilities)
    npt.assert_array_equal(choices.index, choosers.index)
    assert choices.isnull().sum() == 3
    npt.assert_array_equal(sorted(choices[~choices.isnull()]), ['f', 'h'])


def test_unit_choice_none_available(choosers, alternatives):
    probabilities = [0] * len(alternatives)
    choices = lcm.unit_choice(
        choosers.index, alternatives.index, probabilities)
    npt.assert_array_equal(choices.index, choosers.index)
    assert choices.isnull().all()


def test_mnl_lcm(choosers, alternatives):
    model_exp = 'var2 + var1:var3'
    sample_size = 5
    location_id_col = 'thing_id'
    choosers_fit_filters = ['var1 != 5']
    choosers_predict_filters = ['var1 != 7']
    alts_fit_filters = ['var3 != 15']
    alts_predict_filters = ['var2 != 14']
    interaction_predict_filters = None
    estimation_sample_size = None
    choice_column = None
    name = 'Test LCM'

    model = lcm.MNLLocationChoiceModel(
        model_exp, sample_size, location_id_col,
        choosers_fit_filters, choosers_predict_filters,
        alts_fit_filters, alts_predict_filters,
        interaction_predict_filters, estimation_sample_size,
        choice_column, name)
    loglik = model.fit(choosers, alternatives, choosers.thing_id)
    model.report_fit()

    # hard to test things exactly because there's some randomness
    # involved, but can at least do a smoke test.
    assert len(loglik) == 3
    assert len(model.fit_parameters) == 2
    assert len(model.fit_parameters.columns) == 3

    choosers.thing_id = np.nan
    choosers.thing_id.iloc[0] = 'a'

    choices = model.predict(choosers, alternatives)

    pdt.assert_index_equal(choices.index, pd.Index([1, 3, 4]))
    assert choices.isin(alternatives.index).all()

    # check that we can do a YAML round-trip
    yaml_str = model.to_yaml()
    new_model = lcm.MNLLocationChoiceModel.from_yaml(yaml_str)

    assert new_model.fitted
    assert model.fit_parameters.to_dict() == new_model.fit_parameters.to_dict()


def test_mnl_lcm_repeated_alts(choosers, alternatives):
    model_exp = 'var2 + var1:var3'
    sample_size = 5
    location_id_col = None
    choosers_fit_filters = ['var1 != 5']
    choosers_predict_filters = ['var1 != 7']
    alts_fit_filters = ['var3 != 15']
    alts_predict_filters = ['var2 != 14']
    interaction_predict_filters = ['var1 * var2 > 50']
    estimation_sample_size = None
    choice_column = 'thing_id'
    name = 'Test LCM'

    model = lcm.MNLLocationChoiceModel(
        model_exp, sample_size, location_id_col,
        choosers_fit_filters, choosers_predict_filters,
        alts_fit_filters, alts_predict_filters,
        interaction_predict_filters, estimation_sample_size,
        choice_column, name)
    loglik = model.fit(choosers, alternatives, choosers.thing_id)
    model.report_fit()

    # hard to test things exactly because there's some randomness
    # involved, but can at least do a smoke test.
    assert len(loglik) == 3
    assert len(model.fit_parameters) == 2
    assert len(model.fit_parameters.columns) == 3

    repeated_index = alternatives.index.repeat([1, 2, 3, 2, 4, 3, 2, 1, 5, 8])
    repeated_alts = alternatives.loc[repeated_index].reset_index()

    choices = model.predict(choosers, repeated_alts)

    pdt.assert_index_equal(choices.index, pd.Index([0, 1, 3, 4]))
    assert choices.isin(alternatives.index).all()
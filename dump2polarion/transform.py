# -*- coding: utf-8 -*-
"""
Functions for validating and transforming results. These are specific for given Polarion project.

If the 'polarion-lookup-method' is set to 'custom', this is the place where you can
set the 'id' of the testcase to desired value.
"""

from __future__ import absolute_import, unicode_literals

import re

from dump2polarion.verdicts import Verdicts


# pylint: disable=inconsistent-return-statements
def only_passed_and_wait(result):
    """Returns PASS and WAIT results only, skips everything else."""
    verdict = result.get('verdict', '').strip().lower()
    if verdict in Verdicts.PASS + Verdicts.WAIT:
        return result


def _insert_source_info(result):
    """Adds info about source of test result if available."""
    comment = result.get('comment')
    # don't change comment if it already exists
    if comment:
        return

    source = result.get('source')
    job_name = result.get('job_name')
    run = result.get('run')
    source_list = [source, job_name, run]
    if not all(source_list):
        return

    source_note = '/'.join(source_list)
    source_note = 'Source: {}'.format(source_note)
    result['comment'] = source_note


# pylint: disable=unused-argument
def get_results_transform_cfme(config):
    """Return result transformation function for CFME."""
    skip_searches = [
        'SKIPME:',
        'Skipping due to these blockers',
        'BZ ?[0-9]+',
        'GH ?#?[0-9]+',
        'GH#ManageIQ',
    ]
    skips = re.compile('(' + ')|('.join(skip_searches) + ')')

    def results_transform(result):
        """Results transform for CFME."""
        result = result.copy()

        # make sure that last part of classname is included in "title", e.g.
        # "TestServiceRESTAPI.test_power_parent_service"
        classname = result.get('classname', '')
        if classname:
            filepath = result.get('file', '')
            title = result.get('title')
            if title and '/' in filepath and '.' in classname:
                fname = filepath.split('/')[-1].replace('.py', '')
                last_classname = classname.split('.')[-1]
                # last part of classname is not file name
                if fname != last_classname and last_classname not in title:
                    result['title'] = '{0}.{1}'.format(last_classname, title)
            # we don't need to pass classnames?
            del result['classname']

        # add source of test result if available
        _insert_source_info(result)

        verdict = result.get('verdict', '').strip().lower()
        # we want to submit PASS and WAIT results
        if verdict in Verdicts.PASS + Verdicts.WAIT:
            return result
        comment = result.get('comment')
        # ... and SKIP results where there is a good reason (blocker etc.)
        if verdict in Verdicts.SKIP and comment and skips.search(comment):
            # found reason for skip
            result['comment'] = comment.replace('SKIPME: ', '').replace('SKIPME', '')
            return result
        if verdict in Verdicts.FAIL and comment and 'FAILME' in comment:
            result['comment'] = comment.replace('FAILME: ', '').replace('FAILME', '')
            return result
        # we don't want to report this result if here
        return None

    return results_transform


# pylint: disable=unused-argument
def get_results_transform_cmp(config):
    """Return result transformation function for CFME."""
    skip_searches = [
        'SKIPME:',
        'Skipping due to these blockers',
        'BZ ?[0-9]+',
        'GH ?#?[0-9]+',
        'GH#ManageIQ',
    ]
    skips = re.compile('(' + ')|('.join(skip_searches) + ')')

    def results_transform(result):
        """Results transform for CMP."""
        result = result.copy()

        classname = result.get('classname', '')
        if classname:
            # we don't need to pass classnames?
            del result['classname']

        # if the "test_id" property is present, use it as testcase ID
        test_id = result.get('test_id', '')
        if test_id:
            result['id'] = test_id

        verdict = result.get('verdict', '').strip().lower()
        # we want to submit PASS and WAIT results
        if verdict in Verdicts.PASS + Verdicts.WAIT:
            return result
        comment = result.get('comment')
        # ... and SKIP results where there is a good reason (blocker etc.)
        if verdict in Verdicts.SKIP and comment and skips.search(comment):
            # found reason for skip
            result['comment'] = comment.replace('SKIPME: ', '').replace('SKIPME', '')
            return result
        if verdict in Verdicts.FAIL and comment and 'FAILME' in comment:
            result['comment'] = comment.replace('FAILME: ', '').replace('FAILME', '')
            return result
        # we don't want to report this result if here
        return None

    return results_transform


PROJECT_MAPPING = {
    'RHCF3': get_results_transform_cfme,
    'CMP': get_results_transform_cmp,
}


# pylint: disable=inconsistent-return-statements
def get_results_transform(config):
    """Returns results transformation function.

    The transformation function is returned by calling corresponding "getter" function.

    This allows customizations of results data according to requirements
    of the specific project.

    When no results data are returned, this result will be ignored
    and will not be written to the resulting XML.
    """

    project = config['xunit_import_properties']['polarion-project-id']
    if project in PROJECT_MAPPING:
        return PROJECT_MAPPING[project](config)

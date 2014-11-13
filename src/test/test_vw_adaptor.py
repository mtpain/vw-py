"""
Testing module for Virtual Watershed Data adaptor.
"""

from vw_adaptor import *

import unittest
import os

from nose.tools import raises
from difflib import Differ
from requests.exceptions import HTTPError


def showStringDiff(s1, s2):
    """ Writes differences between strings s1 and s2 """
    d = Differ()
    diff = d.compare(s1.splitlines(), s2.splitlines())
    diffList = [el for el in diff
                if el[0] != ' ' and el[0] != '?']

    for l in diffList:

        if l[0] == '+':
            print "+" + bcolors.GREEN + l[1:] + bcolors.ENDC
        elif l[0] == '-':
            print "-" + bcolors.RED + l[1:] + bcolors.ENDC
        else:
            assert False, "Error, diffList entry must start with + or -"


class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'


class TestJSONMetadata(unittest.TestCase):
    """ Test that individual and sets of JSON metadata are being properly
        generated. """
    def setUp(self):
        """
        initialize the class with some appropriate entry
        metadata from file
        """
        self.config = get_config("src/test/test.conf")

        self.modelRunUUID = "09079630-5ef8-11e4-9803-0800200c9a66"
        self.parentModelRunUUID = "373ae181-a0b2-4998-ba32-e27da190f6dd"

    def testCorrectMetadatum(self):
        """ Test that a single metadata JSON string is properly built (JSON)"""
        # Run test for 'inputs' model_set
        # create metadata file
        model_set = "inputs"
        generated = makeWatershedMetadatum("src/test/data/i_dont_exist.data",
                                           self.config,
                                           self.parentModelRunUUID,
                                           self.modelRunUUID,
                                           model_set,
                                           "Testing metadata!",
                                           "<XML>yup.</XML>"
                                           )
        # load expected json metadata file
        expected = open("src/test/data/expected1_in.json", 'r').read()

        # check equality
        assert generated == expected, \
            showStringDiff(generated, expected)

        model_set = "outputs"
        generated = makeWatershedMetadatum("src/test/data/fake_output.tif",
                                           self.config,
                                           self.parentModelRunUUID,
                                           self.modelRunUUID,
                                           model_set,
                                           "Testing metadata!",
                                           "<XML>yup.</XML>"
                                           )
        # load expected json metadata file
        expected = open("src/test/data/expected_w_services.json", 'r').read()

        # check equality
        assert generated == expected, \
            showStringDiff(generated, expected)


class TestFGDCMetadata(unittest.TestCase):
    """ Test individual and sets of XML FGDC-standard metadata are being
        properly generated and uploaded to the Virtual Watershed
    """
    def setUp(self):
        """ initialize the class with some appropriate entry
            metadata from file
        """
        self.config = get_config("src/test/test.conf")

        self.modelRunUUID = "09079630-5ef8-11e4-9803-0800200c9a66"
        self.dataFile = "src/test/data/in.00"

    def testCorrectMetadatum(self):
        """ Test that a single metadata JSON string is properly built (FGDC)"""

        generated = makeFGDCMetadatum(self.dataFile, self.config,
                                      self.modelRunUUID)

        expected = open("src/test/data/expected1_in.xml", 'r').read()
        assert generated == expected, \
            showStringDiff(generated, expected)


class TestVWClient(unittest.TestCase):
    """ Test the functionality of the Virtual Watershed client """

    def setUp(self):

        self.vwClient = default_vw_client()

        self.modelRunUUID = \
            self.vwClient.search(limit=20).records[0]['model_run_uuid']

        self.config = get_config("src/test/test.conf")

    @raises(HTTPError)
    def test_authFail(self):
        """ Test that failed authorization is correctly caught """
        actualVWip = "129.24.196.43"
        VWClient(actualVWip, "fake_user", "fake_passwd")

    def test_insert(self):
        """ VW Client properly inserts data """

        hostname = self.config['Common']['watershedIP']
        modelIdUrl = "https://" + hostname + "/apps/my_app/newmodelrun"

        data = {"description": "inital insert"}

        result = \
            requests.post(modelIdUrl, data=json.dumps(data),
                          auth=(self.vwClient.uname, self.vwClient.passwd),
                          verify=False)

        modelRunUUID = result.text

        self.vwClient.upload(modelRunUUID, "src/test/data/in.00")

        dataFile = "src/test/data/in.00"

        fgdcXML = \
            makeFGDCMetadatum(dataFile, self.config, modelRunUUID=modelRunUUID)

        watershedJSON = \
            makeWatershedMetadatum(dataFile, self.config, modelRunUUID,
                                   modelRunUUID, "inputs",
                                   "Description of the data", "filePath")

        self.vwClient.insert_metadata(watershedJSON, fgdcXML)

        vwTestUUIDEntries = self.vwClient.fetch_records(modelRunUUID)

        assert vwTestUUIDEntries,\
            "No VW Entries corresponding to the test UUID"

    @raises(HTTPError)
    def test_insertFail(self):
        """ VW Client throws error on failed insert"""
        self.vwClient.insert_metadata('{"metadata": {"xml": "mo garbage"}}',
                                      "<XML?></XML>")

    def test_upload(self):
        """ VW Client properly uploads data """

        self.vwClient.upload(self.modelRunUUID, "src/test/data/in.00")

        # fetch the file from the url we know from the VW file storage pattern
        results = \
            self.vwClient.search(modelRunUUID=self.modelRunUUID, limit=1)

        url = results.records[0]['downloads'][0]['bin']

        outfile = "src/test/data/back_in.00"

        if os.path.isfile(outfile):
            os.remove(outfile)

        self.vwClient.download(url, outfile)

        # check that the file now exists in the file system as expected
        assert os.path.isfile(outfile)

        os.remove(outfile)

    def test_fetch(self):
        """ VW Client properly fetches data """

        # search for a valid modelRunUUID to use as a parent modelRunUUID
        uuid = self.modelRunUUID

        # use that to fetch metadata for that single modelRunUUID
        assert self.vwClient.fetch_records(uuid).total > 0

    @raises(AssertionError)
    def test_fetchFail(self):
        """
        VW Client fails when trying to fetch non-existent modelRunUUID
        """
        self.vwClient.fetch_records("invalid_uuid")

    def test_download(self):
        """
        VW Client properly downloads data
        """
        result = \
            self.vwClient.search(modelRunUUID=self.modelRunUUID, limit=1)
        url = result.records[0]['downloads'][0]['bin']

        outfile = "src/test/data/test_dl.file"

        if os.path.isfile(outfile):
            os.remove(outfile)

        self.vwClient.download(url, outfile)

        assert os.path.isfile(outfile)

        os.remove(outfile)

    @raises(AssertionError)
    def test_downloadFail(self):
        """ VW Client throws error on failed download """
        url = "http://httpbin.org/status/404"

        self.vwClient.download(url, "this won't ever exist")
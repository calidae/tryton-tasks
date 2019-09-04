#!/usr/bin/env python
from .scm import ScmCollection as ns
from .bootstrap import BootstrapCollection
from .config import ConfigCollection
from .bucket.bitbucket import BitbucketCollection
from .utils import UtilsCollection
from .tryton import TrytonCollection
from .tests import TestCollection
from .reviewboard import ReviewCollection
from .tryton_component import ComponentCollection
from .project import ProjectCollection
from .userdoc import DocCollection
from .patches import QuiltCollection
from .gal import GalCollection
from .pypi import PypiCollection
from .meeting import MeetingCollection
from .startup import StartupCollection
from .database import DatabaseCollection
from .features import FeatureCollection
from .bugs import BugCollection

ns.add_collection(BootstrapCollection, 'bs')
ns.add_collection(BitbucketCollection, 'bucket')
ns.add_collection(UtilsCollection, 'utils')
ns.add_collection(ConfigCollection, 'config')
ns.add_collection(TrytonCollection, 'tryton')
ns.add_collection(TestCollection, 'test')
ns.add_collection(ReviewCollection, 'rb')
ns.add_collection(ComponentCollection, 'component')
ns.add_collection(ProjectCollection, 'project')
ns.add_collection(DocCollection, 'doc')
ns.add_collection(QuiltCollection, 'quilt')
ns.add_collection(GalCollection, 'gal')
ns.add_collection(PypiCollection, 'pypi')
ns.add_collection(MeetingCollection, 'meeting')
ns.add_collection(StartupCollection, 'startup')
ns.add_collection(DatabaseCollection, 'database')
ns.add_collection(FeatureCollection, 'features')
ns.add_collection(BugCollection, 'bugs')

from ntds.miners import Miner
from collections import defaultdict

SDTABLE="sdtable"
DATATABLE="datatable"

class HRec: # wraps sd entries to make them hashable
    def __init__(self, rec):
        self.rec = rec
    def __hash__(self):
        return hash(self.rec["hash"])



@Miner.register
class SDusers(Miner):
    _name_ = "SDusers"
    _desc_ = "List users in SD"
    @classmethod
    def create_arg_subparser(cls, parser):
        parser.add_argument("--match", help="Look only for users matching REGEX", metavar="REGEX")
        parser.add_argument("--verbose", action="store_true", help="List security descriptors for each user")
    
    def run(self, options):

        dt = options.db.db[DATATABLE]
        sd = options.db.db[SDTABLE]
    
        match = None
        if options.match:
            match = {"$or": [
                    { "value.DACL.ACEList":
                          {"$elemMatch":
                               {"SID": { "$regex": options.match } }
                           }
                      },
                    { "value.SACL.ACEList":
                          {"$elemMatch":
                               {"SID": { "$regex": options.match } }
                           }
                      },
                    ] }
                    
        users = defaultdict(lambda:set())
        
        for r in sd.find(match):
            for aclt in "SACL","DACL":
                if r["value"] and aclt in r["value"]:
                    for ace in r["value"][aclt]["ACEList"]:
                        sid = ace["SID"]
                        # XXX check sid matches regex
                        users[sid].add(HRec(r))
        
        for sid,lsd in sorted(users.iteritems(), key=lambda (x,y):len(y)):
            c = dt.find({"objectSid":sid}) #, "name":{"$exists":True}})
            names = set([ r["name"] for r in c if "name" in r])
            c.rewind()
            dates = set([ r["whenCreated"].ctime() for r in c if "whenCreated" in r])
            print "%-50s %5i SD (%3i objects) %-60s   %s" % (sid, len(lsd), c.count(), " | ".join(names), " | ".join(dates))
            if options.verbose:
                for sd in lsd:
                    print "    id=%(id)7i refcount=%(refcount)4i hash=%(hash)s" % sd.rec
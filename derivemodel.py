import yaml
from rdflib import URIRef, Literal, BNode, Graph, ConjunctiveGraph
from rdflib.namespace import RDF, RDFS, SKOS, OWL, Namespace, NamespaceManager, XSD
import sys
import csv

BDR = Namespace("http://purl.bdrc.io/resource/")
BDO = Namespace("http://purl.bdrc.io/ontology/core/")
TMP = Namespace("http://purl.bdrc.io/ontology/tmp/")
BDA = Namespace("http://purl.bdrc.io/admindata/")
ADM = Namespace("http://purl.bdrc.io/ontology/admin/")

res = Graph()

NSM = NamespaceManager(res)
NSM.bind("bdr", BDR)
NSM.bind("bdo", BDO)
NSM.bind("tmp", TMP)
NSM.bind("bda", BDA)
NSM.bind("adm", ADM)
NSM.bind("skos", SKOS)
NSM.bind("rdfs", RDFS)

IIIFPREFIX = "https://iiif.bdrc.io/"
if len(sys.argv) > 1:
    IIIFPREFIX = sys.argv[1]

RICMODE = "-ric" in sys.argv
RICMODEWL = {}

# use yaml.CSafeLoader / if available but don't crash if it isn't
try:
    yaml_loader = yaml.CSafeLoader
except (ImportError, AttributeError):
    yaml_loader = yaml.SafeLoader

with open('ricmodelist.txt', newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for row in reader:
        RICMODEWL[row[0]] = True

def getThForInstance(thdict):
	keys = sorted(thdict.keys())
	if len(keys) == 0:
		return None
	for iinstanceQname in keys:
		if iinstanceQname.startswith("bdr:W1FEMC03"):
			return thdict[iinstanceQname]
	return thdict[keys[0]]

def main():
	iiifdb = {}
	with open("iiifdb.yml", 'r') as stream:
	    iiifdb = yaml.load(stream, Loader=yaml_loader)

	instancesTh = {}

	for iinstanceQname, infos in iiifdb.items():
		if RICMODE and iinstanceQname[4:] not in RICMODEWL:
			continue
		iinstanceRes = URIRef("http://purl.bdrc.io/resource/"+iinstanceQname[4:])
		instanceRes = URIRef("http://purl.bdrc.io/resource/"+infos["instanceQname"][4:])
		# case of external iiif volumes
		if "service" in infos and infos["service"] is not None:
			thservice = URIRef(infos["service"])
			res.add( (instanceRes, TMP.thumbnailIIIFService, thservice) )
			res.add( (iinstanceRes, TMP.thumbnailIIIFService, thservice) )
			continue
		if " " in infos["imgfname"]:
			print("space in filename: "+infos["imgfname"])
			continue
		if "selector" in infos:
			selector = infos["selector"]
			selected = "/"
			selected += selector["region"]+"/" if "region" in selector else "full/"
			selected += selector["size"]+"/" if "size" in selector else "max/"
			selected += selector["rotation"]+"/" if "rotation" in selector else "0/"
			selected += selector["quality"]+"." if "quality" in selector else "default."
			lowercasefname = infos["imgfname"].lower()
			defaultformat = "jpg"
			if ".tif" in lowercasefname:
				defaultformat = "png"
			selected += selector["format"]+"." if "format" in selector else defaultformat
			selectedres = URIRef(IIIFPREFIX+infos["igQname"]+"::"+infos["imgfname"]+selected)
			# TODO: not well handled for instance clusters
			res.add( (instanceRes, TMP.thumbnailIIIFSelected, selectedres) )
			res.add( (iinstanceRes, TMP.thumbnailIIIFSelected, selectedres) )
			continue
		thservice = URIRef(IIIFPREFIX+infos["igQname"]+"::"+infos["imgfname"])
		if infos["instanceQname"] not in instancesTh:
			instancesTh[infos["instanceQname"]] = {}
		instancesTh[infos["instanceQname"]][iinstanceQname] = thservice
		res.add( (iinstanceRes, TMP.thumbnailIIIFService, thservice) )
	
	for instanceQname in instancesTh:
		instanceRes = URIRef("http://purl.bdrc.io/resource/"+instanceQname[4:])
		res.add( (instanceRes, TMP.thumbnailIIIFService, getThForInstance(instancesTh[instanceQname])) )

	res.serialize("thumbnails.ttl", format="turtle")

main()
import yaml
from rdflib import URIRef, Literal, BNode, Graph, ConjunctiveGraph
from rdflib.namespace import RDF, RDFS, SKOS, OWL, Namespace, NamespaceManager, XSD
import sys

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

def main():
	iiifdb = {}
	with open("iiifdb.yml", 'r') as stream:
	    iiifdb = yaml.safe_load(stream)

	for iinstanceQname, infos in iiifdb.items():
		instanceRes = URIRef("http://purl.bdrc.io/resource/"+infos["instanceQname"][4:])
		iinstanceRes = URIRef("http://purl.bdrc.io/resource/"+iinstanceQname[4:])
		# case of external iiif volumes
		if "service" in infos and infos["service"] is not None:
			thservice = URIRef(infos["service"])
			res.add( (instanceRes, TMP.thumbnailIIIFService, thservice) )
			res.add( (iinstanceRes, TMP.thumbnailIIIFService, thservice) )
			continue
		if " " in infos["imgfname"]:
			print("space in filename: "+infos["imgfname"])
			continue
		# case of BDRC good old volumes
		
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
			res.add( (instanceRes, TMP.thumbnailIIIFSelected, selectedres) )
			res.add( (iinstanceRes, TMP.thumbnailIIIFSelected, selectedres) )
			continue
		thservice = URIRef(IIIFPREFIX+infos["igQname"]+"::"+infos["imgfname"])
		res.add( (instanceRes, TMP.thumbnailIIIFService, thservice) )
		res.add( (iinstanceRes, TMP.thumbnailIIIFService, thservice) )
	
	res.serialize("thumbnails.ttl", format="turtle")

main()
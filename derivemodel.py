import yaml
from rdflib import URIRef, Literal, BNode, Graph, ConjunctiveGraph
from rdflib.namespace import RDF, RDFS, SKOS, OWL, Namespace, NamespaceManager, XSD

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
		thservice = URIRef("https://iiif.bdrc.io/"+infos["igQname"]+"::"+infos["imgfname"])
		res.add( (instanceRes, TMP.thumbnailIIIFService, thservice) )
		res.add( (iinstanceRes, TMP.thumbnailIIIFService, thservice) )
	
	res.serialize("thumbnails.ttl", format="turtle")

main()
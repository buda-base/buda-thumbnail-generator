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

	for instanceUri, infos in iiifdb.items():
		instanceRes = URIRef(instanceUri)
		thservice = URIRef(infos["service"])
		res.add( (instanceRes, TMP.thumbnailIIIFService, thservice) )
	
	res.serialize("thumbnails.ttl", format="turtle")

main()
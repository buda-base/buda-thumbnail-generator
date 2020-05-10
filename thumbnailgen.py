import hashlib
import PIL
import PIL.Image
import PIL.ImageOps
import PIL.ImageCms
import io
import os
import glob
from rdflib import URIRef, Literal, BNode, Graph, ConjunctiveGraph
from rdflib.namespace import RDF, RDFS, SKOS, OWL, Namespace, NamespaceManager, XSD
import requests

IIGITDIR="../xmltoldmigration/tbrc-ttl/iinstances/"
BASE_MAX_DIM=370
BASE_CROP_DIM=185
MAX_RATIO=2

BDR = Namespace("http://purl.bdrc.io/resource/")
BDO = Namespace("http://purl.bdrc.io/ontology/core/")
TMP = Namespace("http://purl.bdrc.io/ontology/tmp/")
BDA = Namespace("http://purl.bdrc.io/admindata/")
ADM = Namespace("http://purl.bdrc.io/ontology/admin/")

NSM = NamespaceManager(Graph())
NSM.bind("bdr", BDR)
NSM.bind("bdo", BDO)
NSM.bind("tmp", TMP)
NSM.bind("bda", BDA)
NSM.bind("adm", ADM)
NSM.bind("skos", SKOS)
NSM.bind("rdfs", RDFS)

def get_s3_folder_prefix(iiLocalName, igLocalName):
    """
    gives the s3 prefix (~folder) in which the volume will be present.
    inpire from https://github.com/buda-base/buda-iiif-presentation/blob/master/src/main/java/
    io/bdrc/iiif/presentation/ImageInfoListService.java#L73
    Example:
       - iiLocalName=W22084, igLocalName=I0886
       - result = "Works/60/W22084/images/W22084-0886/
    where:
       - 60 is the first two characters of the md5 of the string W22084
       - 0886 is:
          * the image group ID without the initial "I" if the image group ID is in the form I\\d\\d\\d\\d
          * or else the full image group ID (incuding the "I")
    """
    md5 = hashlib.md5(str.encode(iiLocalName))
    two = md5.hexdigest()[:2]

    pre, rest = igLocalName[0], igLocalName[1:]
    if pre == 'I' and rest.isdigit() and len(rest) == 4:
        suffix = rest
    else:
        suffix = igLocalName

    return 'Works/{two}/{RID}/images/{RID}-{suffix}/'.format(two=two, RID=iiLocalName, suffix=suffix)


def print_all_errors():
    """ prints all the errors in the db in a human friendly way"""
    pass

def gets3blob(bucket, s3Key):
    f = io.BytesIO()
    try:
        bucket.download_fileobj(s3Key, f)
        return f
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return None
        else:
            raise

def getImageList(iiLocalName, igLocalName):
    s3key = get_s3_folder_prefix(iiLocalName, igLocalName)+"dimensions.json"
    blob = gets3blob(s3key)
    if blob is None:
        return None
    return gzip.decompress(blob)

def findBestThumbnailIdx(igQname, imageList, tbrcintroimages):
    idx = tbrcintroimages+1
    if igQname.startswith("bdr:W1FEMC"):
        idx = 1
    # if there's a very big image, use it as thumbnail
    for i in range(min(len(imageList), 10)):
        if imageList[i].size > 3000000:
            idx = i
            break
    return idx

def getImage(igQname, iiLocalName, imageFileName):
    pass

def uploadThumbnail(blob, bucketname, filename, iiLocalName, igQname):
    s3key = get_s3_folder_prefix(iiLocalName, igLocalName)+filename
    s3 = boto3.resource('s3')
    obj = s3.Object(bucketname, s3key)
    obj.put(Body=blob)

SRGB = PIL.ImageCms.createProfile('sRGB')

def thumbnailizeAndWriteInfo(im, info):
    if im.width > MAX_RATIO*im.height:
        th = PIL.ImageOps.fit(im, (BASE_MAX_DIM,BASE_CROP_DIM), PIL.Image.LANCZOS, centering=(0,0))
    elif im.height > MAX_RATIO*im.width:
        th = PIL.ImageOps.fit(im, (BASE_CROP_DIM,BASE_MAX_DIM), PIL.Image.LANCZOS, centering=(0,0))
    else:
        factor = BASE_MAX_DIM / max(im.width, im.height)
        th = PIL.ImageOps.scale(im, factor, PIL.Image.LANCZOS)
    if th.mode != "1" and th.mode != "P":
        #th = PIL.ImageOps.autocontrast(th)
        icc_blob = im.info.get('icc_profile')
        if icc_blob is not None:
            f = io.BytesIO(icc_blob)
            icc = PIL.ImageCms.ImageCmsProfile(f)
            th = PIL.ImageCms.profileToProfile(th, icc, SRGB)
    return th

def getThumbnailBlob(im):
    if im.mode == "1" or im.mode == "P":
        with io.BytesIO() as output:
            im.save(output, format="png", optimize=True, pnginfo=None, exif=b"")
            return output.getvalue()
    else:
        with io.BytesIO() as output:
            #im.save(output, format="jpeg", quality=75, optimize=True, progressive=True, icc_profile=None, exif=b"", subsampling=2, qtables="web_low")
            im.save(output, format="jpeg", quality=75, optimize=True, progressive=True, icc_profile=None, exif=b"", subsampling=2)
            return output.getvalue()

def listFiles(iiGitPath):
    return glob.glob(iiGitPath+'/**/W*.trig')

def getThumbnailForIIIFManifest(manifestUrl):
    # examples: 
    #  - https://eap.bl.uk/archive-file/EAP676-12-2/manifest
    #  - https://iiif.archivelab.org/iiif/rashodgson13/manifest.json
    #  - https://cudl.lib.cam.ac.uk/iiif/MS-OR-00159
    res = {"canvas": None, "service": None}
    try:
        resp = requests.get(url=manifestUrl)
        manifest = resp.json()
        firstseq = manifest["sequences"][0]
        startcanvas = firstseq["canvases"][0]
        if "startCanvas" in firstseq:
            startcanvasid = firstseq["startCanvas"]
            for canvas in firstseq["canvases"]:
                if canvas["@id"] == startcanvasid:
                    startcanvas = canvas
        res["canvas"] = startcanvas["@id"]
        res["service"] = startcanvas["images"][0]["resource"]["@id"]
        return res
    finally:
        return res

def localname(res):
    # a quick hack
    s = str(res)
    idx = s.rindex("/")

def thumbnailForIiFile(iiFilePath, infodb, force=False):
    # read file
    model = ConjunctiveGraph()
    model.parse(str(iiFilePath), format="trig")
    # if status != released, pass
    if (None,  ADM.status, BDA.StatusReleased) not in model:
        return
    # get first volume resource
    firstvolRes = None
    for s, p, o in model.triples( (None, BDO.volumeNumber, Literal(1)) ):
        firstvolRes = s
    if firstvolRes is None:
        return
    # handle iiif case:
    for s, p, o in model.triples( (firstvolRes, BDO.hasIIIFManifest, None) ):
        manifestUrl = str(o)
        return getThumbnailForIIIFManifest(manifestUrl)
    # get first volume local name:
    _, _, firstVolLname = NSM.compute_qname_strict(firstvolRes)
    # get instance local name
    iinstanceRes = None
    for s, p, o in model.triples( (s, BDO.instanceHasVolume, firstvolRes) ):
        iinstanceRes = s
    if iinstanceRes is None:
        return
    instanceRes = None
    for s, p, o in model.triples( (s, BDO.instanceHasVolume, firstvolRes) ):
        iinstanceRes = s
    # findBestThumbnail
    # getImage
    # get/createinfo
    # thumbnailizeandwriteinfo
    # uploadthumbnail
    pass

def testThgen():
    for imgfilename in ["test/femc.jpeg", "test/modern.jpeg", "test/08860003.tif"]:
        im = PIL.Image.open(imgfilename)
        if im is None:
            print("error: PIL can't open "+imgfilename)
            continue
        #print(imgfilename+" is mode "+im.mode)
        data = {}
        th = thumbnailizeAndWriteInfo(im, data)
        thblob = getThumbnailBlob(th)
        outfname = "test/output/"+os.path.basename(imgfilename).replace(".tif", ".png")
        with open(outfname,'wb') as out:
            out.write(thblob)
    print(data)

def testGetIIIFTh():
    print(getThumbnailForIIIFManifest("https://eap.bl.uk/archive-file/EAP676-12-2/manifest"))
    print(getThumbnailForIIIFManifest("https://iiif.archivelab.org/iiif/rashodgson13/manifest.json"))
    print(getThumbnailForIIIFManifest("https://cudl.lib.cam.ac.uk/iiif/MS-OR-00159"))

def test():
    print(listFiles("/home/eroux/BUDA/softs/xmltoldmigration/tbrc-ttl/iinstances"))

testGetIIIFTh()
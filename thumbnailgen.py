import hashlib
import PIL
import PIL.Image
import PIL.ImageOps
import PIL.ImageCms
import io
import os
import yaml
import json
from pathlib import Path
import glob
from rdflib import URIRef, Literal, BNode, Graph, ConjunctiveGraph
from rdflib.namespace import RDF, RDFS, SKOS, OWL, Namespace, NamespaceManager, XSD
import requests
from tqdm import tqdm
import boto3
import botocore
import gzip
import sys
from datetime import datetime
import time

BASE_MAX_DIM=370
BASE_CROP_DIM=185
MAX_RATIO=2

#GITPATH = "/home/eroux/BUDA/softs/xmltoldmigration/tbrc-ttl/iinstances"
GITPATH = "../xmltoldmigration/tbrc-ttl/iinstances/"
if len(sys.argv) > 1:
    GITPATH = sys.argv[1]

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

SESSION = boto3.Session(profile_name='thumbnailgen')
S3 = SESSION.client('s3')

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

def gets3blob(s3Key):
    f = io.BytesIO()
    try:
        S3.download_fileobj('archive.tbrc.org', s3Key, f)
        return f
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return None
        else:
            raise

# This has a cache mechanism
def getImageList(iiLocalName, igLocalName, force=False):
    cachepath = Path("cache/il/"+igLocalName+".json.gz")
    if not force and cachepath.is_file():
        with gzip.open(str(cachepath), 'r') as gzipfile:
            try:
                res = json.loads(gzipfile.read())
                return res
            except:
                tqdm.write("can't read "+str(cachepath))
                pass
    s3key = get_s3_folder_prefix(iiLocalName, igLocalName)+"dimensions.json"
    blob = gets3blob(s3key)
    if blob is None:
        return None
    blob.seek(0)
    b = blob.read()
    ub = gzip.decompress(b)
    s = ub.decode('utf8')
    data = json.loads(s)
    with gzip.open(str(cachepath), 'w') as gzipfile:
        gzipfile.write(json.dumps(data).encode('utf-8'))
    return data

def findBestThumbnailIdxImage(igLname, imageList, tbrcintroimages):
    if igLname.startswith("W1FEMC"):
        return 1
    # if there's a very big image, use it as thumbnail
    for i in range(min(len(imageList), 10)):
        if "size" in imageList[i] and imageList[i]["size"] > 3000000:
            return i
    return tbrcintroimages

def findBestThumbnailIdxService(igLname, imageList, tbrcintroimages):
    if len(imageList) == 0:
        return -1
    if igLname.startswith("W1FEMC"):
        if len(imageList) < 2:
            return -1
        return 1
    # if there's a very big image, use it as thumbnail
    for i in range(tbrcintroimages, min(len(imageList)-1, 20)):
        if "size" not in imageList[i]:
            return i
    # this branch is pretty unlikely...
    return -1

def likelyHasIntroImages(imageList, iiLocalName):
    if len(imageList) < 2:
        return False
    if 'width' not in imageList[0] or 'width' not in imageList[1] or 'height' not in imageList[0] or 'height' not in imageList[0]:
        tqdm.write("ill formed image list for "+iiLocalName)
        return False
    if (imageList[0]['width'] == 2550 and imageList[0]['height'] == 3300 and imageList[1]['width'] == 2550 and imageList[1]['height'] == 3300):
        return True
    # if the first two are not tif, abandon
    if (not imageList[0]['filename'].lower().endswith(".tif")) or (not imageList[1]['filename'].lower().endswith(".tif")):
        return False
    # if the first one has not width < height, abandon
    if imageList[0]['width'] > imageList[0]['height']:
        return False
    # if the third one is not tif, return True (may have some false positives)
    if len(imageList) >= 3:
        if (not imageList[2]['filename'].lower().endswith(".tif")) and (not imageList[2]['filename'].lower().endswith(".tiff")):
            return True
    return False


def getImage(igQname, iiLocalName, imageFileName):
    # TODO
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

def thumbnailForIiFile(iiFilePath, filesdb, iiifdb, missinglists, forceIfPresent=True, forceRefreshDimensions=False):
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
        tqdm.write("can't find first volume in "+iiFilePath)
        return
    # get first volume local name:
    _, _, firstVolLname = NSM.compute_qname_strict(firstvolRes)
    # get image instance local name
    iinstanceRes = None
    for s, p, o in model.triples( (None, BDO.instanceHasVolume, firstvolRes) ):
        iinstanceRes = s
    if iinstanceRes is None:
        tqdm.write("can't find iinstance in "+iinstanceLname)
        return
    _, _, iinstanceLname = NSM.compute_qname_strict(iinstanceRes)
    # get instance
    instanceRes = None
    for s, p, o in model.triples( (iinstanceRes, BDO.instanceReproductionOf, None) ):
        instanceRes = o
    if instanceRes is None:
        tqdm.write("can't find instance in "+iinstanceLname)
        return
    _, _, instanceLname = NSM.compute_qname_strict(instanceRes)
    
    # ignore if we know the list is missing
    if (not forceIfPresent) and (iinstanceLname+'-'+firstVolLname) in missinglists:
        return
    # TODO: in a first time, we just add stuff, we don't modify anything if it's there
    # but in the future we should check the commit of the trig file. We could also assume
    # that external manifests never change
    if (not forceIfPresent) and str(instanceRes) in iiifdb:
        return
    # handle external iiif case:
    for s, p, o in model.triples( (firstvolRes, BDO.hasIIIFManifest, None) ):
        manifestUrl = str(o)
        iiifthumbnail = getThumbnailForIIIFManifest(manifestUrl)
        iiifthumbnail["infotimestamp"] = datetime.now().isoformat()
        iiifthumbnail["imagegroup"] = str(firstvolRes)
        iiifdb[str(instanceRes)] = iiifthumbnail
        return iiifthumbnail
    # get image list
    imglist = getImageList(iinstanceLname, firstVolLname, forceRefreshDimensions)
    if imglist is None:
        missinglists.append(iinstanceLname+"-"+firstVolLname)
        return
    # get intro images value
    tbrcintroimages = 0
    tbrcintroimagesoriginal = False
    for s, p, o in model.triples( (firstvolRes, BDO.volumePagesTbrcIntro, None) ):
        tbrcintroimages = int(o)
        tbrcintroimagesoriginal = True
    if tbrcintroimages == 0 and likelyHasIntroImages(imglist, iinstanceLname):
        tbrcintroimages = 2
        tbrcintroimagesoriginal = False
    # get thumbnail index in list
    thumbnailserviceidx = findBestThumbnailIdxService(firstVolLname, imglist, tbrcintroimages)
    if thumbnailserviceidx == -1 or thumbnailserviceidx >= len(imglist):
        tqdm.write("cannot find reasonable iiif thumbnail for "+iinstanceLname+'-'+firstVolLname)
        return
    thumbnailserviceiinfo = imglist[thumbnailserviceidx]
    canvasurl = "https://iiifpres.bdrc.io/v:bdr:"+firstVolLname+"/canvas/"+thumbnailserviceiinfo["filename"]
    serviceurl = "https://iiif.bdrc.io/bdr:"+firstVolLname+"::"+thumbnailserviceiinfo["filename"]
    iiifinfo = {"canvas": canvasurl, "service": serviceurl}
    iiifinfo["infotimestamp"] = datetime.now().isoformat()
    iiifinfo["imagegroup"] = str(firstvolRes)
    if not tbrcintroimagesoriginal:
        iiifinfo["guessedtbrcintroimages"] = tbrcintroimages
    iiifdb[str(instanceRes)] = iiifinfo
    return iiifinfo
    # get image
    # getImage
    # get/createinfo
    # thumbnailizeandwriteinfo
    # uploadthumbnail


def mainIiif(wrid=None):
    # this currently only generates iiifdb.yml
    # create image list cache dir
    cachedir = Path("cache/il/")
    if not cachedir.is_dir():
        os.makedirs(str(cachedir))
    # read iiifdb
    iiifdb = {}
    if Path("iiifdb.yml").is_file():
        with open("iiifdb.yml", 'r') as stream:
            iiifdb = yaml.safe_load(stream)
    missinglists = []
    if Path("missinglists.yml").is_file():
        with open("missinglists.yml", 'r') as stream:
            missinglists = yaml.safe_load(stream)
    # TODO: get iinstances path from cli
    if wrid is not None:
        md5 = hashlib.md5(str.encode(wrid))
        two = md5.hexdigest()[:2]
        iiifinfo = thumbnailForIiFile(GITPATH+'/'+two+'/'+wrid+'.trig', None, iiifdb, missinglists, forceIfPresent=True, forceRefreshDimensions=False)
        print(yaml.dump(iiifinfo))
        return
    i = 0
    for fname in tqdm(sorted(glob.glob(GITPATH+'/**/W*.trig'))):
        thumbnailForIiFile(fname, None, iiifdb, missinglists)
        i += 1
        if i>= 800:
            try:
                with open("iiifdb.yml", 'w') as stream:
                    yaml.dump(iiifdb, stream)
                with open("missinglists.yml", 'w') as stream:
                    yaml.dump(missinglists, stream)
                i = 0
            except KeyboardInterrupt:
                # poor man's atomicity
                time.sleep(2)
                raise


mainIiif("W20325")
#mainIiif()

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

def testcache():
    cachepath = Path("cache/il/I00EGS1017179.json.gz")
    if cachepath.is_file():
        with gzip.open(str(cachepath), 'r') as gzipfile:
            print(json.loads(gzipfile.read()))

#testcache()

#testGetIIIFTh()
import hashlib
import PIL
import PIL.Image
import PIL.ImageOps
import PIL.ImageCms
import io
import os

IIGITDIR="../xmltoldmigration/tbrc-ttl/iinstances/"

def get_s3_folder_prefix(workRID, imageGroupID):
    """
    gives the s3 prefix (~folder) in which the volume will be present.
    inpire from https://github.com/buda-base/buda-iiif-presentation/blob/master/src/main/java/
    io/bdrc/iiif/presentation/ImageInfoListService.java#L73
    Example:
       - workRID=W22084, imageGroupID=I0886
       - result = "Works/60/W22084/images/W22084-0886/
    where:
       - 60 is the first two characters of the md5 of the string W22084
       - 0886 is:
          * the image group ID without the initial "I" if the image group ID is in the form I\\d\\d\\d\\d
          * or else the full image group ID (incuding the "I")
    """
    md5 = hashlib.md5(str.encode(workRID))
    two = md5.hexdigest()[:2]

    pre, rest = imageGroupID[0], imageGroupID[1:]
    if pre == 'I' and rest.isdigit() and len(rest) == 4:
        suffix = rest
    else:
        suffix = imageGroupID

    return 'Works/{two}/{RID}/images/{RID}-{suffix}/'.format(two=two, RID=workRID, suffix=suffix)


def print_all_errors():
    """ prints all the errors in the db in a human friendly way"""
    pass

def gets3blob(bucket, s3imageKey):
    f = io.BytesIO()
    try:
        bucket.download_fileobj(s3imageKey, f)
        return f
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return None
        else:
            raise

def getIcc(image):
    pass

def getImageList(igQname):
    pass

def findBestThumbnail(igQname, imageList):
    pass

def getImage(igQname, iiLocalName, imageFileName):
    pass

def uploadThumbnail(blob, filename, iiLocalName, igQname):
    pass

SRGB = PIL.ImageCms.createProfile('sRGB')

def thumbnailizeAndWriteInfo(im, info):
    if im.width > 2*im.height:
        th = PIL.ImageOps.fit(im, (400,200), PIL.Image.LANCZOS, centering=(0,0))
    elif im.height > 2*im.width:
        th = PIL.ImageOps.fit(im, (200,400), PIL.Image.LANCZOS, centering=(0,0))
    else:
        factor = 400 / max(im.width, im.height)
        th = PIL.ImageOps.scale(im, factor, PIL.Image.LANCZOS)
    if th.mode != "1" and th.mode != "P":
        th = PIL.ImageOps.autocontrast(th)
        icc_blob = im.info.get('icc_profile')
        if icc_blob is not None:
            f = io.BytesIO(icc_blob)
            icc = PIL.ImageCms.ImageCmsProfile(f)
            th = PIL.ImageCms.profileToProfile(th, icc, SRGB)
    return th

def getThumbnailBlob(im):
    with io.BytesIO() as output:
        if im.mode == "1":
            im.save(output, format="png", optimize=True, pnginfo=None, exif=b"")
        else:
            im.save(output, format="jpeg", quality=100, optimize=True, progressive=True, icc_profile=None, exif=b"", subsampling=2, qtables="web_low")
        return output.getvalue()

def listFiles(iiGitPath):
    pass

def getThumbnailForManifest(manifestUrl):
    pass

def thumbnailForIiFile(iiFilePath, infodb, force=False):
    # read file
    # if status != released, pass
    # if not force and 
    # get first igQname
    # findBestThumbnail
    # getImage
    # get/createinfo
    # thumbnailizeandwriteinfo
    # uploadthumbnail
    pass

def test():
    for imgfilename in ["test/femc.jpeg", "test/modern.jpeg", "test/08860003.tif"]:
        im = PIL.Image.open(imgfilename)
        if im is None:
            print("can't open "+imgfilename)
            continue
        print(imgfilename+" is mode "+im.mode)
        data = {}
        th = thumbnailizeAndWriteInfo(im, data)
        thblob = getThumbnailBlob(th)
        outfname = "test/output/"+os.path.basename(imgfilename).replace(".tif", ".png")
        with open(outfname,'wb') as out:
            out.write(thblob)
    print(data)

test()
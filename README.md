# Thumbnail generator for BUDA

This python script generates one thumbnail for each image instance (`W` record) in BDRC's archive. The general workflow is:

- have a database of generated thumbnails ([iinstance-thumbnails.json](iinstance-thumbnails.json))
- access all image instances in BDRC's database by looking at the git repository
- for each instance where a thumbnail needs to be generated:
   * get the ID for the first image group in the trig file
   * get the `dimensions.json` from s3
   * get the BVM if it exists in the bvm git repo (TODO)
   * perform some magick to generate a thumbnail
   * upload the thumbnail on the bucket `thumbnail.bdrc.io`
   * add the thumbnail in the database

The thumbnails are generated in the following way for image instances:
- 400px for the biggest dimension
- if ratio < 1:2 or 2:1
   * then keep the entire image
   * else crop the image so that it has a 2:1 / 1:2 ratio, keeping the left / top part
- png for bitonal, else jpg
- no metadata, no thumbnail, sRGB color profile, color profile not included
- jpg at 70% quality, progressive, optimized, lowest quality subsampling

## Configuration

The script supposes that it can access AWS credentials with the name `thumbgen`, and that they allow:
- read the `archive.tbrc.org` bucket
- read/write the `thumbnails.bdrc.io` bucket

The script supposes that it can access the following git repos:
- image instances in `repos/iinstances/`
- bvm in `repos/bvm/`

note that these can be symlinks.

It also supposes that a `thumbnailgen` AWS user is configured on the machine and has credentials accessible to the script.

## TODO

- generate thumbnail links for image instances with external manifest
- iiif manifests: record canvas + service
- triples on instance or image instance?
- yaml instead of json?

## Probable API


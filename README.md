# Thumbnail generator for BUDA

## Dependencies

```
$ sudo apt install -y liblcms2-dev liblcms2-2 libtiff5 libtiff5-dev python3-libtiff
$ pip3 install --no-cache-dir -I pillow
$ pip3 install -r requirements.txt
```

## Running

To update the database:

```
curl 'https://ldspdi.bdrc.io/query/table/AO_mustbeonmirror?format=csv&pageSize=50000' | tail -n +2 | sed -re 's/^"bdr:(.*)"$/\1/g' | sort > ricmodelist.txt
python3 thumbnailgen.py path_to_iinstance_repo
```

with the third argument properly set. Then to derive and upload the RDF:


```
python3 derivemodel.py iiif_prefix
curl -v -X PUT -H 'Content-Type:text/turtle' --url 'http://buda5.bdrc.io:13180/fuseki/corerw?graph=http%3A%2F%2Fpurl.bdrc.io%2Fgraph%2Fthumbnails' -T thumbnails.ttl
```

where `iiif_prefix` is the start of the iiifserv url, defaulting to `https://iiif.bdrc.io/`.

## Configuration

The script supposes that it can access AWS credentials with the name `thumbgen`, and that they allow:
- read the `archive.tbrc.org` bucket

It also supposes that a `thumbnailgen` AWS user is configured on the machine and has credentials accessible to the script.

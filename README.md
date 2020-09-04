# Thumbnail generator for BUDA

## Dependencies

```
$ pip install -r requirements.txt
```

## Running

To update the database:

```
python3 thumbnailgen.py path_to_iinstance_repo
```

with the third argument properly set. Then to derive and upload the RDF:


```
python3 derivemodel.py
curl -X PUT -H Content-Type:text/turtle -T thumbnails.ttl -G http://buda1.bdrc.io:13180/fuseki/corerw/data --data-urlencode 'graph=http://purl.bdrc.io/graph/thumbnails'
```

## Configuration

The script supposes that it can access AWS credentials with the name `thumbgen`, and that they allow:
- read the `archive.tbrc.org` bucket

It also supposes that a `thumbnailgen` AWS user is configured on the machine and has credentials accessible to the script.


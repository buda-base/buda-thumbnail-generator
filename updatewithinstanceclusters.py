import yaml
import csv

WTOMW = {}
with open('../xmltoldmigration/src/main/resources/instance-clusters.csv', newline='') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        WTOMW[row[0]] = row[1]

iiifdb = {}
with open("iiifdb.yml", 'r') as stream:
    iiifdb = yaml.safe_load(stream)
    for iinstanceQname, infos in iiifdb.items():
        if iinstanceQname[4:] in WTOMW:
            infos["instanceQname"] = "bdr:"+WTOMW[iinstanceQname[4:]]
    with open("iiifdb.yml", 'w') as stream:
        yaml.dump(iiifdb, stream, default_flow_style=False)
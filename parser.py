import requests
import html
import geopy

def load_index_data(index, do_districts=True, postal=False):
    data = {
        "parties": [],
    }
    if do_districts:
        data.update({
            "districts": []
        })
    source = requests.get(index)
    lines = source.text.split("\n")

    for i in range(0, len(lines)):
        line = lines[i]
        if line.startswith("<td style=\"vertical-align:middle\" ><div style=\"width:10px;height:10px;background-color: "): # Party line
            color = line.split("background-color: ")[1].split(";")[0] # Party color
            party_line = lines[i+1] # Line of source code containing party full name and abbr
            name = abbr = ""
            if "<abbr" in party_line:
                abbr = html.unescape(party_line.split("title=\"")[1].split("\"")[0])
                name = html.unescape(party_line.split(" >")[1].split("</")[0])
            else:
                name = html.unescape(party_line.split(">")[1].split("</")[0])

            absolute_line = lines[i+2] # Line of source code containing absolute number of votes
            relative_line = lines[i+3] # Line of source code containing relative number of votes

            absolute_votes = int(absolute_line.split("<nobr>")[1].split("</nobr>")[0].replace(".", ""))
            relative_votes = float(relative_line.split("<nobr>")[1].split(" %</nobr>")[0].replace(",", "."))

            data["parties"].append({
                "name": name,
                "abbr": abbr,
                "color": color,
                "absolute": absolute_votes,
                "relative": relative_votes
            })
        if line.startswith("<td>Wahlberechtigte") and not postal:
            electorate = int(lines[i+2].split(" >")[1].split("<")[0].replace(".", ""))
            data.update({"electorate": electorate})
        if line.startswith("<td>W&auml;hler/innen"):
            voters_absolute = int(lines[i+2].split(" >")[1].replace(".", ""))
            data.update({"voters_absolute": voters_absolute})
            if not postal:
                voters_relative = float(lines[i+4].split(" >")[1].split(" %")[0].replace(",", "."))
                data.update({"voters_relative": voters_relative})
        if line.startswith("<td>ung&uuml;ltige Stimmen"):
            invalid_votes_absolute = int(lines[i+2].split(" >")[1].replace(".", ""))
            data.update({"invalid_votes_absolute": invalid_votes_absolute})
            if not postal:
                invalid_votes_relative = float(lines[i+4].split(" >")[1].split(" %")[0].replace(",", "."))
                data.update({"invalid_votes_relative": invalid_votes_relative})
        if line.startswith("<td>g&uuml;ltige Stimmen"):
            valid_votes_absolute = int(lines[i+2].split(" >")[1].replace(".", ""))
            data.update({"valid_votes_absolute": valid_votes_absolute})
            if not postal:
                valid_votes_relative = float(lines[i+4].split(" >")[1].split(" %")[0].replace(",", "."))
                data.update({"valid_votes_relative": valid_votes_relative})

        if do_districts:
            if line.startswith("<div class=\"col-sm-2\"  style=\"padding: 4px\" ><div class=\"d-inline-block text-truncate\" ><a title=\""):
                name = html.unescape(line.split("<a title=\"")[1].split("\"")[0])
                id = name.split(" ")[0]
                name = " ".join(name.split(" ")[1:])
                href = '/'.join(index.split("/")[:-1]) + "/" + line.split("href=\"")[1].split("\"")[0]
                data["districts"].append({
                    "name": name,
                    "id": id,
                    "href": href
                })

        if "Wahlraum" in line:
            room_href = '/'.join(index.split("/")[:-1]) + "/" + line.split("href=\"")[1].split("\"")[0]
            source_ = requests.get(room_href)
            lines_ = source_.text.split("\n")
            room = {"accessible": False}
            for line in lines_:
                if line == "<div class=\"label label-success pull-right\" >barrierefrei</div>":
                    room.update({"accessible": True})
                if "Google-Maps" in line and line.startswith("</div><div class=\"panel-body\" ><p><b>"):
                    addr = html.unescape(line.split(" >")[2].split("</a")[0].replace("<br>", ", "))
                    geolocator = geopy.geocoders.Nominatim()
                    try:
                        location = geolocator.geocode(addr)
                        room.update({"lat": location.latitude, "lon": location.longitude})
                    except (geopy.exc.GeopyError, AttributeError) as e:
                        print(e)
                    name = html.unescape(line.split("<p><b>")[1].split("<br>")[0])
                    room.update({"name": name, "addr": addr})
            data.update({"room": room})

    return data


def load_districts_data(data):
    l = len(data["districts"])
    i = 1
    for district in data["districts"]:
        print("LOADING DISTRICT %d / %d (%s)" % (i, l, district["name"]))
        postal = district["id"].startswith("B")
        dist_data = load_index_data(district["href"], False, postal)
        district.update(dist_data)
        i += 1


if __name__ == "__main__":
    import json, argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("index", help="Link to index")
    parser.add_argument("out", help="Output file, probably should end with .json")
    args = parser.parse_args()
    data = load_index_data(args.index)
    print("DONE LOADING INDEX DATA...")
    load_districts_data(data)
    print("DONE LOADING DISTRICTS")
    with open(args.out, "w+") as target:
        json.dump(data, target)
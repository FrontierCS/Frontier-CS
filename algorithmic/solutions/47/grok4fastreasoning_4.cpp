#include <bits/stdc++.h>
using namespace std;

struct FreeRect {
    int x, y, w, h;
};

struct PlaceInfo {
    int idx, px, py;
    bool valid() const { return idx >= 0; }
};

struct Item {
    string type;
    int w, h, v, limit;
    double density() const { return static_cast<double>(v) / (w * h); }
};

struct Placement {
    string type;
    int x, y, rot;
};

int posi;
void skip_ws(const string& s) {
    while (posi < s.size() && (s[posi] == ' ' || s[posi] == '\t' || s[posi] == '\n' || s[posi] == '\r')) posi++;
}

bool parse_string(const string& s, string& val) {
    skip_ws(s);
    if (posi >= s.size() || s[posi] != '"') return false;
    posi++;
    val.clear();
    while (posi < s.size() && s[posi] != '"') {
        val += s[posi++];
    }
    if (posi >= s.size() || s[posi] != '"') return false;
    posi++;
    return true;
}

bool parse_int(const string& s, int& val) {
    skip_ws(s);
    string numstr;
    if (posi < s.size() && s[posi] == '-') {
        numstr += '-';
        posi++;
    }
    bool has_digit = false;
    while (posi < s.size() && isdigit(s[posi])) {
        numstr += s[posi++];
        has_digit = true;
    }
    if (!has_digit) return false;
    try {
        val = stoi(numstr);
    } catch (...) {
        return false;
    }
    return true;
}

bool parse_bool(const string& s, bool& val) {
    skip_ws(s);
    if (posi + 4 <= static_cast<int>(s.size()) && s.substr(posi, 4) == "true") {
        posi += 4;
        val = true;
        return true;
    }
    if (posi + 5 <= static_cast<int>(s.size()) && s.substr(posi, 5) == "false") {
        posi += 5;
        val = false;
        return true;
    }
    return false;
}

int main() {
    istreambuf_iterator<char> begin_cin(cin), end_cin;
    string s(begin_cin, end_cin);

    posi = 0;
    skip_ws(s);
    if (s[posi++] != '{') {
        // error, output empty
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }

    // parse bin
    string key;
    skip_ws(s);
    if (!parse_string(s, key) || key != "bin") {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    skip_ws(s);
    if (s[posi++] != ':') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    skip_ws(s);
    if (s[posi++] != '{') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }

    // W
    skip_ws(s);
    if (!parse_string(s, key) || key != "W") {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    skip_ws(s);
    if (s[posi++] != ':') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    int W;
    if (!parse_int(s, W)) {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }

    // H
    skip_ws(s);
    if (s[posi++] != ',') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    skip_ws(s);
    if (!parse_string(s, key) || key != "H") {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    skip_ws(s);
    if (s[posi++] != ':') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    int H;
    if (!parse_int(s, H)) {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }

    // allow_rotate
    skip_ws(s);
    if (s[posi++] != ',') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    skip_ws(s);
    if (!parse_string(s, key) || key != "allow_rotate") {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    skip_ws(s);
    if (s[posi++] != ':') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    bool allow_rotate;
    if (!parse_bool(s, allow_rotate)) {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }

    skip_ws(s);
    if (s[posi++] != '}') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }

    // items
    skip_ws(s);
    if (s[posi++] != ',') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    skip_ws(s);
    if (!parse_string(s, key) || key != "items") {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    skip_ws(s);
    if (s[posi++] != ':') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }
    skip_ws(s);
    if (s[posi++] != '[') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }

    vector<Item> items_v;
    while (true) {
        skip_ws(s);
        if (s[posi] == ']') {
            posi++;
            break;
        }
        if (s[posi++] != '{') {
            break; // error
        }

        Item it;
        // type key
        skip_ws(s);
        string key_str;
        if (!parse_string(s, key_str) || key_str != "type") continue;
        skip_ws(s);
        if (s[posi++] != ':') continue;
        skip_ws(s);
        if (!parse_string(s, it.type)) continue;

        // w
        skip_ws(s);
        if (s[posi++] != ',') continue;
        skip_ws(s);
        if (!parse_string(s, key_str) || key_str != "w") continue;
        skip_ws(s);
        if (s[posi++] != ':') continue;
        if (!parse_int(s, it.w)) continue;

        // h
        skip_ws(s);
        if (s[posi++] != ',') continue;
        skip_ws(s);
        if (!parse_string(s, key_str) || key_str != "h") continue;
        skip_ws(s);
        if (s[posi++] != ':') continue;
        if (!parse_int(s, it.h)) continue;

        // v
        skip_ws(s);
        if (s[posi++] != ',') continue;
        skip_ws(s);
        if (!parse_string(s, key_str) || key_str != "v") continue;
        skip_ws(s);
        if (s[posi++] != ':') continue;
        if (!parse_int(s, it.v)) continue;

        // limit
        skip_ws(s);
        if (s[posi++] != ',') continue;
        skip_ws(s);
        if (!parse_string(s, key_str) || key_str != "limit") continue;
        skip_ws(s);
        if (s[posi++] != ':') continue;
        if (!parse_int(s, it.limit)) continue;

        skip_ws(s);
        if (s[posi++] != '}') continue;

        items_v.push_back(it);

        skip_ws(s);
        if (s[posi] == ']') {
            posi++;
            break;
        } else if (s[posi] == ',') {
            posi++;
        } else {
            break;
        }
    }

    skip_ws(s);
    if (posi >= static_cast<int>(s.size()) || s[posi] != '}') {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }

    // now process
    if (items_v.empty()) {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }

    // sort by density desc
    sort(items_v.begin(), items_v.end(), [](const Item& a, const Item& b) {
        return a.density() > b.density();
    });

    vector<FreeRect> free_space;
    free_space.push_back({0, 0, W, H});

    vector<Placement> placements;
    map<string, int> used_count;

    auto find_best_pos = [&](int pw, int ph) -> PlaceInfo {
        PlaceInfo res{-1, -1, -1};
        int best_y = INT_MAX;
        int best_x = INT_MAX;
        for (int i = 0; i < static_cast<int>(free_space.size()); ++i) {
            const auto& fr = free_space[i];
            if (fr.w >= pw && fr.h >= ph) {
                int cx = fr.x, cy = fr.y;
                bool better = false;
                if (cy < best_y) better = true;
                else if (cy == best_y && cx < best_x) better = true;
                else if (cy == best_y && cx == best_x && i < res.idx) better = true;
                if (better) {
                    best_y = cy;
                    best_x = cx;
                    res.idx = i;
                    res.px = cx;
                    res.py = cy;
                }
            }
        }
        return res;
    };

    for (const auto& it : items_v) {
        int placed = 0;
        while (placed < it.limit) {
            PlaceInfo p0 = find_best_pos(it.w, it.h);
            PlaceInfo p1 = PlaceInfo{-1, -1, -1};
            if (allow_rotate) {
                p1 = find_best_pos(it.h, it.w);
            }

            PlaceInfo chosen;
            int ch_rot = 0;
            if (!p0.valid() && !p1.valid()) {
                break;
            } else if (!p0.valid()) {
                chosen = p1;
                ch_rot = 1;
            } else if (!p1.valid()) {
                chosen = p0;
                ch_rot = 0;
            } else {
                bool use1 = false;
                if (p1.py < p0.py || (p1.py == p0.py && p1.px < p0.px) ||
                    (p1.py == p0.py && p1.px == p0.px && p1.idx < p0.idx)) {
                    use1 = true;
                }
                if (use1) {
                    chosen = p1;
                    ch_rot = 1;
                } else {
                    chosen = p0;
                    ch_rot = 0;
                }
            }

            // place
            int idx = chosen.idx;
            FreeRect fr = free_space[idx];
            if (free_space.size() > 1) {
                free_space[idx] = free_space.back();
            }
            free_space.pop_back();

            int place_w = (ch_rot == 0 ? it.w : it.h);
            int place_h = (ch_rot == 0 ? it.h : it.w);

            // add splits
            int rx = fr.x + place_w;
            int ry = fr.y + place_h;
            int rw = fr.w - place_w;
            int rh = fr.h - place_h;
            if (rw > 0) {
                free_space.push_back({rx, fr.y, rw, fr.h});
            }
            if (rh > 0) {
                free_space.push_back({fr.x, ry, place_w, rh});
            }

            placements.push_back({it.type, chosen.px, chosen.py, ch_rot});
            placed++;
        }
    }

    // output
    cout << "{" << endl << "  \"placements\": [" << endl;
    for (size_t i = 0; i < placements.size(); ++i) {
        const auto& p = placements[i];
        cout << "    {\"type\":\"" << p.type << "\", \"x\":" << p.x << ", \"y\":" << p.y << ", \"rot\":" << p.rot << "}";
        if (i + 1 < placements.size()) cout << ",";
        cout << endl;
    }
    cout << "  ]" << endl << "}" << endl;

    return 0;
}
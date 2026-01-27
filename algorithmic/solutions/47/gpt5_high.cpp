#include <bits/stdc++.h>
using namespace std;

struct Item {
    string type;
    int w, h;
    long long v;
    int limit;
};

struct Rect {
    int x, y, w, h;
};

struct Placement {
    string type;
    int x, y, rot;
};

struct JSONParser {
    string s;
    size_t i = 0;

    JSONParser(const string& str) : s(str), i(0) {}

    void skipWS() {
        while (i < s.size() && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) i++;
    }

    bool match(char c) {
        skipWS();
        if (i < s.size() && s[i] == c) {
            i++;
            return true;
        }
        return false;
    }

    void expect(char c) {
        skipWS();
        if (i >= s.size() || s[i] != c) {
            // Invalid JSON, but we will try to proceed
            // to avoid crashing. For contest inputs, format is valid.
        } else {
            i++;
        }
    }

    string parseString() {
        skipWS();
        string res;
        if (i >= s.size() || s[i] != '"') { return res; }
        i++; // skip opening quote
        while (i < s.size()) {
            char c = s[i++];
            if (c == '"') break;
            if (c == '\\') {
                if (i >= s.size()) break;
                char e = s[i++];
                switch (e) {
                    case '"': res.push_back('"'); break;
                    case '\\': res.push_back('\\'); break;
                    case '/': res.push_back('/'); break;
                    case 'b': res.push_back('\b'); break;
                    case 'f': res.push_back('\f'); break;
                    case 'n': res.push_back('\n'); break;
                    case 'r': res.push_back('\r'); break;
                    case 't': res.push_back('\t'); break;
                    case 'u':
                        // Skip \uXXXX (we'll ignore exact decoding and just skip 4 hex digits)
                        for (int k=0; k<4 && i < s.size(); ++k) {
                            char h = s[i];
                            if (!isxdigit((unsigned char)h)) break;
                            i++;
                        }
                        // We won't add any char for \u escapes; not expected in inputs.
                        break;
                    default:
                        res.push_back(e);
                        break;
                }
            } else {
                res.push_back(c);
            }
        }
        return res;
    }

    long long parseInt64() {
        skipWS();
        bool neg = false;
        if (i < s.size() && (s[i] == '-' || s[i] == '+')) {
            neg = (s[i] == '-');
            i++;
        }
        long long val = 0;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            val = val * 10 + (s[i] - '0');
            i++;
        }
        return neg ? -val : val;
    }

    bool parseBool() {
        skipWS();
        if (i + 3 < s.size() && s.compare(i, 4, "true") == 0) {
            i += 4;
            return true;
        }
        if (i + 4 < s.size() && s.compare(i, 5, "false") == 0) {
            i += 5;
            return false;
        }
        return false;
    }

    void skipValue() {
        skipWS();
        if (i >= s.size()) return;
        if (s[i] == '{') {
            int depth = 0;
            do {
                if (s[i] == '{') depth++;
                else if (s[i] == '}') depth--;
                i++;
            } while (i < s.size() && depth > 0);
        } else if (s[i] == '[') {
            int depth = 0;
            do {
                if (s[i] == '[') depth++;
                else if (s[i] == ']') depth--;
                i++;
            } while (i < s.size() && depth > 0);
        } else if (s[i] == '"') {
            parseString();
        } else if (s[i] == 't' || s[i] == 'f') {
            parseBool();
        } else if (s[i] == 'n') {
            // null
            if (i + 3 < s.size() && s.compare(i, 4, "null") == 0) i += 4;
            else i++;
        } else {
            // number
            if (s[i] == '-' || s[i] == '+') i++;
            while (i < s.size() && (isdigit((unsigned char)s[i]) || s[i]=='.' || s[i]=='e' || s[i]=='E' || s[i]=='+' || s[i]=='-')) i++;
        }
    }

    void parseBin(int &W, int &H, bool &allow_rotate) {
        expect('{');
        while (true) {
            skipWS();
            if (match('}')) break;
            string key = parseString();
            expect(':');
            if (key == "W") {
                W = (int)parseInt64();
            } else if (key == "H") {
                H = (int)parseInt64();
            } else if (key == "allow_rotate") {
                allow_rotate = parseBool();
            } else {
                skipValue();
            }
            skipWS();
            match(',');
        }
    }

    void parseItems(vector<Item> &items) {
        expect('[');
        skipWS();
        while (!match(']')) {
            expect('{');
            Item it;
            it.w = it.h = 0;
            it.v = 0;
            it.limit = 0;
            it.type.clear();
            while (true) {
                skipWS();
                if (match('}')) break;
                string key = parseString();
                expect(':');
                if (key == "type") {
                    it.type = parseString();
                } else if (key == "w") {
                    it.w = (int)parseInt64();
                } else if (key == "h") {
                    it.h = (int)parseInt64();
                } else if (key == "v") {
                    it.v = parseInt64();
                } else if (key == "limit") {
                    it.limit = (int)parseInt64();
                } else {
                    skipValue();
                }
                skipWS();
                match(',');
            }
            items.push_back(it);
            skipWS();
            match(',');
            skipWS();
        }
    }

    void parseRoot(int &W, int &H, bool &allow_rotate, vector<Item> &items) {
        expect('{');
        while (true) {
            skipWS();
            if (match('}')) break;
            string key = parseString();
            expect(':');
            if (key == "bin") {
                parseBin(W, H, allow_rotate);
            } else if (key == "items") {
                parseItems(items);
            } else {
                skipValue();
            }
            skipWS();
            match(',');
        }
    }
};

static inline string escapeJSONString(const string& s) {
    string out;
    out.reserve(s.size() + 10);
    for (char c : s) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if ((unsigned char)c < 0x20) {
                    char buf[7];
                    snprintf(buf, sizeof(buf), "\\u%04x", c & 0xFF);
                    out += buf;
                } else {
                    out.push_back(c);
                }
        }
    }
    return out;
}

struct Candidate {
    int fi;      // free rect index
    int ti;      // item index
    int rot;     // 0/1
    int x, y;    // placement coords
    double density;
    long long areaWaste;
    int shortFit;
    int longFit;
    long long value;
    int w, h;
    bool valid = false;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read all input
    string input, line;
    {
        std::ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    int W = 0, H = 0;
    bool allow_rotate = false;
    vector<Item> items;

    JSONParser parser(input);
    parser.parseRoot(W, H, allow_rotate, items);

    // Remove items with zero limit or zero size
    vector<Item> filtered;
    for (auto &it : items) {
        if (it.limit <= 0) continue;
        if (it.w <= 0 || it.h <= 0) continue;
        if (it.w > W || it.h > H) {
            // Keep; maybe rotation allows it to fit
            if (!allow_rotate || (it.h > W || it.w > H)) {
                // Neither orientation fits; skip
                continue;
            }
        }
        filtered.push_back(it);
    }
    items.swap(filtered);

    int M = (int)items.size();
    vector<int> rem(M);
    for (int i = 0; i < M; ++i) rem[i] = items[i].limit;

    vector<Rect> freeRects;
    freeRects.push_back({0, 0, W, H});
    vector<Placement> placements;
    placements.reserve(10000);

    auto better = [](const Candidate &a, const Candidate &b) -> bool {
        if (!b.valid) return a.valid;
        if (!a.valid) return false;
        // Prefer higher density
        if (fabs(a.density - b.density) > 1e-12) return a.density > b.density;
        // Then less area waste
        if (a.areaWaste != b.areaWaste) return a.areaWaste < b.areaWaste;
        // Then better short side fit
        if (a.shortFit != b.shortFit) return a.shortFit < b.shortFit;
        // Then better long side fit
        if (a.longFit != b.longFit) return a.longSideFit < b.longSideFit;
        // Then higher absolute value
        if (a.value != b.value) return a.value > b.value;
        return false;
    };

    while (true) {
        Candidate best;
        best.valid = false;

        for (int fi = 0; fi < (int)freeRects.size(); ++fi) {
            const Rect &fr = freeRects[fi];
            if (fr.w <= 0 || fr.h <= 0) continue;

            long long frArea = 1LL * fr.w * fr.h;

            for (int ti = 0; ti < M; ++ti) {
                if (rem[ti] <= 0) continue;
                const Item &it = items[ti];
                for (int rot = 0; rot <= (allow_rotate ? 1 : 0); ++rot) {
                    int iw = (rot ? it.h : it.w);
                    int ih = (rot ? it.w : it.h);
                    if (iw <= 0 || ih <= 0) continue;
                    if (iw > fr.w || ih > fr.h) continue;

                    long long iarea = 1LL * iw * ih;
                    long long waste = frArea - iarea;
                    int ssf = min(fr.w - iw, fr.h - ih);
                    int lsf = max(fr.w - iw, fr.h - ih);

                    Candidate cand;
                    cand.fi = fi;
                    cand.ti = ti;
                    cand.rot = rot;
                    cand.x = fr.x;
                    cand.y = fr.y;
                    cand.density = (double)it.v / (double)iarea;
                    cand.areaWaste = waste;
                    cand.shortFit = ssf;
                    cand.longFit = lsf;
                    cand.value = it.v;
                    cand.w = iw;
                    cand.h = ih;
                    cand.valid = true;

                    if (better(cand, best)) {
                        best = cand;
                    }
                }
            }
        }

        if (!best.valid) break;

        // Place the best candidate
        const Rect fr = freeRects[best.fi];
        int x = best.x, y = best.y;
        int iw = best.w, ih = best.h;

        placements.push_back({items[best.ti].type, x, y, best.rot});
        rem[best.ti]--;

        // Split the free rectangle using a guillotine split
        int remW = fr.w - iw;
        int remH = fr.h - ih;

        bool splitVertical = (remW > remH); // heuristic
        // Remove the used free rect
        // Replace with children (if any)
        if (splitVertical) {
            // Right child: full height
            // Top child: width iw
            if (remW > 0) {
                Rect right = {fr.x + iw, fr.y, remW, fr.h};
                freeRects[best.fi] = right;
                if (remH > 0) {
                    Rect top = {fr.x, fr.y + ih, iw, remH};
                    freeRects.push_back(top);
                }
            } else {
                if (remH > 0) {
                    Rect top = {fr.x, fr.y + ih, iw, remH};
                    freeRects[best.fi] = top;
                } else {
                    // No child
                    freeRects.erase(freeRects.begin() + best.fi);
                }
            }
        } else {
            // Top child: full width
            // Right child: height ih
            if (remH > 0) {
                Rect top = {fr.x, fr.y + ih, fr.w, remH};
                freeRects[best.fi] = top;
                if (remW > 0) {
                    Rect right = {fr.x + iw, fr.y, remW, ih};
                    freeRects.push_back(right);
                }
            } else {
                if (remW > 0) {
                    Rect right = {fr.x + iw, fr.y, remW, ih};
                    freeRects[best.fi] = right;
                } else {
                    freeRects.erase(freeRects.begin() + best.fi);
                }
            }
        }
    }

    // Output JSON
    cout << "{\n\"placements\": [";
    for (size_t i = 0; i < placements.size(); ++i) {
        const auto &p = placements[i];
        if (i) cout << ",";
        cout << "\n{\"type\":\"" << escapeJSONString(p.type) << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << "\n]}\n";

    return 0;
}
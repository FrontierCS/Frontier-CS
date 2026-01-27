#include <bits/stdc++.h>
using namespace std;

struct JsonVal {
    enum Type {NIL, OBJ, ARR, STR, NUM, BOOL} type = NIL;
    unordered_map<string, JsonVal> obj;
    vector<JsonVal> arr;
    string s;
    long long num = 0;
    bool b = false;
};

struct Parser {
    string s;
    size_t i = 0;

    Parser(const string& in): s(in), i(0) {}

    void skip_ws() {
        while (i < s.size() && (s[i]==' ' || s[i]=='\n' || s[i]=='\t' || s[i]=='\r')) i++;
    }

    bool match(char c) {
        skip_ws();
        if (i < s.size() && s[i] == c) { i++; return true; }
        return false;
    }

    char peek() {
        skip_ws();
        return (i < s.size()) ? s[i] : '\0';
    }

    char get() {
        if (i < s.size()) return s[i++];
        return '\0';
    }

    void expect(char c) {
        skip_ws();
        if (i >= s.size() || s[i] != c) throw runtime_error("JSON parse error: expected char");
        i++;
    }

    string parse_string() {
        skip_ws();
        if (i >= s.size() || s[i] != '"') throw runtime_error("JSON parse error: expected string");
        i++;
        string out;
        while (i < s.size()) {
            char c = s[i++];
            if (c == '"') break;
            if (c == '\\') {
                if (i >= s.size()) break;
                char e = s[i++];
                switch (e) {
                    case '"': out.push_back('"'); break;
                    case '\\': out.push_back('\\'); break;
                    case '/': out.push_back('/'); break;
                    case 'b': out.push_back('\b'); break;
                    case 'f': out.push_back('\f'); break;
                    case 'n': out.push_back('\n'); break;
                    case 'r': out.push_back('\r'); break;
                    case 't': out.push_back('\t'); break;
                    case 'u': {
                        // minimal unicode handling: skip 4 hex digits, ignore and put '?'
                        for (int k=0;k<4;k++) if (i < s.size()) i++;
                        out.push_back('?');
                        break;
                    }
                    default: out.push_back(e); break;
                }
            } else {
                out.push_back(c);
            }
        }
        return out;
    }

    long long parse_number() {
        skip_ws();
        size_t start = i;
        if (i < s.size() && (s[i] == '-' || s[i] == '+')) i++;
        while (i < s.size() && isdigit((unsigned char)s[i])) i++;
        // we will ignore fractional/exponent parts (inputs are ints)
        string numstr = s.substr(start, i - start);
        if (numstr.empty() || numstr == "+" || numstr == "-") throw runtime_error("JSON parse error: bad number");
        long long v = 0;
        try {
            v = stoll(numstr);
        } catch (...) {
            throw runtime_error("JSON parse error: number out of range");
        }
        return v;
    }

    JsonVal parse_value() {
        skip_ws();
        if (i >= s.size()) throw runtime_error("JSON parse error: unexpected end");
        char c = s[i];
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '"') {
            JsonVal v; v.type = JsonVal::STR; v.s = parse_string(); return v;
        }
        if (c == 't') {
            // true
            if (s.compare(i, 4, "true") == 0) {
                i += 4; JsonVal v; v.type = JsonVal::BOOL; v.b = true; return v;
            } else throw runtime_error("JSON parse error: expected true");
        }
        if (c == 'f') {
            if (s.compare(i, 5, "false") == 0) {
                i += 5; JsonVal v; v.type = JsonVal::BOOL; v.b = false; return v;
            } else throw runtime_error("JSON parse error: expected false");
        }
        if (c == 'n') {
            if (s.compare(i, 4, "null") == 0) {
                i += 4; JsonVal v; v.type = JsonVal::NIL; return v;
            } else throw runtime_error("JSON parse error: expected null");
        }
        if (c == '-' || c == '+' || isdigit((unsigned char)c)) {
            JsonVal v; v.type = JsonVal::NUM; v.num = parse_number(); return v;
        }
        throw runtime_error("JSON parse error: unknown value");
    }

    JsonVal parse_object() {
        JsonVal v; v.type = JsonVal::OBJ;
        expect('{');
        skip_ws();
        if (match('}')) return v;
        while (true) {
            skip_ws();
            string key = parse_string();
            skip_ws();
            expect(':');
            JsonVal val = parse_value();
            v.obj.emplace(std::move(key), std::move(val));
            skip_ws();
            if (match('}')) break;
            expect(',');
        }
        return v;
    }

    JsonVal parse_array() {
        JsonVal v; v.type = JsonVal::ARR;
        expect('[');
        skip_ws();
        if (match(']')) return v;
        while (true) {
            JsonVal e = parse_value();
            v.arr.emplace_back(std::move(e));
            skip_ws();
            if (match(']')) break;
            expect(',');
        }
        return v;
    }
};

string json_escape(const string& in) {
    string out;
    out.reserve(in.size()+8);
    for (char c: in) {
        switch (c) {
            case '\"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if ((unsigned char)c < 0x20) {
                    char buf[7];
                    snprintf(buf, sizeof(buf), "\\u%04x", (int)(unsigned char)c);
                    out += buf;
                } else {
                    out.push_back(c);
                }
        }
    }
    return out;
}

struct ItemType {
    string type;
    int w, h;
    long long v;
    int limit;
};

struct Orientation {
    int type_idx;
    int w, h;
    int rot; // 0 or 1
    long long v;
    double density;
    int area;
};

struct Rect {
    int x, y, w, h;
};

struct Candidate {
    bool found = false;
    int fr_idx = -1;
    int type_idx = -1;
    int rot = 0;
    int w = 0, h = 0;
    long long v = 0;
    double density = 0.0;
    long long waste = 0;
    int x = 0, y = 0;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire stdin
    string input, line;
    {
        std::ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    int W=0, H=0;
    bool allow_rotate = false;
    vector<ItemType> items;

    try {
        Parser p(input);
        JsonVal root = p.parse_value();
        if (root.type != JsonVal::OBJ) throw runtime_error("Root not object");
        if (!root.obj.count("bin") || !root.obj.count("items")) throw runtime_error("Missing keys");
        JsonVal bin = root.obj["bin"];
        JsonVal its = root.obj["items"];
        if (bin.type != JsonVal::OBJ) throw runtime_error("bin not object");
        if (!bin.obj.count("W") || !bin.obj.count("H") || !bin.obj.count("allow_rotate")) throw runtime_error("bin keys missing");
        if (bin.obj["W"].type != JsonVal::NUM || bin.obj["H"].type != JsonVal::NUM) throw runtime_error("W/H not number");
        if (bin.obj["allow_rotate"].type != JsonVal::BOOL) throw runtime_error("allow_rotate not bool");
        W = (int)bin.obj["W"].num;
        H = (int)bin.obj["H"].num;
        allow_rotate = bin.obj["allow_rotate"].b;

        if (its.type != JsonVal::ARR) throw runtime_error("items not array");
        for (auto &e: its.arr) {
            if (e.type != JsonVal::OBJ) throw runtime_error("item not object");
            auto &o = e.obj;
            if (!o.count("type") || !o.count("w") || !o.count("h") || !o.count("v") || !o.count("limit"))
                throw runtime_error("item keys missing");
            if (o["type"].type != JsonVal::STR) throw runtime_error("type not string");
            if (o["w"].type != JsonVal::NUM || o["h"].type != JsonVal::NUM || o["v"].type != JsonVal::NUM || o["limit"].type != JsonVal::NUM)
                throw runtime_error("w/h/v/limit not numbers");
            ItemType it;
            it.type = o["type"].s;
            it.w = (int)o["w"].num;
            it.h = (int)o["h"].num;
            it.v = (long long)o["v"].num;
            it.limit = (int)o["limit"].num;
            items.push_back(it);
        }
    } catch (...) {
        // On parse failure, output empty placements
        cout << "{\"placements\":[]}\n";
        return 0;
    }

    int M = (int)items.size();
    vector<int> remaining(M);
    for (int i=0;i<M;i++) remaining[i] = max(0, items[i].limit);

    // Build orientations
    vector<Orientation> orients;
    orients.reserve(M * 2);
    for (int i=0;i<M;i++) {
        Orientation o1;
        o1.type_idx = i;
        o1.w = items[i].w;
        o1.h = items[i].h;
        o1.rot = 0;
        o1.v = items[i].v;
        o1.area = o1.w * o1.h;
        o1.density = (o1.area > 0) ? (double)o1.v / (double)o1.area : 0.0;
        orients.push_back(o1);
        if (allow_rotate && items[i].w != items[i].h) {
            Orientation o2;
            o2.type_idx = i;
            o2.w = items[i].h;
            o2.h = items[i].w;
            o2.rot = 1;
            o2.v = items[i].v;
            o2.area = o2.w * o2.h;
            o2.density = (o2.area > 0) ? (double)o2.v / (double)o2.area : 0.0;
            orients.push_back(o2);
        }
    }

    // Free rectangles: start with whole bin
    vector<Rect> freeRects;
    freeRects.push_back({0,0,W,H});

    struct Placement { string type; int x,y,rot; };
    vector<Placement> placements;
    placements.reserve(4096);

    const int MAX_PLACEMENTS = 6000;

    auto fits = [](const Rect& r, const Orientation& o)->bool{
        return o.w <= r.w && o.h <= r.h;
    };

    while (true) {
        if ((int)placements.size() >= MAX_PLACEMENTS) break;

        Candidate best;
        best.found = false;

        for (int ri = 0; ri < (int)freeRects.size(); ri++) {
            const Rect& R = freeRects[ri];
            if (R.w <= 0 || R.h <= 0) continue;
            for (const auto& o: orients) {
                if (remaining[o.type_idx] <= 0) continue;
                if (!fits(R, o)) continue;

                long long waste = 1LL * R.w * R.h - 1LL * o.w * o.h;
                // Ranking: primary density, secondary profit, tertiary lower waste, then lower y, lower x
                if (!best.found) {
                    best.found = true;
                    best.fr_idx = ri;
                    best.type_idx = o.type_idx;
                    best.rot = o.rot;
                    best.w = o.w; best.h = o.h;
                    best.v = o.v;
                    best.density = o.density;
                    best.waste = waste;
                    best.x = R.x; best.y = R.y;
                } else {
                    bool better = false;
                    if (o.density > best.density + 1e-12) better = true;
                    else if (fabs(o.density - best.density) <= 1e-12) {
                        if (o.v > best.v) better = true;
                        else if (o.v == best.v) {
                            if (waste < best.waste) better = true;
                            else if (waste == best.waste) {
                                if (R.y < best.y) better = true;
                                else if (R.y == best.y) {
                                    if (R.x < best.x) better = true;
                                }
                            }
                        }
                    }
                    if (better) {
                        best.fr_idx = ri;
                        best.type_idx = o.type_idx;
                        best.rot = o.rot;
                        best.w = o.w; best.h = o.h;
                        best.v = o.v;
                        best.density = o.density;
                        best.waste = waste;
                        best.x = R.x; best.y = R.y;
                    }
                }
            }
        }

        if (!best.found) break;

        // Place it
        const Rect R = freeRects[best.fr_idx];
        Placement pl;
        pl.type = items[best.type_idx].type;
        pl.x = R.x;
        pl.y = R.y;
        pl.rot = best.rot;
        placements.push_back(pl);
        remaining[best.type_idx]--;

        // Split the free rectangle into two using guillotine split
        Rect r1, r2;
        int dw = R.w - best.w;
        int dh = R.h - best.h;
        vector<Rect> newRects;

        if (dw > dh) {
            // vertical split: right full height, top above placed width
            if (dw > 0) {
                r1 = {R.x + best.w, R.y, dw, R.h};
                if (r1.w > 0 && r1.h > 0) newRects.push_back(r1);
            }
            if (dh > 0) {
                r2 = {R.x, R.y + best.h, best.w, dh};
                if (r2.w > 0 && r2.h > 0) newRects.push_back(r2);
            }
        } else {
            // horizontal split: top full width, right below with placed height
            if (dh > 0) {
                r1 = {R.x, R.y + best.h, R.w, dh};
                if (r1.w > 0 && r1.h > 0) newRects.push_back(r1);
            }
            if (dw > 0) {
                r2 = {R.x + best.w, R.y, dw, best.h};
                if (r2.w > 0 && r2.h > 0) newRects.push_back(r2);
            }
        }

        // Replace R with newRects
        // Remove R by swapping with back
        freeRects[best.fr_idx] = freeRects.back();
        freeRects.pop_back();
        // Insert newRects
        for (auto &nr : newRects) freeRects.push_back(nr);
    }

    // Output JSON
    cout << "{\"placements\":[";
    for (size_t i=0;i<placements.size();i++) {
        auto &p = placements[i];
        if (i) cout << ",";
        cout << "{\"type\":\"" << json_escape(p.type) << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << "]}\n";
    return 0;
}
#include <bits/stdc++.h>
using namespace std;

// Minimal JSON parser supporting objects, arrays, strings, integers, booleans and null.

struct JValue {
    enum Type {NUL, BOOL, NUM, STR, ARR, OBJ} type = NUL;
    bool b = false;
    long long num = 0;
    string s;
    vector<JValue> a;
    map<string, JValue> o;
};

struct JSONParser {
    const string *p;
    size_t i = 0, n = 0;

    JSONParser(const string &s) { p = &s; n = s.size(); i = 0; }

    void skip_ws() {
        while (i < n && ( (*p)[i] == ' ' || (*p)[i] == '\n' || (*p)[i] == '\r' || (*p)[i] == '\t' )) i++;
    }

    bool match(char c) {
        skip_ws();
        if (i < n && (*p)[i] == c) { i++; return true; }
        return false;
    }

    bool expect(char c) {
        skip_ws();
        if (i < n && (*p)[i] == c) { i++; return true; }
        return false;
    }

    int hexval(char c) {
        if ('0' <= c && c <= '9') return c - '0';
        if ('a' <= c && c <= 'f') return 10 + c - 'a';
        if ('A' <= c && c <= 'F') return 10 + c - 'A';
        return -1;
    }

    string parse_string_raw() {
        string out;
        if (!expect('"')) return out;
        while (i < n) {
            char c = (*p)[i++];
            if (c == '"') break;
            if (c == '\\') {
                if (i >= n) break;
                char esc = (*p)[i++];
                switch (esc) {
                    case '"': out.push_back('"'); break;
                    case '\\': out.push_back('\\'); break;
                    case '/': out.push_back('/'); break;
                    case 'b': out.push_back('\b'); break;
                    case 'f': out.push_back('\f'); break;
                    case 'n': out.push_back('\n'); break;
                    case 'r': out.push_back('\r'); break;
                    case 't': out.push_back('\t'); break;
                    case 'u': {
                        if (i + 4 > n) break;
                        int cp = 0;
                        for (int k = 0; k < 4; ++k) {
                            int hv = hexval((*p)[i++]);
                            if (hv < 0) { cp = 0; break; }
                            cp = (cp << 4) | hv;
                        }
                        // Encode to UTF-8
                        if (cp <= 0x7F) out.push_back(char(cp));
                        else if (cp <= 0x7FF) {
                            out.push_back(char(0xC0 | ((cp >> 6) & 0x1F)));
                            out.push_back(char(0x80 | (cp & 0x3F)));
                        } else {
                            out.push_back(char(0xE0 | ((cp >> 12) & 0x0F)));
                            out.push_back(char(0x80 | ((cp >> 6) & 0x3F)));
                            out.push_back(char(0x80 | (cp & 0x3F)));
                        }
                        break;
                    }
                    default:
                        out.push_back(esc);
                        break;
                }
            } else {
                out.push_back(c);
            }
        }
        return out;
    }

    JValue parse_string() {
        JValue v;
        v.type = JValue::STR;
        v.s = parse_string_raw();
        return v;
    }

    JValue parse_number() {
        JValue v; v.type = JValue::NUM; v.num = 0;
        skip_ws();
        bool neg = false;
        if (i < n && (*p)[i] == '-') { neg = true; i++; }
        long long val = 0;
        bool hasDigits = false;
        while (i < n && isdigit((*p)[i])) {
            hasDigits = true;
            int d = (*p)[i++] - '0';
            val = val * 10 + d;
        }
        // Skip optional fractional/exponent parts if present (input shouldn't have them)
        if (i < n && (*p)[i] == '.') {
            i++;
            while (i < n && isdigit((*p)[i])) i++;
        }
        if (i < n && ((*p)[i] == 'e' || (*p)[i] == 'E')) {
            i++;
            if (i < n && ((*p)[i] == '+' || (*p)[i] == '-')) i++;
            while (i < n && isdigit((*p)[i])) i++;
        }
        if (!hasDigits) { v.num = 0; }
        else v.num = neg ? -val : val;
        return v;
    }

    JValue parse_true() {
        JValue v; v.type = JValue::BOOL; v.b = true;
        // expecting "true"
        i += 4; // assume valid input
        return v;
    }

    JValue parse_false() {
        JValue v; v.type = JValue::BOOL; v.b = false;
        // expecting "false"
        i += 5; // assume valid input
        return v;
    }

    JValue parse_null() {
        JValue v; v.type = JValue::NUL;
        i += 4; // "null"
        return v;
    }

    JValue parse_array() {
        JValue v; v.type = JValue::ARR;
        expect('[');
        skip_ws();
        if (match(']')) return v;
        while (true) {
            JValue elem = parse_value();
            v.a.push_back(move(elem));
            skip_ws();
            if (match(']')) break;
            expect(',');
        }
        return v;
    }

    JValue parse_object() {
        JValue v; v.type = JValue::OBJ;
        expect('{');
        skip_ws();
        if (match('}')) return v;
        while (true) {
            JValue key = parse_string();
            skip_ws();
            expect(':');
            JValue val = parse_value();
            v.o.emplace(key.s, move(val));
            skip_ws();
            if (match('}')) break;
            expect(',');
        }
        return v;
    }

    JValue parse_value() {
        skip_ws();
        if (i >= n) { JValue v; return v; }
        char c = (*p)[i];
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '"') return parse_string();
        if (c == '-' || isdigit(c)) return parse_number();
        if (c == 't') return parse_true();
        if (c == 'f') return parse_false();
        if (c == 'n') return parse_null();
        // Fallback
        JValue v; return v;
    }
};

static string json_escape(const string &s) {
    string out;
    out.push_back('"');
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
                    snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out.push_back(c);
                }
        }
    }
    out.push_back('"');
    return out;
}

// Packing

struct ItemType {
    string id;
    int w, h;
    long long v;
    int limit;
};

struct Ori {
    int typeIndex;
    int rot; // 0 or 1
    int w, h;
    long long v;
    double density;
};

struct Node { int x, y; };

struct Position {
    bool valid = false;
    int index = -1;
    int x = 0, y = 0;
};

struct Placement {
    string type;
    int x, y, rot;
};

struct SkylinePacker {
    int W, H;
    vector<Node> skyline;

    SkylinePacker(int W_, int H_) : W(W_), H(H_) {
        skyline.clear();
        skyline.push_back({0, 0});
        skyline.push_back({W, 0});
    }

    bool rectangleFits(int index, int w, int h, int &y_out) {
        int x = skyline[index].x;
        if (x + w > W) return false;
        int widthLeft = w;
        int j = index;
        int y = 0;
        while (widthLeft > 0) {
            if (j >= (int)skyline.size() - 1) return false;
            y = max(y, skyline[j].y);
            if (y + h > H) return false;
            int segWidth = skyline[j+1].x - skyline[j].x;
            widthLeft -= segWidth;
            j++;
        }
        y_out = y;
        return true;
    }

    Position findPositionBottomLeft(int w, int h) {
        Position best;
        int bestY = INT_MAX;
        int bestX = INT_MAX;
        int bestIndex = -1;

        for (int i = 0; i < (int)skyline.size(); ++i) {
            int y;
            if (rectangleFits(i, w, h, y)) {
                int x = skyline[i].x;
                if (y < bestY || (y == bestY && x < bestX)) {
                    bestY = y;
                    bestX = x;
                    bestIndex = i;
                }
            }
        }
        if (bestIndex != -1) {
            best.valid = true;
            best.index = bestIndex;
            best.x = bestX;
            best.y = bestY;
        }
        return best;
    }

    void mergeSkylines() {
        for (int i = 0; i < (int)skyline.size() - 1; ) {
            if (skyline[i].y == skyline[i+1].y) {
                skyline.erase(skyline.begin() + i + 1);
            } else {
                ++i;
            }
        }
    }

    void addSkylineLevel(int index, int x, int y, int w, int h) {
        Node newNode = {x, y + h};
        skyline.insert(skyline.begin() + index, newNode);
        int i = index + 1;
        while (i < (int)skyline.size() && skyline[i].x < x + w) {
            skyline.erase(skyline.begin() + i);
        }
        if (i >= (int)skyline.size() || skyline[i].x > x + w) {
            Node node = {x + w, y};
            skyline.insert(skyline.begin() + i, node);
        }
        mergeSkylines();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input, line;
    {
        ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    JSONParser parser(input);
    JValue root = parser.parse_value();

    // Extract data
    JValue bin = root.o["bin"];
    int W = (int)bin.o["W"].num;
    int H = (int)bin.o["H"].num;
    bool allow_rotate = bin.o["allow_rotate"].b;

    vector<ItemType> types;
    JValue items = root.o["items"];
    for (auto &it : items.a) {
        ItemType t;
        const auto &o = it.o;
        t.id = o.at("type").s;
        t.w = (int)o.at("w").num;
        t.h = (int)o.at("h").num;
        t.v = o.at("v").num;
        t.limit = (int)o.at("limit").num;
        // Cap sizes to bin (though input ensures w<=W and h<=H)
        t.w = min(t.w, W);
        t.h = min(t.h, H);
        types.push_back(t);
    }

    // Build orientations
    vector<Ori> oris;
    for (int i = 0; i < (int)types.size(); ++i) {
        const auto &t = types[i];
        // normal
        if (t.w <= W && t.h <= H) {
            Ori o;
            o.typeIndex = i;
            o.rot = 0;
            o.w = t.w;
            o.h = t.h;
            o.v = t.v;
            o.density = (double)t.v / (double)((long long)o.w * (long long)o.h);
            oris.push_back(o);
        }
        // rotated
        if (allow_rotate) {
            if (!(t.w == t.h)) {
                if (t.h <= W && t.w <= H) {
                    Ori o;
                    o.typeIndex = i;
                    o.rot = 1;
                    o.w = t.h;
                    o.h = t.w;
                    o.v = t.v;
                    o.density = (double)t.v / (double)((long long)o.w * (long long)o.h);
                    oris.push_back(o);
                }
            }
        }
    }

    // Sort orientations by density descending to try better choices when ties
    sort(oris.begin(), oris.end(), [](const Ori &a, const Ori &b){
        if (a.density != b.density) return a.density > b.density;
        if (a.v != b.v) return a.v > b.v;
        if (a.h != b.h) return a.h < b.h; // prefer shorter height in ties
        return a.w < b.w;
    });

    SkylinePacker packer(W, H);
    vector<int> used(types.size(), 0);
    vector<Placement> placements;

    // Packing loop
    while (true) {
        bool foundAny = false;
        int best_type = -1, best_rot = 0, best_x = 0, best_y = 0, best_w = 0, best_h = 0, best_index = -1;
        int bestY = INT_MAX, bestX = INT_MAX;
        double bestDensity = -1.0;
        long long bestV = -1;

        for (const auto &o : oris) {
            if (used[o.typeIndex] >= types[o.typeIndex].limit) continue;
            // quick skip if cannot possibly fit at all
            if (o.w > W || o.h > H) continue;
            Position pos = packer.findPositionBottomLeft(o.w, o.h);
            if (!pos.valid) continue;

            // Evaluate candidate: bottom-left priority
            bool better = false;
            if (pos.y < bestY) better = true;
            else if (pos.y == bestY) {
                if (pos.x < bestX) better = true;
                else if (pos.x == bestX) {
                    // tie-breakers: higher density, then higher profit
                    if (o.density > bestDensity) better = true;
                    else if (o.density == bestDensity && o.v > bestV) better = true;
                }
            }

            if (better) {
                foundAny = true;
                best_type = o.typeIndex;
                best_rot = o.rot;
                best_x = pos.x;
                best_y = pos.y;
                best_w = o.w;
                best_h = o.h;
                best_index = pos.index;
                bestY = pos.y;
                bestX = pos.x;
                bestDensity = o.density;
                bestV = o.v;
            }
        }

        if (!foundAny) break;

        packer.addSkylineLevel(best_index, best_x, best_y, best_w, best_h);
        used[best_type]++;

        Placement pl;
        pl.type = types[best_type].id;
        pl.x = best_x;
        pl.y = best_y;
        pl.rot = best_rot ? 1 : 0;
        placements.push_back(move(pl));
    }

    // Output JSON
    cout << "{\n  \"placements\": [";
    for (size_t i = 0; i < placements.size(); ++i) {
        const auto &p = placements[i];
        if (i) cout << ",";
        cout << "\n    {\"type\": " << json_escape(p.type)
             << ", \"x\": " << p.x
             << ", \"y\": " << p.y
             << ", \"rot\": " << p.rot
             << "}";
    }
    cout << "\n  ]\n}\n";

    return 0;
}
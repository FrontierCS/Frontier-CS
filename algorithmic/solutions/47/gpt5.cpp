#include <bits/stdc++.h>
using namespace std;

// Minimal JSON parser supporting objects, arrays, strings, integers, booleans, null.

struct JsonValue {
    enum Type {NUL, BOOL, NUMBER, STRING, OBJECT, ARRAY} type = NUL;
    bool b = false;
    long long num = 0;
    string str;
    unordered_map<string, JsonValue> obj;
    vector<JsonValue> arr;
};

struct JsonParser {
    const string &s;
    size_t pos = 0;
    JsonParser(const string &s_) : s(s_) {}
    void skip_ws() {
        while (pos < s.size() && (s[pos] == ' ' || s[pos] == '\n' || s[pos] == '\r' || s[pos] == '\t')) pos++;
    }
    bool match(const string &kw) {
        skip_ws();
        if (s.compare(pos, kw.size(), kw) == 0) { pos += kw.size(); return true; }
        return false;
    }
    JsonValue parse() {
        return parse_value();
    }
    JsonValue parse_value() {
        skip_ws();
        if (pos >= s.size()) return JsonValue();
        char c = s[pos];
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '"') return parse_string();
        if (c == 't' || c == 'f') return parse_bool();
        if (c == 'n') return parse_null();
        if (c == '-' || (c >= '0' && c <= '9')) return parse_number();
        // Fallback
        return JsonValue();
    }
    JsonValue parse_null() {
        JsonValue v;
        if (match("null")) { v.type = JsonValue::NUL; }
        return v;
    }
    JsonValue parse_bool() {
        JsonValue v;
        if (match("true")) { v.type = JsonValue::BOOL; v.b = true; }
        else if (match("false")) { v.type = JsonValue::BOOL; v.b = false; }
        return v;
    }
    JsonValue parse_number() {
        skip_ws();
        bool neg = false;
        if (pos < s.size() && s[pos] == '-') { neg = true; pos++; }
        long long val = 0;
        while (pos < s.size() && isdigit((unsigned char)s[pos])) {
            int d = s[pos] - '0';
            val = val * 10 + d;
            pos++;
        }
        // Ignore fractional/exponent parts if any (not expected)
        JsonValue v;
        v.type = JsonValue::NUMBER;
        v.num = neg ? -val : val;
        return v;
    }
    JsonValue parse_string() {
        JsonValue v;
        v.type = JsonValue::STRING;
        if (pos >= s.size() || s[pos] != '"') return v;
        pos++;
        string out;
        while (pos < s.size()) {
            char c = s[pos++];
            if (c == '"') break;
            if (c == '\\') {
                if (pos >= s.size()) break;
                char e = s[pos++];
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
                        // Read 4 hex digits; convert to UTF-16 code unit; we will just skip and put '?'
                        int cnt = 0;
                        while (cnt < 4 && pos < s.size() && isxdigit((unsigned char)s[pos])) { pos++; cnt++; }
                        out.push_back('?');
                        break;
                    }
                    default: out.push_back(e); break;
                }
            } else {
                out.push_back(c);
            }
        }
        v.str = std::move(out);
        return v;
    }
    JsonValue parse_object() {
        JsonValue v; v.type = JsonValue::OBJECT;
        if (pos >= s.size() || s[pos] != '{') return v;
        pos++;
        skip_ws();
        if (pos < s.size() && s[pos] == '}') { pos++; return v; }
        while (pos < s.size()) {
            skip_ws();
            if (pos >= s.size() || s[pos] != '"') { break; }
            JsonValue key = parse_string();
            skip_ws();
            if (pos < s.size() && s[pos] == ':') pos++;
            JsonValue val = parse_value();
            v.obj[std::move(key.str)] = std::move(val);
            skip_ws();
            if (pos < s.size() && s[pos] == ',') { pos++; continue; }
            if (pos < s.size() && s[pos] == '}') { pos++; break; }
        }
        return v;
    }
    JsonValue parse_array() {
        JsonValue v; v.type = JsonValue::ARRAY;
        if (pos >= s.size() || s[pos] != '[') return v;
        pos++;
        skip_ws();
        if (pos < s.size() && s[pos] == ']') { pos++; return v; }
        while (pos < s.size()) {
            JsonValue el = parse_value();
            v.arr.push_back(std::move(el));
            skip_ws();
            if (pos < s.size() && s[pos] == ',') { pos++; continue; }
            if (pos < s.size() && s[pos] == ']') { pos++; break; }
        }
        return v;
    }
};

struct ItemType {
    string type;
    int w, h;
    long long v;
    int limit;
};

struct Variant {
    int typeIndex;
    int rot; // 0 or 1
    int w, h;
    long long v;
    double density;
};

struct Node {
    int x;
    int y;
};

struct Placement {
    string type;
    int x, y;
    int rot;
};

struct SkylinePacker {
    int W, H;
    bool allowRotate;
    vector<ItemType> items;
    vector<int> remain;
    vector<Node> nodes; // skyline nodes with sentinel at x=W
    vector<Variant> variants;
    vector<Placement> placements;

    SkylinePacker(int W_, int H_, bool allowRotate_, const vector<ItemType>& items_)
        : W(W_), H(H_), allowRotate(allowRotate_), items(items_) {
        remain.resize(items.size());
        for (size_t i = 0; i < items.size(); ++i) remain[i] = items[i].limit;
        nodes.clear();
        nodes.push_back({0, 0});
        nodes.push_back({W, 0}); // sentinel
        buildVariants();
    }

    void buildVariants() {
        variants.clear();
        variants.reserve(items.size() * 2);
        for (int i = 0; i < (int)items.size(); ++i) {
            const auto &it = items[i];
            {
                Variant v;
                v.typeIndex = i;
                v.rot = 0;
                v.w = it.w;
                v.h = it.h;
                v.v = it.v;
                v.density = (double)it.v / (double)(max(1, it.w * it.h));
                variants.push_back(v);
            }
            if (allowRotate) {
                if (it.w != it.h) {
                    Variant v;
                    v.typeIndex = i;
                    v.rot = 1;
                    v.w = it.h;
                    v.h = it.w;
                    v.v = it.v;
                    v.density = (double)it.v / (double)(max(1, it.w * it.h)); // same area
                    variants.push_back(v);
                }
            }
        }
    }

    // Finds minimal y level greater than prevY among nodes (excluding last sentinel)
    int nextYLevelGreaterThan(int prevY) {
        int best = INT_MAX;
        for (size_t i = 0; i + 1 < nodes.size(); ++i) {
            int yy = nodes[i].y;
            if (yy > prevY && yy < best) best = yy;
        }
        return best;
    }

    bool fitAtIndex(int idx, int w, int h, int &yFit, int &endYRight) {
        int xStart = nodes[idx].x;
        if (xStart + w > W) return false;
        int xEnd = xStart + w;
        int j = idx;
        int y = 0;
        while (nodes[j].x < xEnd) {
            y = max(y, nodes[j].y);
            if (y + h > H) return false;
            ++j;
        }
        // j is first index with nodes[j].x >= xEnd
        if (nodes[j].x == xEnd) endYRight = nodes[j].y;
        else endYRight = nodes[j - 1].y;
        yFit = y;
        return true;
    }

    void addSkylineLevel(int idx, int w, int h, int yFit, int endYRight) {
        int xStart = nodes[idx].x;
        int xEnd = xStart + w;

        nodes[idx].y = yFit + h;
        int start = idx + 1;
        int end = start;
        while (end < (int)nodes.size() && nodes[end].x <= xEnd) ++end;
        nodes.erase(nodes.begin() + start, nodes.begin() + end);
        nodes.insert(nodes.begin() + start, Node{xEnd, endYRight});

        // Merge with left neighbor if same height
        if (idx > 0 && nodes[idx - 1].y == nodes[idx].y) {
            nodes.erase(nodes.begin() + idx);
            --start;
            --idx;
        }
        // Merge with right neighbor if same height
        int right = idx + 1;
        if (right < (int)nodes.size() && nodes[right].y == nodes[idx].y) {
            nodes.erase(nodes.begin() + right);
        }
    }

    void pack() {
        // Greedy packing by scanning low skyline levels first
        while (true) {
            bool placed = false;

            int prevY = -1;
            while (true) {
                int yLevel = nextYLevelGreaterThan(prevY);
                if (yLevel == INT_MAX) break;

                // Gather indices having this yLevel
                vector<int> indices;
                for (int i = 0; i + 1 < (int)nodes.size(); ++i) {
                    if (nodes[i].y == yLevel) indices.push_back(i);
                }

                struct Candidate {
                    bool ok = false;
                    int idx = -1;
                    int x = 0, y = 0;
                    int w = 0, h = 0;
                    int endY = 0;
                    int typeIndex = -1;
                    int rot = 0;
                    long long v = 0;
                    double density = 0.0;
                } best;

                for (int idx : indices) {
                    for (const auto &var : variants) {
                        if (remain[var.typeIndex] <= 0) continue;
                        // skip rot variants if rotation isn't allowed (we constructed only allowed ones)
                        if (nodes[idx].x + var.w > W) continue;
                        int yFit, endY;
                        if (!fitAtIndex(idx, var.w, var.h, yFit, endY)) continue;

                        // Candidate scoring: lowest y first, then higher density, then higher profit, then leftmost x
                        if (!best.ok ||
                            yFit < best.y ||
                            (yFit == best.y && (var.density > best.density + 1e-12)) ||
                            (yFit == best.y && fabs(var.density - best.density) <= 1e-12 && var.v > best.v) ||
                            (yFit == best.y && fabs(var.density - best.density) <= 1e-12 && var.v == best.v && nodes[idx].x < best.x)
                        ) {
                            best.ok = true;
                            best.idx = idx;
                            best.x = nodes[idx].x;
                            best.y = yFit;
                            best.w = var.w;
                            best.h = var.h;
                            best.endY = endY;
                            best.typeIndex = var.typeIndex;
                            best.rot = var.rot;
                            best.v = var.v;
                            best.density = var.density;
                        }
                    }
                }

                if (best.ok) {
                    // Place the rectangle
                    addSkylineLevel(best.idx, best.w, best.h, best.y, best.endY);
                    remain[best.typeIndex]--;
                    Placement p;
                    p.type = items[best.typeIndex].type;
                    p.x = best.x;
                    p.y = best.y;
                    p.rot = (allowRotate ? best.rot : 0);
                    placements.push_back(std::move(p));
                    placed = true;
                    break;
                } else {
                    prevY = yLevel;
                }
            }

            if (!placed) break;
        }
    }
};

static string escape_json_string(const string &s) {
    string out;
    out.reserve(s.size() + 8);
    for (char c : s) {
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
                    // control char -> \u00XX
                    static const char *hex = "0123456789abcdef";
                    out += "\\u00";
                    out += hex[(c >> 4) & 0xF];
                    out += hex[c & 0xF];
                } else {
                    out += c;
                }
        }
    }
    return out;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    JsonParser parser(input);
    JsonValue root = parser.parse();

    // Extract bin and items
    int W = 0, H = 0;
    bool allow_rotate = false;
    vector<ItemType> items;

    if (root.type == JsonValue::OBJECT) {
        auto itb = root.obj.find("bin");
        auto iti = root.obj.find("items");
        if (itb != root.obj.end() && iti != root.obj.end()) {
            const JsonValue &bin = itb->second;
            if (bin.type == JsonValue::OBJECT) {
                auto iw = bin.obj.find("W");
                auto ih = bin.obj.find("H");
                auto ir = bin.obj.find("allow_rotate");
                if (iw != bin.obj.end() && ih != bin.obj.end() && ir != bin.obj.end()) {
                    if (iw->second.type == JsonValue::NUMBER) W = (int)iw->second.num;
                    if (ih->second.type == JsonValue::NUMBER) H = (int)ih->second.num;
                    if (ir->second.type == JsonValue::BOOL) allow_rotate = ir->second.b;
                }
            }
            const JsonValue &arr = iti->second;
            if (arr.type == JsonValue::ARRAY) {
                for (const auto &el : arr.arr) {
                    if (el.type != JsonValue::OBJECT) continue;
                    ItemType it;
                    auto jt = el.obj.find("type");
                    auto jw = el.obj.find("w");
                    auto jh = el.obj.find("h");
                    auto jv = el.obj.find("v");
                    auto jl = el.obj.find("limit");
                    if (jt != el.obj.end() && jt->second.type == JsonValue::STRING) it.type = jt->second.str;
                    if (jw != el.obj.end() && jw->second.type == JsonValue::NUMBER) it.w = (int)jw->second.num;
                    if (jh != el.obj.end() && jh->second.type == JsonValue::NUMBER) it.h = (int)jh->second.num;
                    if (jv != el.obj.end() && jv->second.type == JsonValue::NUMBER) it.v = jv->second.num;
                    if (jl != el.obj.end() && jl->second.type == JsonValue::NUMBER) it.limit = (int)jl->second.num;
                    items.push_back(it);
                }
            }
        }
    }

    // Basic validation fallback
    if (W <= 0 || H <= 0) {
        cout << "{\"placements\":[]}\n";
        return 0;
    }

    SkylinePacker packer(W, H, allow_rotate, items);
    packer.pack();

    // Output JSON
    cout << "{\"placements\":[";
    for (size_t i = 0; i < packer.placements.size(); ++i) {
        const auto &p = packer.placements[i];
        if (i) cout << ",";
        cout << "{\"type\":\"" << escape_json_string(p.type) << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << "]}\n";
    return 0;
}
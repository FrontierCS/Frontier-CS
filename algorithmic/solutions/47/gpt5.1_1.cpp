#include <bits/stdc++.h>
using namespace std;

// ---------------- JSON Parser ----------------

struct JSONValue {
    enum class Type { NUL, NUMBER, STRING, BOOL, OBJECT, ARRAY } type;
    long long num;
    bool boolean;
    string str;
    unordered_map<string, JSONValue> obj;
    vector<JSONValue> arr;

    JSONValue() : type(Type::NUL), num(0), boolean(false) {}
};

struct JSONParser {
    string s;
    size_t pos;

    JSONParser(const string &src) : s(src), pos(0) {
        // Skip BOM if present
        if (s.size() >= 3 &&
            (unsigned char)s[0] == 0xEF &&
            (unsigned char)s[1] == 0xBB &&
            (unsigned char)s[2] == 0xBF) {
            pos = 3;
        }
    }

    void skip_ws() {
        while (pos < s.size() && isspace((unsigned char)s[pos])) pos++;
    }

    JSONValue parse() {
        JSONValue v = parse_value();
        return v;
    }

    JSONValue parse_value() {
        skip_ws();
        if (pos >= s.size()) return JSONValue();
        char c = s[pos];
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '"') return parse_string_value();
        if (c == 't' || c == 'f') return parse_bool();
        if (c == 'n') return parse_null();
        return parse_number();
    }

    JSONValue parse_object() {
        JSONValue v;
        v.type = JSONValue::Type::OBJECT;
        if (s[pos] != '{') return v;
        pos++; // skip '{'
        skip_ws();
        if (pos < s.size() && s[pos] == '}') {
            pos++;
            return v;
        }
        while (pos < s.size()) {
            skip_ws();
            string key = parse_string();
            skip_ws();
            if (pos >= s.size() || s[pos] != ':') return v;
            pos++; // skip ':'
            JSONValue val = parse_value();
            v.obj.emplace(std::move(key), std::move(val));
            skip_ws();
            if (pos >= s.size()) return v;
            if (s[pos] == ',') {
                pos++;
                continue;
            } else if (s[pos] == '}') {
                pos++;
                break;
            } else {
                // invalid, but we'll just break
                break;
            }
        }
        return v;
    }

    JSONValue parse_array() {
        JSONValue v;
        v.type = JSONValue::Type::ARRAY;
        if (s[pos] != '[') return v;
        pos++; // skip '['
        skip_ws();
        if (pos < s.size() && s[pos] == ']') {
            pos++;
            return v;
        }
        while (pos < s.size()) {
            JSONValue elem = parse_value();
            v.arr.emplace_back(std::move(elem));
            skip_ws();
            if (pos >= s.size()) return v;
            if (s[pos] == ',') {
                pos++;
                continue;
            } else if (s[pos] == ']') {
                pos++;
                break;
            } else {
                // invalid
                break;
            }
        }
        return v;
    }

    string parse_string() {
        skip_ws();
        string out;
        if (pos >= s.size() || s[pos] != '"') return out;
        pos++; // skip opening quote
        while (pos < s.size()) {
            char c = s[pos++];
            if (c == '"') break;
            if (c == '\\') {
                if (pos >= s.size()) break;
                char esc = s[pos++];
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
                        int code = 0;
                        for (int i = 0; i < 4 && pos < s.size(); ++i) {
                            char h = s[pos++];
                            code <<= 4;
                            if (h >= '0' && h <= '9') code |= (h - '0');
                            else if (h >= 'a' && h <= 'f') code |= (h - 'a' + 10);
                            else if (h >= 'A' && h <= 'F') code |= (h - 'A' + 10);
                        }
                        if (code < 0x80) out.push_back((char)code);
                        else out.push_back('?');
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

    JSONValue parse_string_value() {
        JSONValue v;
        v.type = JSONValue::Type::STRING;
        v.str = parse_string();
        return v;
    }

    JSONValue parse_bool() {
        JSONValue v;
        v.type = JSONValue::Type::BOOL;
        if (s.compare(pos, 4, "true") == 0) {
            v.boolean = true;
            pos += 4;
        } else if (s.compare(pos, 5, "false") == 0) {
            v.boolean = false;
            pos += 5;
        }
        return v;
    }

    JSONValue parse_null() {
        JSONValue v;
        v.type = JSONValue::Type::NUL;
        if (s.compare(pos, 4, "null") == 0) {
            pos += 4;
        }
        return v;
    }

    JSONValue parse_number() {
        JSONValue v;
        v.type = JSONValue::Type::NUMBER;
        skip_ws();
        bool neg = false;
        if (pos < s.size() && s[pos] == '-') {
            neg = true;
            pos++;
        }
        long long x = 0;
        bool has_digits = false;
        while (pos < s.size() && isdigit((unsigned char)s[pos])) {
            has_digits = true;
            x = x * 10 + (s[pos] - '0');
            pos++;
        }
        if (!has_digits) {
            v.num = 0;
            return v;
        }
        // Skip fractional part if any (not expected)
        if (pos < s.size() && s[pos] == '.') {
            pos++;
            while (pos < s.size() && isdigit((unsigned char)s[pos])) pos++;
        }
        // Skip exponent if any
        if (pos < s.size() && (s[pos] == 'e' || s[pos] == 'E')) {
            pos++;
            if (pos < s.size() && (s[pos] == '+' || s[pos] == '-')) pos++;
            while (pos < s.size() && isdigit((unsigned char)s[pos])) pos++;
        }
        v.num = neg ? -x : x;
        return v;
    }
};

// ---------------- Problem Structures ----------------

struct ItemType {
    string id;
    int w, h;
    long long v;
    int limit;
};

struct OriItem {
    int type_index;
    int w, h;
    int rot; // 0 or 1
    long long v;
    long long area;
};

struct Shelf {
    int y;
    int h;
    int x;
};

struct Placement {
    int type_index;
    int x, y;
    int rot;
};

// ---------------- JSON String Output ----------------

void print_json_string(const string &s) {
    cout << '"';
    for (unsigned char uc : s) {
        char c = (char)uc;
        switch (c) {
            case '"':  cout << "\\\""; break;
            case '\\': cout << "\\\\"; break;
            case '\b': cout << "\\b";  break;
            case '\f': cout << "\\f";  break;
            case '\n': cout << "\\n";  break;
            case '\r': cout << "\\r";  break;
            case '\t': cout << "\\t";  break;
            default:
                if (uc < 0x20) {
                    static const char hex[] = "0123456789abcdef";
                    cout << "\\u00" << hex[(uc >> 4) & 0xF] << hex[uc & 0xF];
                } else {
                    cout << c;
                }
        }
    }
    cout << '"';
}

// ---------------- Main ----------------

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire input
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());

    if (input.empty()) {
        // Output empty placements if no input
        cout << "{\n  \"placements\": []\n}\n";
        return 0;
    }

    JSONParser parser(input);
    JSONValue root = parser.parse();
    if (root.type != JSONValue::Type::OBJECT) {
        cout << "{\n  \"placements\": []\n}\n";
        return 0;
    }

    auto &root_obj = root.obj;

    // Parse bin
    auto it_bin = root_obj.find("bin");
    auto it_items = root_obj.find("items");
    if (it_bin == root_obj.end() || it_items == root_obj.end()) {
        cout << "{\n  \"placements\": []\n}\n";
        return 0;
    }

    JSONValue &bin_val = it_bin->second;
    JSONValue &items_val = it_items->second;
    if (bin_val.type != JSONValue::Type::OBJECT || items_val.type != JSONValue::Type::ARRAY) {
        cout << "{\n  \"placements\": []\n}\n";
        return 0;
    }

    auto &bin_obj = bin_val.obj;

    int W = 0, H = 0;
    bool allow_rotate = false;

    auto itW = bin_obj.find("W");
    auto itH = bin_obj.find("H");
    auto itR = bin_obj.find("allow_rotate");
    if (itW != bin_obj.end() && itW->second.type == JSONValue::Type::NUMBER)
        W = (int)itW->second.num;
    if (itH != bin_obj.end() && itH->second.type == JSONValue::Type::NUMBER)
        H = (int)itH->second.num;
    if (itR != bin_obj.end() && itR->second.type == JSONValue::Type::BOOL)
        allow_rotate = itR->second.boolean;

    // Parse items
    vector<ItemType> items;
    for (const JSONValue &iv : items_val.arr) {
        if (iv.type != JSONValue::Type::OBJECT) continue;
        const auto &obj = iv.obj;
        ItemType it;
        auto t_it = obj.find("type");
        auto w_it = obj.find("w");
        auto h_it = obj.find("h");
        auto v_it = obj.find("v");
        auto l_it = obj.find("limit");
        if (t_it == obj.end() || w_it == obj.end() || h_it == obj.end() ||
            v_it == obj.end() || l_it == obj.end()) continue;
        if (t_it->second.type != JSONValue::Type::STRING) continue;
        if (w_it->second.type != JSONValue::Type::NUMBER) continue;
        if (h_it->second.type != JSONValue::Type::NUMBER) continue;
        if (v_it->second.type != JSONValue::Type::NUMBER) continue;
        if (l_it->second.type != JSONValue::Type::NUMBER) continue;
        it.id = t_it->second.str;
        it.w = (int)w_it->second.num;
        it.h = (int)h_it->second.num;
        it.v = v_it->second.num;
        it.limit = (int)l_it->second.num;
        if (it.limit < 0) it.limit = 0;
        items.push_back(it);
    }

    int M = (int)items.size();
    if (W <= 0 || H <= 0 || M == 0) {
        cout << "{\n  \"placements\": []\n}\n";
        return 0;
    }

    // Generate orientation variants
    vector<OriItem> oris;
    oris.reserve(M * 2);
    for (int i = 0; i < M; ++i) {
        const auto &it = items[i];
        if (it.v <= 0 || it.limit <= 0) continue;
        OriItem o0;
        o0.type_index = i;
        o0.w = it.w;
        o0.h = it.h;
        o0.rot = 0;
        o0.v = it.v;
        o0.area = (long long)o0.w * (long long)o0.h;
        if (o0.w <= W && o0.h <= H && o0.area > 0)
            oris.push_back(o0);
        if (allow_rotate && it.w != it.h) {
            OriItem o1;
            o1.type_index = i;
            o1.w = it.h;
            o1.h = it.w;
            o1.rot = 1;
            o1.v = it.v;
            o1.area = (long long)o1.w * (long long)o1.h;
            if (o1.w <= W && o1.h <= H && o1.area > 0)
                oris.push_back(o1);
        }
    }

    if (oris.empty()) {
        cout << "{\n  \"placements\": []\n}\n";
        return 0;
    }

    // Sort orientation variants by value density (v/area), descending
    sort(oris.begin(), oris.end(), [](const OriItem &a, const OriItem &b) {
        __int128 lhs = (__int128)a.v * b.area;
        __int128 rhs = (__int128)b.v * a.area;
        if (lhs != rhs) return lhs > rhs;
        if (a.area != b.area) return a.area > b.area;
        if (a.h != b.h) return a.h > b.h;
        if (a.w != b.w) return a.w > b.w;
        return a.type_index < b.type_index;
    });

    vector<int> used(M, 0);
    vector<Shelf> shelves;
    shelves.reserve(H / 5 + 5);
    int current_y = 0;

    vector<Placement> placements;
    placements.reserve(10000);

    auto tryPlace = [&](const OriItem &oi) -> bool {
        int w = oi.w;
        int h = oi.h;
        int t = oi.type_index;
        // Try existing shelves
        for (auto &shelf : shelves) {
            if (h <= shelf.h && shelf.x + w <= W) {
                Placement p;
                p.type_index = t;
                p.x = shelf.x;
                p.y = shelf.y;
                p.rot = allow_rotate ? oi.rot : 0; // enforce rot=0 if rotation not allowed
                placements.push_back(p);
                shelf.x += w;
                used[t]++;
                return true;
            }
        }
        // Try to create new shelf
        if (current_y + h > H) return false;
        Shelf s;
        s.y = current_y;
        s.h = h;
        s.x = 0;
        shelves.push_back(s);
        current_y += h;
        // Place in new shelf
        Shelf &ns = shelves.back();
        Placement p;
        p.type_index = t;
        p.x = ns.x;
        p.y = ns.y;
        p.rot = allow_rotate ? oi.rot : 0;
        placements.push_back(p);
        ns.x += w;
        used[t]++;
        return true;
    };

    // Greedy packing
    for (const auto &oi : oris) {
        int t = oi.type_index;
        int lim = items[t].limit;
        while (used[t] < lim) {
            if (!tryPlace(oi)) break;
        }
    }

    // Output JSON placements
    cout << "{\n  \"placements\": [";
    for (size_t i = 0; i < placements.size(); ++i) {
        const auto &p = placements[i];
        if (i > 0) cout << ",";
        cout << "\n    {\"type\":";
        print_json_string(items[p.type_index].id);
        cout << ",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << "\n  ]\n}\n";

    return 0;
}
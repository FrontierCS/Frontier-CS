#include <bits/stdc++.h>
using namespace std;

struct BinInfo {
    int W = 0, H = 0;
    bool allow_rotate = false;
};

struct ItemType {
    string type;
    int w = 0, h = 0;
    long long v = 0;
    int limit = 0;
};

struct Placement {
    string type;
    int x;
    int y;
    int rot;
};

struct Variant {
    int type_idx;
    int w, h;
    long long v;
    int rot; // 0 or 1
    double density;
};

struct Parser {
    string s;
    size_t i;

    Parser(const string& str) : s(str), i(0) {}

    void skip_ws() {
        while (i < s.size() && isspace((unsigned char)s[i])) ++i;
    }

    string parse_string() {
        skip_ws();
        string res;
        if (i >= s.size() || s[i] != '"') return res;
        ++i; // skip "
        while (i < s.size()) {
            char c = s[i++];
            if (c == '\\') {
                if (i >= s.size()) break;
                char esc = s[i++];
                switch (esc) {
                    case '"': res.push_back('"'); break;
                    case '\\': res.push_back('\\'); break;
                    case '/': res.push_back('/'); break;
                    case 'b': res.push_back('\b'); break;
                    case 'f': res.push_back('\f'); break;
                    case 'n': res.push_back('\n'); break;
                    case 'r': res.push_back('\r'); break;
                    case 't': res.push_back('\t'); break;
                    case 'u':
                        // Simple handling: skip next 4 hex digits (no proper unicode)
                        for (int k = 0; k < 4 && i < s.size(); ++k) ++i;
                        break;
                    default:
                        res.push_back(esc);
                        break;
                }
            } else if (c == '"') {
                break;
            } else {
                res.push_back(c);
            }
        }
        return res;
    }

    long long parse_int64() {
        skip_ws();
        long long sign = 1;
        if (i < s.size() && s[i] == '-') {
            sign = -1;
            ++i;
        }
        long long val = 0;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            val = val * 10 + (s[i] - '0');
            ++i;
        }
        return sign * val;
    }

    bool parse_bool() {
        skip_ws();
        if (i + 3 < s.size() && s.compare(i, 4, "true") == 0) {
            i += 4;
            return true;
        }
        if (i + 4 < s.size() && s.compare(i, 5, "false") == 0) {
            i += 5;
            return false;
        }
        // Fallback
        return false;
    }

    void skip_value() {
        skip_ws();
        if (i >= s.size()) return;
        char c = s[i];
        if (c == '"') {
            (void)parse_string();
        } else if (c == '{') {
            int depth = 0;
            do {
                if (s[i] == '{') ++depth;
                else if (s[i] == '}') --depth;
                ++i;
                if (i >= s.size()) break;
            } while (depth > 0);
        } else if (c == '[') {
            int depth = 0;
            do {
                if (s[i] == '[') ++depth;
                else if (s[i] == ']') --depth;
                ++i;
                if (i >= s.size()) break;
            } while (depth > 0);
        } else if (c == 't' || c == 'f') {
            (void)parse_bool();
        } else if (c == 'n') {
            // null
            if (i + 3 < s.size() && s.compare(i, 4, "null") == 0) i += 4;
            else ++i;
        } else if (c == '-' || isdigit((unsigned char)c)) {
            (void)parse_int64();
        } else {
            ++i;
        }
    }

    void expect_char(char ch) {
        skip_ws();
        if (i < s.size() && s[i] == ch) {
            ++i;
        } else {
            // malformed JSON; best-effort skip
            if (i < s.size()) ++i;
        }
    }

    void parse_bin(BinInfo &bin) {
        skip_ws();
        expect_char('{');
        while (true) {
            skip_ws();
            if (i >= s.size()) break;
            if (s[i] == '}') {
                ++i;
                break;
            }
            string key = parse_string();
            skip_ws();
            expect_char(':');
            if (key == "W") {
                bin.W = (int)parse_int64();
            } else if (key == "H") {
                bin.H = (int)parse_int64();
            } else if (key == "allow_rotate") {
                bin.allow_rotate = parse_bool();
            } else {
                skip_value();
            }
            skip_ws();
            if (i < s.size() && s[i] == ',') {
                ++i;
                continue;
            }
        }
    }

    ItemType parse_item() {
        ItemType it;
        skip_ws();
        expect_char('{');
        while (true) {
            skip_ws();
            if (i >= s.size()) break;
            if (s[i] == '}') {
                ++i;
                break;
            }
            string key = parse_string();
            skip_ws();
            expect_char(':');
            if (key == "type") {
                it.type = parse_string();
            } else if (key == "w") {
                it.w = (int)parse_int64();
            } else if (key == "h") {
                it.h = (int)parse_int64();
            } else if (key == "v") {
                it.v = parse_int64();
            } else if (key == "limit") {
                it.limit = (int)parse_int64();
            } else {
                skip_value();
            }
            skip_ws();
            if (i < s.size() && s[i] == ',') {
                ++i;
                continue;
            }
        }
        return it;
    }

    void parse_items(vector<ItemType> &items) {
        skip_ws();
        expect_char('[');
        while (true) {
            skip_ws();
            if (i >= s.size()) break;
            if (s[i] == ']') {
                ++i;
                break;
            }
            ItemType it = parse_item();
            items.push_back(it);
            skip_ws();
            if (i < s.size() && s[i] == ',') {
                ++i;
                continue;
            } else if (i < s.size() && s[i] == ']') {
                ++i;
                break;
            }
        }
    }

    void parse_root(BinInfo &bin, vector<ItemType> &items) {
        skip_ws();
        expect_char('{');
        while (true) {
            skip_ws();
            if (i >= s.size()) break;
            if (s[i] == '}') {
                ++i;
                break;
            }
            string key = parse_string();
            skip_ws();
            expect_char(':');
            if (key == "bin") {
                parse_bin(bin);
            } else if (key == "items") {
                parse_items(items);
            } else {
                skip_value();
            }
            skip_ws();
            if (i < s.size() && s[i] == ',') {
                ++i;
                continue;
            }
        }
    }
};

string escape_json_string(const string &s) {
    string out;
    out.reserve(s.size() + 8);
    for (unsigned char c : s) {
        switch (c) {
            case '\"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (c < 0x20) {
                    char buf[7];
                    snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out.push_back((char)c);
                }
        }
    }
    return out;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire stdin into string
    string input;
    {
        std::ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    BinInfo bin;
    vector<ItemType> items;
    {
        Parser parser(input);
        parser.parse_root(bin, items);
    }

    int M = (int)items.size();
    vector<Variant> variants;

    for (int i = 0; i < M; ++i) {
        // Orientation 0
        Variant v0;
        v0.type_idx = i;
        v0.w = items[i].w;
        v0.h = items[i].h;
        v0.v = items[i].v;
        v0.rot = 0;
        if (v0.w > 0 && v0.h > 0) {
            v0.density = (double)v0.v / (double)(v0.w * (double)v0.h);
            if (v0.w <= bin.W && v0.h <= bin.H)
                variants.push_back(v0);
        }
        // Orientation 1 (rotation) if allowed
        if (bin.allow_rotate) {
            Variant v1;
            v1.type_idx = i;
            v1.w = items[i].h;
            v1.h = items[i].w;
            v1.v = items[i].v;
            v1.rot = 1;
            if (v1.w > 0 && v1.h > 0) {
                v1.density = (double)v1.v / (double)(v1.w * (double)v1.h);
                if (v1.w <= bin.W && v1.h <= bin.H)
                    variants.push_back(v1);
            }
        }
    }

    // If no variants (shouldn't happen), output empty placements
    vector<Placement> placements;
    if (!variants.empty()) {
        sort(variants.begin(), variants.end(),
             [](const Variant &a, const Variant &b) {
                 if (a.density != b.density)
                     return a.density > b.density;
                 if (a.v != b.v)
                     return a.v > b.v;
                 int areaA = a.w * a.h;
                 int areaB = b.w * b.h;
                 return areaA < areaB;
             });

        vector<int> remaining(M);
        for (int i = 0; i < M; ++i) remaining[i] = items[i].limit;

        int currY = 0;
        const int binW = bin.W;
        const int binH = bin.H;

        while (true) {
            // Check if any variant can start a new shelf
            bool can_start_shelf = false;
            for (const auto &v : variants) {
                if (remaining[v.type_idx] <= 0) continue;
                if (v.h <= binH - currY && v.w <= binW) {
                    can_start_shelf = true;
                    break;
                }
            }
            if (!can_start_shelf) break;

            int shelfHeight = 0;
            int x = 0;

            while (true) {
                Variant const *best = nullptr;
                for (const auto &v : variants) {
                    if (remaining[v.type_idx] <= 0) continue;
                    if (v.w <= binW - x && v.h <= binH - currY) {
                        best = &v;
                        break; // first in density-sorted order
                    }
                }
                if (!best) break;

                Placement p;
                p.type = items[best->type_idx].type;
                p.x = x;
                p.y = currY;
                p.rot = best->rot;
                placements.push_back(p);

                remaining[best->type_idx]--;
                x += best->w;
                if (best->h > shelfHeight) shelfHeight = best->h;
                if (x >= binW) break;
            }

            if (shelfHeight <= 0) break;
            currY += shelfHeight;
            if (currY >= binH) break;
        }
    }

    // Output JSON
    cout << "{\"placements\":[";
    for (size_t i = 0; i < placements.size(); ++i) {
        if (i) cout << ",";
        const Placement &p = placements[i];
        cout << "{\"type\":\"" << escape_json_string(p.type)
             << "\",\"x\":" << p.x
             << ",\"y\":" << p.y
             << ",\"rot\":" << p.rot
             << "}";
    }
    cout << "]}\n";

    return 0;
}
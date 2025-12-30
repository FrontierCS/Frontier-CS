#include <bits/stdc++.h>
using namespace std;

string s;
size_t pos = 0;

int W = 0, H = 0;
bool allow_rotate = false;

struct Item {
    string type;
    int w, h;
    long long v;
    int limit;
};

vector<Item> items;

struct Placement {
    string type;
    int x, y;
    int rot;
};

inline void skip_ws() {
    while (pos < s.size() && isspace((unsigned char)s[pos])) pos++;
}

void expect(char c) {
    skip_ws();
    if (pos < s.size() && s[pos] == c) {
        ++pos;
    } else if (pos < s.size()) {
        ++pos; // simple recovery on unexpected char
    }
}

string parse_string() {
    skip_ws();
    string res;
    if (pos >= s.size() || s[pos] != '\"') {
        return res;
    }
    ++pos; // skip opening "
    while (pos < s.size()) {
        char c = s[pos++];
        if (c == '\\') {
            if (pos >= s.size()) break;
            char esc = s[pos++];
            switch (esc) {
                case '\"': res.push_back('\"'); break;
                case '\\': res.push_back('\\'); break;
                case '/':  res.push_back('/');  break;
                case 'b':  res.push_back('\b'); break;
                case 'f':  res.push_back('\f'); break;
                case 'n':  res.push_back('\n'); break;
                case 'r':  res.push_back('\r'); break;
                case 't':  res.push_back('\t'); break;
                case 'u': {
                    unsigned code = 0;
                    for (int i = 0; i < 4 && pos < s.size(); ++i) {
                        char h = s[pos++];
                        code <<= 4;
                        if (h >= '0' && h <= '9') code += h - '0';
                        else if (h >= 'a' && h <= 'f') code += 10 + h - 'a';
                        else if (h >= 'A' && h <= 'F') code += 10 + h - 'A';
                        else {}
                    }
                    if (code <= 0x7F) res.push_back((char)code);
                    // for simplicity, ignore non-ASCII codes
                    break;
                }
                default:
                    res.push_back(esc);
                    break;
            }
        } else if (c == '\"') {
            break;
        } else {
            res.push_back(c);
        }
    }
    return res;
}

long long parse_number() {
    skip_ws();
    int sign = 1;
    if (pos < s.size() && s[pos] == '-') {
        sign = -1;
        ++pos;
    }
    long long val = 0;
    while (pos < s.size() && isdigit((unsigned char)s[pos])) {
        val = val * 10 + (s[pos] - '0');
        ++pos;
    }
    return sign * val;
}

bool parse_bool() {
    skip_ws();
    if (pos + 4 <= s.size() && s.compare(pos, 4, "true") == 0) {
        pos += 4;
        return true;
    }
    if (pos + 5 <= s.size() && s.compare(pos, 5, "false") == 0) {
        pos += 5;
        return false;
    }
    if (pos < s.size()) ++pos;
    return false;
}

void parseBin() {
    skip_ws();
    expect('{');
    bool first = true;
    while (true) {
        skip_ws();
        if (pos >= s.size()) return;
        if (s[pos] == '}') {
            ++pos;
            break;
        }
        if (!first) {
            if (s[pos] == ',') {
                ++pos;
                skip_ws();
            }
        }
        first = false;
        string key = parse_string();
        skip_ws();
        expect(':');
        if (key == "W") {
            W = (int)parse_number();
        } else if (key == "H") {
            H = (int)parse_number();
        } else if (key == "allow_rotate") {
            allow_rotate = parse_bool();
        } else {
            // skip unknown value
            // very simple: try to skip one token
            skip_ws();
            if (pos < s.size() && s[pos] == '{') {
                int depth = 0;
                do {
                    if (s[pos] == '{') depth++;
                    else if (s[pos] == '}') depth--;
                    ++pos;
                } while (pos < s.size() && depth > 0);
            } else if (pos < s.size() && s[pos] == '[') {
                int depth = 0;
                do {
                    if (s[pos] == '[') depth++;
                    else if (s[pos] == ']') depth--;
                    ++pos;
                } while (pos < s.size() && depth > 0);
            } else if (pos < s.size() && s[pos] == '\"') {
                parse_string();
            } else {
                parse_number();
            }
        }
    }
}

void parseItems() {
    skip_ws();
    expect('[');
    bool firstItem = true;
    while (true) {
        skip_ws();
        if (pos >= s.size()) return;
        if (s[pos] == ']') {
            ++pos;
            break;
        }
        if (!firstItem) {
            if (s[pos] == ',') {
                ++pos;
                skip_ws();
            }
        }
        firstItem = false;

        skip_ws();
        expect('{');
        Item it;
        it.w = it.h = it.limit = 0;
        it.v = 0;
        it.type.clear();

        bool firstProp = true;
        while (true) {
            skip_ws();
            if (pos >= s.size()) return;
            if (s[pos] == '}') {
                ++pos;
                break;
            }
            if (!firstProp) {
                if (s[pos] == ',') {
                    ++pos;
                    skip_ws();
                }
            }
            firstProp = false;
            string key = parse_string();
            skip_ws();
            expect(':');
            if (key == "type") {
                it.type = parse_string();
            } else if (key == "w") {
                it.w = (int)parse_number();
            } else if (key == "h") {
                it.h = (int)parse_number();
            } else if (key == "v") {
                it.v = parse_number();
            } else if (key == "limit") {
                it.limit = (int)parse_number();
            } else {
                // skip unknown
                skip_ws();
                if (pos < s.size() && s[pos] == '{') {
                    int depth = 0;
                    do {
                        if (s[pos] == '{') depth++;
                        else if (s[pos] == '}') depth--;
                        ++pos;
                    } while (pos < s.size() && depth > 0);
                } else if (pos < s.size() && s[pos] == '[') {
                    int depth = 0;
                    do {
                        if (s[pos] == '[') depth++;
                        else if (s[pos] == ']') depth--;
                        ++pos;
                    } while (pos < s.size() && depth > 0);
                } else if (pos < s.size() && s[pos] == '\"') {
                    parse_string();
                } else {
                    parse_number();
                }
            }
        }
        items.push_back(it);
    }
}

void parseTop() {
    skip_ws();
    expect('{');
    bool first = true;
    while (true) {
        skip_ws();
        if (pos >= s.size()) return;
        if (s[pos] == '}') {
            ++pos;
            break;
        }
        if (!first) {
            if (s[pos] == ',') {
                ++pos;
                continue;
            }
        }
        first = false;
        string key = parse_string();
        skip_ws();
        expect(':');
        if (key == "bin") {
            parseBin();
        } else if (key == "items") {
            parseItems();
        } else {
            // skip unknown value
            skip_ws();
            if (pos < s.size() && s[pos] == '{') {
                int depth = 0;
                do {
                    if (s[pos] == '{') depth++;
                    else if (s[pos] == '}') depth--;
                    ++pos;
                } while (pos < s.size() && depth > 0);
            } else if (pos < s.size() && s[pos] == '[') {
                int depth = 0;
                do {
                    if (s[pos] == '[') depth++;
                    else if (s[pos] == ']') depth--;
                    ++pos;
                } while (pos < s.size() && depth > 0);
            } else if (pos < s.size() && s[pos] == '\"') {
                parse_string();
            } else {
                parse_number();
            }
        }
    }
}

string escape_json(const string &in) {
    string out;
    for (char c : in) {
        switch (c) {
            case '\"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b";  break;
            case '\f': out += "\\f";  break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if ((unsigned char)c < 0x20) {
                    char buf[7];
                    sprintf(buf, "\\u%04x", (unsigned char)c);
                    out += buf;
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

    // Read entire input
    s.assign((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    pos = 0;
    parseTop();

    vector<Placement> placements;

    if (W > 0 && H > 0 && !items.empty()) {
        // Simple shelf packing, no rotations used (rot = 0)
        sort(items.begin(), items.end(),
             [](const Item &a, const Item &b) { return a.h > b.h; });

        int m = (int)items.size();
        vector<int> remaining(m);
        for (int i = 0; i < m; ++i) remaining[i] = items[i].limit;

        int y = 0;
        while (y < H) {
            bool placed_shelf = false;
            for (int i = 0; i < m; ++i) {
                if (remaining[i] <= 0) continue;
                int w = items[i].w;
                int h = items[i].h;
                if (w <= 0 || h <= 0) continue;
                if (h > H - y) continue;
                if (w > W) continue;

                int max_per_row = W / w;
                if (max_per_row <= 0) continue;

                int can = min(remaining[i], max_per_row);
                if (can <= 0) continue;

                int x = 0;
                for (int k = 0; k < can; ++k) {
                    Placement p;
                    p.type = items[i].type;
                    p.x = x;
                    p.y = y;
                    p.rot = 0;
                    placements.push_back(p);
                    x += w;
                }
                remaining[i] -= can;
                y += h;
                placed_shelf = true;
                if (y >= H) break;
            }
            if (!placed_shelf) break;
        }
    }

    // Output JSON
    cout << "{\n  \"placements\": [";
    if (!placements.empty()) cout << "\n";
    for (size_t i = 0; i < placements.size(); ++i) {
        if (i > 0) cout << ",\n";
        const auto &p = placements[i];
        cout << "    {\"type\":\"" << escape_json(p.type)
             << "\",\"x\":" << p.x
             << ",\"y\":" << p.y
             << ",\"rot\":" << p.rot << "}";
    }
    if (!placements.empty()) cout << "\n";
    cout << "  ]\n}\n";

    return 0;
}
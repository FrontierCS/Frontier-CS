#include <bits/stdc++.h>
using namespace std;

struct JsonValue {
    enum Type { NUL, BOOL, NUMBER, STRING, ARRAY, OBJECT } type;
    bool b;
    long long num;
    string str;
    vector<JsonValue> arr;
    unordered_map<string, JsonValue> obj;
    JsonValue() : type(NUL), b(false), num(0) {}
};

struct Parser {
    string s;
    size_t i, n;
    Parser(const string &input) : s(input), i(0), n(input.size()) {
        // Skip UTF-8 BOM if present
        if (n >= 3 &&
            (unsigned char)s[0] == 0xEF &&
            (unsigned char)s[1] == 0xBB &&
            (unsigned char)s[2] == 0xBF) {
            i = 3;
        }
    }

    void skip_ws() {
        while (i < n && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t'))
            ++i;
    }

    JsonValue parseValue() {
        skip_ws();
        if (i >= n) return JsonValue();
        char c = s[i];
        if (c == '{') return parseObject();
        if (c == '[') return parseArray();
        if (c == '"') {
            JsonValue j;
            j.type = JsonValue::STRING;
            j.str = parseString();
            return j;
        }
        if (c == 't' || c == 'f') return parseBool();
        if (c == 'n') return parseNull();
        JsonValue j;
        j.type = JsonValue::NUMBER;
        j.num = parseNumber();
        return j;
    }

    JsonValue parseObject() {
        JsonValue j;
        j.type = JsonValue::OBJECT;
        if (i < n && s[i] == '{') ++i;
        skip_ws();
        if (i < n && s[i] == '}') {
            ++i;
            return j;
        }
        while (i < n) {
            skip_ws();
            string key = parseString();
            skip_ws();
            if (i < n && s[i] == ':') ++i;
            JsonValue val = parseValue();
            j.obj.emplace(move(key), move(val));
            skip_ws();
            if (i < n && s[i] == ',') {
                ++i;
                continue;
            } else if (i < n && s[i] == '}') {
                ++i;
                break;
            } else {
                break;
            }
        }
        return j;
    }

    JsonValue parseArray() {
        JsonValue j;
        j.type = JsonValue::ARRAY;
        if (i < n && s[i] == '[') ++i;
        skip_ws();
        if (i < n && s[i] == ']') {
            ++i;
            return j;
        }
        while (i < n) {
            JsonValue val = parseValue();
            j.arr.emplace_back(move(val));
            skip_ws();
            if (i < n && s[i] == ',') {
                ++i;
                continue;
            } else if (i < n && s[i] == ']') {
                ++i;
                break;
            } else {
                break;
            }
        }
        return j;
    }

    string parseString() {
        skip_ws();
        string res;
        if (i < n && s[i] == '"') ++i;
        while (i < n) {
            char c = s[i++];
            if (c == '"') break;
            if (c == '\\') {
                if (i >= n) break;
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
                    case 'u': {
                        if (i + 4 <= n) {
                            int code = 0;
                            for (int k = 0; k < 4; ++k) {
                                char hc = s[i++];
                                code <<= 4;
                                if (hc >= '0' && hc <= '9') code += hc - '0';
                                else if (hc >= 'a' && hc <= 'f') code += 10 + hc - 'a';
                                else if (hc >= 'A' && hc <= 'F') code += 10 + hc - 'A';
                            }
                            if (code <= 0x7F) {
                                res.push_back((char)code);
                            } else if (code <= 0x7FF) {
                                res.push_back((char)(0xC0 | (code >> 6)));
                                res.push_back((char)(0x80 | (code & 0x3F)));
                            } else {
                                res.push_back((char)(0xE0 | (code >> 12)));
                                res.push_back((char)(0x80 | ((code >> 6) & 0x3F)));
                                res.push_back((char)(0x80 | (code & 0x3F)));
                            }
                        }
                        break;
                    }
                    default:
                        res.push_back(esc);
                        break;
                }
            } else {
                res.push_back(c);
            }
        }
        return res;
    }

    long long parseNumber() {
        skip_ws();
        bool neg = false;
        if (i < n && s[i] == '-') {
            neg = true;
            ++i;
        }
        long long val = 0;
        if (i < n && s[i] == '0') {
            ++i;
        } else {
            while (i < n && isdigit((unsigned char)s[i])) {
                val = val * 10 + (s[i] - '0');
                ++i;
            }
        }
        if (i < n && s[i] == '.') {
            ++i;
            while (i < n && isdigit((unsigned char)s[i])) ++i;
        }
        if (i < n && (s[i] == 'e' || s[i] == 'E')) {
            ++i;
            if (i < n && (s[i] == '+' || s[i] == '-')) ++i;
            while (i < n && isdigit((unsigned char)s[i])) ++i;
        }
        return neg ? -val : val;
    }

    JsonValue parseBool() {
        JsonValue j;
        j.type = JsonValue::BOOL;
        if (s.compare(i, 4, "true") == 0) {
            j.b = true;
            i += 4;
        } else if (s.compare(i, 5, "false") == 0) {
            j.b = false;
            i += 5;
        }
        return j;
    }

    JsonValue parseNull() {
        JsonValue j;
        j.type = JsonValue::NUL;
        if (s.compare(i, 4, "null") == 0) {
            i += 4;
        }
        return j;
    }
};

string escapeJSONString(const string &s) {
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
                    snprintf(buf, sizeof(buf), "\\u%04X", c);
                    out += buf;
                } else {
                    out += (char)c;
                }
        }
    }
    return out;
}

struct Item {
    string id;
    int w, h;
    long long v;
    long long limit;
};

struct Placement {
    string type;
    int x, y;
    int rot;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    if (input.empty()) {
        cout << "{\"placements\":[]}\n";
        return 0;
    }

    Parser parser(input);
    JsonValue root = parser.parseValue();
    if (root.type != JsonValue::OBJECT) {
        cout << "{\"placements\":[]}\n";
        return 0;
    }

    auto itBin = root.obj.find("bin");
    auto itItems = root.obj.find("items");
    if (itBin == root.obj.end() || itItems == root.obj.end()) {
        cout << "{\"placements\":[]}\n";
        return 0;
    }

    JsonValue &binObj = itBin->second;
    JsonValue &itemsArr = itItems->second;
    if (binObj.type != JsonValue::OBJECT || itemsArr.type != JsonValue::ARRAY) {
        cout << "{\"placements\":[]}\n";
        return 0;
    }

    int W = 0, H = 0;
    bool allow_rotate = false;

    auto bw = binObj.obj.find("W");
    auto bh = binObj.obj.find("H");
    auto br = binObj.obj.find("allow_rotate");
    if (bw != binObj.obj.end() && bw->second.type == JsonValue::NUMBER)
        W = (int)bw->second.num;
    if (bh != binObj.obj.end() && bh->second.type == JsonValue::NUMBER)
        H = (int)bh->second.num;
    if (br != binObj.obj.end() && br->second.type == JsonValue::BOOL)
        allow_rotate = br->second.b;

    vector<Item> items;
    items.reserve(itemsArr.arr.size());
    for (auto &iv : itemsArr.arr) {
        if (iv.type != JsonValue::OBJECT) continue;
        Item it;
        auto ttype = iv.obj.find("type");
        auto tw = iv.obj.find("w");
        auto th = iv.obj.find("h");
        auto tv = iv.obj.find("v");
        auto tl = iv.obj.find("limit");
        if (ttype != iv.obj.end() && ttype->second.type == JsonValue::STRING)
            it.id = ttype->second.str;
        if (tw != iv.obj.end() && tw->second.type == JsonValue::NUMBER)
            it.w = (int)tw->second.num;
        else it.w = 0;
        if (th != iv.obj.end() && th->second.type == JsonValue::NUMBER)
            it.h = (int)th->second.num;
        else it.h = 0;
        if (tv != iv.obj.end() && tv->second.type == JsonValue::NUMBER)
            it.v = tv->second.num;
        else it.v = 0;
        if (tl != iv.obj.end() && tl->second.type == JsonValue::NUMBER)
            it.limit = tl->second.num;
        else it.limit = 0;
        items.push_back(it);
    }

    struct Candidate {
        int idx;
        int rot;
        long long profit;
        int w, h;
        long long useCount;
    };

    bool hasBest = false;
    Candidate best{};
    long long bestProfit = -1;

    for (int i = 0; i < (int)items.size(); ++i) {
        Item &it = items[i];
        if (it.limit <= 0 || it.w <= 0 || it.h <= 0 || it.v <= 0) continue;
        for (int rot = 0; rot < 2; ++rot) {
            if (rot == 1 && !allow_rotate) continue;
            int cw = rot ? it.h : it.w;
            int ch = rot ? it.w : it.h;
            if (cw <= 0 || ch <= 0) continue;
            if (cw > W || ch > H) continue;
            long long maxPerRow = W / cw;
            long long maxRows = H / ch;
            if (maxPerRow <= 0 || maxRows <= 0) continue;
            long long capacity = maxPerRow * maxRows;
            if (capacity <= 0) continue;
            long long canUse = min(capacity, it.limit);
            if (canUse <= 0) continue;
            long long totProfit = canUse * it.v;
            if (!hasBest || totProfit > bestProfit) {
                hasBest = true;
                bestProfit = totProfit;
                best.idx = i;
                best.rot = rot;
                best.profit = totProfit;
                best.w = cw;
                best.h = ch;
                best.useCount = canUse;
            }
        }
    }

    vector<Placement> placements;
    if (hasBest) {
        Item &it = items[best.idx];
        int cw = best.w;
        int ch = best.h;
        int numPerRow = (cw > 0) ? W / cw : 0;
        int numRows = (ch > 0) ? H / ch : 0;
        long long toPlace = best.useCount;
        placements.reserve((size_t)toPlace);
        long long placed = 0;
        for (int row = 0; row < numRows && placed < toPlace; ++row) {
            for (int col = 0; col < numPerRow && placed < toPlace; ++col) {
                Placement p;
                p.type = it.id;
                p.x = col * cw;
                p.y = row * ch;
                p.rot = allow_rotate ? best.rot : 0;
                placements.push_back(move(p));
                ++placed;
            }
        }
    }

    cout << "{\n  \"placements\": [";
    if (!placements.empty()) {
        cout << "\n";
        for (size_t i = 0; i < placements.size(); ++i) {
            const auto &p = placements[i];
            cout << "    {\"type\":\"" << escapeJSONString(p.type)
                 << "\",\"x\":" << p.x
                 << ",\"y\":" << p.y
                 << ",\"rot\":" << p.rot << "}";
            if (i + 1 < placements.size()) cout << ",";
            cout << "\n";
        }
        cout << "  ]\n";
    } else {
        cout << "]\n";
    }
    cout << "}\n";

    return 0;
}
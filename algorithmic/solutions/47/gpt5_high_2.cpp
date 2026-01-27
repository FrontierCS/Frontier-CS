#include <bits/stdc++.h>
using namespace std;

// Minimal JSON parser sufficient for this problem

struct JValue {
    enum Type {NUL, OBJ, ARR, STR, NUM, BOOL} type = NUL;
    unordered_map<string, JValue> obj;
    vector<JValue> arr;
    string str;
    long long num = 0;
    bool b = false;

    bool is_obj() const { return type == OBJ; }
    bool is_arr() const { return type == ARR; }
    bool is_str() const { return type == STR; }
    bool is_num() const { return type == NUM; }
    bool is_bool() const { return type == BOOL; }
};

struct JsonParser {
    string s;
    size_t i = 0;

    JsonParser(const string& src) : s(src), i(0) {}

    void skip_ws() {
        while (i < s.size() && (s[i] == ' ' || s[i] == '\n' || s[i] == '\t' || s[i] == '\r')) i++;
    }

    bool match(const string& t) {
        if (s.compare(i, t.size(), t) == 0) {
            i += t.size();
            return true;
        }
        return false;
    }

    char peek() { return i < s.size() ? s[i] : '\0'; }
    char get() { return i < s.size() ? s[i++] : '\0'; }

    static int hex_val(char c) {
        if ('0'<=c && c<='9') return c-'0';
        if ('a'<=c && c<='f') return 10 + (c-'a');
        if ('A'<=c && c<='F') return 10 + (c-'A');
        return -1;
    }

    void append_utf8(string& out, unsigned int cp) {
        if (cp <= 0x7F) {
            out.push_back((char)cp);
        } else if (cp <= 0x7FF) {
            out.push_back((char)(0xC0 | ((cp >> 6) & 0x1F)));
            out.push_back((char)(0x80 | (cp & 0x3F)));
        } else if (cp <= 0xFFFF) {
            out.push_back((char)(0xE0 | ((cp >> 12) & 0x0F)));
            out.push_back((char)(0x80 | ((cp >> 6) & 0x3F)));
            out.push_back((char)(0x80 | (cp & 0x3F)));
        } else {
            out.push_back((char)(0xF0 | ((cp >> 18) & 0x07)));
            out.push_back((char)(0x80 | ((cp >> 12) & 0x3F)));
            out.push_back((char)(0x80 | ((cp >> 6) & 0x3F)));
            out.push_back((char)(0x80 | (cp & 0x3F)));
        }
    }

    string parse_string() {
        string out;
        char quote = get(); // should be '"'
        (void)quote;
        while (i < s.size()) {
            char c = get();
            if (c == '"') break;
            if (c == '\\') {
                char e = get();
                if (e == '"' || e == '\\' || e == '/') out.push_back(e);
                else if (e == 'b') out.push_back('\b');
                else if (e == 'f') out.push_back('\f');
                else if (e == 'n') out.push_back('\n');
                else if (e == 'r') out.push_back('\r');
                else if (e == 't') out.push_back('\t');
                else if (e == 'u') {
                    // parse 4 hex digits
                    unsigned int cp = 0;
                    for (int k = 0; k < 4; ++k) {
                        if (i >= s.size()) break;
                        int hv = hex_val(get());
                        if (hv < 0) { hv = 0; }
                        cp = (cp << 4) | (unsigned)hv;
                    }
                    append_utf8(out, cp);
                } else {
                    out.push_back(e);
                }
            } else {
                out.push_back(c);
            }
        }
        return out;
    }

    long long parse_number() {
        size_t start = i;
        if (peek() == '-') get();
        while (isdigit(peek())) get();
        // ignore fractional/exponent for this problem; assume integers
        string numstr = s.substr(start, i - start);
        long long val = 0;
        try {
            size_t idx = 0;
            val = stoll(numstr, &idx, 10);
        } catch (...) {
            val = 0;
        }
        return val;
    }

    JValue parse_value() {
        skip_ws();
        char c = peek();
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '"') {
            JValue v;
            v.type = JValue::STR;
            v.str = parse_string();
            return v;
        }
        if (c == 't') {
            if (match("true")) {
                JValue v; v.type = JValue::BOOL; v.b = true; return v;
            }
        }
        if (c == 'f') {
            if (match("false")) {
                JValue v; v.type = JValue::BOOL; v.b = false; return v;
            }
        }
        if (c == 'n') {
            if (match("null")) {
                JValue v; v.type = JValue::NUL; return v;
            }
        }
        if (c == '-' || isdigit(c)) {
            JValue v; v.type = JValue::NUM; v.num = parse_number(); return v;
        }
        // Fallback
        JValue v; v.type = JValue::NUL; return v;
    }

    JValue parse_object() {
        JValue v; v.type = JValue::OBJ;
        get(); // '{'
        skip_ws();
        if (peek() == '}') { get(); return v; }
        while (i < s.size()) {
            skip_ws();
            string key = parse_string();
            skip_ws();
            if (get() != ':') { /* invalid */ }
            JValue val = parse_value();
            v.obj.emplace(key, std::move(val));
            skip_ws();
            char c = get();
            if (c == '}') break;
            if (c != ',') { /* invalid */ break; }
        }
        return v;
    }

    JValue parse_array() {
        JValue v; v.type = JValue::ARR;
        get(); // '['
        skip_ws();
        if (peek() == ']') { get(); return v; }
        while (i < s.size()) {
            JValue elem = parse_value();
            v.arr.push_back(std::move(elem));
            skip_ws();
            char c = get();
            if (c == ']') break;
            if (c != ',') { /* invalid */ break; }
        }
        return v;
    }
};

static string json_escape(const string& s) {
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
                    out += (char)c;
                }
        }
    }
    return out;
}

struct Item {
    string type;
    int w, h;
    long long v;
    int limit;
    double density;
    long long area;
    int id;
};

struct Rect {
    int x, y, w, h;
};

struct Placement {
    string type;
    int x, y;
    int rot;
};

struct FRComp {
    bool operator()(Rect const& a, Rect const& b) const {
        if (a.y != b.y) return a.y > b.y;     // smaller y first
        if (a.x != b.x) return a.x > b.x;     // smaller x first
        if (a.h != b.h) return a.h < b.h;     // larger height first
        return a.w < b.w;                     // larger width first
    }
};

struct Candidate {
    bool found = false;
    int itemIndex = -1;
    int rot = 0; // 0=no, 1=yes
    int pw = 0, ph = 0;
    double dens = -1e300;
    long long area = 0;
    long long profit = 0;
};

static Candidate choose_item_for_rect(const Rect& r, vector<Item>& items, bool allow_rotate) {
    Candidate best;
    double bestD = -1e300;
    long long bestArea = -1;
    for (int i = 0; i < (int)items.size(); ++i) {
        if (items[i].limit <= 0) continue;
        // rot=0
        {
            int ww = items[i].w, hh = items[i].h;
            if (ww <= r.w && hh <= r.h) {
                double d = items[i].density;
                long long a = 1LL * ww * hh;
                bool better = false;
                if (d > bestD + 1e-12) better = true;
                else if (fabs(d - bestD) <= 1e-12 && a > bestArea) better = true;
                if (better) {
                    best.found = true;
                    best.itemIndex = i;
                    best.rot = 0;
                    best.pw = ww; best.ph = hh;
                    best.dens = d;
                    best.area = a;
                    best.profit = items[i].v;
                    bestD = d; bestArea = a;
                }
            }
        }
        if (allow_rotate) {
            int ww = items[i].h, hh = items[i].w;
            if (ww <= r.w && hh <= r.h) {
                double d = items[i].density; // same density; profit/area unaffected by rotation
                long long a = 1LL * ww * hh;
                bool better = false;
                if (d > bestD + 1e-12) better = true;
                else if (fabs(d - bestD) <= 1e-12 && a > bestArea) better = true;
                if (better) {
                    best.found = true;
                    best.itemIndex = i;
                    best.rot = 1;
                    best.pw = ww; best.ph = hh;
                    best.dens = d;
                    best.area = a;
                    best.profit = items[i].v;
                    bestD = d; bestArea = a;
                }
            }
        }
    }
    return best;
}

static void pack(const int W, const int H, const bool allow_rotate,
                 vector<Item> items,
                 vector<Placement>& placements_out) {
    priority_queue<Rect, vector<Rect>, FRComp> pq;
    pq.push({0, 0, W, H});
    long long remaining = 0;
    for (auto& it : items) remaining += it.limit;

    while (!pq.empty() && remaining > 0) {
        Rect r = pq.top(); pq.pop();
        if (r.w <= 0 || r.h <= 0) continue;
        Candidate cand = choose_item_for_rect(r, items, allow_rotate);
        if (!cand.found) continue;

        // Place item
        placements_out.push_back({items[cand.itemIndex].type, r.x, r.y, cand.rot});
        items[cand.itemIndex].limit--;
        remaining--;

        // Split into right and top
        int right_w = r.w - cand.pw;
        int right_h = cand.ph;
        if (right_w > 0 && right_h > 0) {
            pq.push({r.x + cand.pw, r.y, right_w, right_h});
        }
        int top_w = r.w;
        int top_h = r.h - cand.ph;
        if (top_w > 0 && top_h > 0) {
            pq.push({r.x, r.y + cand.ph, top_w, top_h});
        }
    }
}

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

    JsonParser parser(input);
    JValue root = parser.parse_value();

    int W = 0, H = 0;
    bool allow_rotate = false;
    vector<Item> items;

    if (root.is_obj()) {
        auto it_bin = root.obj.find("bin");
        if (it_bin != root.obj.end() && it_bin->second.is_obj()) {
            JValue& bin = it_bin->second;
            if (bin.obj.find("W") != bin.obj.end() && bin.obj["W"].is_num()) W = (int)bin.obj["W"].num;
            if (bin.obj.find("H") != bin.obj.end() && bin.obj["H"].is_num()) H = (int)bin.obj["H"].num;
            if (bin.obj.find("allow_rotate") != bin.obj.end() && bin.obj["allow_rotate"].is_bool())
                allow_rotate = bin.obj["allow_rotate"].b;
        }
        auto it_items = root.obj.find("items");
        if (it_items != root.obj.end() && it_items->second.is_arr()) {
            for (auto& jitem : it_items->second.arr) {
                if (!jitem.is_obj()) continue;
                Item it;
                it.type = jitem.obj["type"].is_str() ? jitem.obj["type"].str : "";
                it.w = jitem.obj["w"].is_num() ? (int)jitem.obj["w"].num : 0;
                it.h = jitem.obj["h"].is_num() ? (int)jitem.obj["h"].num : 0;
                it.v = jitem.obj["v"].is_num() ? jitem.obj["v"].num : 0;
                it.limit = jitem.obj["limit"].is_num() ? (int)jitem.obj["limit"].num : 0;
                it.area = 1LL * it.w * it.h;
                if (it.area <= 0) it.area = 1;
                it.density = (double)it.v / (double)it.area;
                items.push_back(it);
            }
        }
    }

    // Simple heuristic: pack using guillotine-like splitting (bottom-left preference)
    vector<Placement> placements;
    pack(W, H, allow_rotate, items, placements);

    // Output JSON
    cout << "{";
    cout << "\"placements\":[";
    for (size_t i = 0; i < placements.size(); ++i) {
        const auto& p = placements[i];
        if (i) cout << ",";
        cout << "{\"type\":\"" << json_escape(p.type) << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << "]}";
    return 0;
}
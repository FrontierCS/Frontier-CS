#include <bits/stdc++.h>
using namespace std;

// Minimal JSON parser to handle objects, arrays, strings, integers, booleans, null.
struct JVal {
    enum Type { Null, Bool, Number, String, Array, Object } type = Null;
    bool b = false;
    long long num = 0;
    string str;
    vector<JVal> arr;
    unordered_map<string, JVal> obj;
};

struct JParser {
    const string &s;
    size_t i = 0;

    JParser(const string &s_) : s(s_) {}

    void skip_ws() {
        while (i < s.size() && (s[i] == ' ' || s[i] == '\t' || s[i] == '\r' || s[i] == '\n')) i++;
    }

    bool match(const string &t) {
        skip_ws();
        if (s.compare(i, t.size(), t) == 0) {
            i += t.size();
            return true;
        }
        return false;
    }

    char peek() {
        skip_ws();
        return (i < s.size() ? s[i] : '\0');
    }

    char get() {
        return (i < s.size() ? s[i++] : '\0');
    }

    string parse_string_raw() {
        string out;
        if (get() != '"') return out;
        while (i < s.size()) {
            char c = get();
            if (c == '"') break;
            if (c == '\\') {
                if (i >= s.size()) break;
                char e = get();
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
                        // Parse 4 hex digits, but store as '?' to keep simple.
                        for (int k = 0; k < 4 && i < s.size(); ++k) get();
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

    long long parse_number_raw() {
        skip_ws();
        size_t start = i;
        if (i < s.size() && (s[i] == '-' || s[i] == '+')) i++;
        while (i < s.size() && isdigit((unsigned char)s[i])) i++;
        // We ignore fractions/exponents; inputs are integers in this problem.
        string numstr = s.substr(start, i - start);
        long long val = 0;
        try {
            val = stoll(numstr);
        } catch (...) {
            val = 0;
        }
        return val;
    }

    JVal parse_value() {
        skip_ws();
        if (i >= s.size()) return JVal();
        char c = s[i];
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '"') {
            JVal v; v.type = JVal::String; v.str = parse_string_raw(); return v;
        }
        if (c == 't') {
            if (match("true")) { JVal v; v.type = JVal::Bool; v.b = true; return v; }
        }
        if (c == 'f') {
            if (match("false")) { JVal v; v.type = JVal::Bool; v.b = false; return v; }
        }
        if (c == 'n') {
            if (match("null")) { JVal v; v.type = JVal::Null; return v; }
        }
        if (c == '-' || c == '+' || isdigit((unsigned char)c)) {
            JVal v; v.type = JVal::Number; v.num = parse_number_raw(); return v;
        }
        // Fallback: consume one char to avoid infinite loop
        i++;
        return JVal();
    }

    JVal parse_object() {
        JVal v; v.type = JVal::Object;
        get(); // '{'
        skip_ws();
        if (peek() == '}') { get(); return v; }
        while (i < s.size()) {
            skip_ws();
            if (peek() != '"') { // invalid; try to recover
                // skip until next valid end
                while (i < s.size() && s[i] != '}') i++;
                if (i < s.size()) get();
                return v;
            }
            string key = parse_string_raw();
            skip_ws();
            if (get() != ':') { /* invalid */ }
            JVal val = parse_value();
            v.obj.emplace(key, move(val));
            skip_ws();
            char ch = get();
            if (ch == '}') break;
            if (ch != ',') {
                // invalid; try to recover
                while (i < s.size() && s[i] != '}') i++;
                if (i < s.size()) get();
                break;
            }
        }
        return v;
    }

    JVal parse_array() {
        JVal v; v.type = JVal::Array;
        get(); // '['
        skip_ws();
        if (peek() == ']') { get(); return v; }
        while (i < s.size()) {
            JVal elem = parse_value();
            v.arr.push_back(move(elem));
            skip_ws();
            char ch = get();
            if (ch == ']') break;
            if (ch != ',') {
                // invalid; try to recover
                while (i < s.size() && s[i] != ']') i++;
                if (i < s.size()) get();
                break;
            }
        }
        return v;
    }
};

struct Item {
    string type;
    int w, h;
    long long v;
    int limit;
};

struct Variant {
    int type_idx;
    int w, h;
    int rot; // 0 or 1
};

struct Placement {
    int type_idx;
    int x, y;
    int rot;
};

struct Result {
    vector<Placement> placements;
    long long value = 0;
};

// Scoring helpers
static inline double density(const Item &it, const Variant &var) {
    return double(it.v) / double(max(1, var.w * var.h));
}
static inline double v_over_w(const Item &it, const Variant &var) {
    return double(it.v) / double(max(1, var.w));
}
static inline double v_over_h(const Item &it, const Variant &var) {
    return double(it.v) / double(max(1, var.h));
}

// Packing strategies
Result pack_shelves(const vector<Item> &items, const vector<Variant> &vars, int W, int H, int starter_mode, int next_mode) {
    int M = (int)items.size();
    vector<int> left(M);
    for (int t = 0; t < M; ++t) left[t] = items[t].limit;

    vector<Placement> placements;
    long long total_val = 0;

    int y = 0;
    while (y < H) {
        // Choose starter: variant that fits within full width and remaining height
        int best_idx = -1;
        double best_score = -1e300;
        for (int i = 0; i < (int)vars.size(); ++i) {
            const Variant &v = vars[i];
            if (left[v.type_idx] <= 0) continue;
            if (v.w > W) continue;
            if (v.h > H - y) continue;
            double sc = 0.0;
            if (starter_mode == 0) sc = density(items[v.type_idx], v);
            else if (starter_mode == 1) sc = v_over_h(items[v.type_idx], v);
            else if (starter_mode == 2) sc = double(v.h);
            else if (starter_mode == 3) sc = double(items[v.type_idx].v);
            else if (starter_mode == 4) sc = double(v.w);
            else sc = density(items[v.type_idx], v);
            if (sc > best_score) { best_score = sc; best_idx = i; }
        }
        if (best_idx == -1) break;
        int shelf_h = vars[best_idx].h;
        if (shelf_h <= 0) break;
        if (y + shelf_h > H) break;

        int x = 0;
        while (x < W) {
            int best2 = -1;
            double best2_score = -1e300;
            for (int i = 0; i < (int)vars.size(); ++i) {
                const Variant &v = vars[i];
                if (left[v.type_idx] <= 0) continue;
                if (v.w > W - x) continue;
                if (v.h > shelf_h) continue;
                double sc = 0.0;
                if (next_mode == 0) sc = v_over_w(items[v.type_idx], v);
                else sc = density(items[v.type_idx], v);
                if (sc > best2_score) { best2_score = sc; best2 = i; }
            }
            if (best2 == -1) break;
            const Variant &pv = vars[best2];
            placements.push_back({pv.type_idx, x, y, pv.rot});
            left[pv.type_idx]--;
            total_val += items[pv.type_idx].v;
            x += pv.w;
        }
        y += shelf_h;
    }

    return Result{placements, total_val};
}

Result pack_columns(const vector<Item> &items, const vector<Variant> &vars, int W, int H, int starter_mode, int next_mode) {
    int M = (int)items.size();
    vector<int> left(M);
    for (int t = 0; t < M; ++t) left[t] = items[t].limit;

    vector<Placement> placements;
    long long total_val = 0;

    int x = 0;
    while (x < W) {
        // Choose starter variant for column
        int best_idx = -1;
        double best_score = -1e300;
        for (int i = 0; i < (int)vars.size(); ++i) {
            const Variant &v = vars[i];
            if (left[v.type_idx] <= 0) continue;
            if (v.w > W - x) continue;
            if (v.h > H) continue;
            double sc = 0.0;
            if (starter_mode == 0) sc = density(items[v.type_idx], v);
            else if (starter_mode == 1) sc = v_over_w(items[v.type_idx], v);
            else if (starter_mode == 2) sc = double(v.w);
            else if (starter_mode == 3) sc = double(items[v.type_idx].v);
            else sc = density(items[v.type_idx], v);
            if (sc > best_score) { best_score = sc; best_idx = i; }
        }
        if (best_idx == -1) break;
        int col_w = vars[best_idx].w;
        if (col_w <= 0) break;
        if (x + col_w > W) break;

        int y = 0;
        while (y < H) {
            int best2 = -1;
            double best2_score = -1e300;
            for (int i = 0; i < (int)vars.size(); ++i) {
                const Variant &v = vars[i];
                if (left[v.type_idx] <= 0) continue;
                if (v.w > col_w) continue;
                if (v.h > H - y) continue;
                double sc = 0.0;
                if (next_mode == 0) sc = v_over_h(items[v.type_idx], v);
                else sc = density(items[v.type_idx], v);
                if (sc > best2_score) { best2_score = sc; best2 = i; }
            }
            if (best2 == -1) break;
            const Variant &pv = vars[best2];
            placements.push_back({pv.type_idx, x, y, pv.rot});
            left[pv.type_idx]--;
            total_val += items[pv.type_idx].v;
            y += pv.h;
        }
        x += col_w;
    }

    return Result{placements, total_val};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire stdin
    string input, line;
    {
        ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    // Parse JSON
    JParser parser(input);
    JVal root = parser.parse_value();

    // Extract bin and items
    JVal bin = root.obj["bin"];
    JVal items_arr = root.obj["items"];

    int W = 0, H = 0;
    bool allow_rotate = false;
    if (bin.type == JVal::Object) {
        if (bin.obj.count("W")) W = (int)bin.obj["W"].num;
        if (bin.obj.count("H")) H = (int)bin.obj["H"].num;
        if (bin.obj.count("allow_rotate")) allow_rotate = bin.obj["allow_rotate"].b;
    }

    vector<Item> items;
    if (items_arr.type == JVal::Array) {
        for (const auto &it : items_arr.arr) {
            if (it.type != JVal::Object) continue;
            Item item;
            if (it.obj.count("type")) item.type = it.obj.at("type").str;
            if (it.obj.count("w")) item.w = (int)it.obj.at("w").num;
            if (it.obj.count("h")) item.h = (int)it.obj.at("h").num;
            if (it.obj.count("v")) item.v = it.obj.at("v").num;
            if (it.obj.count("limit")) item.limit = (int)it.obj.at("limit").num;
            // Sanitize to fit bin
            if (item.w > W || item.h > H || item.limit <= 0 || item.w <= 0 || item.h <= 0) {
                // Keep but will never be placed; limit could be zero or dims invalid
            }
            items.push_back(item);
        }
    }

    // Prepare variants (orientations)
    vector<Variant> vars;
    for (int i = 0; i < (int)items.size(); ++i) {
        const Item &it = items[i];
        if (it.w <= W && it.h <= H) {
            vars.push_back({i, it.w, it.h, 0});
        }
        if (allow_rotate) {
            if (it.h <= W && it.w <= H) {
                if (!(it.w == it.h)) { // avoid duplicate identical orientations
                    vars.push_back({i, it.h, it.w, 1});
                } else {
                    // square, rot identical; but rot must be 0 if rotation not allowed; if allowed, we can still use rot=0
                    // to avoid duplicates, we skip.
                }
            }
        }
    }

    // If no variants or dimensions invalid, output empty placements
    Result best;
    best.value = -1;

    // Heuristic attempts
    vector<Result> attempts;

    // Shelves: starter modes: 0 density, 1 v/h, 2 height, 3 value; next modes: 0 v/w, 1 density
    vector<pair<int,int>> shelf_params = {{0,0},{1,0},{2,0},{3,0},{0,1}};
    for (auto pr : shelf_params) {
        Result r = pack_shelves(items, vars, W, H, pr.first, pr.second);
        attempts.push_back(r);
    }
    // Columns: starter modes: 0 density, 1 v/w, 2 width, 3 value; next modes: 0 v/h, 1 density
    vector<pair<int,int>> col_params = {{0,0},{1,0},{2,0},{3,0},{0,1}};
    for (auto pr : col_params) {
        Result r = pack_columns(items, vars, W, H, pr.first, pr.second);
        attempts.push_back(r);
    }

    // Choose best
    for (auto &r : attempts) {
        if (r.value > best.value) best = r;
    }
    if (best.value < 0) { best.value = 0; best.placements.clear(); }

    // Print JSON output
    // {
    //   "placements": [
    //     {"type":"id","x":X,"y":Y,"rot":R}, ...
    //   ]
    // }
    cout << "{\n  \"placements\": [";
    for (size_t i = 0; i < best.placements.size(); ++i) {
        const Placement &p = best.placements[i];
        // If rotation not allowed, ensure rot=0
        int rot = allow_rotate ? p.rot : 0;
        cout << "{\"type\":\"" << items[p.type_idx].type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << rot << "}";
        if (i + 1 < best.placements.size()) cout << ",";
    }
    cout << "]\n}\n";

    return 0;
}
#include <bits/stdc++.h>
using namespace std;

struct JSON {
    enum Type {NUL, BOOL, NUM, STR, ARR, OBJ};
    Type type = NUL;
    bool b = false;
    long long n = 0;
    string s;
    vector<JSON> a;
    unordered_map<string, JSON> o;

    bool is_null() const { return type == NUL; }
    bool is_bool() const { return type == BOOL; }
    bool is_num()  const { return type == NUM; }
    bool is_str()  const { return type == STR; }
    bool is_arr()  const { return type == ARR; }
    bool is_obj()  const { return type == OBJ; }

    bool get_bool() const { return b; }
    long long get_num() const { return n; }
    const string& get_str() const { return s; }
    const vector<JSON>& get_arr() const { return a; }
    const unordered_map<string, JSON>& get_obj() const { return o; }
    const JSON& operator[](const string& k) const { 
        static JSON null;
        auto it = o.find(k);
        if (it == o.end()) return null;
        return it->second;
    }
};

struct Parser {
    string s;
    size_t p = 0;

    Parser(const string& str): s(str), p(0) {}

    void skip_ws() {
        while (p < s.size() && isspace((unsigned char)s[p])) ++p;
    }
    bool match(char c) {
        skip_ws();
        if (p < s.size() && s[p] == c) { ++p; return true; }
        return false;
    }
    char peek() {
        skip_ws();
        return p < s.size() ? s[p] : '\0';
    }
    bool eof() { skip_ws(); return p >= s.size(); }

    JSON parse() { return parse_value(); }

    JSON parse_value() {
        skip_ws();
        if (p >= s.size()) return JSON();
        char c = s[p];
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '"') return parse_string();
        if (c == 't' || c == 'f') return parse_bool();
        if (c == '-' || isdigit((unsigned char)c)) return parse_number();
        // null or unknown -> consume token "null" if present
        if (s.compare(p, 4, "null") == 0) { p += 4; return JSON(); }
        // fallback
        return JSON();
    }

    JSON parse_object() {
        JSON j; j.type = JSON::OBJ;
        match('{');
        skip_ws();
        if (match('}')) return j;
        while (true) {
            skip_ws();
            JSON key = parse_string();
            string k = key.s;
            skip_ws();
            match(':');
            JSON val = parse_value();
            j.o.emplace(k, std::move(val));
            skip_ws();
            if (match('}')) break;
            match(',');
        }
        return j;
    }

    JSON parse_array() {
        JSON j; j.type = JSON::ARR;
        match('[');
        skip_ws();
        if (match(']')) return j;
        while (true) {
            JSON v = parse_value();
            j.a.push_back(std::move(v));
            skip_ws();
            if (match(']')) break;
            match(',');
        }
        return j;
    }

    JSON parse_string() {
        JSON j; j.type = JSON::STR;
        match('"');
        string out;
        while (p < s.size()) {
            char c = s[p++];
            if (c == '"') break;
            if (c == '\\') {
                if (p >= s.size()) break;
                char e = s[p++];
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
                        // parse 4 hex digits, ignore unicode specifics, store as-is or skip
                        // We'll just read 4 hex chars and ignore (append '?')
                        for (int i = 0; i < 4 && p < s.size(); ++i) ++p;
                        out.push_back('?');
                        break;
                    }
                    default: out.push_back(e); break;
                }
            } else {
                out.push_back(c);
            }
        }
        j.s = std::move(out);
        return j;
    }

    JSON parse_bool() {
        JSON j; j.type = JSON::BOOL;
        if (s.compare(p, 4, "true") == 0) { j.b = true; p += 4; }
        else if (s.compare(p, 5, "false") == 0) { j.b = false; p += 5; }
        else { j.b = false; }
        return j;
    }

    JSON parse_number() {
        JSON j; j.type = JSON::NUM;
        bool neg = false;
        if (p < s.size() && s[p] == '-') { neg = true; ++p; }
        long long val = 0;
        while (p < s.size() && isdigit((unsigned char)s[p])) {
            val = val * 10 + (s[p] - '0');
            ++p;
        }
        j.n = neg ? -val : val;
        // ignore fractional/exponent if any
        if (p < s.size() && s[p] == '.') {
            // consume fractional part
            ++p;
            while (p < s.size() && isdigit((unsigned char)s[p])) ++p;
        }
        if (p < s.size() && (s[p] == 'e' || s[p] == 'E')) {
            ++p;
            if (p < s.size() && (s[p] == '+' || s[p] == '-')) ++p;
            while (p < s.size() && isdigit((unsigned char)s[p])) ++p;
        }
        return j;
    }
};

struct Item {
    string type;
    int w, h;
    long long v;
    int limit;
};

struct Placement {
    int t_index;
    int x, y;
    int rot; // 0 or 1
};

struct Node {
    int x;
    int y;
};

struct Position {
    bool ok = false;
    int x = 0;
    int y = 0;
    int index = -1; // skyline node index to place at
    long long waste = 0;
};

struct Candidate {
    int t_index = -1;
    int rot = 0;
    int w = 0, h = 0;
    double density = 0.0;
    long long profit = 0;
    long long area = 0;
    Position pos;
};

struct Skyline {
    int W, H;
    vector<Node> nodes;

    Skyline(int W_, int H_) : W(W_), H(H_) {
        nodes.clear();
        nodes.push_back({0, 0});
        nodes.push_back({W, 0}); // sentinel
    }

    Position find_pos(int rw, int rh) const {
        Position best;
        best.ok = false;
        best.y = INT_MAX;
        best.x = INT_MAX;
        best.index = -1;
        best.waste = LLONG_MAX;

        if (rw <= 0 || rh <= 0) return best;
        if (rw > W || rh > H) return best;

        for (int i = 0; i + 1 < (int)nodes.size(); ++i) {
            int x = nodes[i].x;
            if (x + rw > W) break;
            int widthLeft = rw;
            long long sumY = 0;
            int y_max = 0;
            int j = i;
            int curx = x;
            bool fit = true;
            while (widthLeft > 0) {
                if (j >= (int)nodes.size()) { fit = false; break; }
                int nextx = (j + 1 < (int)nodes.size()) ? nodes[j + 1].x : W;
                int segw = nextx - curx;
                if (segw <= 0) { fit = false; break; }
                int take = min(widthLeft, segw);
                y_max = max(y_max, nodes[j].y);
                if (y_max + rh > H) { fit = false; break; }
                sumY += 1LL * nodes[j].y * take;
                widthLeft -= take;
                curx += take;
                if (curx >= nextx) { ++j; curx = nodes[j].x; }
            }
            if (!fit) continue;
            long long waste = 1LL * y_max * rw - sumY;
            // Choose minimal y, then minimal waste, then minimal x
            if (!best.ok || y_max < best.y || (y_max == best.y && (waste < best.waste || (waste == best.waste && x < best.x)))) {
                best.ok = true;
                best.x = x;
                best.y = y_max;
                best.index = i;
                best.waste = waste;
                if (best.y == 0 && best.waste == 0) {
                    // Early perfect fit at ground level for this width; good but still check others maybe
                }
            }
        }
        return best;
    }

    void add_level(int index, int x, int y, int rw, int rh) {
        if (index < 0) return;
        if (index >= (int)nodes.size()) return;
        int endx = x + rw;

        // Raise at index
        nodes[index].y = y + rh;

        // Remove nodes within (index+1) whose x <= endx
        int j = index + 1;
        while (j < (int)nodes.size() && nodes[j].x <= endx) {
            nodes.erase(nodes.begin() + j);
        }
        int rightY = 0;
        if (j < (int)nodes.size()) rightY = nodes[j].y;
        else rightY = 0;
        // Insert node at endx if it's not already at endx
        if (j >= (int)nodes.size() || nodes[j].x != endx) {
            nodes.insert(nodes.begin() + j, {endx, rightY});
        }

        // Optional merge of consecutive nodes with same y (keep sentinel)
        // We will merge to avoid node explosion but preserve sentinel at W.
        for (int k = 1; k < (int)nodes.size(); ) {
            if (nodes[k - 1].y == nodes[k].y) {
                // Prefer to remove the later node only if it's not the last sentinel,
                // otherwise remove the previous node.
                bool k_is_sentinel = (nodes[k].x == W && k == (int)nodes.size() - 1);
                if (!k_is_sentinel) {
                    nodes.erase(nodes.begin() + k);
                } else {
                    nodes.erase(nodes.begin() + (k - 1));
                    // stay at same k (now points to former k)
                }
            } else {
                ++k;
            }
        }
    }
};

struct Packer {
    int W, H;
    bool allow_rotate;
    vector<Item> items;

    enum Strategy {
        ByDensity = 0,
        ByProfit = 1,
        ByArea = 2
    };

    Packer(int W_, int H_, bool allow_rot_, const vector<Item>& items_)
        : W(W_), H(H_), allow_rotate(allow_rot_), items(items_) {}

    vector<Placement> pack_once(Strategy strat, long long& out_profit) {
        Skyline sky(W, H);
        vector<int> remain(items.size());
        for (size_t i = 0; i < items.size(); ++i) remain[i] = items[i].limit;
        vector<Placement> res;
        long long total_profit = 0;

        // Precompute densities
        vector<double> density0(items.size(), 0.0), density1(items.size(), 0.0);
        for (size_t i = 0; i < items.size(); ++i) {
            double d0 = 0.0, d1 = 0.0;
            if (items[i].w > 0 && items[i].h > 0) d0 = (double)items[i].v / (double)(1LL * items[i].w * items[i].h);
            if (allow_rotate && items[i].h > 0 && items[i].w > 0) d1 = (double)items[i].v / (double)(1LL * items[i].h * items[i].w);
            density0[i] = d0;
            density1[i] = d1;
        }

        // Greedy placement loop
        while (true) {
            Candidate best;
            bool found = false;
            for (int t = 0; t < (int)items.size(); ++t) {
                if (remain[t] <= 0) continue;

                // Orientation 0
                {
                    int rw = items[t].w;
                    int rh = items[t].h;
                    if (rw <= W && rh <= H) {
                        Position p = sky.find_pos(rw, rh);
                        if (p.ok) {
                            Candidate c;
                            c.t_index = t;
                            c.rot = 0;
                            c.w = rw; c.h = rh;
                            c.density = density0[t];
                            c.profit = items[t].v;
                            c.area = 1LL * rw * rh;
                            c.pos = p;
                            if (!found || better(c, best, strat)) {
                                best = c; found = true;
                            }
                        }
                    }
                }
                // Orientation 1 if allowed and dimensions differ
                if (allow_rotate) {
                    int rw = items[t].h;
                    int rh = items[t].w;
                    if (rw <= W && rh <= H) {
                        Position p = sky.find_pos(rw, rh);
                        if (p.ok) {
                            Candidate c;
                            c.t_index = t;
                            c.rot = 1;
                            c.w = rw; c.h = rh;
                            c.density = density1[t];
                            c.profit = items[t].v;
                            c.area = 1LL * rw * rh;
                            c.pos = p;
                            if (!found || better(c, best, strat)) {
                                best = c; found = true;
                            }
                        }
                    }
                }
            }
            if (!found) break;

            sky.add_level(best.pos.index, best.pos.x, best.pos.y, best.w, best.h);
            Placement pl;
            pl.t_index = best.t_index;
            pl.x = best.pos.x;
            pl.y = best.pos.y;
            pl.rot = allow_rotate ? best.rot : 0;
            res.push_back(pl);
            remain[best.t_index]--;
            total_profit += items[best.t_index].v;
        }

        out_profit = total_profit;
        return res;
    }

    static bool better(const Candidate& a, const Candidate& b, Strategy strat) {
        // Primary: lower y
        if (a.pos.y != b.pos.y) return a.pos.y < b.pos.y;
        // Secondary: depending on strategy
        switch (strat) {
            case ByDensity:
                if (a.density != b.density) return a.density > b.density;
                break;
            case ByProfit:
                if (a.profit != b.profit) return a.profit > b.profit;
                break;
            case ByArea:
                if (a.area != b.area) return a.area > b.area;
                break;
        }
        // Tertiary: lower waste
        if (a.pos.waste != b.pos.waste) return a.pos.waste < b.pos.waste;
        // Quaternary: lower x
        if (a.pos.x != b.pos.x) return a.pos.x < b.pos.x;
        // Lastly: prefer taller to possibly reduce fragmentation
        if (a.h != b.h) return a.h > b.h;
        return a.w > b.w;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string input, line;
    string tmp;
    while (getline(cin, tmp)) {
        input += tmp;
        input.push_back('\n');
    }
    Parser parser(input);
    JSON root = parser.parse();

    const JSON& bin = root["bin"];
    const JSON& itemsJ = root["items"];

    int W = (int)bin["W"].get_num();
    int H = (int)bin["H"].get_num();
    bool allow_rotate = bin["allow_rotate"].get_bool();

    vector<Item> items;
    if (itemsJ.is_arr()) {
        for (const auto& it : itemsJ.a) {
            Item I;
            I.type = it["type"].get_str();
            I.w = (int)it["w"].get_num();
            I.h = (int)it["h"].get_num();
            I.v = it["v"].get_num();
            I.limit = (int)it["limit"].get_num();
            // Clamp to bin bounds
            I.w = min(I.w, W);
            I.h = min(I.h, H);
            items.push_back(I);
        }
    }

    Packer packer(W, H, allow_rotate, items);

    long long best_profit = -1;
    vector<Placement> best_res;

    // Try multiple strategies and pick the best
    for (int s = 0; s < 3; ++s) {
        long long p = 0;
        vector<Placement> r = packer.pack_once((Packer::Strategy)s, p);
        if (p > best_profit) {
            best_profit = p;
            best_res = std::move(r);
        }
    }

    // Output JSON
    // Exact format:
    // {
    //   "placements": [
    //     { "type":"...", "x":int, "y":int, "rot":0|1 },
    //     ...
    //   ]
    // }
    cout << "{\n  \"placements\": [";
    for (size_t i = 0; i < best_res.size(); ++i) {
        const auto& pl = best_res[i];
        cout << (i == 0 ? "\n    " : ",\n    ");
        cout << "{\"type\":\"" << items[pl.t_index].type << "\",\"x\":" << pl.x << ",\"y\":" << pl.y << ",\"rot\":" << (allow_rotate ? pl.rot : 0) << "}";
    }
    if (!best_res.empty()) cout << "\n";
    cout << "  ]\n}\n";
    return 0;
}
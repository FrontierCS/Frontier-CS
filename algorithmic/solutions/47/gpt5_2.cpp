#include <bits/stdc++.h>
using namespace std;

// ---------------- Minimal JSON Parser ----------------

struct JVal {
    enum Type {NUL, BOOL, NUM, STR, ARR, OBJ} t = NUL;
    bool b = false;
    long long num = 0;
    string s;
    vector<JVal> a;
    unordered_map<string, JVal> o;
};

struct JSONParser {
    string s;
    size_t i = 0;

    JSONParser(const string& str): s(str), i(0) {}

    void skipWS() {
        while (i < s.size() && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) ++i;
    }

    bool match(char c) {
        skipWS();
        if (i < s.size() && s[i] == c) {
            ++i;
            return true;
        }
        return false;
    }

    char peek() {
        skipWS();
        if (i < s.size()) return s[i];
        return '\0';
    }

    JVal parse() {
        return parseValue();
    }

    JVal parseValue() {
        skipWS();
        if (i >= s.size()) return JVal();
        char c = s[i];
        if (c == '{') return parseObject();
        if (c == '[') return parseArray();
        if (c == '"') return parseString();
        if (c == 't' || c == 'f') return parseBool();
        if (c == 'n') return parseNull();
        if (c == '-' || (c >= '0' && c <= '9')) return parseNumber();
        // Fallback null on invalid
        return JVal();
    }

    JVal parseObject() {
        JVal v; v.t = JVal::OBJ;
        match('{');
        skipWS();
        if (match('}')) return v;
        while (true) {
            skipWS();
            JVal key = parseString();
            skipWS();
            match(':');
            JVal val = parseValue();
            v.o[key.s] = val;
            skipWS();
            if (match('}')) break;
            match(',');
        }
        return v;
    }

    JVal parseArray() {
        JVal v; v.t = JVal::ARR;
        match('[');
        skipWS();
        if (match(']')) return v;
        while (true) {
            JVal elem = parseValue();
            v.a.push_back(elem);
            skipWS();
            if (match(']')) break;
            match(',');
        }
        return v;
    }

    JVal parseString() {
        JVal v; v.t = JVal::STR;
        match('"');
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
                        // minimal handling: skip next four hex digits
                        // and ignore unicode specifics; just store '?'
                        for (int k = 0; k < 4 && i < s.size(); ++k) ++i;
                        out.push_back('?');
                        break;
                    }
                    default: out.push_back(e); break;
                }
            } else {
                out.push_back(c);
            }
        }
        v.s = out;
        return v;
    }

    JVal parseBool() {
        JVal v; v.t = JVal::BOOL;
        if (s.compare(i, 4, "true") == 0) {
            v.b = true;
            i += 4;
        } else if (s.compare(i, 5, "false") == 0) {
            v.b = false;
            i += 5;
        } else {
            // invalid -> default false
            v.b = false;
        }
        return v;
    }

    JVal parseNull() {
        JVal v; v.t = JVal::NUL;
        if (s.compare(i, 4, "null") == 0) i += 4;
        return v;
    }

    JVal parseNumber() {
        JVal v; v.t = JVal::NUM;
        skipWS();
        bool neg = false;
        if (i < s.size() && s[i] == '-') { neg = true; ++i; }
        long long n = 0;
        while (i < s.size() && s[i] >= '0' && s[i] <= '9') {
            n = n * 10 + (s[i] - '0');
            ++i;
        }
        if (neg) n = -n;
        // ignore fractional/exponent if present (round/truncate)
        if (i < s.size() && s[i] == '.') {
            ++i;
            while (i < s.size() && s[i] >= '0' && s[i] <= '9') ++i;
        }
        if (i < s.size() && (s[i] == 'e' || s[i] == 'E')) {
            ++i;
            if (i < s.size() && (s[i] == '+' || s[i] == '-')) ++i;
            while (i < s.size() && s[i] >= '0' && s[i] <= '9') ++i;
        }
        v.num = n;
        return v;
    }
};

// --------------- Data Structures --------------------

struct ItemType {
    string id;
    int w, h;
    long long v;
    int limit;
};

struct Placement {
    string type;
    int x, y;
    int rot; // 0 or 1
};

struct Skyline {
    struct Node { int x, y; };
    int W, H;
    vector<Node> nodes;

    Skyline(int W_, int H_) : W(W_), H(H_) {
        nodes.clear();
        nodes.push_back({0, 0});
        nodes.push_back({W, 0});
    }

    int ensureNodeAt(int x) {
        // ensure a node at coordinate x with appropriate y
        // nodes sorted by x
        int l = 0, r = (int)nodes.size();
        while (l < r) {
            int m = (l + r) >> 1;
            if (nodes[m].x < x) l = m + 1;
            else r = m;
        }
        if (l < (int)nodes.size() && nodes[l].x == x) return l;
        int idx = l - 1;
        int y = nodes[idx].y;
        nodes.insert(nodes.begin() + l, {x, y});
        return l;
    }

    bool findPosition(int rw, int rh, int& outX, int& outY) {
        int bestY = INT_MAX;
        int bestX = 0;
        bool found = false;

        // iterate start nodes
        for (int i = 0; i + 1 < (int)nodes.size(); ++i) {
            int x = nodes[i].x;
            if (x + rw > W) break;

            // compute maxY in [x, x + rw)
            int endX = x + rw;
            int j = i;
            int currX = x;
            int maxY = 0;
            while (currX < endX) {
                maxY = max(maxY, nodes[j].y);
                int nx = nodes[j + 1].x;
                if (nx >= endX) break;
                currX = nx;
                ++j;
            }
            if (maxY + rh <= H) {
                if (!found || maxY < bestY || (maxY == bestY && x < bestX)) {
                    found = true;
                    bestY = maxY;
                    bestX = x;
                    if (bestY == 0) {
                        // cannot do better than y=0 and smallest x; early continue scanning few to check if any x smaller
                        // But we already pick smallest x tie, so if x==0 we can break early
                        if (bestX == 0) {
                            // still there could be other items; but for a given item we return; We are in per-item find.
                        }
                    }
                }
            }
            // small early pruning: if found y=0 and bestX==0, we can break.
            if (found && bestY == 0 && bestX == 0) break;
        }

        if (found) {
            outX = bestX;
            outY = bestY;
            return true;
        }
        return false;
    }

    void placeRect(int x, int y, int rw, int rh) {
        int x2 = x + rw;
        int idx1 = ensureNodeAt(x);
        int idx2 = ensureNodeAt(x2);
        // Remove nodes between idx1 and idx2 (exclusive of idx2)
        nodes.erase(nodes.begin() + idx1 + 1, nodes.begin() + idx2);
        // Set height at idx1
        nodes[idx1].y = y + rh;
        // Merge with previous if same height
        if (idx1 > 0 && nodes[idx1 - 1].y == nodes[idx1].y) {
            nodes.erase(nodes.begin() + idx1);
            --idx1;
        }
        // Merge with next if same height
        if (idx1 + 1 < (int)nodes.size() && nodes[idx1].y == nodes[idx1 + 1].y) {
            nodes.erase(nodes.begin() + idx1 + 1);
        }
    }
};

struct Opt {
    int typeIdx;
    int rot;
    int w, h;
    long long v;
    long long area;
    double density;
    string id;
};

struct Solution {
    vector<Placement> places;
    long long profit = 0;
};

// --------------- Packing Strategies ------------------

struct Packer {
    int W, H;
    bool allow_rotate;
    vector<ItemType> items;
    vector<Opt> options;

    Packer(int W_, int H_, bool allow_rotate_, const vector<ItemType>& items_)
        : W(W_), H(H_), allow_rotate(allow_rotate_), items(items_) {
        buildOptions();
    }

    void buildOptions() {
        options.clear();
        for (int i = 0; i < (int)items.size(); ++i) {
            const auto& it = items[i];
            // orientation 0
            {
                Opt o;
                o.typeIdx = i;
                o.rot = 0;
                o.w = it.w;
                o.h = it.h;
                o.v = it.v;
                o.area = 1LL * o.w * o.h;
                o.density = o.area ? (double)o.v / (double)o.area : 0.0;
                o.id = it.id;
                options.push_back(o);
            }
            if (allow_rotate && !(it.w == it.h)) {
                Opt o;
                o.typeIdx = i;
                o.rot = 1;
                o.w = it.h;
                o.h = it.w;
                o.v = it.v;
                o.area = 1LL * o.w * o.h;
                o.density = o.area ? (double)o.v / (double)o.area : 0.0;
                o.id = it.id;
                options.push_back(o);
            }
        }
    }

    long long computeProfit(const vector<Placement>& pls) {
        long long res = 0;
        for (auto& p : pls) {
            // find type by id
            // We'll map id->index earlier for speed
        }
        return res; // not used
    }

    Solution pack_greedy_choice() {
        Skyline sky(W, H);
        vector<int> remain(items.size());
        for (size_t i = 0; i < items.size(); ++i) remain[i] = items[i].limit;

        vector<Placement> placements;
        long long profit = 0;

        while (true) {
            bool anyFit = false;
            int bestX = -1, bestY = -1;
            int bestOptIdx = -1;
            // Heuristic tie-breaker metrics
            double bestDensity = -1e100;
            long long bestV = -1;
            long long bestArea = -1;

            for (int oi = 0; oi < (int)options.size(); ++oi) {
                const auto& o = options[oi];
                if (remain[o.typeIdx] <= 0) continue;
                if (o.w > W || o.h > H) continue;

                int x, y;
                if (!sky.findPosition(o.w, o.h, x, y)) continue;
                // candidate found
                anyFit = true;

                // Select based on minimal y; tie by higher density, then higher v, then larger area, then smaller x
                bool choose = false;
                if (bestOptIdx == -1) {
                    choose = true;
                } else {
                    if (y < bestY) choose = true;
                    else if (y == bestY) {
                        if (o.density > bestDensity + 1e-12) choose = true;
                        else if (fabs(o.density - bestDensity) <= 1e-12) {
                            if (o.v > bestV) choose = true;
                            else if (o.v == bestV) {
                                if (o.area > bestArea) choose = true;
                                else if (o.area == bestArea) {
                                    if (x < bestX) choose = true;
                                }
                            }
                        }
                    }
                }
                if (choose) {
                    bestOptIdx = oi;
                    bestX = x;
                    bestY = y;
                    bestDensity = o.density;
                    bestV = o.v;
                    bestArea = o.area;
                }
            }

            if (!anyFit || bestOptIdx == -1) break;

            const Opt& o = options[bestOptIdx];
            sky.placeRect(bestX, bestY, o.w, o.h);
            placements.push_back({o.id, bestX, bestY, o.rot});
            profit += o.v;
            remain[o.typeIdx]--;
        }

        Solution sol;
        sol.places = move(placements);
        sol.profit = profit;
        return sol;
    }

    Solution pack_by_order(vector<Opt> order) {
        Skyline sky(W, H);
        vector<int> remain(items.size());
        for (size_t i = 0; i < items.size(); ++i) remain[i] = items[i].limit;

        vector<Placement> placements;
        long long profit = 0;

        for (const auto& o : order) {
            while (remain[o.typeIdx] > 0) {
                if (o.w > W || o.h > H) break;
                int x, y;
                if (!sky.findPosition(o.w, o.h, x, y)) break;
                sky.placeRect(x, y, o.w, o.h);
                placements.push_back({o.id, x, y, o.rot});
                profit += o.v;
                remain[o.typeIdx]--;
            }
        }
        Solution sol;
        sol.places = move(placements);
        sol.profit = profit;
        return sol;
    }

    Solution solve() {
        // Try multiple strategies and pick the best
        Solution best;
        best.profit = -1;

        // Strategy 1: Greedy choice across all options each step
        {
            Solution s = pack_greedy_choice();
            if (s.profit > best.profit) best = move(s);
        }

        // Build various orderings
        vector<Opt> opts = options;

        // Strategy 2: by density desc
        {
            auto ord = opts;
            sort(ord.begin(), ord.end(), [](const Opt& a, const Opt& b){
                if (a.density != b.density) return a.density > b.density;
                if (a.v != b.v) return a.v > b.v;
                if (a.area != b.area) return a.area > b.area;
                return a.id < b.id;
            });
            Solution s = pack_by_order(ord);
            if (s.profit > best.profit) best = move(s);
        }

        // Strategy 3: by value desc
        {
            auto ord = opts;
            sort(ord.begin(), ord.end(), [](const Opt& a, const Opt& b){
                if (a.v != b.v) return a.v > b.v;
                if (a.area != b.area) return a.area > b.area;
                return a.density > b.density;
            });
            Solution s = pack_by_order(ord);
            if (s.profit > best.profit) best = move(s);
        }

        // Strategy 4: by area desc
        {
            auto ord = opts;
            sort(ord.begin(), ord.end(), [](const Opt& a, const Opt& b){
                if (a.area != b.area) return a.area > b.area;
                if (a.v != b.v) return a.v > b.v;
                return a.density > b.density;
            });
            Solution s = pack_by_order(ord);
            if (s.profit > best.profit) best = move(s);
        }

        // Strategy 5: by max dimension desc
        {
            auto ord = opts;
            auto key = [](const Opt& o){ return max(o.w, o.h); };
            sort(ord.begin(), ord.end(), [&](const Opt& a, const Opt& b){
                int ka = key(a), kb = key(b);
                if (ka != kb) return ka > kb;
                if (a.area != b.area) return a.area > b.area;
                return a.v > b.v;
            });
            Solution s = pack_by_order(ord);
            if (s.profit > best.profit) best = move(s);
        }

        // Strategy 6: small-first (min dimension asc) to fill gaps
        {
            auto ord = opts;
            auto key = [](const Opt& o){ return min(o.w, o.h); };
            sort(ord.begin(), ord.end(), [&](const Opt& a, const Opt& b){
                int ka = key(a), kb = key(b);
                if (ka != kb) return ka < kb;
                if (a.area != b.area) return a.area < b.area;
                return a.v > b.v;
            });
            Solution s = pack_by_order(ord);
            if (s.profit > best.profit) best = move(s);
        }

        return best;
    }
};

// ------------------- Main ----------------------------

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire stdin to string
    string input;
    {
        std::ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    JSONParser parser(input);
    JVal root = parser.parse();

    // Extract bin
    JVal bin = root.o["bin"];
    int W = (int)bin.o["W"].num;
    int H = (int)bin.o["H"].num;
    bool allow_rotate = bin.o["allow_rotate"].b;

    // Extract items
    vector<ItemType> items;
    JVal arr = root.o["items"];
    for (const auto& it : arr.a) {
        ItemType t;
        t.id = it.o.at("type").s;
        t.w = (int)it.o.at("w").num;
        t.h = (int)it.o.at("h").num;
        t.v = it.o.at("v").num;
        t.limit = (int)it.o.at("limit").num;
        // Sanity clamp to non-negative
        if (t.w < 1) t.w = 1;
        if (t.h < 1) t.h = 1;
        if (t.limit < 0) t.limit = 0;
        if (t.w > W || t.h > H) {
            // keep, but skyline will never place them
        }
        items.push_back(t);
    }

    Packer packer(W, H, allow_rotate, items);
    Solution sol = packer.solve();

    // Output JSON
    cout << "{\n  \"placements\": [";
    for (size_t i = 0; i < sol.places.size(); ++i) {
        const auto& p = sol.places[i];
        cout << "\n    {\"type\":\"" << p.type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
        if (i + 1 != sol.places.size()) cout << ",";
    }
    cout << "\n  ]\n}\n";
    return 0;
}
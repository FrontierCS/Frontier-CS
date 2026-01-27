#include <bits/stdc++.h>
using namespace std;

// Minimal JSON parser tailored for the given problem format

struct Parser {
    string s;
    size_t i = 0;

    Parser(const string& str) : s(str), i(0) {}

    void skipws() {
        while (i < s.size() && isspace((unsigned char)s[i])) i++;
    }

    bool consume(char c) {
        skipws();
        if (i < s.size() && s[i] == c) { i++; return true; }
        return false;
    }

    void expect(char c) {
        skipws();
        if (i >= s.size() || s[i] != c) {
            // Basic failure handling: exit on invalid JSON
            exit(0);
        }
        i++;
    }

    string parseString() {
        skipws();
        if (i >= s.size() || s[i] != '"') exit(0);
        i++;
        string out;
        while (i < s.size()) {
            char c = s[i++];
            if (c == '"') break;
            if (c == '\\') {
                if (i >= s.size()) exit(0);
                char e = s[i++];
                if (e == '"' || e == '\\' || e == '/') out.push_back(e);
                else if (e == 'b') out.push_back('\b');
                else if (e == 'f') out.push_back('\f');
                else if (e == 'n') out.push_back('\n');
                else if (e == 'r') out.push_back('\r');
                else if (e == 't') out.push_back('\t');
                else {
                    // unicode not needed here
                    out.push_back(e);
                }
            } else {
                out.push_back(c);
            }
        }
        return out;
    }

    long long parseInt() {
        skipws();
        bool neg = false;
        if (i < s.size() && (s[i] == '-' || s[i] == '+')) {
            neg = (s[i] == '-');
            i++;
        }
        if (i >= s.size() || !isdigit((unsigned char)s[i])) exit(0);
        long long val = 0;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            val = val * 10 + (s[i] - '0');
            i++;
        }
        return neg ? -val : val;
    }

    bool parseBool() {
        skipws();
        if (s.compare(i, 4, "true") == 0) { i += 4; return true; }
        if (s.compare(i, 5, "false") == 0) { i += 5; return false; }
        exit(0);
        return false;
    }

    void parseNull() {
        skipws();
        if (s.compare(i, 4, "null") == 0) { i += 4; return; }
        exit(0);
    }
};

struct ItemType {
    string type;
    int w, h;
    long long v;
    int limit;
    int id;
};

struct Placement {
    string type;
    int x, y;
    int rot;
};

struct Node {
    int x;
    int y;
};

struct Pos {
    bool ok;
    int x;
    int y;
};

struct Skyline {
    int W, H;
    vector<Node> nodes;

    Skyline() {}
    Skyline(int W_, int H_) : W(W_), H(H_) {
        nodes.clear();
        nodes.push_back({0, 0});
        nodes.push_back({W, 0});
    }

    // Find position using Bottom-Left heuristic for a rectangle w x h
    Pos findPos(int w, int h) const {
        Pos best{false, 0, 0};
        int bestY = INT_MAX;
        int bestX = INT_MAX;

        for (size_t i = 0; i + 1 <= nodes.size(); i++) {
            int x = nodes[i].x;
            if (x + w > W) continue;
            int endX = x + w;
            int maxY = 0;
            // compute maxY over [x, endX)
            size_t k = i;
            while (k < nodes.size() && nodes[k].x < endX) {
                maxY = max(maxY, nodes[k].y);
                k++;
            }
            if (maxY + h <= H) {
                if (maxY < bestY || (maxY == bestY && x < bestX)) {
                    bestY = maxY;
                    bestX = x;
                    best = {true, x, maxY};
                }
            }
        }
        return best;
    }

    int getHeightAt(int x) const {
        // assumes 0 <= x <= W
        // find node k such that nodes[k].x <= x < nodes[k+1].x
        int lo = 0, hi = (int)nodes.size() - 1;
        while (lo + 1 < hi) {
            int mid = (lo + hi) / 2;
            if (nodes[mid].x <= x) lo = mid;
            else hi = mid;
        }
        return nodes[lo].y;
    }

    void ensureNodeAt(int x) {
        // Ensure a node with position x exists; if not, insert with current height at x
        if (x <= 0 || x >= W) return;
        // binary search for position
        int lo = 0, hi = (int)nodes.size() - 1;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            if (nodes[mid].x == x) return; // already there
            if (nodes[mid].x < x) lo = mid + 1;
            else hi = mid - 1;
        }
        // lo is the first index with nodes[lo].x > x
        int h = getHeightAt(x);
        nodes.insert(nodes.begin() + lo, Node{x, h});
    }

    void mergeNeighbors() {
        // Remove consecutive nodes with same y
        vector<Node> nn;
        nn.reserve(nodes.size());
        for (auto &nd : nodes) {
            if (!nn.empty() && nn.back().y == nd.y) continue;
            nn.push_back(nd);
        }
        nodes.swap(nn);
    }

    void placeRect(int x, int y, int w, int h) {
        int left = x;
        int right = x + w;
        int newH = y + h;
        ensureNodeAt(left);
        ensureNodeAt(right);

        // find indices after ensuring
        int idxL = -1, idxR = -1;
        for (int idx = 0; idx < (int)nodes.size(); ++idx) {
            if (nodes[idx].x == left) idxL = idx;
            if (nodes[idx].x == right) { idxR = idx; break; }
        }
        if (idxL == -1 || idxR == -1) return;

        // Set height at left to newH, and erase nodes between (idxL+1 .. idxR-1)
        nodes[idxL].y = newH;
        if (idxR > idxL + 1) {
            nodes.erase(nodes.begin() + idxL + 1, nodes.begin() + idxR);
            idxR = idxL + 1;
        }
        // Now nodes[idxR] is at 'right'; keep its y as before.
        // Merge if needed
        mergeNeighbors();
    }
};

struct AttemptResult {
    long long totalValue = 0;
    vector<Placement> placements;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire stdin into a string
    string input, line;
    {
        ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    Parser p(input);

    // Parse top-level object with keys "bin" and "items"
    p.expect('{');

    bool gotBin = false, gotItems = false;

    int W = 0, H = 0;
    bool allow_rotate = false;
    vector<ItemType> items;

    while (true) {
        p.skipws();
        if (p.consume('}')) break;
        string key = p.parseString();
        p.expect(':');
        if (key == "bin") {
            p.expect('{');
            bool gW=false, gH=false, gR=false;
            while (true) {
                p.skipws();
                if (p.consume('}')) break;
                string bkey = p.parseString();
                p.expect(':');
                if (bkey == "W") { W = (int)p.parseInt(); gW = true; }
                else if (bkey == "H") { H = (int)p.parseInt(); gH = true; }
                else if (bkey == "allow_rotate") { allow_rotate = p.parseBool(); gR = true; }
                else {
                    // unknown key, attempt to skip a value generically
                    // but per statement, keys are exact; we'll bail
                    exit(0);
                }
                p.skipws();
                if (p.consume(',')) continue;
                else if (p.s[p.i-1] != '}') { p.skipws(); }
            }
            if (!(gW && gH && gR)) exit(0);
            gotBin = true;
        } else if (key == "items") {
            p.expect('[');
            int idCounter = 0;
            while (true) {
                p.skipws();
                if (p.consume(']')) break;
                p.expect('{');
                ItemType it;
                bool gt=false, gw=false, gh=false, gv=false, gl=false;
                while (true) {
                    p.skipws();
                    if (p.consume('}')) break;
                    string ikey = p.parseString();
                    p.expect(':');
                    if (ikey == "type") { it.type = p.parseString(); gt = true; }
                    else if (ikey == "w") { it.w = (int)p.parseInt(); gw = true; }
                    else if (ikey == "h") { it.h = (int)p.parseInt(); gh = true; }
                    else if (ikey == "v") { it.v = p.parseInt(); gv = true; }
                    else if (ikey == "limit") { it.limit = (int)p.parseInt(); gl = true; }
                    else { exit(0); }
                    p.skipws();
                    if (p.consume(',')) continue;
                    else if (p.s[p.i-1] != '}') { p.skipws(); }
                }
                if (!(gt && gw && gh && gv && gl)) exit(0);
                it.id = idCounter++;
                items.push_back(it);
                p.skipws();
                if (p.consume(',')) continue;
                else if (p.s[p.i-1] != ']') { p.skipws(); }
            }
            gotItems = true;
        } else {
            // unknown top-level key
            exit(0);
        }
        p.skipws();
        p.consume(',');
    }

    if (!gotBin || !gotItems) {
        // invalid input
        cout << "{\"placements\":[]}\n";
        return 0;
    }

    // Prepare sort orders
    int M = (int)items.size();

    vector<vector<int>> orders;

    // 1) density descending
    {
        vector<int> ord(M);
        iota(ord.begin(), ord.end(), 0);
        vector<double> dens(M);
        for (int i = 0; i < M; ++i) {
            long long area = 1LL * items[i].w * items[i].h;
            dens[i] = area > 0 ? (double)items[i].v / (double)area : 0.0;
        }
        sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (dens[a] != dens[b]) return dens[a] > dens[b];
            long long aa = 1LL * items[a].w * items[a].h;
            long long ab = 1LL * items[b].w * items[b].h;
            if (aa != ab) return aa > ab;
            return items[a].v > items[b].v;
        });
        orders.push_back(ord);
    }

    // 2) area descending
    {
        vector<int> ord(M);
        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int a, int b) {
            long long aa = 1LL * items[a].w * items[a].h;
            long long ab = 1LL * items[b].w * items[b].h;
            if (aa != ab) return aa > ab;
            return items[a].v > items[b].v;
        });
        orders.push_back(ord);
    }

    // 3) max dimension descending
    {
        vector<int> ord(M);
        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int a, int b) {
            int ma = max(items[a].w, items[a].h);
            int mb = max(items[b].w, items[b].h);
            if (ma != mb) return ma > mb;
            long long aa = 1LL * items[a].w * items[a].h;
            long long ab = 1LL * items[b].w * items[b].h;
            return aa > ab;
        });
        orders.push_back(ord);
    }

    // 4) value descending
    {
        vector<int> ord(M);
        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (items[a].v != items[b].v) return items[a].v > items[b].v;
            long long aa = 1LL * items[a].w * items[a].h;
            long long ab = 1LL * items[b].w * items[b].h;
            return aa > ab;
        });
        orders.push_back(ord);
    }

    // 5) height descending then width descending (favor tall pieces)
    {
        vector<int> ord(M);
        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (items[a].h != items[b].h) return items[a].h > items[b].h;
            if (items[a].w != items[b].w) return items[a].w > items[b].w;
            return items[a].v > items[b].v;
        });
        orders.push_back(ord);
    }

    auto run_attempt = [&](const vector<int>& ord) -> AttemptResult {
        AttemptResult res;
        Skyline sky(W, H);
        vector<int> remaining(M);
        for (int i = 0; i < M; ++i) remaining[i] = items[i].limit;

        for (int idx : ord) {
            const ItemType &it = items[idx];
            while (remaining[idx] > 0) {
                Pos best = {false, 0, 0};
                int useW = it.w, useH = it.h;
                int useRot = 0;

                Pos p0 = sky.findPos(it.w, it.h);
                Pos p1 = {false, 0, 0};
                if (allow_rotate) {
                    p1 = sky.findPos(it.h, it.w);
                }
                // choose best
                if (p0.ok && p1.ok) {
                    if (p0.y < p1.y || (p0.y == p1.y && p0.x <= p1.x)) {
                        best = p0; useW = it.w; useH = it.h; useRot = 0;
                    } else {
                        best = p1; useW = it.h; useH = it.w; useRot = 1;
                    }
                } else if (p0.ok) {
                    best = p0; useW = it.w; useH = it.h; useRot = 0;
                } else if (p1.ok) {
                    best = p1; useW = it.h; useH = it.w; useRot = 1;
                } else {
                    break;
                }

                // place
                sky.placeRect(best.x, best.y, useW, useH);
                Placement plc;
                plc.type = it.type;
                plc.x = best.x;
                plc.y = best.y;
                plc.rot = allow_rotate ? useRot : 0;
                res.placements.push_back(plc);
                res.totalValue += it.v;
                remaining[idx]--;
            }
        }
        return res;
    };

    AttemptResult bestRes;
    bestRes.totalValue = -1;

    for (auto &ord : orders) {
        AttemptResult r = run_attempt(ord);
        if (r.totalValue > bestRes.totalValue) bestRes = std::move(r);
    }

    // Output JSON
    cout << "{\n  \"placements\": [";
    for (size_t i = 0; i < bestRes.placements.size(); ++i) {
        auto &pl = bestRes.placements[i];
        cout << "\n    {\"type\":\"" << pl.type << "\",\"x\":" << pl.x << ",\"y\":" << pl.y << ",\"rot\":" << pl.rot << "}";
        if (i + 1 < bestRes.placements.size()) cout << ",";
    }
    cout << "\n  ]\n}\n";

    return 0;
}
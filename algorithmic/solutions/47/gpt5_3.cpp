#include <bits/stdc++.h>
using namespace std;

struct Parser {
    string s;
    size_t i = 0;
    Parser(const string& str) : s(str), i(0) {}
    void skipws() {
        while (i < s.size() && isspace((unsigned char)s[i])) ++i;
    }
    bool match(char c) {
        skipws();
        if (i < s.size() && s[i] == c) { ++i; return true; }
        return false;
    }
    void expect(char c) {
        skipws();
        if (i >= s.size() || s[i] != c) {
            // Invalid JSON; do a best-effort exit.
            // Since the judge uses valid JSON, we keep it simple.
            exit(0);
        }
        ++i;
    }
    string parseString() {
        skipws();
        if (i >= s.size() || s[i] != '"') exit(0);
        ++i;
        string res;
        while (i < s.size()) {
            char c = s[i++];
            if (c == '\\') {
                if (i >= s.size()) break;
                char esc = s[i++];
                // Minimal escape handling
                if (esc == '"' || esc == '\\' || esc == '/') res.push_back(esc);
                else if (esc == 'b') res.push_back('\b');
                else if (esc == 'f') res.push_back('\f');
                else if (esc == 'n') res.push_back('\n');
                else if (esc == 'r') res.push_back('\r');
                else if (esc == 't') res.push_back('\t');
                else {
                    // Unsupported escape; just include as is
                    res.push_back(esc);
                }
            } else if (c == '"') {
                return res;
            } else {
                res.push_back(c);
            }
        }
        return res;
    }
    long long parseInt() {
        skipws();
        bool neg = false;
        if (i < s.size() && (s[i] == '-' || s[i] == '+')) {
            neg = (s[i] == '-');
            ++i;
        }
        long long val = 0;
        bool any = false;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            any = true;
            val = val * 10 + (s[i] - '0');
            ++i;
        }
        if (!any) exit(0);
        return neg ? -val : val;
    }
    bool parseBool() {
        skipws();
        if (s.compare(i, 4, "true") == 0) { i += 4; return true; }
        if (s.compare(i, 5, "false") == 0) { i += 5; return false; }
        exit(0);
        return false;
    }
};

struct BinCfg { int W=0, H=0; bool allow_rotate=false; };
struct ItemType { string type; int w=0, h=0; long long v=0; int limit=0; };

static void parseInput(BinCfg& bin, vector<ItemType>& items) {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string input, line;
    while (getline(cin, line)) input += line + "\n";
    Parser p(input);
    p.expect('{');
    bool gotBin = false, gotItems = false;
    while (true) {
        p.skipws();
        if (p.match('}')) break;
        string key = p.parseString();
        p.expect(':');
        if (key == "bin") {
            p.expect('{');
            bool gotW=false, gotH=false, gotR=false;
            while (true) {
                p.skipws();
                if (p.match('}')) break;
                string k = p.parseString();
                p.expect(':');
                if (k == "W") { bin.W = (int)p.parseInt(); gotW = true; }
                else if (k == "H") { bin.H = (int)p.parseInt(); gotH = true; }
                else if (k == "allow_rotate") { bin.allow_rotate = p.parseBool(); gotR = true; }
                // consume optional comma
                p.skipws();
                p.match(',');
            }
            gotBin = true;
        } else if (key == "items") {
            p.expect('[');
            while (true) {
                p.skipws();
                if (p.match(']')) break;
                ItemType it;
                p.expect('{');
                bool gt=false, gw=false, gh=false, gv=false, gl=false;
                while (true) {
                    p.skipws();
                    if (p.match('}')) break;
                    string k = p.parseString();
                    p.expect(':');
                    if (k == "type") { it.type = p.parseString(); gt = true; }
                    else if (k == "w") { it.w = (int)p.parseInt(); gw = true; }
                    else if (k == "h") { it.h = (int)p.parseInt(); gh = true; }
                    else if (k == "v") { it.v = p.parseInt(); gv = true; }
                    else if (k == "limit") { it.limit = (int)p.parseInt(); gl = true; }
                    p.skipws();
                    p.match(',');
                }
                if (gt && gw && gh && gv && gl) items.push_back(it);
                p.skipws();
                p.match(',');
            }
            gotItems = true;
        } else {
            // Skip unknown value (not expected).
            // Try to consume a generic JSON value in a simplistic way.
            // This input should not happen per problem statement.
            // We will attempt to skip balanced braces/brackets or string/number/bool/null.
            p.skipws();
            if (p.match('{')) {
                int depth = 1;
                while (depth > 0 && p.i < p.s.size()) {
                    if (p.s[p.i] == '"') { // skip string
                        p.parseString();
                    } else if (p.s[p.i] == '{') { ++depth; ++p.i; }
                    else if (p.s[p.i] == '}') { --depth; ++p.i; }
                    else ++p.i;
                }
            } else if (p.match('[')) {
                int depth = 1;
                while (depth > 0 && p.i < p.s.size()) {
                    if (p.s[p.i] == '"') { p.parseString(); }
                    else if (p.s[p.i] == '[') { ++depth; ++p.i; }
                    else if (p.s[p.i] == ']') { --depth; ++p.i; }
                    else ++p.i;
                }
            } else if (p.i < p.s.size() && p.s[p.i] == '"') {
                p.parseString();
            } else {
                // number/bool/null - consume basic token
                size_t j = p.i;
                while (j < p.s.size() && !isspace((unsigned char)p.s[j]) && string(",}]").find(p.s[j]) == string::npos) ++j;
                p.i = j;
            }
        }
        p.skipws();
        p.match(',');
    }
    // Minimal validation
    if (!gotBin) { /* invalid input */ }
    if (!gotItems) { /* invalid input */ }
}

struct Node { int x, y, width; };

static const int INFY = 1e9;

static int computeMinYAtIndex(const vector<Node>& nodes, int idx, int rw, int rh, int W, int H) {
    int x = nodes[idx].x;
    if (x + rw > W) return INFY;
    int y = nodes[idx].y;
    int widthLeft = rw;
    int j = idx;
    int topY = y;
    while (widthLeft > 0) {
        if (j >= (int)nodes.size()) return INFY; // should not happen
        topY = max(topY, nodes[j].y);
        if (topY + rh > H) return INFY;
        int segRight = nodes[j].x + nodes[j].width;
        int take = min(widthLeft, segRight - (j == idx ? x : nodes[j].x));
        widthLeft -= take;
        ++j;
    }
    return topY;
}

static void addSkylineLevel(vector<Node>& nodes, int idx, int x, int y, int rw, int rh, int W) {
    // Insert new node
    Node newNode{ x, y + rh, rw };
    nodes.insert(nodes.begin() + idx, newNode);

    // Remove/adjust overlapping nodes to the right
    int xEnd = x + rw;
    for (int j = idx + 1; j < (int)nodes.size(); ) {
        Node& nd = nodes[j];
        if (nd.x >= xEnd) break;
        int overlap = min(nd.x + nd.width, xEnd) - nd.x;
        if (overlap <= 0) break;
        nd.x += overlap;
        nd.width -= overlap;
        if (nd.width <= 0) {
            nodes.erase(nodes.begin() + j);
        } else {
            break;
        }
    }

    // Merge nodes with same height
    for (int k = 1; k < (int)nodes.size(); ) {
        if (nodes[k-1].y == nodes[k].y) {
            nodes[k-1].width += nodes[k].width;
            nodes.erase(nodes.begin() + k);
        } else {
            ++k;
        }
    }
}

struct Placement { string type; int x, y, rot; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    BinCfg bin;
    vector<ItemType> items;
    parseInput(bin, items);

    int W = bin.W, H = bin.H;
    bool allow_rot = bin.allow_rotate;

    vector<Node> skyline;
    skyline.push_back({0, 0, W});

    int M = (int)items.size();
    vector<int> used(M, 0);

    // Pre-filter items where neither orientation fits at all
    vector<bool> usable(M, false);
    for (int i = 0; i < M; ++i) {
        bool ok = false;
        if (items[i].w <= W && items[i].h <= H) ok = true;
        if (allow_rot && items[i].h <= W && items[i].w <= H) ok = true;
        usable[i] = ok && items[i].limit > 0 && items[i].v > 0;
    }

    vector<Placement> placements;
    placements.reserve(5000);

    int maxPlacements = 8000; // safety cap to avoid huge outputs/time

    // Main greedy loop
    while ((int)placements.size() < maxPlacements) {
        // Check if any item remains usable
        bool anyLeft = false;
        for (int i = 0; i < M; ++i) if (usable[i] && used[i] < items[i].limit) { anyLeft = true; break; }
        if (!anyLeft) break;

        // For each item orientation, find best position (bottom-left)
        struct Cand {
            int itemIdx;
            int rot; // 0 or 1
            int idxInSky;
            int x;
            int y;
            long long v;
            long long area;
            bool valid;
        };
        Cand best;
        best.valid = false;

        for (int it = 0; it < M; ++it) {
            if (!usable[it]) continue;
            if (used[it] >= items[it].limit) continue;

            for (int rot = 0; rot <= 1; ++rot) {
                if (rot == 1 && !allow_rot) continue;
                int rw = (rot ? items[it].h : items[it].w);
                int rh = (rot ? items[it].w : items[it].h);
                if (rw <= 0 || rh <= 0 || rw > W || rh > H) continue;

                int bestY = INFY;
                int bestX = 0;
                int bestIdx = -1;

                // Scan skyline nodes
                for (int idx = 0; idx < (int)skyline.size(); ++idx) {
                    if (skyline[idx].x + rw > W) continue;
                    if (skyline[idx].y > bestY) continue; // cannot improve y
                    int y = computeMinYAtIndex(skyline, idx, rw, rh, W, H);
                    if (y == INFY) continue;
                    int x = skyline[idx].x;
                    if (y < bestY || (y == bestY && x < bestX)) {
                        bestY = y; bestX = x; bestIdx = idx;
                        if (bestY == 0 && bestX == 0) {
                            // Perfect bottom-left; we could consider early break,
                            // but we still may find another item with same y but better v.
                        }
                    }
                }

                if (bestIdx != -1) {
                    Cand c;
                    c.itemIdx = it; c.rot = rot; c.idxInSky = bestIdx;
                    c.x = bestX; c.y = bestY;
                    c.v = items[it].v;
                    c.area = 1LL * rw * rh;
                    c.valid = true;

                    if (!best.valid) {
                        best = c;
                    } else {
                        // Choose candidate with minimal y, tie-break by higher value, then larger area, then smaller x
                        if (c.y < best.y) best = c;
                        else if (c.y == best.y) {
                            if (c.v > best.v) best = c;
                            else if (c.v == best.v) {
                                if (c.area > best.area) best = c;
                                else if (c.area == best.area) {
                                    if (c.x < best.x) best = c;
                                }
                            }
                        }
                    }
                }
            }
        }

        if (!best.valid) break; // no placement possible

        int t = best.itemIdx;
        int rot = best.rot;
        int rw = (rot ? items[t].h : items[t].w);
        int rh = (rot ? items[t].w : items[t].h);
        int x = best.x;
        int y = best.y;
        int idx = best.idxInSky;

        // Place it
        addSkylineLevel(skyline, idx, x, y, rw, rh, W);
        placements.push_back({items[t].type, x, y, rot});
        used[t]++;

        // Update usability if limits reached
        if (used[t] >= items[t].limit) {
            // check if we should still consider other orientation? Limit is global for type.
            // Once the type is exhausted, mark unusable.
            // This is fine.
        }
    }

    // Output JSON
    cout << "{\n  \"placements\": [";
    for (size_t i = 0; i < placements.size(); ++i) {
        const auto& p = placements[i];
        cout << "\n    {\"type\":\"" << p.type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
        if (i + 1 < placements.size()) cout << ",";
    }
    cout << "\n  ]\n}\n";
    return 0;
}
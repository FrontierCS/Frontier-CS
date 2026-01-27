#include <bits/stdc++.h>
using namespace std;

struct Item {
    string type;
    int w, h;
    long long v;
    int limit;
};

struct Placement {
    int typeIndex;
    int x, y;
    int rot; // 0 or 1
};

struct Node {
    int x;
    int y;
};

struct Packer {
    int W, H;
    bool allow_rotate;
    const vector<Item>* items;
    vector<Node> nodes;

    void resetSkyline() {
        nodes.clear();
        nodes.push_back({0, 0});
        nodes.push_back({W, 0});
    }

    int skylineRightYAt(int x) const {
        // Height of skyline immediately to the right of x
        if (x <= nodes.front().x) return nodes.front().y;
        for (size_t i = 0; i < nodes.size(); ++i) {
            if (nodes[i].x == x) {
                return nodes[i].y;
            }
            if (nodes[i].x > x) {
                if (i == 0) return nodes[0].y;
                return nodes[i-1].y;
            }
        }
        return nodes.back().y;
    }

    int computeMaxY(int idx, int w) const {
        int xStart = nodes[idx].x;
        int xEnd = xStart + w;
        int y = 0;
        int i = idx;
        while (i < (int)nodes.size() && nodes[i].x < xEnd) {
            y = max(y, nodes[i].y);
            ++i;
        }
        return y;
    }

    bool rectFitsAt(int idx, int w, int h, int &yOut) const {
        int x = nodes[idx].x;
        if (x + w > W) return false;
        int y = computeMaxY(idx, w);
        if (y + h > H) return false;
        yOut = y;
        return true;
    }

    void addSkylineLevel(int idx, int w, int h, int yBottom) {
        int x = nodes[idx].x;
        int xEnd = x + w;
        int rightOldY = skylineRightYAt(xEnd);

        // Raise at idx
        nodes[idx].y = yBottom + h;

        // Remove nodes covered by [x, xEnd)
        int i = idx + 1;
        while (i < (int)nodes.size() && nodes[i].x < xEnd) {
            nodes.erase(nodes.begin() + i);
        }
        // If there is a node exactly at xEnd, set its y to rightOldY; otherwise insert
        if (i < (int)nodes.size() && nodes[i].x == xEnd) {
            nodes[i].y = rightOldY;
        } else {
            nodes.insert(nodes.begin() + i, {xEnd, rightOldY});
        }

        // Merge with left if same height
        if (idx > 0 && nodes[idx-1].y == nodes[idx].y) {
            nodes.erase(nodes.begin() + idx);
            --idx;
        }
        // Merge with right if same height
        if (idx + 1 < (int)nodes.size() && nodes[idx+1].y == nodes[idx].y) {
            nodes.erase(nodes.begin() + (idx + 1));
        }
    }

    bool findPositionForDims(int w, int h, int &bestIdx, int &bestX, int &bestY) const {
        int bestYVal = INT_MAX, bestXVal = INT_MAX, bestIndex = -1;
        for (int i = 0; i < (int)nodes.size(); ++i) {
            int x = nodes[i].x;
            if (x + w > W) break;
            int y;
            if (!rectFitsAt(i, w, h, y)) continue;
            if (y < bestYVal || (y == bestYVal && x < bestXVal)) {
                bestYVal = y;
                bestXVal = x;
                bestIndex = i;
            }
        }
        if (bestIndex == -1) return false;
        bestIdx = bestIndex;
        bestX = bestXVal;
        bestY = bestYVal;
        return true;
    }

    bool placeOne(const Item& it, int &x, int &y, int &rotOut) {
        int idx0, x0, y0;
        bool ok0 = findPositionForDims(it.w, it.h, idx0, x0, y0);
        int idx1=-1, x1=0, y1=0;
        bool ok1 = false;
        if (allow_rotate) {
            ok1 = findPositionForDims(it.h, it.w, idx1, x1, y1);
        }
        if (!ok0 && !ok1) return false;
        if (ok0 && (!ok1 || y0 < y1 || (y0 == y1 && x0 <= x1))) {
            addSkylineLevel(idx0, it.w, it.h, y0);
            x = x0; y = y0; rotOut = 0;
            return true;
        } else {
            addSkylineLevel(idx1, it.h, it.w, y1);
            x = x1; y = y1; rotOut = 1;
            return true;
        }
    }
};

static inline void skipSpaces(const string& s, size_t &i) {
    while (i < s.size() && isspace((unsigned char)s[i])) ++i;
}

static bool parseIntAfterColon(const string& s, size_t &pos, long long &out) {
    size_t i = pos;
    size_t colon = s.find(':', i);
    if (colon == string::npos) return false;
    i = colon + 1;
    skipSpaces(s, i);
    bool neg = false;
    if (i < s.size() && s[i] == '-') { neg = true; ++i; }
    if (i >= s.size() || !isdigit((unsigned char)s[i])) return false;
    long long val = 0;
    while (i < s.size() && isdigit((unsigned char)s[i])) {
        val = val * 10 + (s[i]-'0');
        ++i;
    }
    out = neg ? -val : val;
    pos = i;
    return true;
}

static bool parseBoolAfterColon(const string& s, size_t &pos, bool &out) {
    size_t i = pos;
    size_t colon = s.find(':', i);
    if (colon == string::npos) return false;
    i = colon + 1;
    skipSpaces(s, i);
    if (s.compare(i, 4, "true") == 0) {
        out = true;
        pos = i + 4;
        return true;
    } else if (s.compare(i, 5, "false") == 0) {
        out = false;
        pos = i + 5;
        return true;
    }
    return false;
}

static bool parseStringAfterColon(const string& s, size_t &pos, string &out) {
    size_t i = pos;
    size_t colon = s.find(':', i);
    if (colon == string::npos) return false;
    i = colon + 1;
    skipSpaces(s, i);
    if (i >= s.size() || s[i] != '"') return false;
    ++i;
    string res;
    while (i < s.size()) {
        char c = s[i++];
        if (c == '\\') {
            if (i < s.size()) {
                char esc = s[i++];
                // Handle basic escapes; here we just take the escaped char
                res.push_back(esc);
            }
        } else if (c == '"') {
            break;
        } else {
            res.push_back(c);
        }
    }
    out = res;
    pos = i;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input, line;
    {
        std::ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    // Parse bin
    int W = 0, H = 0;
    bool allow_rotate = false;

    {
        size_t posBin = input.find("\"bin\"");
        if (posBin == string::npos) { cout << "{\"placements\":[]}"; return 0; }
        size_t brace = input.find('{', posBin);
        size_t endBin = input.find('}', brace);
        if (brace == string::npos || endBin == string::npos) { cout << "{\"placements\":[]}"; return 0; }
        string binStr = input.substr(brace, endBin - brace + 1);

        size_t pW = binStr.find("\"W\"");
        if (pW != string::npos) {
            long long val=0; size_t pp=pW;
            if (parseIntAfterColon(binStr, pp, val)) W = (int)val;
        }
        size_t pH = binStr.find("\"H\"");
        if (pH != string::npos) {
            long long val=0; size_t pp=pH;
            if (parseIntAfterColon(binStr, pp, val)) H = (int)val;
        }
        size_t pR = binStr.find("\"allow_rotate\"");
        if (pR != string::npos) {
            bool b=false; size_t pp=pR;
            if (parseBoolAfterColon(binStr, pp, b)) allow_rotate = b;
        }
    }

    // Parse items array
    vector<Item> items;
    {
        size_t posItems = input.find("\"items\"");
        if (posItems == string::npos) { cout << "{\"placements\":[]}"; return 0; }
        size_t bracket = input.find('[', posItems);
        if (bracket == string::npos) { cout << "{\"placements\":[]}"; return 0; }
        int depth = 1;
        size_t i = bracket + 1;
        size_t endBracket = string::npos;
        while (i < input.size()) {
            if (input[i] == '[') depth++;
            else if (input[i] == ']') {
                depth--;
                if (depth == 0) { endBracket = i; break; }
            }
            ++i;
        }
        if (endBracket == string::npos) { cout << "{\"placements\":[]}"; return 0; }
        string arr = input.substr(bracket + 1, endBracket - bracket - 1);

        size_t pos = 0;
        while (true) {
            size_t lb = arr.find('{', pos);
            if (lb == string::npos) break;
            int d = 1;
            size_t j = lb + 1;
            while (j < arr.size()) {
                if (arr[j] == '{') d++;
                else if (arr[j] == '}') {
                    d--;
                    if (d == 0) break;
                }
                ++j;
            }
            if (j >= arr.size()) break;
            string obj = arr.substr(lb, j - lb + 1);

            Item it;
            // Parse fields
            size_t p;
            p = obj.find("\"type\"");
            if (p != string::npos) {
                size_t pp = p;
                string s; if (parseStringAfterColon(obj, pp, s)) it.type = s;
            }
            p = obj.find("\"w\"");
            if (p != string::npos) {
                long long val=0; size_t pp=p;
                if (parseIntAfterColon(obj, pp, val)) it.w = (int)val;
            }
            p = obj.find("\"h\"");
            if (p != string::npos) {
                long long val=0; size_t pp=p;
                if (parseIntAfterColon(obj, pp, val)) it.h = (int)val;
            }
            p = obj.find("\"v\"");
            if (p != string::npos) {
                long long val=0; size_t pp=p;
                if (parseIntAfterColon(obj, pp, val)) it.v = val;
            }
            p = obj.find("\"limit\"");
            if (p != string::npos) {
                long long val=0; size_t pp=p;
                if (parseIntAfterColon(obj, pp, val)) it.limit = (int)val;
            }
            // Clamp to bin
            it.w = min(it.w, W);
            it.h = min(it.h, H);
            if (it.limit < 0) it.limit = 0;
            items.push_back(it);

            pos = j + 1;
        }
    }

    if (W <= 0 || H <= 0 || items.empty()) {
        cout << "{\"placements\":[]}";
        return 0;
    }

    auto startTime = chrono::high_resolution_clock::now();

    // Prepare orderings
    int M = (int)items.size();
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);

    auto byDensity = idx;
    stable_sort(byDensity.begin(), byDensity.end(), [&](int a, int b){
        long double da = (long double)items[a].v / ((long double)items[a].w * (long double)items[a].h);
        long double db = (long double)items[b].v / ((long double)items[b].w * (long double)items[b].h);
        if (da != db) return da > db;
        return items[a].v > items[b].v;
    });

    auto byProfit = idx;
    stable_sort(byProfit.begin(), byProfit.end(), [&](int a, int b){
        if (items[a].v != items[b].v) return items[a].v > items[b].v;
        long long aa = 1LL*items[a].w*items[a].h;
        long long bb = 1LL*items[b].w*items[b].h;
        return aa > bb;
    });

    auto byArea = idx;
    stable_sort(byArea.begin(), byArea.end(), [&](int a, int b){
        long long aa = 1LL*items[a].w*items[a].h;
        long long bb = 1LL*items[b].w*items[b].h;
        if (aa != bb) return aa > bb;
        return items[a].v > items[b].v;
    });

    auto byMaxSide = idx;
    stable_sort(byMaxSide.begin(), byMaxSide.end(), [&](int a, int b){
        int ma = max(items[a].w, items[a].h);
        int mb = max(items[b].w, items[b].h);
        if (ma != mb) return ma > mb;
        return items[a].v > items[b].v;
    });

    auto genCopies = [&](const vector<int>& order, bool roundRobin){
        vector<int> copies;
        if (roundRobin) {
            vector<int> used(M, 0);
            int remain = 0;
            for (int t = 0; t < M; ++t) remain += items[t].limit;
            while (remain > 0) {
                bool any = false;
                for (int t : order) {
                    if (used[t] < items[t].limit) {
                        copies.push_back(t);
                        used[t]++;
                        remain--;
                        any = true;
                    }
                }
                if (!any) break;
            }
        } else {
            for (int t : order) {
                for (int k = 0; k < items[t].limit; ++k) copies.push_back(t);
            }
        }
        return copies;
    };

    auto packWithCopies = [&](const vector<int>& copies){
        Packer pk;
        pk.W = W; pk.H = H; pk.allow_rotate = allow_rotate; pk.items = &items;
        pk.resetSkyline();
        vector<Placement> pls;
        vector<int> used(M, 0);
        long long profit = 0;

        for (int t : copies) {
            if (used[t] >= items[t].limit) continue;
            int x, y, rot;
            if (pk.placeOne(items[t], x, y, rot)) {
                used[t]++;
                profit += items[t].v;
                if (!allow_rotate) rot = 0;
                pls.push_back({t, x, y, rot});
            }
        }
        return pair<vector<Placement>, long long>(move(pls), profit);
    };

    long long bestProfit = -1;
    vector<Placement> bestPls;

    vector<pair<vector<int>, bool>> attempts;
    attempts.push_back({byDensity, true});
    attempts.push_back({byProfit, true});
    attempts.push_back({byArea, false});
    attempts.push_back({byMaxSide, false});

    for (size_t ai = 0; ai < attempts.size(); ++ai) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        if (elapsed > 0.95) break;

        auto copies = genCopies(attempts[ai].first, attempts[ai].second);
        auto res = packWithCopies(copies);
        if (res.second > bestProfit) {
            bestProfit = res.second;
            bestPls = move(res.first);
        }
    }

    // Output JSON
    cout << "{\"placements\":[";
    for (size_t i = 0; i < bestPls.size(); ++i) {
        const auto& p = bestPls[i];
        cout << "{\"type\":\"" << items[p.typeIndex].type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << (allow_rotate ? p.rot : 0) << "}";
        if (i + 1 < bestPls.size()) cout << ",";
    }
    cout << "]}";
    return 0;
}
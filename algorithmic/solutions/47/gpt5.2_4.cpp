#include <bits/stdc++.h>
using namespace std;

struct JVal {
    enum Type {NIL, BOOL, NUMBER, STRING, ARRAY, OBJECT} type = NIL;
    bool b = false;
    long long num = 0;
    string str;
    vector<JVal> arr;
    map<string, JVal> obj;
};

struct JsonParser {
    string s;
    size_t i = 0;

    explicit JsonParser(string input) : s(std::move(input)) {}

    void skipWS() {
        while (i < s.size() && (unsigned char)s[i] <= 32) i++;
    }

    [[noreturn]] void fail(const string& msg) {
        throw runtime_error("JSON parse error at pos " + to_string(i) + ": " + msg);
    }

    bool consume(char c) {
        skipWS();
        if (i < s.size() && s[i] == c) {
            i++;
            return true;
        }
        return false;
    }

    void expect(char c) {
        skipWS();
        if (i >= s.size() || s[i] != c) fail(string("expected '") + c + "'");
        i++;
    }

    string parseString() {
        skipWS();
        expect('\"');
        string out;
        while (i < s.size()) {
            char c = s[i++];
            if (c == '\"') break;
            if (c == '\\') {
                if (i >= s.size()) fail("bad escape");
                char e = s[i++];
                switch (e) {
                    case '\"': out.push_back('\"'); break;
                    case '\\': out.push_back('\\'); break;
                    case '/': out.push_back('/'); break;
                    case 'b': out.push_back('\b'); break;
                    case 'f': out.push_back('\f'); break;
                    case 'n': out.push_back('\n'); break;
                    case 'r': out.push_back('\r'); break;
                    case 't': out.push_back('\t'); break;
                    case 'u': {
                        if (i + 4 > s.size()) fail("bad \\u escape");
                        // Minimal \u handling: parse hex, emit '?' for non-ASCII
                        unsigned code = 0;
                        for (int k = 0; k < 4; k++) {
                            char h = s[i++];
                            code <<= 4;
                            if (h >= '0' && h <= '9') code += (h - '0');
                            else if (h >= 'a' && h <= 'f') code += (h - 'a' + 10);
                            else if (h >= 'A' && h <= 'F') code += (h - 'A' + 10);
                            else fail("bad hex in \\u");
                        }
                        if (code <= 0x7F) out.push_back((char)code);
                        else out.push_back('?');
                        break;
                    }
                    default: fail("unknown escape");
                }
            } else {
                out.push_back(c);
            }
        }
        return out;
    }

    long long parseNumber() {
        skipWS();
        bool neg = false;
        if (i < s.size() && s[i] == '-') {
            neg = true;
            i++;
        }
        if (i >= s.size() || !isdigit((unsigned char)s[i])) fail("expected digit");
        long long val = 0;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            int d = s[i++] - '0';
            val = val * 10 + d;
        }
        return neg ? -val : val;
    }

    bool parseBool() {
        skipWS();
        if (s.compare(i, 4, "true") == 0) { i += 4; return true; }
        if (s.compare(i, 5, "false") == 0) { i += 5; return false; }
        fail("expected bool");
        return false;
    }

    JVal parseValue() {
        skipWS();
        if (i >= s.size()) fail("unexpected EOF");
        char c = s[i];
        if (c == '{') return parseObject();
        if (c == '[') return parseArray();
        if (c == '"') { JVal v; v.type = JVal::STRING; v.str = parseString(); return v; }
        if (c == 't' || c == 'f') { JVal v; v.type = JVal::BOOL; v.b = parseBool(); return v; }
        if (c == 'n') {
            if (s.compare(i, 4, "null") == 0) { i += 4; JVal v; v.type = JVal::NIL; return v; }
            fail("expected null");
        }
        if (c == '-' || isdigit((unsigned char)c)) { JVal v; v.type = JVal::NUMBER; v.num = parseNumber(); return v; }
        fail("unexpected character");
        return {};
    }

    JVal parseArray() {
        JVal v; v.type = JVal::ARRAY;
        expect('[');
        skipWS();
        if (consume(']')) return v;
        while (true) {
            v.arr.push_back(parseValue());
            skipWS();
            if (consume(']')) break;
            expect(',');
        }
        return v;
    }

    JVal parseObject() {
        JVal v; v.type = JVal::OBJECT;
        expect('{');
        skipWS();
        if (consume('}')) return v;
        while (true) {
            string key = parseString();
            skipWS();
            expect(':');
            JVal val = parseValue();
            v.obj.emplace(std::move(key), std::move(val));
            skipWS();
            if (consume('}')) break;
            expect(',');
        }
        return v;
    }
};

static string jsonEscape(const string& in) {
    string out;
    out.reserve(in.size() + 8);
    for (char c : in) {
        switch (c) {
            case '\"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if ((unsigned char)c < 32) {
                    char buf[7];
                    snprintf(buf, sizeof(buf), "\\u%04x", (unsigned)(unsigned char)c);
                    out += buf;
                } else out.push_back(c);
        }
    }
    return out;
}

struct ItemType {
    string id;
    int w = 0, h = 0;
    long long v = 0;
    int limit = 0;
    int cap = 0;
};

struct Rect {
    int x = 0, y = 0, w = 0, h = 0;
};

enum class Heuristic { ShortSideFit, AreaFit, BottomLeft };
enum class SelectMode { Density, Profit, Area };

struct FitScore {
    int shortSide = INT_MAX;
    int longSide = INT_MAX;
    int areaFit = INT_MAX;
    int x = INT_MAX, y = INT_MAX;
};

struct Placed {
    int t = -1;
    int x = 0, y = 0, rot = 0;
    int w = 0, h = 0;
};

struct MaxRects {
    int W, H;
    vector<Rect> freeRects;

    explicit MaxRects(int w, int h) : W(w), H(h) {
        freeRects.push_back({0,0,W,H});
    }

    static bool intersect(const Rect& a, const Rect& b) {
        return !(b.x >= a.x + a.w || b.x + b.w <= a.x || b.y >= a.y + a.h || b.y + b.h <= a.y);
    }

    static bool containedIn(const Rect& a, const Rect& b) {
        return a.x >= b.x && a.y >= b.y && a.x + a.w <= b.x + b.w && a.y + a.h <= b.y + b.h;
    }

    bool findPosition(int rw, int rh, Heuristic heur, Rect& bestNode, FitScore& bestScore) const {
        bool found = false;
        FitScore scBest;
        Rect nodeBest;
        for (const Rect& fr : freeRects) {
            if (rw <= fr.w && rh <= fr.h) {
                int leftoverHoriz = fr.w - rw;
                int leftoverVert  = fr.h - rh;
                int shortSide = min(leftoverHoriz, leftoverVert);
                int longSide  = max(leftoverHoriz, leftoverVert);
                int areaFit = fr.w * fr.h - rw * rh;

                FitScore sc;
                sc.shortSide = shortSide;
                sc.longSide = longSide;
                sc.areaFit = areaFit;
                sc.x = fr.x;
                sc.y = fr.y;

                bool better = false;
                if (!found) better = true;
                else {
                    if (heur == Heuristic::ShortSideFit) {
                        if (sc.shortSide != scBest.shortSide) better = sc.shortSide < scBest.shortSide;
                        else if (sc.longSide != scBest.longSide) better = sc.longSide < scBest.longSide;
                        else if (sc.areaFit != scBest.areaFit) better = sc.areaFit < scBest.areaFit;
                        else if (sc.y != scBest.y) better = sc.y < scBest.y;
                        else if (sc.x != scBest.x) better = sc.x < scBest.x;
                    } else if (heur == Heuristic::AreaFit) {
                        if (sc.areaFit != scBest.areaFit) better = sc.areaFit < scBest.areaFit;
                        else if (sc.shortSide != scBest.shortSide) better = sc.shortSide < scBest.shortSide;
                        else if (sc.longSide != scBest.longSide) better = sc.longSide < scBest.longSide;
                        else if (sc.y != scBest.y) better = sc.y < scBest.y;
                        else if (sc.x != scBest.x) better = sc.x < scBest.x;
                    } else { // BottomLeft
                        if (sc.y != scBest.y) better = sc.y < scBest.y;
                        else if (sc.x != scBest.x) better = sc.x < scBest.x;
                        else if (sc.shortSide != scBest.shortSide) better = sc.shortSide < scBest.shortSide;
                        else if (sc.longSide != scBest.longSide) better = sc.longSide < scBest.longSide;
                        else if (sc.areaFit != scBest.areaFit) better = sc.areaFit < scBest.areaFit;
                    }
                }

                if (better) {
                    found = true;
                    scBest = sc;
                    nodeBest = {fr.x, fr.y, rw, rh};
                }
            }
        }
        if (found) {
            bestNode = nodeBest;
            bestScore = scBest;
        }
        return found;
    }

    bool splitFreeNode(const Rect& freeNode, const Rect& usedNode, vector<Rect>& newRects) const {
        if (!intersect(freeNode, usedNode)) return false;

        if (usedNode.x > freeNode.x && usedNode.x < freeNode.x + freeNode.w) {
            Rect r = freeNode;
            r.w = usedNode.x - freeNode.x;
            if (r.w > 0 && r.h > 0) newRects.push_back(r);
        }
        if (usedNode.x + usedNode.w < freeNode.x + freeNode.w) {
            Rect r = freeNode;
            int nx = usedNode.x + usedNode.w;
            r.w = (freeNode.x + freeNode.w) - nx;
            r.x = nx;
            if (r.w > 0 && r.h > 0) newRects.push_back(r);
        }
        if (usedNode.y > freeNode.y && usedNode.y < freeNode.y + freeNode.h) {
            Rect r = freeNode;
            r.h = usedNode.y - freeNode.y;
            if (r.w > 0 && r.h > 0) newRects.push_back(r);
        }
        if (usedNode.y + usedNode.h < freeNode.y + freeNode.h) {
            Rect r = freeNode;
            int ny = usedNode.y + usedNode.h;
            r.h = (freeNode.y + freeNode.h) - ny;
            r.y = ny;
            if (r.w > 0 && r.h > 0) newRects.push_back(r);
        }
        return true;
    }

    void pruneFreeList() {
        for (size_t a = 0; a < freeRects.size(); a++) {
            for (size_t b = a + 1; b < freeRects.size(); b++) {
                if (containedIn(freeRects[a], freeRects[b])) {
                    freeRects[a] = freeRects.back();
                    freeRects.pop_back();
                    a--;
                    break;
                }
                if (containedIn(freeRects[b], freeRects[a])) {
                    freeRects[b] = freeRects.back();
                    freeRects.pop_back();
                    b--;
                }
            }
        }
    }

    void placeRect(const Rect& node) {
        vector<Rect> newRects;
        for (size_t i = 0; i < freeRects.size(); ) {
            if (splitFreeNode(freeRects[i], node, newRects)) {
                freeRects[i] = freeRects.back();
                freeRects.pop_back();
            } else {
                i++;
            }
        }
        freeRects.insert(freeRects.end(), newRects.begin(), newRects.end());
        pruneFreeList();
    }

    bool insert(int rw, int rh, Heuristic heur, Rect& placed, FitScore& score) {
        Rect node;
        FitScore sc;
        if (!findPosition(rw, rh, heur, node, sc)) return false;
        placed = node;
        score = sc;
        placeRect(node);
        return true;
    }
};

struct RunResult {
    long long profit = 0;
    vector<Placed> placements;
};

static inline bool betterFit(const FitScore& a, const FitScore& b, Heuristic heur) {
    if (heur == Heuristic::ShortSideFit) {
        if (a.shortSide != b.shortSide) return a.shortSide < b.shortSide;
        if (a.longSide != b.longSide) return a.longSide < b.longSide;
        if (a.areaFit != b.areaFit) return a.areaFit < b.areaFit;
        if (a.y != b.y) return a.y < b.y;
        return a.x < b.x;
    } else if (heur == Heuristic::AreaFit) {
        if (a.areaFit != b.areaFit) return a.areaFit < b.areaFit;
        if (a.shortSide != b.shortSide) return a.shortSide < b.shortSide;
        if (a.longSide != b.longSide) return a.longSide < b.longSide;
        if (a.y != b.y) return a.y < b.y;
        return a.x < b.x;
    } else {
        if (a.y != b.y) return a.y < b.y;
        if (a.x != b.x) return a.x < b.x;
        if (a.shortSide != b.shortSide) return a.shortSide < b.shortSide;
        if (a.longSide != b.longSide) return a.longSide < b.longSide;
        return a.areaFit < b.areaFit;
    }
}

struct Candidate {
    bool ok = false;
    int t = -1;
    int rot = 0;
    int w = 0, h = 0;
    Rect node;
    FitScore fit;
    long long v = 0;
    long long area = 1;
};

static inline bool betterCand(const Candidate& a, const Candidate& b, SelectMode sel, Heuristic heur) {
    if (!a.ok) return false;
    if (!b.ok) return true;

    if (sel == SelectMode::Density) {
        __int128 lhs = (__int128)a.v * (__int128)b.area;
        __int128 rhs = (__int128)b.v * (__int128)a.area;
        if (lhs != rhs) return lhs > rhs;
        if (a.v != b.v) return a.v > b.v;
        if (a.area != b.area) return a.area > b.area;
    } else if (sel == SelectMode::Profit) {
        if (a.v != b.v) return a.v > b.v;
        __int128 lhs = (__int128)a.v * (__int128)b.area;
        __int128 rhs = (__int128)b.v * (__int128)a.area;
        if (lhs != rhs) return lhs > rhs;
        if (a.area != b.area) return a.area > b.area;
    } else { // Area
        if (a.area != b.area) return a.area > b.area;
        __int128 lhs = (__int128)a.v * (__int128)b.area;
        __int128 rhs = (__int128)b.v * (__int128)a.area;
        if (lhs != rhs) return lhs > rhs;
        if (a.v != b.v) return a.v > b.v;
    }

    if (betterFit(a.fit, b.fit, heur)) return true;
    if (betterFit(b.fit, a.fit, heur)) return false;

    if (a.node.y != b.node.y) return a.node.y < b.node.y;
    if (a.node.x != b.node.x) return a.node.x < b.node.x;
    return a.rot < b.rot;
}

static RunResult run_iterative(const vector<ItemType>& items, int W, int H, bool allowRotate,
                               Heuristic heur, SelectMode sel, int maxPlacements) {
    MaxRects pack(W, H);
    vector<int> rem(items.size(), 0);
    for (size_t t = 0; t < items.size(); t++) rem[t] = items[t].cap;

    RunResult rr;
    rr.profit = 0;
    rr.placements.reserve(min<long long>(maxPlacements, (long long)W*H));

    for (int iter = 0; iter < maxPlacements; iter++) {
        Candidate best;
        for (int t = 0; t < (int)items.size(); t++) {
            if (rem[t] <= 0) continue;
            const auto& it = items[t];

            Candidate candBestType;
            candBestType.ok = false;

            auto tryOri = [&](int rot, int rw, int rh) {
                Rect node;
                FitScore sc;
                if (!pack.findPosition(rw, rh, heur, node, sc)) return;
                Candidate c;
                c.ok = true;
                c.t = t;
                c.rot = rot;
                c.w = rw; c.h = rh;
                c.node = node;
                c.fit = sc;
                c.v = it.v;
                c.area = 1LL * rw * rh;
                if (betterCand(c, candBestType, sel, heur)) candBestType = c;
            };

            tryOri(0, it.w, it.h);
            if (allowRotate && it.w != it.h) tryOri(1, it.h, it.w);

            if (betterCand(candBestType, best, sel, heur)) best = candBestType;
        }

        if (!best.ok) break;

        Rect placed;
        FitScore placedScore;
        if (!pack.insert(best.w, best.h, heur, placed, placedScore)) {
            // Should not happen since we found position; but if it does, stop.
            break;
        }

        rr.placements.push_back({best.t, placed.x, placed.y, (allowRotate ? best.rot : 0), best.w, best.h});
        rr.profit += items[best.t].v;
        rem[best.t]--;
    }

    return rr;
}

struct Copy {
    int t = -1;
};

static RunResult run_list(const vector<ItemType>& items, int W, int H, bool allowRotate,
                          Heuristic heur, SelectMode orderKey, int maxPlacements) {
    MaxRects pack(W, H);
    vector<Copy> copies;
    copies.reserve(24000);

    for (int t = 0; t < (int)items.size(); t++) {
        int cnt = items[t].cap;
        for (int k = 0; k < cnt; k++) copies.push_back({t});
    }

    auto cmp = [&](const Copy& A, const Copy& B) {
        const auto& a = items[A.t];
        const auto& b = items[B.t];
        long long areaA = 1LL * a.w * a.h;
        long long areaB = 1LL * b.w * b.h;

        if (orderKey == SelectMode::Density) {
            __int128 lhs = (__int128)a.v * (__int128)areaB;
            __int128 rhs = (__int128)b.v * (__int128)areaA;
            if (lhs != rhs) return lhs > rhs;
            if (a.v != b.v) return a.v > b.v;
            if (areaA != areaB) return areaA > areaB;
        } else if (orderKey == SelectMode::Profit) {
            if (a.v != b.v) return a.v > b.v;
            __int128 lhs = (__int128)a.v * (__int128)areaB;
            __int128 rhs = (__int128)b.v * (__int128)areaA;
            if (lhs != rhs) return lhs > rhs;
            if (areaA != areaB) return areaA > areaB;
        } else {
            if (areaA != areaB) return areaA > areaB;
            __int128 lhs = (__int128)a.v * (__int128)areaB;
            __int128 rhs = (__int128)b.v * (__int128)areaA;
            if (lhs != rhs) return lhs > rhs;
            if (a.v != b.v) return a.v > b.v;
        }
        return A.t < B.t;
    };
    stable_sort(copies.begin(), copies.end(), cmp);

    RunResult rr;
    rr.placements.reserve(min((int)copies.size(), maxPlacements));

    int placedCnt = 0;
    for (const auto& cp : copies) {
        if (placedCnt >= maxPlacements) break;
        const auto& it = items[cp.t];

        Candidate best;
        best.ok = false;

        auto tryOri = [&](int rot, int rw, int rh) {
            Rect node;
            FitScore sc;
            if (!pack.findPosition(rw, rh, heur, node, sc)) return;
            Candidate c;
            c.ok = true;
            c.t = cp.t;
            c.rot = rot;
            c.w = rw; c.h = rh;
            c.node = node;
            c.fit = sc;
            c.v = it.v;
            c.area = 1LL * rw * rh;
            // For choosing orientation for same copy, use fit only (prefer better fit)
            if (!best.ok || betterFit(c.fit, best.fit, heur)) best = c;
        };

        tryOri(0, it.w, it.h);
        if (allowRotate && it.w != it.h) tryOri(1, it.h, it.w);

        if (!best.ok) continue;

        Rect placed;
        FitScore placedScore;
        if (!pack.insert(best.w, best.h, heur, placed, placedScore)) continue;

        rr.placements.push_back({best.t, placed.x, placed.y, (allowRotate ? best.rot : 0), best.w, best.h});
        rr.profit += it.v;
        placedCnt++;
    }

    return rr;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input, line;
    while (getline(cin, line)) input += line;

    int W = 0, H = 0;
    bool allowRotate = false;
    vector<ItemType> items;

    try {
        JsonParser p(input);
        JVal root = p.parseValue();

        auto& bin = root.obj.at("bin").obj;
        W = (int)bin.at("W").num;
        H = (int)bin.at("H").num;
        allowRotate = bin.at("allow_rotate").b;

        auto& arr = root.obj.at("items").arr;
        items.reserve(arr.size());
        for (const auto& j : arr) {
            const auto& o = j.obj;
            ItemType it;
            it.id = o.at("type").str;
            it.w = (int)o.at("w").num;
            it.h = (int)o.at("h").num;
            it.v = o.at("v").num;
            it.limit = (int)o.at("limit").num;
            items.push_back(std::move(it));
        }
    } catch (...) {
        cout << "{\"placements\":[]}\n";
        return 0;
    }

    long long binArea = 1LL * W * H;
    for (auto& it : items) {
        long long a = 1LL * it.w * it.h;
        long long areaCap = (a > 0) ? (binArea / a + 10) : 0;
        long long cap = min<long long>(it.limit, areaCap);
        cap = min<long long>(cap, 5000); // per-type safety cap
        it.cap = (int)cap;
    }

    const int MAX_PLACEMENTS = 6000;

    vector<pair<Heuristic, SelectMode>> iterativeRuns = {
        {Heuristic::ShortSideFit, SelectMode::Density},
        {Heuristic::AreaFit,      SelectMode::Density},
        {Heuristic::BottomLeft,   SelectMode::Density},
        {Heuristic::ShortSideFit, SelectMode::Profit},
        {Heuristic::AreaFit,      SelectMode::Profit},
    };

    vector<tuple<Heuristic, SelectMode>> listRuns = {
        {Heuristic::ShortSideFit, SelectMode::Density},
        {Heuristic::ShortSideFit, SelectMode::Profit},
        {Heuristic::BottomLeft,   SelectMode::Density},
        {Heuristic::AreaFit,      SelectMode::Density},
    };

    RunResult bestAll;
    bestAll.profit = -1;

    for (auto [heur, sel] : iterativeRuns) {
        RunResult rr = run_iterative(items, W, H, allowRotate, heur, sel, MAX_PLACEMENTS);
        if (rr.profit > bestAll.profit) bestAll = std::move(rr);
    }
    for (auto [heur, ord] : listRuns) {
        RunResult rr = run_list(items, W, H, allowRotate, heur, ord, MAX_PLACEMENTS);
        if (rr.profit > bestAll.profit) bestAll = std::move(rr);
    }

    cout << "{\"placements\":[";
    for (size_t i = 0; i < bestAll.placements.size(); i++) {
        const auto& pl = bestAll.placements[i];
        const auto& it = items[pl.t];
        if (i) cout << ",";
        cout << "{\"type\":\"" << jsonEscape(it.id) << "\",\"x\":" << pl.x << ",\"y\":" << pl.y
             << ",\"rot\":" << (allowRotate ? pl.rot : 0) << "}";
    }
    cout << "]}\n";
    return 0;
}
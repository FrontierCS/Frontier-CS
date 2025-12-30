#include <bits/stdc++.h>
using namespace std;

struct JValue {
    enum Type {NUL, BOOL, NUM, STR, ARR, OBJ} type = NUL;
    bool b = false;
    long long n = 0;
    string s;
    vector<JValue> a;
    map<string, JValue> o;
};

struct JsonParser {
    string_view sv;
    size_t i = 0;

    explicit JsonParser(const string &s) : sv(s), i(0) {}

    void skipWS() {
        while (i < sv.size() && (sv[i] == ' ' || sv[i] == '\n' || sv[i] == '\r' || sv[i] == '\t')) i++;
    }

    [[noreturn]] void fail(const string& msg) {
        // In contest environment, input is valid. Still, be safe: output empty placements.
        throw runtime_error("JSON parse error: " + msg);
    }

    char peek() { return i < sv.size() ? sv[i] : '\0'; }
    char get() { return i < sv.size() ? sv[i++] : '\0'; }

    bool consume(char c) {
        skipWS();
        if (peek() == c) { i++; return true; }
        return false;
    }

    void expect(char c) {
        skipWS();
        if (get() != c) fail(string("expected '") + c + "'");
    }

    string parseString() {
        skipWS();
        if (get() != '"') fail("expected string");
        string out;
        while (i < sv.size()) {
            char c = get();
            if (c == '"') break;
            if (c == '\\') {
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
                        // Parse \uXXXX; keep as UTF-8 for BMP subset.
                        unsigned code = 0;
                        for (int k = 0; k < 4; k++) {
                            char h = get();
                            code <<= 4;
                            if (h >= '0' && h <= '9') code |= (h - '0');
                            else if (h >= 'a' && h <= 'f') code |= (h - 'a' + 10);
                            else if (h >= 'A' && h <= 'F') code |= (h - 'A' + 10);
                            else fail("bad \\u escape");
                        }
                        // Encode codepoint (BMP) into UTF-8.
                        if (code <= 0x7F) out.push_back((char)code);
                        else if (code <= 0x7FF) {
                            out.push_back((char)(0xC0 | (code >> 6)));
                            out.push_back((char)(0x80 | (code & 0x3F)));
                        } else {
                            out.push_back((char)(0xE0 | (code >> 12)));
                            out.push_back((char)(0x80 | ((code >> 6) & 0x3F)));
                            out.push_back((char)(0x80 | (code & 0x3F)));
                        }
                        break;
                    }
                    default: fail("bad escape");
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
        if (peek() == '-') { neg = true; i++; }
        if (!(peek() >= '0' && peek() <= '9')) fail("expected number");
        long long val = 0;
        while (i < sv.size() && (sv[i] >= '0' && sv[i] <= '9')) {
            val = val * 10 + (sv[i] - '0');
            i++;
        }
        // No floats needed.
        return neg ? -val : val;
    }

    bool parseBool() {
        skipWS();
        if (sv.substr(i, 4) == "true") { i += 4; return true; }
        if (sv.substr(i, 5) == "false") { i += 5; return false; }
        fail("expected bool");
        return false;
    }

    JValue parseValue() {
        skipWS();
        char c = peek();
        if (c == '{') return parseObject();
        if (c == '[') return parseArray();
        if (c == '"') { JValue v; v.type = JValue::STR; v.s = parseString(); return v; }
        if (c == 't' || c == 'f') { JValue v; v.type = JValue::BOOL; v.b = parseBool(); return v; }
        if (c == 'n') {
            if (sv.substr(i, 4) == "null") { i += 4; JValue v; v.type = JValue::NUL; return v; }
            fail("expected null");
        }
        if (c == '-' || (c >= '0' && c <= '9')) { JValue v; v.type = JValue::NUM; v.n = parseNumber(); return v; }
        fail("unexpected token");
        return {};
    }

    JValue parseArray() {
        expect('[');
        JValue v; v.type = JValue::ARR;
        skipWS();
        if (consume(']')) return v;
        while (true) {
            v.a.push_back(parseValue());
            skipWS();
            if (consume(']')) break;
            expect(',');
        }
        return v;
    }

    JValue parseObject() {
        expect('{');
        JValue v; v.type = JValue::OBJ;
        skipWS();
        if (consume('}')) return v;
        while (true) {
            string key = parseString();
            expect(':');
            JValue val = parseValue();
            v.o.emplace(std::move(key), std::move(val));
            skipWS();
            if (consume('}')) break;
            expect(',');
        }
        return v;
    }

    JValue parseRoot() {
        JValue v = parseValue();
        skipWS();
        if (i != sv.size()) {
            // allow trailing whitespace only
            skipWS();
            if (i != sv.size()) fail("trailing chars");
        }
        return v;
    }
};

static string jsonEscape(const string &in) {
    string out;
    out.reserve(in.size() + 8);
    for (unsigned char c : in) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (c < 0x20) {
                    static const char *hex = "0123456789ABCDEF";
                    out += "\\u00";
                    out.push_back(hex[(c >> 4) & 0xF]);
                    out.push_back(hex[c & 0xF]);
                } else out.push_back((char)c);
        }
    }
    return out;
}

struct ItemType {
    string id;
    int w = 0, h = 0;
    long long v = 0;
    int limit = 0;
};

struct Rect {
    int x=0,y=0,w=0,h=0;
};

static inline bool rectIntersects(const Rect& a, const Rect& b) {
    return !(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y);
}
static inline bool rectContainedIn(const Rect& a, const Rect& b) {
    return a.x >= b.x && a.y >= b.y && (a.x + a.w) <= (b.x + b.w) && (a.y + a.h) <= (b.y + b.h);
}

struct Placement {
    int typeIdx;
    int x,y;
    int rot;
};

struct Candidate {
    bool ok=false;
    int x=0,y=0;
    int idx=-1;
    int w=0,h=0;
    long long p1=0,p2=0,p3=0;
};

struct MaxRectsPacker {
    int W=0, H=0;
    int mode=0; // 0: areaFit, 1: shortSideFit, 2: bottomLeft
    vector<Rect> freeRects;
    vector<Placement> placed;

    MaxRectsPacker() = default;
    MaxRectsPacker(int W_, int H_, int mode_) : W(W_), H(H_), mode(mode_) {
        freeRects.clear();
        placed.clear();
        freeRects.push_back({0,0,W,H});
    }

    static inline void scoreFor(const Rect& fr, int w, int h, int x, int y, int mode, long long &p1, long long &p2, long long &p3) {
        int dw = fr.w - w;
        int dh = fr.h - h;
        long long waste = 1LL*fr.w*fr.h - 1LL*w*h;
        int shortSide = min(dw, dh);
        int longSide = max(dw, dh);
        if (mode == 0) { // area fit
            p1 = waste; p2 = shortSide; p3 = longSide;
        } else if (mode == 1) { // short side fit
            p1 = shortSide; p2 = longSide; p3 = waste;
        } else { // bottom-left
            p1 = (long long)y; p2 = (long long)x; p3 = waste;
        }
        (void)x;
    }

    static inline bool betterCand(const Candidate& a, const Candidate& b) {
        if (!b.ok) return a.ok;
        if (!a.ok) return false;
        if (a.p1 != b.p1) return a.p1 < b.p1;
        if (a.p2 != b.p2) return a.p2 < b.p2;
        if (a.p3 != b.p3) return a.p3 < b.p3;
        if (a.y != b.y) return a.y < b.y;
        if (a.x != b.x) return a.x < b.x;
        return a.idx < b.idx;
    }

    Candidate findPosition(int w, int h) const {
        Candidate best;
        for (int i = 0; i < (int)freeRects.size(); i++) {
            const Rect& fr = freeRects[i];
            if (w > fr.w || h > fr.h) continue;

            // four corners
            int xs[4] = {fr.x, fr.x + fr.w - w, fr.x, fr.x + fr.w - w};
            int ys[4] = {fr.y, fr.y, fr.y + fr.h - h, fr.y + fr.h - h};
            for (int k = 0; k < 4; k++) {
                int x = xs[k], y = ys[k];
                if (x < fr.x || y < fr.y) continue;
                if (x + w > fr.x + fr.w) continue;
                if (y + h > fr.y + fr.h) continue;
                Candidate c;
                c.ok = true; c.x = x; c.y = y; c.idx = i; c.w = w; c.h = h;
                scoreFor(fr, w, h, x, y, mode, c.p1, c.p2, c.p3);
                if (betterCand(c, best)) best = c;
            }
        }
        return best;
    }

    static bool splitFreeRect(const Rect& fr, const Rect& pr, vector<Rect>& out) {
        if (!rectIntersects(fr, pr)) return false;

        // If horizontal overlap
        if (pr.x < fr.x + fr.w && pr.x + pr.w > fr.x) {
            if (pr.y > fr.y && pr.y < fr.y + fr.h) {
                Rect nr{fr.x, fr.y, fr.w, pr.y - fr.y};
                if (nr.w > 0 && nr.h > 0) out.push_back(nr);
            }
            if (pr.y + pr.h < fr.y + fr.h) {
                Rect nr{fr.x, pr.y + pr.h, fr.w, (fr.y + fr.h) - (pr.y + pr.h)};
                if (nr.w > 0 && nr.h > 0) out.push_back(nr);
            }
        }
        // If vertical overlap
        if (pr.y < fr.y + fr.h && pr.y + pr.h > fr.y) {
            if (pr.x > fr.x && pr.x < fr.x + fr.w) {
                Rect nr{fr.x, fr.y, pr.x - fr.x, fr.h};
                if (nr.w > 0 && nr.h > 0) out.push_back(nr);
            }
            if (pr.x + pr.w < fr.x + fr.w) {
                Rect nr{pr.x + pr.w, fr.y, (fr.x + fr.w) - (pr.x + pr.w), fr.h};
                if (nr.w > 0 && nr.h > 0) out.push_back(nr);
            }
        }
        return true;
    }

    void pruneFreeList() {
        // Remove contained rectangles (O(n^2)).
        for (int i = 0; i < (int)freeRects.size(); i++) {
            for (int j = i + 1; j < (int)freeRects.size(); j++) {
                if (rectContainedIn(freeRects[i], freeRects[j])) {
                    freeRects[i] = freeRects.back();
                    freeRects.pop_back();
                    i--;
                    break;
                }
                if (rectContainedIn(freeRects[j], freeRects[i])) {
                    freeRects[j] = freeRects.back();
                    freeRects.pop_back();
                    j--;
                }
            }
        }
    }

    bool place(const Candidate& c) {
        if (!c.ok) return false;
        Rect pr{c.x, c.y, c.w, c.h};
        vector<Rect> newFree;
        newFree.reserve(freeRects.size() + 4);

        for (const Rect& fr : freeRects) {
            if (!splitFreeRect(fr, pr, newFree)) newFree.push_back(fr);
        }
        freeRects.swap(newFree);
        pruneFreeList();
        return true;
    }
};

struct Solution {
    vector<Placement> placements;
    long long profit = 0;
};

static Solution runHeuristic(const vector<ItemType>& items, int W, int H, bool allowRotate,
                             const vector<int>& order, int mode) {
    MaxRectsPacker pack(W, H, mode);
    vector<int> used(items.size(), 0);
    Solution sol;

    for (int idx : order) {
        const auto& it = items[idx];
        int rem = it.limit - used[idx];
        if (rem <= 0) continue;

        while (rem > 0) {
            Candidate best0 = pack.findPosition(it.w, it.h);
            Candidate best1;
            bool canRot = allowRotate && (it.w != it.h);
            if (canRot) best1 = pack.findPosition(it.h, it.w);

            int chooseRot = 0;
            Candidate best = best0;
            if (canRot) {
                if (MaxRectsPacker::betterCand(best1, best0)) {
                    best = best1;
                    chooseRot = 1;
                }
            }
            if (!best.ok) break;

            bool ok = pack.place(best);
            if (!ok) break;

            pack.placed.push_back({idx, best.x, best.y, chooseRot});
            used[idx]++;
            rem--;
        }
    }

    sol.placements = pack.placed;
    long long total = 0;
    for (auto &p : sol.placements) total += items[p.typeIdx].v;
    sol.profit = total;
    return sol;
}

static vector<int> makeOrder(int M, const vector<ItemType>& items, int kind) {
    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);
    auto density = [&](int i)->long double {
        long double a = (long double)items[i].w * (long double)items[i].h;
        if (a <= 0) return 0;
        return (long double)items[i].v / a;
    };
    auto aspect = [&](int i)->long double {
        long double w = items[i].w, h = items[i].h;
        return w > h ? (w / h) : (h / w);
    };
    stable_sort(ord.begin(), ord.end(), [&](int a, int b){
        const auto& A = items[a];
        const auto& B = items[b];
        long double da = density(a), db = density(b);
        long long va = A.v, vb = B.v;
        long long aa = 1LL*A.w*A.h, ab = 1LL*B.w*B.h;
        int maxa = max(A.w, A.h), maxb = max(B.w, B.h);
        int mina = min(A.w, A.h), minb = min(B.w, B.h);
        long double aspa = aspect(a), aspb = aspect(b);

        switch (kind) {
            case 0: // density desc
                if (da != db) return da > db;
                if (va != vb) return va > vb;
                return aa > ab;
            case 1: // value desc
                if (va != vb) return va > vb;
                if (da != db) return da > db;
                return aa > ab;
            case 2: // area desc
                if (aa != ab) return aa > ab;
                if (da != db) return da > db;
                return va > vb;
            case 3: // max dimension desc then density
                if (maxa != maxb) return maxa > maxb;
                if (da != db) return da > db;
                return va > vb;
            case 4: // slender first (min dimension asc), then density desc
                if (mina != minb) return mina < minb;
                if (da != db) return da > db;
                return va > vb;
            case 5: // square-ish first (aspect close to 1), then density desc
                if (aspa != aspb) return aspa < aspb;
                if (da != db) return da > db;
                return va > vb;
            case 6: // limited high density first: density desc, limit asc
                if (da != db) return da > db;
                if (A.limit != B.limit) return A.limit < B.limit;
                return va > vb;
            default:
                if (da != db) return da > db;
                return va > vb;
        }
    });
    return ord;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input, line;
    while (std::getline(cin, line)) {
        input += line;
        input.push_back('\n');
    }

    int W = 0, H = 0;
    bool allowRotate = false;
    vector<ItemType> items;

    try {
        JsonParser p(input);
        JValue root = p.parseRoot();
        if (root.type != JValue::OBJ) throw runtime_error("root not object");
        auto& ro = root.o;

        auto itBin = ro.find("bin");
        auto itItems = ro.find("items");
        if (itBin == ro.end() || itItems == ro.end()) throw runtime_error("missing keys");

        const JValue& bin = itBin->second;
        if (bin.type != JValue::OBJ) throw runtime_error("bin not object");
        const auto& bo = bin.o;
        W = (int)bo.at("W").n;
        H = (int)bo.at("H").n;
        allowRotate = bo.at("allow_rotate").b;

        const JValue& arr = itItems->second;
        if (arr.type != JValue::ARR) throw runtime_error("items not array");
        items.reserve(arr.a.size());
        for (const auto& iv : arr.a) {
            if (iv.type != JValue::OBJ) throw runtime_error("item not object");
            const auto& o = iv.o;
            ItemType t;
            t.id = o.at("type").s;
            t.w = (int)o.at("w").n;
            t.h = (int)o.at("h").n;
            t.v = o.at("v").n;
            t.limit = (int)o.at("limit").n;
            items.push_back(std::move(t));
        }
    } catch (...) {
        cout << "{\"placements\":[]}\n";
        return 0;
    }

    int M = (int)items.size();
    Solution bestSol;
    bestSol.profit = -1;

    vector<int> kinds = {0, 6, 1, 3, 2, 5, 4};
    vector<int> modes = {0, 1, 2};

    for (int kind : kinds) {
        vector<int> ord = makeOrder(M, items, kind);
        for (int mode : modes) {
            Solution sol = runHeuristic(items, W, H, allowRotate, ord, mode);
            if (sol.profit > bestSol.profit) bestSol = std::move(sol);
        }
    }

    // Output JSON
    cout << "{\"placements\":[";
    for (size_t i = 0; i < bestSol.placements.size(); i++) {
        const auto& p = bestSol.placements[i];
        const string& id = items[p.typeIdx].id;
        int rot = allowRotate ? p.rot : 0;
        if (i) cout << ",";
        cout << "{\"type\":\"" << jsonEscape(id) << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << rot << "}";
    }
    cout << "]}\n";
    return 0;
}
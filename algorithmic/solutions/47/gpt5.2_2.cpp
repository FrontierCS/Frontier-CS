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

struct JSONParser {
    string str;
    size_t i = 0;

    JSONParser(string s): str(std::move(s)) {}

    void skip() {
        while (i < str.size() && (unsigned char)str[i] <= 32) i++;
    }

    [[noreturn]] void fail(const string& msg) {
        throw runtime_error("JSON parse error: " + msg);
    }

    bool consume(char c) {
        skip();
        if (i < str.size() && str[i] == c) { i++; return true; }
        return false;
    }

    void expect(char c) {
        skip();
        if (i >= str.size() || str[i] != c) fail(string("expected '") + c + "'");
        i++;
    }

    string parseString() {
        skip();
        if (i >= str.size() || str[i] != '"') fail("expected string");
        i++;
        string out;
        while (i < str.size()) {
            char c = str[i++];
            if (c == '"') break;
            if (c == '\\') {
                if (i >= str.size()) fail("bad escape");
                char e = str[i++];
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
                        if (i + 4 > str.size()) fail("bad unicode escape");
                        int code = 0;
                        for (int k = 0; k < 4; k++) {
                            char h = str[i++];
                            code <<= 4;
                            if (h >= '0' && h <= '9') code += h - '0';
                            else if (h >= 'a' && h <= 'f') code += h - 'a' + 10;
                            else if (h >= 'A' && h <= 'F') code += h - 'A' + 10;
                            else fail("bad unicode hex");
                        }
                        // Only handle BMP basic ASCII range safely.
                        if (code <= 0x7F) out.push_back(char(code));
                        else if (code <= 0x7FF) {
                            out.push_back(char(0xC0 | ((code >> 6) & 0x1F)));
                            out.push_back(char(0x80 | (code & 0x3F)));
                        } else {
                            out.push_back(char(0xE0 | ((code >> 12) & 0x0F)));
                            out.push_back(char(0x80 | ((code >> 6) & 0x3F)));
                            out.push_back(char(0x80 | (code & 0x3F)));
                        }
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
        skip();
        if (i >= str.size()) fail("expected number");
        bool neg = false;
        if (str[i] == '-') { neg = true; i++; }
        if (i >= str.size() || !isdigit((unsigned char)str[i])) fail("bad number");
        long long val = 0;
        while (i < str.size() && isdigit((unsigned char)str[i])) {
            int d = str[i++] - '0';
            if (val > (LLONG_MAX - d) / 10) fail("number overflow");
            val = val * 10 + d;
        }
        return neg ? -val : val;
    }

    JValue parseValue() {
        skip();
        if (i >= str.size()) fail("unexpected end");

        char c = str[i];
        if (c == '{') return parseObject();
        if (c == '[') return parseArray();
        if (c == '"') {
            JValue v; v.type = JValue::STR; v.s = parseString(); return v;
        }
        if (c == '-' || isdigit((unsigned char)c)) {
            JValue v; v.type = JValue::NUM; v.n = parseNumber(); return v;
        }
        if (str.compare(i, 4, "true") == 0) {
            i += 4;
            JValue v; v.type = JValue::BOOL; v.b = true; return v;
        }
        if (str.compare(i, 5, "false") == 0) {
            i += 5;
            JValue v; v.type = JValue::BOOL; v.b = false; return v;
        }
        if (str.compare(i, 4, "null") == 0) {
            i += 4;
            JValue v; v.type = JValue::NUL; return v;
        }
        fail("unexpected token");
        return {};
    }

    JValue parseArray() {
        expect('[');
        JValue v; v.type = JValue::ARR;
        skip();
        if (consume(']')) return v;
        while (true) {
            v.a.push_back(parseValue());
            skip();
            if (consume(']')) break;
            expect(',');
        }
        return v;
    }

    JValue parseObject() {
        expect('{');
        JValue v; v.type = JValue::OBJ;
        skip();
        if (consume('}')) return v;
        while (true) {
            string key = parseString();
            skip();
            expect(':');
            JValue val = parseValue();
            v.o.emplace(std::move(key), std::move(val));
            skip();
            if (consume('}')) break;
            expect(',');
        }
        return v;
    }

    JValue parse() {
        JValue root = parseValue();
        skip();
        if (i != str.size()) fail("trailing characters");
        return root;
    }
};

static string jsonEscape(const string& s) {
    string out;
    out.reserve(s.size() + 8);
    for (unsigned char uc : s) {
        char c = (char)uc;
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (uc < 0x20) {
                    static const char* hex = "0123456789ABCDEF";
                    out += "\\u00";
                    out.push_back(hex[(uc >> 4) & 0xF]);
                    out.push_back(hex[uc & 0xF]);
                } else {
                    out.push_back(c);
                }
        }
    }
    return out;
}

struct ItemType {
    string id;
    int w, h;
    long long v;
    int limit;
};

struct Variant {
    int t = -1;
    int rot = 0;
    int w = 0, h = 0;
    long long v = 0;
    long long area = 0;
};

struct Placement {
    int t = -1;
    int x = 0, y = 0;
    int rot = 0;
};

struct Node {
    int x, y, w;
};

enum class PlaceHeu { MIN_TOP, MIN_Y, MIN_TOP_MIN_RISE };

static inline bool betterKey_tuple(long long a1,long long b1,long long c1,long long a2,long long b2,long long c2){
    if (a1 != a2) return a1 < a2;
    if (b1 != b2) return b1 < b2;
    return c1 < c2;
}

struct PackResult {
    long long profit = 0;
    vector<Placement> plc;
};

struct SkylinePacker {
    int W, H;
    vector<ItemType>* types = nullptr;
    vector<Variant>* variants = nullptr;
    vector<int> rem;
    vector<Node> sky;
    vector<Placement> out;
    long long profit = 0;
    int maxPlacements = 6000;

    SkylinePacker(int W_, int H_, vector<ItemType>& types_, vector<Variant>& vars_)
        : W(W_), H(H_), types(&types_), variants(&vars_) {
        rem.assign(types_.size(), 0);
        for (size_t i = 0; i < types_.size(); i++) rem[i] = types_[i].limit;
        sky.clear();
        sky.push_back({0, 0, W});
    }

    bool findPosForVariant(const Variant& vr, PlaceHeu heu, int& bestI, int& bestX, int& bestY) {
        bestI = -1; bestX = bestY = 0;
        int rw = vr.w, rh = vr.h;
        long long bestA = LLONG_MAX, bestB = LLONG_MAX, bestC = LLONG_MAX;
        for (int i = 0; i < (int)sky.size(); i++) {
            int x = sky[i].x;
            if (x + rw > W) continue;

            int width = rw;
            int j = i;
            int maxy = 0;
            while (width > 0) {
                if (j >= (int)sky.size()) { maxy = INT_MAX; break; }
                maxy = max(maxy, sky[j].y);
                if (maxy + rh > H) { maxy = INT_MAX; break; }
                width -= sky[j].w;
                j++;
            }
            if (maxy == INT_MAX) continue;
            int y = maxy;
            int top = y + rh;

            long long a, b, c;
            if (heu == PlaceHeu::MIN_TOP) {
                a = top; b = y; c = x;
            } else if (heu == PlaceHeu::MIN_Y) {
                a = y; b = top; c = x;
            } else { // MIN_TOP_MIN_RISE
                a = top;
                b = (long long)(y - sky[i].y);
                c = x;
            }

            if (bestI == -1 || betterKey_tuple(a,b,c, bestA,bestB,bestC)) {
                bestI = i; bestX = x; bestY = y;
                bestA = a; bestB = b; bestC = c;
            }
        }
        return bestI != -1;
    }

    void mergeSky() {
        for (int i = 0; i + 1 < (int)sky.size(); ) {
            if (sky[i].y == sky[i+1].y) {
                sky[i].w += sky[i+1].w;
                sky.erase(sky.begin() + (i+1));
            } else i++;
        }
    }

    void addRect(int i, int x, int y, int rw, int rh) {
        Node newNode { x, y + rh, rw };
        sky.insert(sky.begin() + i, newNode);

        int end = x + rw;
        for (int k = i + 1; k < (int)sky.size(); ) {
            if (sky[k].x < end) {
                int overlap = end - sky[k].x;
                if (overlap >= sky[k].w) {
                    sky.erase(sky.begin() + k);
                    continue;
                } else {
                    sky[k].x += overlap;
                    sky[k].w -= overlap;
                    break;
                }
            } else break;
        }

        // Fix x continuity potentially (defensive)
        for (int k = 0; k < (int)sky.size(); k++) {
            if (k == 0) sky[k].x = 0;
            else sky[k].x = sky[k-1].x + sky[k-1].w;
        }
        if (!sky.empty()) sky.back().w = W - sky.back().x;

        mergeSky();
    }

    bool placeOnce(const Variant& vr, PlaceHeu heu) {
        if (rem[vr.t] <= 0) return false;
        if ((int)out.size() >= maxPlacements) return false;

        int bi, bx, by;
        if (!findPosForVariant(vr, heu, bi, bx, by)) return false;

        // Place
        out.push_back({vr.t, bx, by, vr.rot});
        profit += (*types)[vr.t].v;
        rem[vr.t]--;
        addRect(bi, bx, by, vr.w, vr.h);
        return true;
    }

    PackResult run(const vector<int>& order, PlaceHeu heu, bool doFillPass) {
        for (int idx : order) {
            const Variant& vr = (*variants)[idx];
            while (placeOnce(vr, heu)) {}
        }

        if (doFillPass) {
            // density-based fill: sort by value/area decreasing, tie by area desc.
            vector<int> ord2(variants->size());
            iota(ord2.begin(), ord2.end(), 0);
            stable_sort(ord2.begin(), ord2.end(), [&](int a, int b){
                const Variant& A = (*variants)[a];
                const Variant& B = (*variants)[b];
                __int128 lhs = (__int128)A.v * (__int128)B.area;
                __int128 rhs = (__int128)B.v * (__int128)A.area;
                if (lhs != rhs) return lhs > rhs;
                if (A.area != B.area) return A.area > B.area;
                if (A.h != B.h) return A.h > B.h;
                if (A.w != B.w) return A.w > B.w;
                return A.rot < B.rot;
            });

            bool improved = true;
            int iter = 0;
            while (improved && iter < 30) {
                improved = false;
                iter++;
                for (int idx : ord2) {
                    const Variant& vr = (*variants)[idx];
                    bool any = false;
                    while (placeOnce(vr, heu)) { improved = true; any = true; }
                    (void)any;
                }
            }
        }

        PackResult res;
        res.profit = profit;
        res.plc = out;
        return res;
    }
};

struct ShelfPacker {
    int W, H;
    vector<ItemType>* types = nullptr;
    vector<Variant>* variants = nullptr;
    vector<int> rem;
    vector<Placement> out;
    long long profit = 0;
    int maxPlacements = 6000;

    ShelfPacker(int W_, int H_, vector<ItemType>& types_, vector<Variant>& vars_)
        : W(W_), H(H_), types(&types_), variants(&vars_) {
        rem.assign(types_.size(), 0);
        for (size_t i = 0; i < types_.size(); i++) rem[i] = types_[i].limit;
    }

    PackResult run(const vector<int>& order, bool doFillPass) {
        int x = 0, y = 0, shelfH = 0;

        auto canPlace = [&](const Variant& vr)->bool{
            if (rem[vr.t] <= 0) return false;
            if ((int)out.size() >= maxPlacements) return false;
            int newShelfH = max(shelfH, vr.h);
            if (x + vr.w > W) return false;
            if (y + newShelfH > H) return false;
            return true;
        };

        auto place = [&](const Variant& vr){
            int newShelfH = max(shelfH, vr.h);
            shelfH = newShelfH;
            out.push_back({vr.t, x, y, vr.rot});
            profit += (*types)[vr.t].v;
            rem[vr.t]--;
            x += vr.w;
        };

        int guard = 0;
        while (y < H && (int)out.size() < maxPlacements && guard++ < 1000000) {
            bool placedAny = false;
            for (int idx : order) {
                const Variant& vr = (*variants)[idx];
                if (canPlace(vr)) {
                    place(vr);
                    placedAny = true;
                    break;
                }
            }
            if (placedAny) continue;

            if (shelfH == 0) break;
            y += shelfH;
            x = 0;
            shelfH = 0;
        }

        if (doFillPass) {
            // Simple second pass: try again from start while possible in existing shelves by restarting packing.
            // (Not feasible without repacking; skip for shelves.)
        }

        PackResult res;
        res.profit = profit;
        res.plc = out;
        return res;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    if (input.empty()) {
        cout << "{\"placements\":[]}";
        return 0;
    }

    int W = 0, H = 0;
    bool allow_rotate = false;
    vector<ItemType> types;

    try {
        JSONParser p(input);
        JValue root = p.parse();
        if (root.type != JValue::OBJ) throw runtime_error("root not object");

        auto itBin = root.o.find("bin");
        auto itItems = root.o.find("items");
        if (itBin == root.o.end() || itItems == root.o.end()) throw runtime_error("missing bin/items");

        const JValue& bin = itBin->second;
        if (bin.type != JValue::OBJ) throw runtime_error("bin not object");
        const auto& bo = bin.o;

        auto getNum = [&](const map<string,JValue>& o, const string& k)->long long{
            auto it = o.find(k);
            if (it == o.end() || it->second.type != JValue::NUM) throw runtime_error("missing/invalid number key: " + k);
            return it->second.n;
        };
        auto getBool = [&](const map<string,JValue>& o, const string& k)->bool{
            auto it = o.find(k);
            if (it == o.end() || it->second.type != JValue::BOOL) throw runtime_error("missing/invalid bool key: " + k);
            return it->second.b;
        };

        W = (int)getNum(bo, "W");
        H = (int)getNum(bo, "H");
        allow_rotate = getBool(bo, "allow_rotate");

        const JValue& items = itItems->second;
        if (items.type != JValue::ARR) throw runtime_error("items not array");

        for (const JValue& iv : items.a) {
            if (iv.type != JValue::OBJ) throw runtime_error("item not object");
            const auto& io = iv.o;

            auto itType = io.find("type");
            if (itType == io.end() || itType->second.type != JValue::STR) throw runtime_error("missing/invalid item.type");

            ItemType t;
            t.id = itType->second.s;
            t.w = (int)getNum(io, "w");
            t.h = (int)getNum(io, "h");
            t.v = getNum(io, "v");
            t.limit = (int)getNum(io, "limit");
            types.push_back(std::move(t));
        }
    } catch (...) {
        // Fallback: output empty placements if parsing fails.
        cout << "{\"placements\":[]}";
        return 0;
    }

    if (W <= 0 || H <= 0 || types.empty()) {
        cout << "{\"placements\":[]}";
        return 0;
    }

    vector<Variant> vars;
    vars.reserve(types.size() * 2);
    for (int t = 0; t < (int)types.size(); t++) {
        Variant v0;
        v0.t = t; v0.rot = 0; v0.w = types[t].w; v0.h = types[t].h; v0.v = types[t].v;
        v0.area = 1LL * v0.w * v0.h;
        vars.push_back(v0);

        if (allow_rotate && types[t].w != types[t].h) {
            Variant v1;
            v1.t = t; v1.rot = 1; v1.w = types[t].h; v1.h = types[t].w; v1.v = types[t].v;
            v1.area = 1LL * v1.w * v1.h;
            vars.push_back(v1);
        }
    }

    auto makeOrder = [&](auto comp) {
        vector<int> ord(vars.size());
        iota(ord.begin(), ord.end(), 0);
        stable_sort(ord.begin(), ord.end(), comp);
        return ord;
    };

    vector<pair<string, PackResult>> candidates;
    candidates.reserve(32);

    auto start = chrono::steady_clock::now();
    auto timeLeftOk = [&]()->bool{
        auto now = chrono::steady_clock::now();
        double sec = chrono::duration<double>(now - start).count();
        return sec < 0.92;
    };

    // Orders
    auto ordDensity = makeOrder([&](int a, int b){
        const Variant& A = vars[a];
        const Variant& B = vars[b];
        __int128 lhs = (__int128)A.v * (__int128)B.area;
        __int128 rhs = (__int128)B.v * (__int128)A.area;
        if (lhs != rhs) return lhs > rhs;
        if (A.area != B.area) return A.area > B.area;
        if (A.h != B.h) return A.h > B.h;
        if (A.w != B.w) return A.w > B.w;
        return A.rot < B.rot;
    });
    auto ordProfit = makeOrder([&](int a, int b){
        const Variant& A = vars[a];
        const Variant& B = vars[b];
        if (A.v != B.v) return A.v > B.v;
        if (A.area != B.area) return A.area > B.area;
        if (A.h != B.h) return A.h > B.h;
        if (A.w != B.w) return A.w > B.w;
        return A.rot < B.rot;
    });
    auto ordArea = makeOrder([&](int a, int b){
        const Variant& A = vars[a];
        const Variant& B = vars[b];
        if (A.area != B.area) return A.area > B.area;
        if (A.v != B.v) return A.v > B.v;
        if (A.h != B.h) return A.h > B.h;
        if (A.w != B.w) return A.w > B.w;
        return A.rot < B.rot;
    });
    auto ordHeight = makeOrder([&](int a, int b){
        const Variant& A = vars[a];
        const Variant& B = vars[b];
        if (A.h != B.h) return A.h > B.h;
        if (A.v != B.v) return A.v > B.v;
        if (A.area != B.area) return A.area > B.area;
        if (A.w != B.w) return A.w > B.w;
        return A.rot < B.rot;
    });
    auto ordWidth = makeOrder([&](int a, int b){
        const Variant& A = vars[a];
        const Variant& B = vars[b];
        if (A.w != B.w) return A.w > B.w;
        if (A.v != B.v) return A.v > B.v;
        if (A.area != B.area) return A.area > B.area;
        if (A.h != B.h) return A.h > B.h;
        return A.rot < B.rot;
    });
    auto ordShortSide = makeOrder([&](int a, int b){
        const Variant& A = vars[a];
        const Variant& B = vars[b];
        int as = min(A.w, A.h), bs = min(B.w, B.h);
        if (as != bs) return as < bs;
        __int128 lhs = (__int128)A.v * (__int128)B.area;
        __int128 rhs = (__int128)B.v * (__int128)A.area;
        if (lhs != rhs) return lhs > rhs;
        if (A.area != B.area) return A.area > B.area;
        return A.rot < B.rot;
    });

    auto trySky = [&](const vector<int>& order, PlaceHeu heu, bool fill){
        if (!timeLeftOk()) return;
        SkylinePacker pk(W, H, types, vars);
        auto res = pk.run(order, heu, fill);
        candidates.push_back({"sky", std::move(res)});
    };

    auto tryShelf = [&](const vector<int>& order, bool fill){
        if (!timeLeftOk()) return;
        ShelfPacker pk(W, H, types, vars);
        auto res = pk.run(order, fill);
        candidates.push_back({"shelf", std::move(res)});
    };

    trySky(ordDensity, PlaceHeu::MIN_TOP, true);
    trySky(ordDensity, PlaceHeu::MIN_Y, true);
    trySky(ordDensity, PlaceHeu::MIN_TOP_MIN_RISE, true);
    trySky(ordProfit, PlaceHeu::MIN_TOP, true);
    trySky(ordArea, PlaceHeu::MIN_TOP, true);
    trySky(ordHeight, PlaceHeu::MIN_TOP, true);
    trySky(ordWidth, PlaceHeu::MIN_TOP, true);
    trySky(ordShortSide, PlaceHeu::MIN_TOP, true);

    tryShelf(ordDensity, false);
    tryShelf(ordHeight, false);
    tryShelf(ordArea, false);

    // A couple randomized variant orders for diversification
    std::mt19937_64 rng(1234567);
    for (int rep = 0; rep < 4 && timeLeftOk(); rep++) {
        vector<int> ord = ordDensity;
        // shuffle within small windows
        for (int i = 0; i + 4 < (int)ord.size(); i += 5) {
            int r = (int)(rng() % 5);
            rotate(ord.begin() + i, ord.begin() + i + r, ord.begin() + i + min(i + 5, (int)ord.size()));
        }
        trySky(ord, (rep % 2 == 0 ? PlaceHeu::MIN_TOP : PlaceHeu::MIN_TOP_MIN_RISE), true);
    }

    PackResult best;
    best.profit = -1;
    for (auto& c : candidates) {
        if (c.second.profit > best.profit) best = std::move(c.second);
    }
    if (best.profit < 0) {
        best.profit = 0;
        best.plc.clear();
    }

    // Output
    cout << "{\"placements\":[";
    for (size_t i = 0; i < best.plc.size(); i++) {
        const Placement& p = best.plc[i];
        const string& tid = types[p.t].id;
        if (i) cout << ",";
        cout << "{\"type\":\"" << jsonEscape(tid) << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << (allow_rotate ? p.rot : 0) << "}";
    }
    cout << "]}";
    return 0;
}
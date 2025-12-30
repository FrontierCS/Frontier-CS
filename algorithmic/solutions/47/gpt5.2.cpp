#include <bits/stdc++.h>
using namespace std;

struct JValue {
    enum Type { NUL, BOOL, NUMBER, STRING, ARRAY, OBJECT } type = NUL;
    long long num = 0;
    bool b = false;
    string str;
    vector<JValue> arr;
    vector<pair<string, JValue>> obj;

    const JValue* get(const string& k) const {
        for (const auto& kv : obj) if (kv.first == k) return &kv.second;
        return nullptr;
    }
};

struct JsonParser {
    string s;
    size_t i = 0;

    explicit JsonParser(string in) : s(std::move(in)) {}

    void skip() {
        while (i < s.size() && (unsigned char)s[i] <= 32) i++;
    }

    bool consume(char c) {
        skip();
        if (i < s.size() && s[i] == c) { i++; return true; }
        return false;
    }

    char peek() {
        skip();
        return (i < s.size() ? s[i] : '\0');
    }

    static int hexVal(char c) {
        if ('0' <= c && c <= '9') return c - '0';
        if ('a' <= c && c <= 'f') return 10 + (c - 'a');
        if ('A' <= c && c <= 'F') return 10 + (c - 'A');
        return -1;
    }

    string parseString() {
        skip();
        if (i >= s.size() || s[i] != '"') return {};
        i++;
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
                        if (i + 4 <= s.size()) {
                            int code = 0;
                            for (int k = 0; k < 4; k++) {
                                int hv = hexVal(s[i + k]);
                                if (hv < 0) { code = -1; break; }
                                code = (code << 4) | hv;
                            }
                            i += 4;
                            if (code >= 0 && code <= 0x7F) out.push_back((char)code);
                            else out.push_back('?');
                        } else {
                            out.push_back('?');
                        }
                        break;
                    }
                    default:
                        out.push_back(e);
                        break;
                }
            } else {
                out.push_back(c);
            }
        }
        return out;
    }

    long long parseNumber() {
        skip();
        bool neg = false;
        if (i < s.size() && s[i] == '-') { neg = true; i++; }
        long long x = 0;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            x = x * 10 + (s[i] - '0');
            i++;
        }
        return neg ? -x : x;
    }

    bool matchLiteral(const string& lit) {
        skip();
        if (s.compare(i, lit.size(), lit) == 0) { i += lit.size(); return true; }
        return false;
    }

    JValue parseValue() {
        skip();
        char c = peek();
        if (c == '{') return parseObject();
        if (c == '[') return parseArray();
        if (c == '"') {
            JValue v; v.type = JValue::STRING; v.str = parseString(); return v;
        }
        if (c == '-' || isdigit((unsigned char)c)) {
            JValue v; v.type = JValue::NUMBER; v.num = parseNumber(); return v;
        }
        if (c == 't') {
            matchLiteral("true");
            JValue v; v.type = JValue::BOOL; v.b = true; return v;
        }
        if (c == 'f') {
            matchLiteral("false");
            JValue v; v.type = JValue::BOOL; v.b = false; return v;
        }
        if (c == 'n') {
            matchLiteral("null");
            JValue v; v.type = JValue::NUL; return v;
        }
        JValue v; v.type = JValue::NUL; return v;
    }

    JValue parseArray() {
        JValue v; v.type = JValue::ARRAY;
        consume('[');
        skip();
        if (consume(']')) return v;
        while (true) {
            v.arr.push_back(parseValue());
            skip();
            if (consume(']')) break;
            consume(',');
        }
        return v;
    }

    JValue parseObject() {
        JValue v; v.type = JValue::OBJECT;
        consume('{');
        skip();
        if (consume('}')) return v;
        while (true) {
            string key = parseString();
            consume(':');
            JValue val = parseValue();
            v.obj.push_back({std::move(key), std::move(val)});
            skip();
            if (consume('}')) break;
            consume(',');
        }
        return v;
    }
};

static string jsonEscape(const string& in) {
    string out;
    out.reserve(in.size() + 8);
    for (char c : in) {
        switch (c) {
            case '\\': out += "\\\\"; break;
            case '"': out += "\\\""; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if ((unsigned char)c < 32) {
                    char buf[7];
                    snprintf(buf, sizeof(buf), "\\u%04x", (unsigned char)c);
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
};

struct Variant {
    int typeIdx = -1;
    int w = 0, h = 0;
    int rot = 0;
};

struct Rect {
    int x=0, y=0, w=0, h=0;
};

static inline bool intersects(const Rect& a, const Rect& b) {
    if (a.x >= b.x + b.w) return false;
    if (a.x + a.w <= b.x) return false;
    if (a.y >= b.y + b.h) return false;
    if (a.y + a.h <= b.y) return false;
    return true;
}

static inline bool containsRect(const Rect& a, const Rect& b) {
    return a.x <= b.x && a.y <= b.y && a.x + a.w >= b.x + b.w && a.y + a.h >= b.y + b.h;
}

struct Placement {
    string type;
    int x=0, y=0, rot=0;
    int w=0, h=0;
    long long v=0;
};

struct MaxRectsPacker {
    int W, H;
    vector<Rect> freeRects;

    explicit MaxRectsPacker(int W_, int H_) : W(W_), H(H_) {
        freeRects.push_back({0,0,W,H});
    }

    void prune(int maxFree = 2500) {
        // remove invalid
        vector<Rect> r;
        r.reserve(freeRects.size());
        for (auto &fr : freeRects) if (fr.w > 0 && fr.h > 0) r.push_back(fr);
        freeRects.swap(r);

        int n = (int)freeRects.size();
        vector<char> rem(n, 0);
        for (int i = 0; i < n; i++) {
            if (rem[i]) continue;
            for (int j = i + 1; j < n; j++) {
                if (rem[j]) continue;
                if (containsRect(freeRects[i], freeRects[j])) {
                    rem[j] = 1;
                } else if (containsRect(freeRects[j], freeRects[i])) {
                    rem[i] = 1;
                    break;
                }
            }
        }
        vector<Rect> out;
        out.reserve(n);
        for (int i = 0; i < n; i++) if (!rem[i]) out.push_back(freeRects[i]);
        freeRects.swap(out);

        // dedup
        sort(freeRects.begin(), freeRects.end(), [](const Rect& a, const Rect& b){
            if (a.x != b.x) return a.x < b.x;
            if (a.y != b.y) return a.y < b.y;
            if (a.w != b.w) return a.w < b.w;
            return a.h < b.h;
        });
        freeRects.erase(unique(freeRects.begin(), freeRects.end(), [](const Rect& a, const Rect& b){
            return a.x==b.x && a.y==b.y && a.w==b.w && a.h==b.h;
        }), freeRects.end());

        if ((int)freeRects.size() > maxFree) {
            // keep largest areas
            nth_element(freeRects.begin(), freeRects.begin() + maxFree, freeRects.end(),
                        [](const Rect& a, const Rect& b){
                            long long aa = 1LL*a.w*a.h;
                            long long bb = 1LL*b.w*b.h;
                            if (aa != bb) return aa > bb;
                            if (a.y != b.y) return a.y < b.y;
                            return a.x < b.x;
                        });
            freeRects.resize(maxFree);
        }
    }

    void placeRect(const Rect& placed) {
        vector<Rect> newFree;
        newFree.reserve(freeRects.size() * 2 + 8);
        for (const Rect& fr : freeRects) {
            if (!intersects(fr, placed)) {
                newFree.push_back(fr);
                continue;
            }
            // Split fr by placed
            int frRight = fr.x + fr.w;
            int frTop = fr.y + fr.h;
            int prRight = placed.x + placed.w;
            int prTop = placed.y + placed.h;

            if (placed.x > fr.x) {
                Rect left{fr.x, fr.y, placed.x - fr.x, fr.h};
                if (left.w > 0 && left.h > 0) newFree.push_back(left);
            }
            if (prRight < frRight) {
                Rect right{prRight, fr.y, frRight - prRight, fr.h};
                if (right.w > 0 && right.h > 0) newFree.push_back(right);
            }
            if (placed.y > fr.y) {
                Rect bottom{fr.x, fr.y, fr.w, placed.y - fr.y};
                if (bottom.w > 0 && bottom.h > 0) newFree.push_back(bottom);
            }
            if (prTop < frTop) {
                Rect top{fr.x, prTop, fr.w, frTop - prTop};
                if (top.w > 0 && top.h > 0) newFree.push_back(top);
            }
        }
        freeRects.swap(newFree);
        prune();
    }
};

struct Result {
    vector<Placement> placements;
    long long profit = 0;
};

struct Candidate {
    bool ok = false;
    long double score = -1e300L;
    int typeIdx = -1;
    int rot = 0;
    int x=0, y=0, w=0, h=0;
    long long v=0;
    Rect placedRect;
};

static inline long double scoreCandidate(
    int mode,
    const Rect& fr,
    int px, int py,
    int w, int h,
    long long v
) {
    int dx = fr.w - w;
    int dy = fr.h - h;
    int shortSide = min(dx, dy);
    int longSide = max(dx, dy);
    long long frArea = 1LL * fr.w * fr.h;
    long long area = 1LL * w * h;
    long long waste = frArea - area;

    if (mode == 0) {
        long double density = (area > 0) ? ((long double)v / (long double)area) : 0.0L;
        long double sc = density * 1e12L;
        sc -= (long double)shortSide * 1e6L;
        sc -= (long double)longSide * 1e3L;
        sc += (long double)area; // mild
        sc -= (long double)py * 50.0L + (long double)px * 0.1L;
        if (dx == 0 || dy == 0) sc += 5e5L; // edge fit bonus
        if (waste == 0) sc += 5e6L; // perfect fill
        return sc;
    } else {
        long double sc = (long double)v * 1e6L;
        sc -= (long double)waste * 2e3L;
        sc -= (long double)shortSide * 5e3L;
        sc -= (long double)longSide * 5.0L;
        sc -= (long double)py * 2e4L + (long double)px * 10.0L;
        if (waste == 0) sc += 1e10L;
        return sc;
    }
}

static Result runGreedyMaxRects(
    int W, int H,
    const vector<ItemType>& items,
    const vector<vector<Variant>>& variantsByType,
    int mode,
    int maxPlacements,
    double timeLimitSec
) {
    using Clock = chrono::steady_clock;
    auto start = Clock::now();

    int M = (int)items.size();
    vector<int> used(M, 0);

    MaxRectsPacker packer(W, H);
    Result res;

    auto elapsedSec = [&]() -> double {
        return chrono::duration<double>(Clock::now() - start).count();
    };

    for (int iter = 0; iter < maxPlacements; iter++) {
        if ((iter & 31) == 0 && elapsedSec() > timeLimitSec) break;

        Candidate best;

        // Early exit if no free rectangles
        if (packer.freeRects.empty()) break;

        // Scan all free rectangles and all type variants
        for (const Rect& fr : packer.freeRects) {
            // If very late in time, reduce search slightly
            // (still always feasible; just may stop earlier)
            if ((iter & 63) == 0 && elapsedSec() > timeLimitSec) break;

            for (int t = 0; t < M; t++) {
                if (used[t] >= items[t].limit) continue;
                if (items[t].v <= 0) continue;

                const auto& vars = variantsByType[t];
                for (const Variant& var : vars) {
                    int w = var.w, h = var.h;
                    if (w > fr.w || h > fr.h) continue;

                    int xs[4] = {fr.x, fr.x + (fr.w - w), fr.x, fr.x + (fr.w - w)};
                    int ys[4] = {fr.y, fr.y, fr.y + (fr.h - h), fr.y + (fr.h - h)};

                    for (int k = 0; k < 4; k++) {
                        int px = xs[k], py = ys[k];
                        // Ensure inside free rect
                        if (px < fr.x || py < fr.y) continue;
                        if (px + w > fr.x + fr.w) continue;
                        if (py + h > fr.y + fr.h) continue;

                        long double sc = scoreCandidate(mode, fr, px, py, w, h, items[t].v);
                        if (!best.ok || sc > best.score) {
                            best.ok = true;
                            best.score = sc;
                            best.typeIdx = t;
                            best.rot = var.rot;
                            best.x = px; best.y = py;
                            best.w = w; best.h = h;
                            best.v = items[t].v;
                            best.placedRect = {px, py, w, h};
                        }
                    }
                }
            }
        }

        if (!best.ok) break;

        // Apply placement
        used[best.typeIdx]++;
        res.profit += best.v;
        res.placements.push_back({items[best.typeIdx].id, best.x, best.y, best.rot, best.w, best.h, best.v});
        packer.placeRect(best.placedRect);
    }

    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    JsonParser parser(input);
    JValue root = parser.parseValue();

    const JValue* bin = root.get("bin");
    const JValue* itemsV = root.get("items");
    int W = 0, H = 0;
    bool allow_rotate = false;

    if (bin && bin->type == JValue::OBJECT) {
        const JValue* Wv = bin->get("W");
        const JValue* Hv = bin->get("H");
        const JValue* rv = bin->get("allow_rotate");
        if (Wv && Wv->type == JValue::NUMBER) W = (int)Wv->num;
        if (Hv && Hv->type == JValue::NUMBER) H = (int)Hv->num;
        if (rv && rv->type == JValue::BOOL) allow_rotate = rv->b;
    }

    vector<ItemType> items;
    if (itemsV && itemsV->type == JValue::ARRAY) {
        for (const auto& it : itemsV->arr) {
            if (it.type != JValue::OBJECT) continue;
            ItemType t;
            const JValue* tv = it.get("type");
            const JValue* wv = it.get("w");
            const JValue* hv = it.get("h");
            const JValue* vv = it.get("v");
            const JValue* lv = it.get("limit");
            if (tv && tv->type == JValue::STRING) t.id = tv->str;
            if (wv && wv->type == JValue::NUMBER) t.w = (int)wv->num;
            if (hv && hv->type == JValue::NUMBER) t.h = (int)hv->num;
            if (vv && vv->type == JValue::NUMBER) t.v = vv->num;
            if (lv && lv->type == JValue::NUMBER) t.limit = (int)lv->num;
            items.push_back(std::move(t));
        }
    }

    int M = (int)items.size();
    vector<vector<Variant>> variantsByType(M);
    for (int t = 0; t < M; t++) {
        // rot=0 always allowed
        variantsByType[t].push_back({t, items[t].w, items[t].h, 0});
        if (allow_rotate && items[t].w != items[t].h) {
            variantsByType[t].push_back({t, items[t].h, items[t].w, 1});
        }
        // filter variants that don't fit bin (optional optimization)
        vector<Variant> filtered;
        for (auto &v : variantsByType[t]) {
            if (v.w <= W && v.h <= H) filtered.push_back(v);
        }
        variantsByType[t].swap(filtered);
    }

    int maxPlacements = 4500;
    double timeLimitSec = 0.88;

    Result r0 = runGreedyMaxRects(W, H, items, variantsByType, 0, maxPlacements, timeLimitSec);
    Result r1 = runGreedyMaxRects(W, H, items, variantsByType, 1, maxPlacements, timeLimitSec);

    const Result& best = (r1.profit > r0.profit ? r1 : r0);

    cout << "{\"placements\":[";
    for (size_t i = 0; i < best.placements.size(); i++) {
        const auto& p = best.placements[i];
        if (i) cout << ",";
        cout << "{\"type\":\"" << jsonEscape(p.type) << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << "]}";
    return 0;
}
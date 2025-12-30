#include <bits/stdc++.h>
using namespace std;

struct TypeInfo {
    string id;
    int w = 0, h = 0;
    long long v = 0;
    int limit = 0;
    long long area = 0;
    int maxDim = 0;
    int minDim = 0;
};

struct Placement {
    int t = -1;
    int x = 0, y = 0;
    int rot = 0;
};

struct ShelfH {
    int y = 0;
    int height = 0;
    int xNext = 0;
};

struct ColumnV {
    int x = 0;
    int width = 0;
    int yNext = 0;
};

struct Parser {
    string s;
    size_t p = 0;

    explicit Parser(string in) : s(std::move(in)) {}

    void skipWS() {
        while (p < s.size() && (unsigned char)s[p] <= 32) p++;
    }

    bool consumeIf(char c) {
        skipWS();
        if (p < s.size() && s[p] == c) { p++; return true; }
        return false;
    }

    void expect(char c) {
        skipWS();
        if (p >= s.size() || s[p] != c) throw runtime_error("JSON parse error");
        p++;
    }

    string parseString() {
        skipWS();
        expect('"');
        string out;
        while (p < s.size()) {
            char c = s[p++];
            if (c == '"') break;
            if (c == '\\') {
                if (p >= s.size()) throw runtime_error("JSON parse error");
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
                        // Minimal \uXXXX support: parse and emit as UTF-8 for BMP
                        if (p + 4 > s.size()) throw runtime_error("JSON parse error");
                        int code = 0;
                        for (int i = 0; i < 4; i++) {
                            char h = s[p++];
                            code <<= 4;
                            if ('0' <= h && h <= '9') code += h - '0';
                            else if ('a' <= h && h <= 'f') code += 10 + (h - 'a');
                            else if ('A' <= h && h <= 'F') code += 10 + (h - 'A');
                            else throw runtime_error("JSON parse error");
                        }
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
                    default: throw runtime_error("JSON parse error");
                }
            } else {
                out.push_back(c);
            }
        }
        return out;
    }

    long long parseInt() {
        skipWS();
        int sign = 1;
        if (p < s.size() && s[p] == '-') { sign = -1; p++; }
        if (p >= s.size() || !isdigit((unsigned char)s[p])) throw runtime_error("JSON parse error");
        long long x = 0;
        while (p < s.size() && isdigit((unsigned char)s[p])) {
            x = x * 10 + (s[p++] - '0');
        }
        return x * sign;
    }

    bool parseBool() {
        skipWS();
        if (p + 4 <= s.size() && s.compare(p, 4, "true") == 0) { p += 4; return true; }
        if (p + 5 <= s.size() && s.compare(p, 5, "false") == 0) { p += 5; return false; }
        throw runtime_error("JSON parse error");
    }

    void parseNull() {
        skipWS();
        if (p + 4 <= s.size() && s.compare(p, 4, "null") == 0) { p += 4; return; }
        throw runtime_error("JSON parse error");
    }

    void skipValue() {
        skipWS();
        if (p >= s.size()) throw runtime_error("JSON parse error");
        char c = s[p];
        if (c == '{') {
            p++;
            skipWS();
            if (consumeIf('}')) return;
            while (true) {
                (void)parseString();
                expect(':');
                skipValue();
                skipWS();
                if (consumeIf('}')) break;
                expect(',');
            }
        } else if (c == '[') {
            p++;
            skipWS();
            if (consumeIf(']')) return;
            while (true) {
                skipValue();
                skipWS();
                if (consumeIf(']')) break;
                expect(',');
            }
        } else if (c == '"') {
            (void)parseString();
        } else if (c == 't' || c == 'f') {
            (void)parseBool();
        } else if (c == 'n') {
            parseNull();
        } else if (c == '-' || isdigit((unsigned char)c)) {
            (void)parseInt();
        } else {
            throw runtime_error("JSON parse error");
        }
    }
};

static string jsonEscape(const string& in) {
    string out;
    out.reserve(in.size() + 8);
    for (char c : in) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if ((unsigned char)c < 0x20) {
                    static const char* hex = "0123456789abcdef";
                    out += "\\u00";
                    out.push_back(hex[(c >> 4) & 0xF]);
                    out.push_back(hex[c & 0xF]);
                } else out.push_back(c);
        }
    }
    return out;
}

struct Sorter {
    int mode = 0;
    const vector<TypeInfo>* T = nullptr;

    bool operator()(int a, int b) const {
        const auto& A = (*T)[a];
        const auto& B = (*T)[b];

        auto tieBreak = [&]() -> bool {
            if (A.v != B.v) return A.v > B.v;
            if (A.area != B.area) return A.area > B.area;
            if (A.maxDim != B.maxDim) return A.maxDim > B.maxDim;
            return A.id < B.id;
        };

        switch (mode) {
            case 0: { // density desc: v/area
                __int128 lhs = (__int128)A.v * (__int128)B.area;
                __int128 rhs = (__int128)B.v * (__int128)A.area;
                if (lhs != rhs) return lhs > rhs;
                return tieBreak();
            }
            case 1: { // value desc
                if (A.v != B.v) return A.v > B.v;
                // prefer higher density next
                __int128 lhs = (__int128)A.v * (__int128)B.area;
                __int128 rhs = (__int128)B.v * (__int128)A.area;
                if (lhs != rhs) return lhs > rhs;
                return tieBreak();
            }
            case 2: { // area desc
                if (A.area != B.area) return A.area > B.area;
                __int128 lhs = (__int128)A.v * (__int128)B.area;
                __int128 rhs = (__int128)B.v * (__int128)A.area;
                if (lhs != rhs) return lhs > rhs;
                return tieBreak();
            }
            case 3: { // maxDim desc
                if (A.maxDim != B.maxDim) return A.maxDim > B.maxDim;
                __int128 lhs = (__int128)A.v * (__int128)B.area;
                __int128 rhs = (__int128)B.v * (__int128)A.area;
                if (lhs != rhs) return lhs > rhs;
                return tieBreak();
            }
            case 4: { // v/maxDim desc
                __int128 lhs = (__int128)A.v * (__int128)B.maxDim;
                __int128 rhs = (__int128)B.v * (__int128)A.maxDim;
                if (lhs != rhs) return lhs > rhs;
                __int128 lhs2 = (__int128)A.v * (__int128)B.area;
                __int128 rhs2 = (__int128)B.v * (__int128)A.area;
                if (lhs2 != rhs2) return lhs2 > rhs2;
                return tieBreak();
            }
            default:
                return a < b;
        }
    }
};

struct RunResult {
    long long profit = 0;
    vector<Placement> placements;
};

static inline bool betterNewShelfHorizontal(int w1, int h1, int w2, int h2) {
    // prefer smaller shelf height; tie: larger width (fills row earlier)
    if (h1 != h2) return h1 < h2;
    if (w1 != w2) return w1 > w2;
    return false;
}

static inline bool betterNewColVertical(int w1, int h1, int w2, int h2) {
    // prefer smaller column width; tie: larger height (fills column earlier)
    if (w1 != w2) return w1 < w2;
    if (h1 != h2) return h1 > h2;
    return false;
}

static RunResult packHorizontalFFDH(int W, int H, bool allowRotate, const vector<TypeInfo>& types, const vector<int>& itemsSorted) {
    vector<ShelfH> shelves;
    shelves.reserve(512);
    vector<Placement> out;
    out.reserve(itemsSorted.size());
    int curY = 0;
    long long profit = 0;

    for (int tidx : itemsSorted) {
        const auto& t = types[tidx];

        // Choose best shelf placement (best-fit by minimal leftover width)
        int bestShelf = -1, bestRot = 0;
        int bestW = 0, bestH = 0;
        int bestLeftover = INT_MAX;
        int bestShelfY = INT_MAX;

        for (int i = 0; i < (int)shelves.size(); i++) {
            int remW = W - shelves[i].xNext;
            int sh = shelves[i].height;

            // rot 0
            if (t.w <= remW && t.h <= sh) {
                int leftover = remW - t.w;
                if (leftover < bestLeftover || (leftover == bestLeftover && shelves[i].y < bestShelfY)) {
                    bestLeftover = leftover;
                    bestShelfY = shelves[i].y;
                    bestShelf = i;
                    bestRot = 0;
                    bestW = t.w;
                    bestH = t.h;
                }
            }
            // rot 1
            if (allowRotate && t.w != t.h) {
                if (t.h <= remW && t.w <= sh) {
                    int leftover = remW - t.h;
                    if (leftover < bestLeftover || (leftover == bestLeftover && shelves[i].y < bestShelfY)) {
                        bestLeftover = leftover;
                        bestShelfY = shelves[i].y;
                        bestShelf = i;
                        bestRot = 1;
                        bestW = t.h;
                        bestH = t.w;
                    }
                }
            }
        }

        if (bestShelf != -1) {
            int x = shelves[bestShelf].xNext;
            int y = shelves[bestShelf].y;
            shelves[bestShelf].xNext += bestW;
            out.push_back({tidx, x, y, bestRot});
            profit += t.v;
            continue;
        }

        // Create new shelf
        int chosenRot = -1;
        int cw = 0, ch = 0;

        // rot 0
        if (t.w <= W && curY + t.h <= H) {
            chosenRot = 0; cw = t.w; ch = t.h;
        }
        // rot 1
        if (allowRotate && t.w != t.h) {
            if (t.h <= W && curY + t.w <= H) {
                if (chosenRot == -1 || betterNewShelfHorizontal(t.h, t.w, cw, ch)) {
                    chosenRot = 1; cw = t.h; ch = t.w;
                }
            }
        }

        if (chosenRot != -1) {
            ShelfH sh;
            sh.y = curY;
            sh.height = ch;
            sh.xNext = cw;
            shelves.push_back(sh);
            out.push_back({tidx, 0, curY, chosenRot});
            profit += t.v;
            curY += ch;
        }
    }

    return {profit, std::move(out)};
}

static RunResult packVerticalFFDH(int W, int H, bool allowRotate, const vector<TypeInfo>& types, const vector<int>& itemsSorted) {
    vector<ColumnV> cols;
    cols.reserve(512);
    vector<Placement> out;
    out.reserve(itemsSorted.size());
    int curX = 0;
    long long profit = 0;

    for (int tidx : itemsSorted) {
        const auto& t = types[tidx];

        // Choose best column placement (best-fit by minimal leftover height)
        int bestCol = -1, bestRot = 0;
        int bestW = 0, bestH = 0;
        int bestLeftover = INT_MAX;
        int bestColX = INT_MAX;

        for (int i = 0; i < (int)cols.size(); i++) {
            int remH = H - cols[i].yNext;
            int cw = cols[i].width;

            // rot 0
            if (t.w <= cw && t.h <= remH) {
                int leftover = remH - t.h;
                if (leftover < bestLeftover || (leftover == bestLeftover && cols[i].x < bestColX)) {
                    bestLeftover = leftover;
                    bestColX = cols[i].x;
                    bestCol = i;
                    bestRot = 0;
                    bestW = t.w;
                    bestH = t.h;
                }
            }
            // rot 1
            if (allowRotate && t.w != t.h) {
                if (t.h <= cw && t.w <= remH) {
                    int leftover = remH - t.w;
                    if (leftover < bestLeftover || (leftover == bestLeftover && cols[i].x < bestColX)) {
                        bestLeftover = leftover;
                        bestColX = cols[i].x;
                        bestCol = i;
                        bestRot = 1;
                        bestW = t.h;
                        bestH = t.w;
                    }
                }
            }
        }

        if (bestCol != -1) {
            int x = cols[bestCol].x;
            int y = cols[bestCol].yNext;
            cols[bestCol].yNext += bestH;
            out.push_back({tidx, x, y, bestRot});
            profit += t.v;
            continue;
        }

        // Create new column
        int chosenRot = -1;
        int cw = 0, ch = 0;

        // rot 0
        if (t.w <= W - curX && t.h <= H) {
            chosenRot = 0; cw = t.w; ch = t.h;
        }
        // rot 1
        if (allowRotate && t.w != t.h) {
            if (t.h <= W - curX && t.w <= H) {
                if (chosenRot == -1 || betterNewColVertical(t.h, t.w, cw, ch)) {
                    chosenRot = 1; cw = t.h; ch = t.w;
                }
            }
        }

        if (chosenRot != -1) {
            ColumnV c;
            c.x = curX;
            c.width = cw;
            c.yNext = ch;
            cols.push_back(c);
            out.push_back({tidx, curX, 0, chosenRot});
            profit += t.v;
            curX += cw;
        }
    }

    return {profit, std::move(out)};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());

    int W = 0, H = 0;
    bool allowRotate = false;
    vector<TypeInfo> types;

    try {
        Parser ps(input);
        ps.skipWS();
        ps.expect('{');

        bool gotBin = false, gotItems = false;

        ps.skipWS();
        if (!ps.consumeIf('}')) {
            while (true) {
                string key = ps.parseString();
                ps.expect(':');

                if (key == "bin") {
                    gotBin = true;
                    ps.expect('{');
                    ps.skipWS();
                    if (!ps.consumeIf('}')) {
                        while (true) {
                            string bk = ps.parseString();
                            ps.expect(':');
                            if (bk == "W") W = (int)ps.parseInt();
                            else if (bk == "H") H = (int)ps.parseInt();
                            else if (bk == "allow_rotate") allowRotate = ps.parseBool();
                            else ps.skipValue();
                            ps.skipWS();
                            if (ps.consumeIf('}')) break;
                            ps.expect(',');
                        }
                    }
                } else if (key == "items") {
                    gotItems = true;
                    ps.expect('[');
                    ps.skipWS();
                    if (!ps.consumeIf(']')) {
                        while (true) {
                            TypeInfo t;
                            ps.expect('{');
                            ps.skipWS();
                            if (!ps.consumeIf('}')) {
                                while (true) {
                                    string ik = ps.parseString();
                                    ps.expect(':');
                                    if (ik == "type") t.id = ps.parseString();
                                    else if (ik == "w") t.w = (int)ps.parseInt();
                                    else if (ik == "h") t.h = (int)ps.parseInt();
                                    else if (ik == "v") t.v = ps.parseInt();
                                    else if (ik == "limit") t.limit = (int)ps.parseInt();
                                    else ps.skipValue();
                                    ps.skipWS();
                                    if (ps.consumeIf('}')) break;
                                    ps.expect(',');
                                }
                            }
                            t.area = 1LL * t.w * t.h;
                            t.maxDim = max(t.w, t.h);
                            t.minDim = min(t.w, t.h);
                            types.push_back(std::move(t));

                            ps.skipWS();
                            if (ps.consumeIf(']')) break;
                            ps.expect(',');
                        }
                    }
                } else {
                    ps.skipValue();
                }

                ps.skipWS();
                if (ps.consumeIf('}')) break;
                ps.expect(',');
            }
        }

        if (!gotBin || !gotItems) throw runtime_error("missing keys");
    } catch (...) {
        cout << "{\"placements\":[]}";
        return 0;
    }

    int M = (int)types.size();
    if (W <= 0 || H <= 0 || M == 0) {
        cout << "{\"placements\":[]}";
        return 0;
    }

    // Expand copies list
    vector<int> copies;
    copies.reserve(30000);
    for (int i = 0; i < M; i++) {
        int lim = max(0, types[i].limit);
        for (int k = 0; k < lim; k++) copies.push_back(i);
    }
    if (copies.empty()) {
        cout << "{\"placements\":[]}";
        return 0;
    }

    auto start = chrono::steady_clock::now();
    auto elapsedSec = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - start).count();
    };

    RunResult best;
    best.profit = -1;

    vector<int> modes = {0, 1, 2, 4, 3}; // density, value, area, v/maxDim, maxDim
    for (int mode : modes) {
        if (elapsedSec() > 0.92) break;

        vector<int> items = copies;
        Sorter sorter{mode, &types};
        stable_sort(items.begin(), items.end(), sorter);

        // Horizontal
        if (elapsedSec() <= 0.95) {
            RunResult r = packHorizontalFFDH(W, H, allowRotate, types, items);
            if (r.profit > best.profit) best = std::move(r);
        }
        // Vertical
        if (elapsedSec() <= 0.95) {
            RunResult r = packVerticalFFDH(W, H, allowRotate, types, items);
            if (r.profit > best.profit) best = std::move(r);
        }
    }

    // Output best
    cout << "{\"placements\":[";
    for (size_t i = 0; i < best.placements.size(); i++) {
        const auto& p = best.placements[i];
        const auto& t = types[p.t];
        int rot = allowRotate ? p.rot : 0;
        if (i) cout << ",";
        cout << "{\"type\":\"" << jsonEscape(t.id) << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << rot << "}";
    }
    cout << "]}";
    return 0;
}
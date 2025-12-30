#include <bits/stdc++.h>
using namespace std;

struct JSONValue {
    enum Type {Null, Bool, Number, String, Array, Object} type = Null;
    bool b = false;
    long long num = 0;
    string str;
    vector<JSONValue> arr;
    map<string, JSONValue> obj;
};

struct JSONParser {
    const string &s;
    size_t i = 0;
    JSONParser(const string &s): s(s) {}
    void skipWS() {
        while (i < s.size() && (s[i]==' ' || s[i]=='\n' || s[i]=='\r' || s[i]=='\t')) ++i;
    }
    bool match(const string &t) {
        size_t j = i;
        for (char c: t) {
            if (j >= s.size() || s[j] != c) return false;
            ++j;
        }
        i = j;
        return true;
    }
    int hexVal(char c){
        if (c>='0'&&c<='9') return c-'0';
        if (c>='a'&&c<='f') return c-'a'+10;
        if (c>='A'&&c<='F') return c-'A'+10;
        return -1;
    }
    string parseStringRaw() {
        string out;
        if (i >= s.size() || s[i] != '"') return out;
        ++i;
        while (i < s.size()) {
            char c = s[i++];
            if (c == '"') break;
            if (c == '\\') {
                if (i >= s.size()) break;
                char e = s[i++];
                if (e == '"' || e == '\\' || e == '/') out.push_back(e);
                else if (e == 'b') out.push_back('\b');
                else if (e == 'f') out.push_back('\f');
                else if (e == 'n') out.push_back('\n');
                else if (e == 'r') out.push_back('\r');
                else if (e == 't') out.push_back('\t');
                else if (e == 'u') {
                    // parse 4 hex digits
                    if (i + 4 <= s.size()) {
                        int code = 0;
                        bool ok = true;
                        for (int k=0;k<4;k++) {
                            int hv = hexVal(s[i+k]);
                            if (hv < 0) { ok = false; break; }
                            code = (code<<4) | hv;
                        }
                        i += 4;
                        if (ok) {
                            // Basic Unicode handling: encode as UTF-8
                            if (code <= 0x7F) out.push_back((char)code);
                            else if (code <= 0x7FF) {
                                out.push_back((char)(0xC0 | ((code>>6)&0x1F)));
                                out.push_back((char)(0x80 | (code & 0x3F)));
                            } else {
                                out.push_back((char)(0xE0 | ((code>>12)&0x0F)));
                                out.push_back((char)(0x80 | ((code>>6)&0x3F)));
                                out.push_back((char)(0x80 | (code & 0x3F)));
                            }
                        }
                    }
                } else {
                    // Unknown escape, ignore
                }
            } else {
                out.push_back(c);
            }
        }
        return out;
    }
    JSONValue parseValue() {
        skipWS();
        JSONValue v;
        if (i >= s.size()) return v;
        char c = s[i];
        if (c == 'n') {
            if (match("null")) { v.type = JSONValue::Null; return v; }
        } else if (c == 't') {
            if (match("true")) { v.type = JSONValue::Bool; v.b = true; return v; }
        } else if (c == 'f') {
            if (match("false")) { v.type = JSONValue::Bool; v.b = false; return v; }
        } else if (c == '"') {
            v.type = JSONValue::String;
            v.str = parseStringRaw();
            return v;
        } else if (c == '[') {
            ++i;
            v.type = JSONValue::Array;
            skipWS();
            if (i < s.size() && s[i] == ']') { ++i; return v; }
            while (true) {
                JSONValue elem = parseValue();
                v.arr.push_back(elem);
                skipWS();
                if (i < s.size() && s[i] == ',') { ++i; continue; }
                if (i < s.size() && s[i] == ']') { ++i; break; }
                // malformed, break
                break;
            }
            return v;
        } else if (c == '{') {
            ++i;
            v.type = JSONValue::Object;
            skipWS();
            if (i < s.size() && s[i] == '}') { ++i; return v; }
            while (true) {
                skipWS();
                if (i >= s.size() || s[i] != '"') break;
                string key = parseStringRaw();
                skipWS();
                if (i < s.size() && s[i] == ':') ++i;
                JSONValue val = parseValue();
                v.obj[key] = val;
                skipWS();
                if (i < s.size() && s[i] == ',') { ++i; continue; }
                if (i < s.size() && s[i] == '}') { ++i; break; }
                break;
            }
            return v;
        } else if (c == '-' || (c >= '0' && c <= '9')) {
            // number (integer only in this problem)
            bool neg = false;
            if (s[i] == '-') { neg = true; ++i; }
            long long num = 0;
            bool hasDigits = false;
            while (i < s.size() && s[i] >= '0' && s[i] <= '9') {
                hasDigits = true;
                int d = s[i] - '0';
                if (num <= (LLONG_MAX - d) / 10) num = num*10 + d;
                else {
                    // overflow: clamp
                    num = LLONG_MAX/2;
                }
                ++i;
            }
            // ignore decimals/exponents if present (unlikely)
            v.type = JSONValue::Number;
            v.num = neg ? -num : num;
            return v;
        }
        // fallback
        return v;
    }
};

static string jsonEscape(const string &s) {
    string out;
    out.push_back('"');
    for (char c : s) {
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
                    char buf[8];
                    snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out.push_back(c);
                }
        }
    }
    out.push_back('"');
    return out;
}

struct Item {
    string type;
    int w, h;
    long long v;
    int limit;
};

struct Rect {
    int x, y, w, h;
};

struct Placement {
    int itemIndex;
    int x, y;
    int rot; // 0 or 1
};

static bool rectValid(const Rect &r) {
    return r.w > 0 && r.h > 0;
}

static bool canFit(const Rect &r, int w, int h) {
    return w <= r.w && h <= r.h;
}

static bool chooseVerticalSplit(const Rect &F, int w, int h) {
    long long wrem = (long long)F.w - w;
    long long hrem = (long long)F.h - h;
    long long areaH1 = (long long)F.w * hrem;
    long long areaH2 = wrem * h;
    long long maxH = max(areaH1, areaH2);
    long long areaV1 = wrem * (long long)F.h;
    long long areaV2 = (long long)w * hrem;
    long long maxV = max(areaV1, areaV2);
    if (maxV < maxH) return true;
    if (maxV > maxH) return false;
    // tie-breaks
    if (wrem < hrem) return true;
    if (wrem > hrem) return false;
    // prefer vertical if free rect is wider than tall
    if (F.w > F.h) return true;
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    JSONParser parser(input);
    JSONValue root = parser.parseValue();
    int W = 0, H = 0;
    bool allow_rotate = false;
    vector<Item> items;

    if (root.type == JSONValue::Object) {
        auto itb = root.obj.find("bin");
        if (itb != root.obj.end() && itb->second.type == JSONValue::Object) {
            auto &B = itb->second.obj;
            if (B.find("W") != B.end() && B["W"].type == JSONValue::Number) W = (int)B["W"].num;
            if (B.find("H") != B.end() && B["H"].type == JSONValue::Number) H = (int)B["H"].num;
            if (B.find("allow_rotate") != B.end()) {
                auto &ar = B["allow_rotate"];
                if (ar.type == JSONValue::Bool) allow_rotate = ar.b;
                else if (ar.type == JSONValue::Number) allow_rotate = (ar.num != 0);
            }
        }
        auto iti = root.obj.find("items");
        if (iti != root.obj.end() && iti->second.type == JSONValue::Array) {
            for (auto &iv : iti->second.arr) {
                if (iv.type != JSONValue::Object) continue;
                Item it;
                auto &O = iv.obj;
                if (O.find("type") != O.end() && O["type"].type == JSONValue::String) it.type = O["type"].str;
                if (O.find("w") != O.end() && O["w"].type == JSONValue::Number) it.w = (int)O["w"].num;
                if (O.find("h") != O.end() && O["h"].type == JSONValue::Number) it.h = (int)O["h"].num;
                if (O.find("v") != O.end() && O["v"].type == JSONValue::Number) it.v = (long long)O["v"].num;
                if (O.find("limit") != O.end() && O["limit"].type == JSONValue::Number) it.limit = (int)O["limit"].num;
                // sanity
                if (it.w <= 0 || it.h <= 0 || it.limit <= 0 || it.w > W || it.h > H) {
                    // keep item but it may not fit; limit could be >0 (we can handle)
                }
                items.push_back(it);
            }
        }
    }

    if (W <= 0 || H <= 0 || items.empty()) {
        // Output empty placements
        cout << "{\n  \"placements\": []\n}\n";
        return 0;
    }

    // Prepare packing
    int M = (int)items.size();
    vector<int> remaining(M);
    for (int i = 0; i < M; ++i) remaining[i] = max(0, items[i].limit);

    vector<Rect> freeRects;
    freeRects.push_back({0, 0, W, H});

    vector<Placement> placements;

    // Greedy packing loop (Guillotine splitting)
    // Score function: maximize v * (item_area / free_area), tie-break by larger item area, then tighter fit.
    auto compute_score = [&](long double v, long double itemArea, long double freeArea) -> long double {
        if (freeArea <= 0.0L) return -1e100L;
        return v * (itemArea / freeArea);
    };

    while (true) {
        int bestF = -1;
        int bestItem = -1;
        int bestRot = 0;
        int bestW = 0, bestH = 0;
        long double bestScore = -1e100L;
        long long bestItemArea = -1;
        int bestShortLeftover = INT_MAX;
        int bestLongLeftover = INT_MAX;

        for (int f = 0; f < (int)freeRects.size(); ++f) {
            Rect F = freeRects[f];
            if (F.w <= 0 || F.h <= 0) continue;
            long long freeArea = 1LL * F.w * F.h;
            for (int t = 0; t < M; ++t) {
                if (remaining[t] <= 0) continue;
                // orientation 0
                {
                    int w = items[t].w, h = items[t].h;
                    if (w <= F.w && h <= F.h) {
                        long long itemArea = 1LL * w * h;
                        long double score = compute_score((long double)items[t].v, (long double)itemArea, (long double)freeArea);
                        int shortLeft = min(F.w - w, F.h - h);
                        int longLeft = max(F.w - w, F.h - h);
                        if (score > bestScore + 1e-18L ||
                            (fabsl(score - bestScore) <= 1e-18L && (itemArea > bestItemArea ||
                              (itemArea == bestItemArea && (shortLeft < bestShortLeftover ||
                                  (shortLeft == bestShortLeftover && longLeft < bestLongLeftover)))))) {
                            bestScore = score;
                            bestF = f;
                            bestItem = t;
                            bestRot = 0;
                            bestW = w;
                            bestH = h;
                            bestItemArea = itemArea;
                            bestShortLeftover = shortLeft;
                            bestLongLeftover = longLeft;
                        }
                    }
                }
                // orientation 1
                if (allow_rotate) {
                    int w = items[t].h, h = items[t].w;
                    if (w <= F.w && h <= F.h) {
                        long long itemArea = 1LL * w * h;
                        long double score = compute_score((long double)items[t].v, (long double)itemArea, (long double)freeArea);
                        int shortLeft = min(F.w - w, F.h - h);
                        int longLeft = max(F.w - w, F.h - h);
                        if (score > bestScore + 1e-18L ||
                            (fabsl(score - bestScore) <= 1e-18L && (itemArea > bestItemArea ||
                              (itemArea == bestItemArea && (shortLeft < bestShortLeftover ||
                                  (shortLeft == bestShortLeftover && longLeft < bestLongLeftover)))))) {
                            bestScore = score;
                            bestF = f;
                            bestItem = t;
                            bestRot = 1;
                            bestW = w;
                            bestH = h;
                            bestItemArea = itemArea;
                            bestShortLeftover = shortLeft;
                            bestLongLeftover = longLeft;
                        }
                    }
                }
            }
        }

        if (bestF == -1 || bestItem == -1) break;

        Rect F = freeRects[bestF];
        // Place at bottom-left of F
        Placement P;
        P.itemIndex = bestItem;
        P.x = F.x;
        P.y = F.y;
        P.rot = allow_rotate ? bestRot : 0;
        placements.push_back(P);
        remaining[bestItem]--;

        // Split the free rectangle F into two guillotine parts
        // Choose split heuristic
        bool vertical = chooseVerticalSplit(F, bestW, bestH);

        // Remove F
        freeRects[bestF] = freeRects.back();
        freeRects.pop_back();

        if (vertical) {
            // Right of placed
            Rect R1 = {F.x + bestW, F.y, F.w - bestW, F.h};
            if (rectValid(R1)) freeRects.push_back(R1);
            // Top of placed (above within used width)
            Rect R2 = {F.x, F.y + bestH, bestW, F.h - bestH};
            if (rectValid(R2)) freeRects.push_back(R2);
        } else {
            // Top of placed
            Rect R1 = {F.x, F.y + bestH, F.w, F.h - bestH};
            if (rectValid(R1)) freeRects.push_back(R1);
            // Right of placed (beside within used height)
            Rect R2 = {F.x + bestW, F.y, F.w - bestW, bestH};
            if (rectValid(R2)) freeRects.push_back(R2);
        }

        // Optional: could add simple coalescing of adjacent free rects, but skip for speed.
    }

    // Output JSON
    cout << "{\n  \"placements\": [";
    bool first = true;
    for (const auto &p : placements) {
        if (!first) cout << ",\n";
        else cout << "\n";
        first = false;
        const Item &it = items[p.itemIndex];
        cout << "    {\"type\":" << jsonEscape(it.type)
             << ",\"x\":" << p.x
             << ",\"y\":" << p.y
             << ",\"rot\":" << (allow_rotate ? p.rot : 0)
             << "}";
    }
    if (!first) cout << "\n";
    cout << "  ]\n}\n";
    return 0;
}
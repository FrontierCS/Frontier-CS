#include <cmath>
#include <algorithm>

// Natural-log calibration above the previous 60-point threshold.
// Keep validation and low scores; an exact zero minimization cost earns 100.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0 || !(value > 0.0L) || !(anchor > 0.0L))
        return old_points;
    const long double delta = minimize ? std::log(anchor) - std::log(value)
                                       : std::log(value) - std::log(anchor);
    return (double)std::min(100.0L, 60.0L + delta);
}


// Preserve the bounded base ratio for the unchanged low-score branch.
static double penalized(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <charconv>
// Performance anchor: 60 points; logarithmic credit above it.
static double reference_score(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6*r : 0.6 + 0.02*std::log(r);
}

#include <bits/stdc++.h>
using namespace std;

struct Item { long long w,h,v,limit; };
struct BinSpec { long long W,H; bool allow_rotate; };

void skipWS(InStream& s){ while(!s.eof() && isspace((unsigned char)s.curChar())) s.readChar(); }
void expectChar(InStream& s, char c){ skipWS(s); if (s.eof() || s.readChar()!=c) s.quitf(_pe,"Expected JSON character '%c'", c); }
string readString(InStream& s){
    skipWS(s);
    expectChar(s, '"');
    string out; char c;
    while(true){
        if (s.eof()) s.quitf(_pe, "Unterminated JSON string");
        c = s.readChar();
        if ((unsigned char)c < 32) s.quitf(_pe, "Unescaped control character");
        if (c=='"') break;
        if (c=='\\'){
            if (s.eof()) s.quitf(_pe, "Unterminated JSON escape");
            char e = s.readChar();
            switch(e){
                case '"': out.push_back('"'); break;
                case '\\': out.push_back('\\'); break;
                case '/': out.push_back('/'); break;
                case 'b': out.push_back('\b'); break;
                case 'f': out.push_back('\f'); break;
                case 'n': out.push_back('\n'); break;
                case 'r': out.push_back('\r'); break;
                case 't': out.push_back('\t'); break;
                case 'u': {
                    auto hex4 = [&]() {
                        unsigned value = 0;
                        for (int i = 0; i < 4; ++i) {
                            if (s.eof()) s.quitf(_pe, "Incomplete Unicode escape");
                            char h = s.readChar();
                            int d = h >= '0' && h <= '9' ? h-'0' :
                                    h >= 'a' && h <= 'f' ? h-'a'+10 :
                                    h >= 'A' && h <= 'F' ? h-'A'+10 : -1;
                            if (d < 0) s.quitf(_pe, "Invalid Unicode escape");
                            value = value*16+d;
                        }
                        return value;
                    };
                    unsigned code = hex4();
                    if (code >= 0xD800 && code <= 0xDBFF) {
                        if (s.eof() || s.readChar() != '\\' || s.eof() || s.readChar() != 'u')
                            s.quitf(_pe, "Missing low surrogate");
                        unsigned low = hex4();
                        if (low < 0xDC00 || low > 0xDFFF) s.quitf(_pe, "Invalid low surrogate");
                        code = 0x10000 + (code-0xD800)*1024 + low-0xDC00;
                    } else if (code >= 0xDC00 && code <= 0xDFFF) s.quitf(_pe, "Unexpected low surrogate");
                    if (code < 0x80) out += char(code);
                    else if (code < 0x800) { out += char(0xC0 | code>>6); out += char(0x80 | (code&63)); }
                    else if (code < 0x10000) { out += char(0xE0 | code>>12); out += char(0x80 | ((code>>6)&63)); out += char(0x80 | (code&63)); }
                    else { out += char(0xF0 | code>>18); out += char(0x80 | ((code>>12)&63)); out += char(0x80 | ((code>>6)&63)); out += char(0x80 | (code&63)); }
                    break;
                }
                default: s.quitf(_pe, "Invalid JSON escape");
            }
        } else {
            out.push_back(c);
        }
    }
    return out;
}
long long readJsonLong(InStream& stream) {
    skipWS(stream);
    string token;
    if (!stream.eof() && stream.curChar() == '-') token += stream.readChar();
    while (!stream.eof() && stream.curChar() >= '0' && stream.curChar() <= '9') {
        token += stream.readChar();
        if (token.size() > 20) stream.quitf(_pe, "JSON integer is out of range");
    }
    size_t first = !token.empty() && token[0] == '-' ? 1 : 0;
    if (first == token.size() || (token[first] == '0' && token.size() > first + 1))
        stream.quitf(_pe, "Expected JSON integer without leading zeroes");
    long long value;
    auto parsed = from_chars(token.data(), token.data() + token.size(), value);
    if (parsed.ec != errc() || parsed.ptr != token.data() + token.size())
        stream.quitf(_pe, "JSON integer is out of range");
    return value;
}
bool readJsonBool(InStream& s){
    skipWS(s);
    if (s.curChar()=='t'){ string ex="true"; for(char c:ex){ if (s.readChar()!=c) s.quitf(_pe,"Malformed boolean"); } return true; }
    if (s.curChar()=='f'){ string ex="false"; for(char c:ex){ if (s.readChar()!=c) s.quitf(_pe,"Malformed boolean"); } return false; }
    s.quitf(_pe, "Expected boolean"); return false;
}

void parseInput(map<string,Item>& items, BinSpec& bin){
    expectChar(inf,'{');
    for (int iter=0; iter<2; ++iter){
        if (iter>0){ expectChar(inf, ','); }
        string k = readString(inf);
        expectChar(inf, ':');
        if (k=="bin"){
            expectChar(inf, '{');
            bool first=true; long long mask=0;
            for (int i=0;i<3;i++){
                if (!first) expectChar(inf, ','); first=false;
                string bk = readString(inf);
                expectChar(inf, ':');
                if (bk=="W"){ bin.W = readJsonLong(inf); mask|=1; }
                else if (bk=="H"){ bin.H = readJsonLong(inf); mask|=2; }
                else if (bk=="allow_rotate"){ bin.allow_rotate = readJsonBool(inf); mask|=4; }
                else quitf(_fail, "Unknown bin key: %s", bk.c_str());
            }
            if (mask!=7) quitf(_fail, "Missing bin fields");
            expectChar(inf, '}');
        }else if (k=="items"){
            expectChar(inf, '[');
            bool first = true;
            while(true){
                skipWS(inf);
                if (inf.curChar()==']'){ inf.readChar(); break; }
                if (!first) expectChar(inf, ',');
                first=false;
                expectChar(inf, '{');
                string t; long long w=0,h=0,v=0,limit=0; long long mask=0;
                bool firstIt=true;
                for (int fld=0; fld<5; ++fld){
                    if (!firstIt){ expectChar(inf, ','); } firstIt=false;
                    string key = readString(inf);
                    expectChar(inf, ':');
                    if (key=="type"){ t = readString(inf); mask|=1; }
                    else if (key=="w"){ w = readJsonLong(inf); mask|=2; }
                    else if (key=="h"){ h = readJsonLong(inf); mask|=4; }
                    else if (key=="v"){ v = readJsonLong(inf); mask|=8; }
                    else if (key=="limit"){ limit = readJsonLong(inf); mask|=16; }
                    else quitf(_fail, "Unknown item field: %s", key.c_str());
                }
                expectChar(inf, '}');
                if (mask!=31) quitf(_fail, "Missing fields in item");
                if (w<=0||h<=0||v<0||limit<0) quitf(_wa, "Invalid item parameters for %s", t.c_str());
                items[t] = Item{w,h,v,limit};
            }
        }else quitf(_fail, "Unknown top-level key: %s", k.c_str());
    }
    expectChar(inf, '}');
    if (items.empty()) quitf(_fail, "No items in input");
}

struct Place { string t; long long x,y; int rot; long long w,h; };
vector<Place> parseOutput(const map<string,Item>& items, const BinSpec& bin){
    vector<Place> res;
    expectChar(ouf, '{');
    string k = readString(ouf);
    expectChar(ouf, ':');
    if (k!="placements") quitf(_wa, "Top-level key must be \"placements\"");
    expectChar(ouf, '[');
    bool first = true;
    while(true){
        skipWS(ouf);
        if (ouf.curChar()==']'){ ouf.readChar(); break; }
        if (!first) expectChar(ouf, ',');
        first=false;
        expectChar(ouf, '{');
        string t; long long x=0,y=0; int rot=0; long long mask = 0;
        bool firstF = true;
        while(true){
            skipWS(ouf);
            if (!firstF){
                if (ouf.curChar()=='}') break;
                expectChar(ouf, ',');
            }
            firstF=false;
            string kk = readString(ouf);
            expectChar(ouf, ':');
            int bit = kk=="type" ? 1 : kk=="x" ? 2 : kk=="y" ? 4 : kk=="rot" ? 8 : 0;
            if (mask & bit) quitf(_pe, "Duplicate placement field");
            if (kk=="type"){ t = readString(ouf); mask|=1; }
            else if (kk=="x"){ x = readJsonLong(ouf); mask|=2; }
            else if (kk=="y"){ y = readJsonLong(ouf); mask|=4; }
            else if (kk=="rot"){ long long b = readJsonLong(ouf); if (b!=0 && b!=1) quitf(_wa,"rot must be 0 or 1"); rot = (int)b; mask|=8; }
            else quitf(_wa,"Unknown field in placement: %s", kk.c_str());
        }
        expectChar(ouf, '}');
        if (mask!=15) quitf(_wa,"Missing one of required fields in a placement");
        auto it = items.find(t);
        if (it==items.end()) quitf(_wa,"Unknown item type in placement: %s", t.c_str());
        if (rot && !bin.allow_rotate) quitf(_wa,"Rotation not allowed by this test");
        long long w = rot ? it->second.h : it->second.w;
        long long h = rot ? it->second.w : it->second.h;
        if (x < 0 || y < 0 || w > bin.W || h > bin.H || x > bin.W - w || y > bin.H - h) quitf(_wa,"Placement of %s is out of bin bounds", t.c_str());
        res.push_back(Place{t,x,y,rot,w,h});
    }
    expectChar(ouf, '}');
    if (!ouf.seekEof()) ouf.quitf(_pe, "Extra data after JSON object");
    return res;
}

long long evaluate(const vector<Place>& P, const map<string,Item>& items){
    unordered_map<string,long long> used;
    used.reserve(P.size()*2+1);
    for (auto &p: P){
        used[p.t]++;
        const auto &it = items.at(p.t);
        if (used[p.t] > it.limit) quitf(_wa, "Used too many items of type %s", p.t.c_str());
    }
    struct Ev { long long x; int id; bool open; };
    vector<Ev> ev; ev.reserve(P.size()*2);
    for (int i=0;i<(int)P.size();++i){
        ev.push_back({P[i].x, i, true});
        ev.push_back({P[i].x + P[i].w, i, false});
    }
    // IMPORTANT: process close events BEFORE open events at the same x
    sort(ev.begin(), ev.end(), [](const Ev&a, const Ev&b){
        if (a.x != b.x) return a.x < b.x;
        return a.open < b.open; // close (false) first
    });
    struct Seg { long long y1,y2; int id; };
    struct Cmp { bool operator()(Seg const& a, Seg const& b) const {
        if (a.y1!=b.y1) return a.y1<b.y1;
        if (a.y2!=b.y2) return a.y2<b.y2;
        return a.id<b.id;
    }};
    std::set<Seg, Cmp> active;
    for (auto &e: ev){
        const auto &r = P[e.id];
        if (e.open){
            Seg s{r.y, r.y + r.h, e.id};
            auto it = active.lower_bound(s);
            if (it!=active.end()){
                if (!(it->y1 >= s.y2 || it->y2 <= s.y1)) quitf(_wa, "Rectangles overlap");
            }
            if (it!=active.begin()){
                auto it2 = prev(it);
                if (!(it2->y1 >= s.y2 || it2->y2 <= s.y1)) quitf(_wa, "Rectangles overlap");
            }
            active.insert(s);
        }else{
            Seg s{r.y, r.y + r.h, e.id};
            auto it = active.find(s);
            if (it!=active.end()) active.erase(it);
        }
    }
    long long value=0;
    for (auto &p: P) value += items.at(p.t).v;
    return value;
}

int main(int argc, char* argv[]){
    registerTestlibCmd(argc, argv);
    map<string,Item> items;
    BinSpec bin;
    parseInput(items, bin);
    vector<Place> P = parseOutput(items, bin);
    long long baseline = ans.readLong();
    long long best = ans.readLong();
    long long value = evaluate(P, items);
    // Fractional area relaxation is a rigorous integer-profit upper bound.
    vector<Item> by_density;
    for (const auto &kv : items) by_density.push_back(kv.second);
    sort(by_density.begin(), by_density.end(), [](const Item &a, const Item &b) {
        return (__int128)a.v*b.w*b.h > (__int128)b.v*a.w*a.h;
    });
    long long remaining = bin.W*bin.H, upper = 0;
    for (const Item &a : by_density) {
        long long area = a.w*a.h;
        long long take = min(a.limit, remaining/area);
        upper += take*a.v;
        remaining -= take*area;
        if (take < a.limit) {
            upper += (long long)((__int128)remaining*a.v/area);
            break;
        }
    }
    const bool exact_bound = best >= upper;
    double ratio, unbounded_ratio = 0.0;
    if (best <= baseline){
        ratio = (value >= best) ? 1.0 : 0.0;
        unbounded_ratio = ratio;
    }else{
        ratio = (double)(value - baseline) / (double)(best - baseline);
        if (ratio < 0) ratio = 0;
        ratio = exact_bound ? penalized(ratio) : reference_score(ratio);
    ratio = natural_log_score(100.0 * ratio, value, exact_bound ? baseline + 0.6L*(best-baseline) : (long double)best, false) / 100.0;
        unbounded_ratio = ratio;
    }
    quitp(ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", value, ratio, unbounded_ratio);
}

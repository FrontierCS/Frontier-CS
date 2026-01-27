#include <bits/stdc++.h>
using namespace std;

struct JSON {
    enum Type {NUL, BOOL, NUM, STR, ARR, OBJ} type = NUL;
    bool b = false;
    long long n = 0;
    string s;
    vector<JSON> a;
    unordered_map<string, JSON> o;
    bool is_null() const { return type==NUL; }
    bool is_bool() const { return type==BOOL; }
    bool is_num() const { return type==NUM; }
    bool is_str() const { return type==STR; }
    bool is_arr() const { return type==ARR; }
    bool is_obj() const { return type==OBJ; }
    const JSON& operator[](const string& k) const {
        static JSON nullv;
        auto it=o.find(k);
        if(it==o.end()) return nullv;
        return it->second;
    }
    JSON& operator[](const string& k) { return o[k]; }
};

struct Parser {
    string s; size_t i=0;
    Parser(const string& str):s(str){}
    void skip() { while(i<s.size() && (s[i]==' '||s[i]=='\n'||s[i]=='\r'||s[i]=='\t')) ++i; }
    bool match(char c){ skip(); if(i<s.size() && s[i]==c){++i; return true;} return false; }
    char peek(){ skip(); return i<s.size()?s[i]:'\0'; }
    JSON parse() { skip(); return parseValue(); }
    JSON parseValue(){
        skip();
        if(i>=s.size()) return JSON();
        char c=s[i];
        if(c=='{') return parseObject();
        if(c=='[') return parseArray();
        if(c=='"') return parseString();
        if(c=='t' || c=='f') return parseBool();
        if(c=='-' || isdigit((unsigned char)c)) return parseNumber();
        // null
        if(s.compare(i,4,"null")==0){ i+=4; return JSON(); }
        // fallback
        JSON v; return v;
    }
    JSON parseObject(){
        JSON v; v.type=JSON::OBJ;
        match('{');
        skip();
        if(match('}')) return v;
        while(true){
            JSON key = parseString();
            match(':');
            JSON val = parseValue();
            v.o[key.s]=val;
            skip();
            if(match('}')) break;
            match(',');
        }
        return v;
    }
    JSON parseArray(){
        JSON v; v.type=JSON::ARR;
        match('[');
        skip();
        if(match(']')) return v;
        while(true){
            JSON elem = parseValue();
            v.a.push_back(move(elem));
            skip();
            if(match(']')) break;
            match(',');
        }
        return v;
    }
    JSON parseString(){
        JSON v; v.type=JSON::STR; v.s.clear();
        match('"');
        while(i<s.size()){
            char c=s[i++];
            if(c=='"') break;
            if(c=='\\'){
                if(i>=s.size()) break;
                char e=s[i++];
                switch(e){
                    case '"': v.s.push_back('"'); break;
                    case '\\': v.s.push_back('\\'); break;
                    case '/': v.s.push_back('/'); break;
                    case 'b': v.s.push_back('\b'); break;
                    case 'f': v.s.push_back('\f'); break;
                    case 'n': v.s.push_back('\n'); break;
                    case 'r': v.s.push_back('\r'); break;
                    case 't': v.s.push_back('\t'); break;
                    case 'u': {
                        // rudimentary: skip 4 hex digits, ignore unicode specifics
                        int cnt=0; while(cnt<4 && i<s.size() && isxdigit((unsigned char)s[i])){ ++i; ++cnt; }
                        // we won't embed unicode; just skip
                    } break;
                    default: v.s.push_back(e); break;
                }
            } else {
                v.s.push_back(c);
            }
        }
        return v;
    }
    JSON parseBool(){
        JSON v; v.type=JSON::BOOL;
        if(s.compare(i,4,"true")==0){ v.b=true; i+=4; }
        else if(s.compare(i,5,"false")==0){ v.b=false; i+=5; }
        else { v.type=JSON::NUL; }
        return v;
    }
    JSON parseNumber(){
        JSON v; v.type=JSON::NUM;
        long long sign=1;
        if(s[i]=='-'){ sign=-1; ++i; }
        long long num=0;
        while(i<s.size() && isdigit((unsigned char)s[i])){
            num = num*10 + (s[i]-'0');
            ++i;
        }
        // ignore fractional/exponent (assumed integers in problem)
        v.n = num*sign;
        return v;
    }
};

struct ItemType {
    string id;
    int w,h;
    long long v;
    int limit;
};

struct Oriented {
    int idx; // type index
    int w,h;
    int rot; // 0/1
    double density;
};

struct Placement { string type; int x,y; int rot; };

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    Parser p(input);
    JSON root = p.parse();
    const JSON& bin = root["bin"];
    int W = (int)bin.o.at("W").n;
    int H = (int)bin.o.at("H").n;
    bool allow_rotate = bin.o.at("allow_rotate").b;
    vector<ItemType> items;
    const JSON& arr = root["items"];
    for(const auto& it : arr.a){
        ItemType t;
        t.id = it.o.at("type").s;
        t.w = (int)it.o.at("w").n;
        t.h = (int)it.o.at("h").n;
        t.v = it.o.at("v").n;
        t.limit = (int)it.o.at("limit").n;
        items.push_back(t);
    }
    int M = (int)items.size();
    vector<int> remain(M);
    for(int i=0;i<M;++i) remain[i]=items[i].limit;

    vector<Placement> placements;
    placements.reserve(10000);

    auto build_oriented = [&](vector<Oriented>& out){
        out.clear();
        out.reserve(M*(allow_rotate?2:1));
        for(int i=0;i<M;++i){
            if(remain[i]<=0) continue;
            // rot 0
            if(items[i].w <= W && items[i].h <= H){
                Oriented o; o.idx=i; o.w=items[i].w; o.h=items[i].h; o.rot=0;
                o.density = (double)items[i].v / (double)(o.w * (long long)o.h);
                out.push_back(o);
            }
            if(allow_rotate){
                if(items[i].h <= W && items[i].w <= H){
                    Oriented o; o.idx=i; o.w=items[i].h; o.h=items[i].w; o.rot=1;
                    o.density = (double)items[i].v / (double)(o.w * (long long)o.h);
                    out.push_back(o);
                }
            }
        }
    };

    int y = 0;
    vector<Oriented> oriented;
    while(y < H){
        build_oriented(oriented);
        // pick shelf height hs by best density among those that fit in remaining height
        double bestD = -1.0;
        int hs = -1;
        for(const auto& o : oriented){
            if(o.h <= H - y){
                if(o.density > bestD){
                    bestD = o.density;
                    hs = o.h;
                }
            }
        }
        if(hs<=0) break;
        int x = 0;
        int remainingWidth = W;
        // fill shelf
        while(remainingWidth > 0){
            int bestIdx = -1;
            int bestRot = 0;
            int bestW=0, bestH=0;
            double bestScore = -1.0;
            int bestType = -1;
            for(int i=0;i<M;++i){
                if(remain[i]<=0) continue;
                // try orientation 0
                auto tryCand = [&](int cw,int ch,int crot){
                    if(ch <= hs && cw <= remainingWidth){
                        double dens = (double)items[i].v / (double)(cw * (long long)ch);
                        if(dens > bestScore){
                            bestScore = dens;
                            bestIdx = i;
                            bestRot = crot;
                            bestW = cw; bestH = ch;
                            bestType = i;
                        }
                    }
                };
                if(items[i].w <= W && items[i].h <= H && (!allow_rotate || true)){
                    tryCand(items[i].w, items[i].h, 0);
                }
                if(allow_rotate){
                    if(items[i].h <= W && items[i].w <= H){
                        tryCand(items[i].h, items[i].w, 1);
                    }
                }
            }
            if(bestIdx==-1) break;
            // place it
            Placement pl;
            pl.type = items[bestIdx].id;
            pl.x = x;
            pl.y = y;
            pl.rot = bestRot;
            placements.push_back(pl);
            remain[bestIdx]--;
            x += bestW;
            remainingWidth -= bestW;
            if(remain[bestIdx]==0){
                // nothing extra to do
            }
        }
        y += hs;
    }

    // Output JSON
    cout << "{\n  \"placements\": [";
    for(size_t i=0;i<placements.size();++i){
        const auto& p = placements[i];
        cout << "\n    {\"type\":\"" << p.type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
        if(i+1<placements.size()) cout << ",";
    }
    cout << "\n  ]\n}\n";
    return 0;
}
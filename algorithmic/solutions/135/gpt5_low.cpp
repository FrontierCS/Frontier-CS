#include <bits/stdc++.h>
using namespace std;

struct TripleKey {
    int a, b, c;
    bool operator==(const TripleKey& o) const {
        return a==o.a && b==o.b && c==o.c;
    }
};
struct TripleKeyHash {
    size_t operator()(const TripleKey& k) const {
        return ((size_t)k.a*1000003u) ^ ((size_t)k.b*10007u) ^ (size_t)k.c;
    }
};

struct QueryResult {
    int r;
    vector<pair<int,int>> pairs;
};

int n;
unordered_map<TripleKey, QueryResult, TripleKeyHash> cache;

QueryResult ask_query(int x, int y, int z){
    // make ordered key for caching
    int s[3] = {x,y,z};
    sort(s, s+3);
    TripleKey key{s[0], s[1], s[2]};
    auto it = cache.find(key);
    if(it != cache.end()) return it->second;

    cout << "? " << x << " " << y << " " << z << "\n";
    cout.flush();
    QueryResult res;
    if(!(cin >> res.r)) {
        // In non-interactive environment, just exit
        exit(0);
    }
    res.pairs.resize(res.r);
    for(int i=0;i<res.r;i++){
        int a,b; cin >> a >> b;
        res.pairs[i] = {min(a,b), max(a,b)};
    }
    cache.emplace(key, res);
    return res;
}

// Return middle vertex if determinable (when r==2 and two pairs share a vertex), else -1.
// Additionally return flags for single smallest pair to help classification.
int get_middle_from_query(const QueryResult& res, int x, int y, int z){
    if(res.r != 2) return -1;
    unordered_map<int,int> cnt;
    cnt[x]=0; cnt[y]=0; cnt[z]=0;
    for(auto &p: res.pairs){
        cnt[p.first]++; cnt[p.second]++;
    }
    int middle = -1;
    for(auto &kv: cnt){
        if(kv.second==2){ middle = kv.first; break; }
    }
    return middle;
}

bool is_pair_in_res(const QueryResult& res, int a, int b){
    int u=min(a,b), v=max(a,b);
    for(auto &p: res.pairs){
        if(p.first==u && p.second==v) return true;
    }
    return false;
}

struct Comparator {
    int anchor;
    int alt_anchor;
    // returns true if u < v (u closer to anchor along the arc from anchor towards other endpoint)
    bool operator()(int u, int v) const {
        if(u==v) return false;
        QueryResult res = ask_query(anchor, u, v);
        int middle = get_middle_from_query(res, anchor, u, v);
        if(middle == u) return true;
        if(middle == v) return false;
        if(middle == anchor){
            // ambiguous with this anchor; try alt anchor
            QueryResult res2 = ask_query(alt_anchor, u, v);
            int mid2 = get_middle_from_query(res2, alt_anchor, u, v);
            if(mid2 == u) return false; // closer to alt_anchor means farther from anchor
            if(mid2 == v) return true;
            // Still ambiguous: fall back to id to keep deterministic
            return u < v;
        }
        // r != 2 or other ambiguity: try alt anchor
        QueryResult res2 = ask_query(alt_anchor, u, v);
        int mid2 = get_middle_from_query(res2, alt_anchor, u, v);
        if(mid2 == u) return false;
        if(mid2 == v) return true;
        // If still ambiguous (r==1 or r==3), tie-break by id
        return u < v;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int k;
    if(!(cin >> k >> n)) return 0;

    // Choose anchors a and b
    int a = 0, b = n>1?1:0;
    if(n>=3){
        // try to pick b somewhat far from a: pick n/2
        b = (n/2) % n;
        if(b==a) b = (a+1)%n;
    }

    vector<int> S_between; // middle == x
    vector<int> S_other;   // middle == a or b or undecided/other arc
    vector<int> amb_ax;    // ambiguous with pair {a,x} smallest or r==3
    vector<int> amb_bx;    // ambiguous with pair {b,x} smallest or r==3
    for(int x=0;x<n;x++){
        if(x==a || x==b) continue;
        QueryResult res = ask_query(a,b,x);
        int middle = get_middle_from_query(res, a,b,x);
        if(middle == x){
            S_between.push_back(x);
        } else if(middle == a || middle == b){
            S_other.push_back(x);
        } else {
            // r != 2
            if(res.r == 1){
                if(is_pair_in_res(res, a, b)){
                    S_other.push_back(x);
                } else if(is_pair_in_res(res, a, x)){
                    amb_ax.push_back(x);
                } else if(is_pair_in_res(res, b, x)){
                    amb_bx.push_back(x);
                } else {
                    // shouldn't happen
                    S_other.push_back(x);
                }
            } else if(res.r == 3){
                // equally spaced with a,b,x; undecided
                // defer classification, pick one side later; use proximity tests
                amb_ax.push_back(x); // put to one amb, will resolve
            } else {
                // r==0 impossible; default other
                S_other.push_back(x);
            }
        }
    }

    // Resolve amb_ax using a sample from S_between if available, else from S_other with b as anchor
    for(int x: amb_ax){
        bool placed = false;
        if(!S_between.empty()){
            int y = S_between[0];
            QueryResult res = ask_query(a, x, y);
            int middle = get_middle_from_query(res, a, x, y);
            if(middle == a){
                // x and y on opposite sides -> x in other arc
                S_other.push_back(x);
            } else {
                // middle is x or y -> same side between a and b
                S_between.push_back(x);
            }
            placed = true;
        } else if(!S_other.empty()){
            int y = S_other[0];
            QueryResult res = ask_query(a, x, y);
            int middle = get_middle_from_query(res, a, x, y);
            if(middle == a){
                // x opposite side to y relative to a, since y in other arc, x in between
                S_between.push_back(x);
            } else {
                S_other.push_back(x);
            }
            placed = true;
        } else {
            // Only a and b exist; arbitrarily put to between
            S_between.push_back(x);
            placed = true;
        }
        (void)placed;
    }
    // Resolve amb_bx similarly using S_other if available, else S_between
    for(int x: amb_bx){
        bool placed = false;
        if(!S_other.empty()){
            int y = S_other[0];
            QueryResult res = ask_query(b, x, y);
            int middle = get_middle_from_query(res, b, x, y);
            if(middle == b){
                // opposite sides -> x in between arc
                S_between.push_back(x);
            } else {
                S_other.push_back(x);
            }
            placed = true;
        } else if(!S_between.empty()){
            int y = S_between[0];
            QueryResult res = ask_query(b, x, y);
            int middle = get_middle_from_query(res, b, x, y);
            if(middle == b){
                // x opposite to y relative to b -> x in other arc
                S_other.push_back(x);
            } else {
                S_between.push_back(x);
            }
            placed = true;
        } else {
            S_other.push_back(x);
            placed = true;
        }
        (void)placed;
    }

    // Sort S_between using anchor a, S_other using anchor b
    Comparator cmpA{a, b};
    Comparator cmpB{b, a};
    sort(S_between.begin(), S_between.end(), cmpA);
    sort(S_other.begin(), S_other.end(), cmpB);

    // Build final sequence: a, S_between, b, S_other
    vector<int> order;
    order.reserve(n);
    order.push_back(a);
    for(int x: S_between) order.push_back(x);
    order.push_back(b);
    for(int x: S_other) order.push_back(x);

    // Ensure we have all n elements
    if((int)order.size() != n){
        // In case of duplicates or missing due to unexpected behavior, fill remaining arbitrarily
        vector<int> used(n,0);
        for(int v: order) if(v>=0 && v<n) used[v]=1;
        for(int i=0;i<n;i++) if(!used[i]) order.push_back(i);
        while((int)order.size()>n) order.pop_back();
    }

    cout << "! ";
    for(int i=0;i<n;i++){
        if(i) cout << " ";
        cout << order[i];
    }
    cout << "\n";
    cout.flush();
    return 0;
}
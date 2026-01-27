#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ull;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ull;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebull;
    return x ^ (x >> 31);
}

struct PairHash {
    size_t operator()(const pair<uint64_t,uint64_t>& p) const noexcept {
        uint64_t h1 = p.first, h2 = p.second;
        uint64_t x = h1 ^ (h2 + 0x9e3779b97f4a7c15ULL + (h1<<6) + (h1>>2));
        return (size_t)x;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long m;
    if(!(cin >> n >> m)) {
        return 0;
    }
    int W = (n + 63) >> 6;
    vector<vector<unsigned long long>> adj1(n, vector<unsigned long long>(W, 0));
    vector<vector<unsigned long long>> adj2_bit(n, vector<unsigned long long>(W, 0));
    vector<vector<int>> g1(n), g2(n);
    vector<pair<int,int>> edges2;
    edges2.reserve(m);
    auto setbit = [&](vector<vector<unsigned long long>>& A, int u, int v){
        A[u][v>>6] |= (1ULL << (v & 63));
    };
    auto hasbit1 = [&](int u, int v)->int{
        return (int)((adj1[u][v>>6] >> (v & 63)) & 1ULL);
    };
    for(long long i=0;i<m;i++){
        int u,v; cin>>u>>v; --u;--v;
        if(u==v) continue;
        g1[u].push_back(v);
        g1[v].push_back(u);
        setbit(adj1,u,v);
        setbit(adj1,v,u);
    }
    for(long long i=0;i<m;i++){
        int u,v; cin>>u>>v; --u;--v;
        if(u==v) continue;
        g2[u].push_back(v);
        g2[v].push_back(u);
        setbit(adj2_bit,u,v);
        setbit(adj2_bit,v,u);
        if(u<v) edges2.emplace_back(u,v);
        else edges2.emplace_back(v,u);
    }
    // Degrees
    vector<int> deg1(n), deg2(n);
    for(int i=0;i<n;i++){ deg1[i] = (int)g1[i].size(); deg2[i] = (int)g2[i].size(); }
    // Initial colors from degree with unified mapping
    vector<int> c1(n), c2(n);
    unordered_map<int,int> deg2col;
    deg2col.reserve(n*2);
    int cid = 0;
    for(int i=0;i<n;i++){
        int d = deg1[i];
        auto it = deg2col.find(d);
        if(it==deg2col.end()){
            deg2col.emplace(d, cid);
            c1[i] = cid++;
        }else c1[i] = it->second;
    }
    for(int i=0;i<n;i++){
        int d = deg2[i];
        auto it = deg2col.find(d);
        if(it==deg2col.end()){
            deg2col.emplace(d, cid);
            c2[i] = cid++;
        }else c2[i] = it->second;
    }
    auto compute_signatures = [&](const vector<vector<int>>& g, const vector<int>& col, int numColors){
        vector<pair<uint64_t,uint64_t>> sig(n);
        vector<int> seen(numColors+5, 0), cnt(numColors+5, 0);
        int timer = 1;
        for(int i=0;i<n;i++){
            ++timer;
            vector<int> used;
            used.reserve(g[i].size());
            for(int j: g[i]){
                int c = col[j];
                if(seen[c] != timer){
                    seen[c] = timer;
                    cnt[c] = 1;
                    used.push_back(c);
                }else{
                    cnt[c]++;
                }
            }
            sort(used.begin(), used.end());
            uint64_t h1 = splitmix64((uint64_t)col[i] + 0x9f4a7c15ULL) ^ 0x123456789abcdef0ULL;
            uint64_t h2 = splitmix64((uint64_t)col[i] + 0x1bd11bdaa9fc1a22ULL) ^ 0xfedcba9876543210ULL;
            for(int c : used){
                uint64_t x = (((uint64_t)c) << 32) ^ (uint64_t)cnt[c];
                uint64_t mx1 = splitmix64(x ^ 0x6a09e667f3bcc909ULL);
                uint64_t mx2 = splitmix64(x ^ 0xbb67ae8584caa73bULL);
                h1 ^= mx1;
                h1 = splitmix64(h1 + 0x3c6ef372fe94f82bULL);
                h2 ^= mx2;
                h2 = splitmix64(h2 + 0xa54ff53a5f1d36f1ULL);
            }
            sig[i] = {h1,h2};
        }
        return sig;
    };
    // 1-WL refinement
    int max_iter = 7;
    for(int it=0; it<max_iter; ++it){
        int numColors = max(*max_element(c1.begin(), c1.end()),
                            *max_element(c2.begin(), c2.end())) + 1;
        auto sig1 = compute_signatures(g1, c1, numColors);
        auto sig2 = compute_signatures(g2, c2, numColors);
        unordered_map<pair<uint64_t,uint64_t>, int, PairHash> mp;
        mp.reserve(n*4);
        int newId = 0;
        vector<int> nc1(n), nc2(n);
        for(int i=0;i<n;i++){
            auto key = sig1[i];
            auto itf = mp.find(key);
            if(itf==mp.end()){
                mp.emplace(key, newId);
                nc1[i] = newId++;
            }else{
                nc1[i] = itf->second;
            }
        }
        for(int i=0;i<n;i++){
            auto key = sig2[i];
            auto itf = mp.find(key);
            if(itf==mp.end()){
                mp.emplace(key, newId);
                nc2[i] = newId++;
            }else{
                nc2[i] = itf->second;
            }
        }
        if(nc1==c1 && nc2==c2) break;
        c1.swap(nc1);
        c2.swap(nc2);
    }
    // Create a hash of neighbor-colors for final key (reuse compute_signatures)
    int numColors = max(*max_element(c1.begin(), c1.end()),
                        *max_element(c2.begin(), c2.end())) + 1;
    auto sigKey1 = compute_signatures(g1, c1, numColors);
    auto sigKey2 = compute_signatures(g2, c2, numColors);
    // Additional features: sum of neighbor degrees
    vector<long long> sdeg1(n,0), sdeg2(n,0);
    for(int i=0;i<n;i++){
        long long s=0;
        for(int j: g1[i]) s += deg1[j];
        sdeg1[i]=s;
    }
    for(int i=0;i<n;i++){
        long long s=0;
        for(int j: g2[i]) s += deg2[j];
        sdeg2[i]=s;
    }
    struct Key {
        int col;
        int deg;
        long long sdeg;
        uint64_t h1,h2;
        int id;
    };
    vector<Key> K1(n), K2(n);
    for(int i=0;i<n;i++){
        K1[i] = {c1[i], deg1[i], sdeg1[i], sigKey1[i].first, sigKey1[i].second, i};
        K2[i] = {c2[i], deg2[i], sdeg2[i], sigKey2[i].first, sigKey2[i].second, i};
    }
    auto cmpKey = [](const Key& a, const Key& b){
        if(a.col != b.col) return a.col < b.col;
        if(a.deg != b.deg) return a.deg < b.deg;
        if(a.sdeg != b.sdeg) return a.sdeg < b.sdeg;
        if(a.h1 != b.h1) return a.h1 < b.h1;
        if(a.h2 != b.h2) return a.h2 < b.h2;
        return a.id < b.id;
    };
    sort(K1.begin(), K1.end(), cmpKey);
    sort(K2.begin(), K2.end(), cmpKey);
    vector<int> p(n,-1), inv(n,-1);
    for(int k=0;k<n;k++){
        int v2 = K2[k].id;
        int v1 = K1[k].id;
        p[v2] = v1;
        inv[v1] = v2;
    }
    // Compute initial matched edges count
    long long matched = 0;
    for(auto &e: edges2){
        if(hasbit1(p[e.first], p[e.second])) matched++;
    }
    // Prepare color classes in G2 for local search
    int C = *max_element(c2.begin(), c2.end()) + 1;
    vector<vector<int>> cls2(C);
    for(int i=0;i<n;i++){
        if(c2[i] >= (int)cls2.size()) cls2.resize(c2[i]+1);
        cls2[c2[i]].push_back(i);
    }
    // Local improvement by random swaps
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto rand_int = [&](int l, int r)->int{
        uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    };
    auto delta_swap = [&](int x, int y)->long long {
        if(x==y) return 0;
        int a = p[x], b = p[y];
        if(a==b) return 0;
        long long delta = 0;
        // x neighbors
        for(int w: g2[x]){
            if(w == y) continue;
            delta += hasbit1(b, p[w]) - hasbit1(a, p[w]);
        }
        // y neighbors
        for(int w: g2[y]){
            if(w == x) continue;
            delta += hasbit1(a, p[w]) - hasbit1(b, p[w]);
        }
        return delta;
    };
    auto apply_swap = [&](int x, int y, long long d){
        matched += d;
        int a = p[x], b = p[y];
        swap(p[x], p[y]);
        inv[a] = y;
        inv[b] = x;
    };
    auto start = chrono::steady_clock::now();
    double timeLimit = 0.65; // seconds for local search
    int attempts = 0;
    int maxAttempts = max(2000, min(200000, n * 100));
    while(attempts < maxAttempts){
        if((attempts & 255) == 0){
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start).count();
            if(elapsed > timeLimit) break;
        }
        attempts++;
        int x = rand_int(0, n-1);
        int col = c2[x];
        int y;
        if((int)cls2[col].size() > 1 && (rng() & 3) != 0){
            // within class
            int idx = rand_int(0, (int)cls2[col].size()-1);
            y = cls2[col][idx];
            if(y==x){
                if(cls2[col].size() >= 2){
                    idx = (idx + 1) % cls2[col].size();
                    y = cls2[col][idx];
                } else {
                    do { y = rand_int(0, n-1); } while(y==x);
                }
            }
        } else {
            // across classes
            do { y = rand_int(0, n-1); } while(y==x);
        }
        // Try few candidates pick best
        long long bestDelta = LLONG_MIN;
        int bestY = y;
        int samples = 4;
        for(int s=0;s<samples;s++){
            long long d = delta_swap(x, y);
            if(d > bestDelta){
                bestDelta = d; bestY = y;
            }
            // pick another y from same class if possible
            if((int)cls2[col].size() > 1){
                int idx = rand_int(0, (int)cls2[col].size()-1);
                y = cls2[col][idx];
                if(y==x){
                    if(cls2[col].size() >= 2){
                        idx = (idx + 1) % cls2[col].size();
                        y = cls2[col][idx];
                    } else {
                        do { y = rand_int(0, n-1); } while(y==x);
                    }
                }
            } else {
                do { y = rand_int(0, n-1); } while(y==x);
            }
        }
        if(bestDelta > 0){
            long long d = delta_swap(x, bestY);
            if(d > 0) apply_swap(x, bestY, d);
        }
    }
    // Output permutation p: p_i = j means vertex i of G2 maps to vertex j of G1 (1-based)
    for(int i=0;i<n;i++){
        if(i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}
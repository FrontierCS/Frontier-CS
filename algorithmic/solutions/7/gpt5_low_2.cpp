#include <bits/stdc++.h>
using namespace std;

struct Edge { int to, w; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long L, R;
    if(!(cin >> L >> R)) return 0;

    auto bits_of = [](long long x){
        vector<int> b;
        while(x){ b.push_back((int)(x&1)); x>>=1; }
        if(b.empty()) b.push_back(0);
        reverse(b.begin(), b.end());
        return b;
    };

    int lenL = 64 - __builtin_clzll(L);
    int lenR = 64 - __builtin_clzll(R);

    vector<int> Lbits = bits_of(L);
    vector<int> Rbits = bits_of(R);

    // Suffix arrays excluding MSB
    vector<int> lowA_suf, lowB_suf, highA_suf, highB_suf, bothA_suf, bothB_suf;

    bool equalLen = (lenL == lenR);

    if (equalLen) {
        // both category: A=L, B=R
        for (int i = 1; i < (int)Lbits.size(); ++i) bothA_suf.push_back(Lbits[i]);
        for (int i = 1; i < (int)Rbits.size(); ++i) bothB_suf.push_back(Rbits[i]);
    } else {
        // low category: A=L, B=2^{lenL}-1
        for (int i = 1; i < (int)Lbits.size(); ++i) lowA_suf.push_back(Lbits[i]);
        lowB_suf.assign(lenL - 1, 1);
        // high category: A=2^{lenR-1}, B=R
        highA_suf.assign(lenR - 1, 0);
        for (int i = 1; i < (int)Rbits.size(); ++i) highB_suf.push_back(Rbits[i]);
    }

    // Graph storage
    vector<vector<Edge>> g(1); // 1-based, g[0] unused

    auto newNode = [&](){
        g.push_back({});
        return (int)g.size() - 1;
    };

    // Free chain nodes F[d], d=0..lenR-1
    vector<int> freeId(lenR + 1, -1);
    function<int(int)> getFree = [&](int d) -> int {
        if (freeId[d] != -1) return freeId[d];
        int id = newNode();
        freeId[d] = id;
        if (d > 0) {
            int to = getFree(d - 1);
            g[id].push_back({to, 0});
            g[id].push_back({to, 1});
        }
        // d==0: sink with outdegree 0
        return id;
    };

    // Categories: 0=mid, 1=low, 2=high, 3=both
    // Memoization for constrained states
    unordered_map<long long,int> memo;
    memo.reserve(1024);

    auto keyOf = [&](int cat, int d, int lo, int hi)->long long{
        // pack into 64-bit
        return ((long long)cat<<40) | ((long long)d<<32) | ((long long)lo<<1) | (long long)hi;
    };

    function<int(int,int,int,int)> build_state = [&](int cat, int d, int lo, int hi)->int {
        if (d == 0) return getFree(0);
        if (!lo && !hi) return getFree(d);
        long long key = keyOf(cat, d, lo, hi);
        auto it = memo.find(key);
        if (it != memo.end()) return it->second;
        int id = newNode();
        memo[key] = id;

        auto getBits = [&](int cat, int idx, int &Ab, int &Bb){
            if (cat == 0) { Ab = 0; Bb = 1; }
            else if (cat == 1) { Ab = lowA_suf[idx]; Bb = lowB_suf[idx]; }
            else if (cat == 2) { Ab = highA_suf[idx]; Bb = highB_suf[idx]; }
            else { Ab = bothA_suf[idx]; Bb = bothB_suf[idx]; }
        };

        int idx; // index in suffix arrays
        // For suffix arrays, total length equals initial d0; current index = len_suf - d
        // We always enter with d equal to remaining suffix length. So idx = len_suf - d.
        // For mid category, bits are constant so idx doesn't matter but compute for consistency.
        // Determine len_suf based on category:
        int len_suf = d; // for mid, this definition works
        if (cat == 1) len_suf = (int)lowA_suf.size();
        else if (cat == 2) len_suf = (int)highA_suf.size();
        else if (cat == 3) len_suf = (int)bothA_suf.size();
        idx = len_suf - d;

        for (int b = 0; b <= 1; ++b) {
            int Ab, Bb;
            getBits(cat, idx, Ab, Bb);
            if (lo && b < Ab) continue;
            if (hi && b > Bb) continue;
            int lo2 = lo && (b == Ab);
            int hi2 = hi && (b == Bb);
            int to = build_state(cat, d - 1, lo2, hi2);
            g[id].push_back({to, b});
        }
        return id;
    };

    int start = newNode(); // node 1
    // Ensure sink exists
    getFree(0);

    if (equalLen) {
        int d = lenL - 1;
        if (lenL >= 1) {
            int to = (d==0)? getFree(0) : build_state(3, d, 1, 1);
            g[start].push_back({to, 1});
        }
    } else {
        // lenL
        if (lenL >= 1) {
            int d = lenL - 1;
            int to = (d==0)? getFree(0) : build_state(1, d, 1, 1);
            g[start].push_back({to, 1});
        }
        // middle lengths
        for (int len = lenL + 1; len <= lenR - 1; ++len) {
            int d = len - 1;
            int to = (d==0)? getFree(0) : build_state(0, d, 1, 1);
            g[start].push_back({to, 1});
        }
        // lenR
        if (lenR >= 1) {
            int d = lenR - 1;
            int to = (d==0)? getFree(0) : build_state(2, d, 1, 1);
            g[start].push_back({to, 1});
        }
    }

    // Output
    int n = (int)g.size() - 1;
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        cout << g[i].size();
        for (auto &e : g[i]) cout << " " << e.to << " " << e.w;
        cout << "\n";
    }
    return 0;
}
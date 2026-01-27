#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<vector<uint8_t>> D(n, vector<uint8_t>(n));
    vector<vector<uint8_t>> F(n, vector<uint8_t>(n));
    vector<int> rD(n,0), cD(n,0), rF(n,0), cF(n,0);
    
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x; cin >> x;
            D[i][j] = (uint8_t)x;
            rD[i] += x;
            cD[j] += x;
        }
    }
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x; cin >> x;
            F[i][j] = (uint8_t)x;
            rF[i] += x;
            cF[j] += x;
        }
    }
    
    // Degrees (sum of row and column) for heuristic
    vector<int> degD(n), degF(n);
    for (int i = 0; i < n; ++i) {
        degD[i] = rD[i] + cD[i];
        degF[i] = rF[i] + cF[i];
    }
    
    // Sort facilities by descending degF
    vector<int> facOrder(n);
    iota(facOrder.begin(), facOrder.end(), 0);
    sort(facOrder.begin(), facOrder.end(), [&](int a, int b){
        if (degF[a] != degF[b]) return degF[a] > degF[b];
        return a < b;
    });
    
    // Sort locations by ascending degD
    vector<int> locOrder(n);
    iota(locOrder.begin(), locOrder.end(), 0);
    sort(locOrder.begin(), locOrder.end(), [&](int a, int b){
        if (degD[a] != degD[b]) return degD[a] < degD[b];
        return a < b;
    });
    
    // Initial assignment: high F-degree -> low D-degree
    vector<int> p(n, -1);          // facility -> location
    vector<int> facAtLoc(n, -1);   // location -> facility
    for (int idx = 0; idx < n; ++idx) {
        int u = facOrder[idx];
        int l = locOrder[idx];
        p[u] = l;
        facAtLoc[l] = u;
    }
    
    // Prepare helpers for local search
    vector<int> locRank(n);
    for (int i = 0; i < n; ++i) locRank[locOrder[i]] = i;
    
    auto deltaSwap = [&](int u, int v) -> long long {
        if (u == v) return 0;
        int a = p[u];
        int b = p[v];
        long long delta = 0;
        // Sum over k
        // Using pointers to speed up inner loop
        uint8_t* Fu = F[u].data();
        uint8_t* Fv = F[v].data();
        for (int k = 0; k < n; ++k) {
            int pk = p[k];
            // Terms with F[u][k] and F[v][k]
            if (Fu[k]) {
                delta += (long long)D[b][pk] - (long long)D[a][pk];
            }
            if (Fv[k]) {
                delta += (long long)D[a][pk] - (long long)D[b][pk];
            }
            // Terms with F[k][u] and F[k][v]
            if (F[k][u]) {
                delta += (long long)D[pk][b] - (long long)D[pk][a];
            }
            if (F[k][v]) {
                delta += (long long)D[pk][a] - (long long)D[pk][b];
            }
        }
        return delta;
    };
    
    // Local search: few passes, limited candidates
    mt19937 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
    int passes = 2;
    int maxCand = min(8, n-1);
    vector<int> order = facOrder; // start with deg order
    for (int pass = 0; pass < passes; ++pass) {
        // Shuffle order slightly for diversity except first pass
        if (pass > 0) shuffle(order.begin(), order.end(), rng);
        for (int idx = 0; idx < n; ++idx) {
            int u = order[idx];
            int a = p[u];
            vector<int> vlist;
            vlist.reserve(maxCand);
            // Choose candidates based on degree mismatch
            bool highF = (degF[u] * 2 >= degF[facOrder[n/2]] * 2); // rough threshold using median-ish
            int take = 0;
            if (highF) {
                // prefer locations with smallest degD
                for (int t = 0; t < n && take < maxCand; ++t) {
                    int lc = locOrder[t];
                    int v = facAtLoc[lc];
                    if (v != u) {
                        vlist.push_back(v);
                        ++take;
                    }
                }
            } else {
                // prefer locations with largest degD
                for (int t = n-1; t >= 0 && take < maxCand; --t) {
                    int lc = locOrder[t];
                    int v = facAtLoc[lc];
                    if (v != u) {
                        vlist.push_back(v);
                        ++take;
                    }
                }
            }
            // Fill with random candidates if needed
            uniform_int_distribution<int> dist(0, n-1);
            while ((int)vlist.size() < maxCand) {
                int v = dist(rng);
                if (v != u) vlist.push_back(v);
            }
            // Try first improvement
            bool improved = false;
            for (int v : vlist) {
                long long d = deltaSwap(u, v);
                if (d < 0) {
                    // apply swap
                    int aLoc = p[u], bLoc = p[v];
                    swap(p[u], p[v]);
                    facAtLoc[aLoc] = v;
                    facAtLoc[bLoc] = u;
                    improved = true;
                    break;
                }
            }
            (void)improved;
        }
    }
    
    // Output permutation 1-based
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}
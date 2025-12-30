#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;
        vector<long long> D;
        D.assign(1LL * n * n, 0);
        auto idx = [n](int i, int j) { return 1LL * (i - 1) * n + (j - 1); };
        
        // Read full n x n distance matrix
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                long long x;
                cin >> x;
                D[idx(i, j)] = x;
            }
        }
        
        vector<int> order(n);
        iota(order.begin(), order.end(), 1);
        sort(order.begin(), order.end(), [&](int a, int b){
            return D[idx(1, a)] < D[idx(1, b)];
        });
        
        vector<char> inserted(n + 1, false);
        inserted[order[0]] = true; // root
        
        vector<tuple<int,int,long long>> edges;
        for (int t = 1; t < n; ++t) {
            int v = order[t];
            long long dv = D[idx(1, v)];
            int best = -1;
            long long bestd = -1;
            for (int k = 0; k < t; ++k) {
                int u = order[k];
                if (!inserted[u]) continue;
                long long du = D[idx(1, u)];
                long long duv = D[idx(u, v)];
                if (du + duv == dv) {
                    if (du > bestd) {
                        bestd = du;
                        best = u;
                    }
                }
            }
            if (best == -1) {
                // Fallback: connect to closest previous node if invariant fails
                long long mn = LLONG_MAX;
                int ubest = order[0];
                for (int k = 0; k < t; ++k) {
                    int u = order[k];
                    if (!inserted[u]) continue;
                    long long duv = D[idx(u, v)];
                    if (duv < mn) {
                        mn = duv;
                        ubest = u;
                    }
                }
                best = ubest;
            }
            long long w = D[idx(best, v)];
            edges.emplace_back(best, v, w);
            inserted[v] = true;
        }
        
        // Output in one line with '!' prefix as described
        cout << "!";
        for (auto &e : edges) {
            int u, v; long long w;
            tie(u, v, w) = e;
            cout << " " << u << " " << v << " " << w;
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}
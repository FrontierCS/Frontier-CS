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
        vector<vector<long long>> d(n + 1, vector<long long>(n + 1, 0));
        for (int i = 1; i <= n; ++i) d[i][i] = 0;
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                long long x; 
                cin >> x;
                d[i][j] = d[j][i] = x;
            }
        }
        
        if (n == 1) {
            cout << "!\n";
            continue;
        }
        
        vector<long long> dr(n + 1, 0);
        for (int i = 1; i <= n; ++i) dr[i] = d[1][i];
        
        vector<pair<long long,int>> order;
        order.reserve(n);
        for (int i = 1; i <= n; ++i) order.push_back({dr[i], i});
        sort(order.begin(), order.end());
        
        vector<int> processed;
        processed.reserve(n);
        processed.push_back(1);
        
        vector<tuple<int,int,long long>> edges;
        edges.reserve(n - 1);
        
        for (auto &p : order) {
            int v = p.second;
            if (v == 1) continue;
            long long D = -1;
            int z = -1;
            for (int w : processed) {
                long long l = (dr[w] + dr[v] - d[w][v]) / 2;
                if (l > D) {
                    D = l;
                    z = (dr[w] == l ? w : -1);
                } else if (l == D) {
                    if (z == -1 && dr[w] == l) z = w;
                }
            }
            if (z == -1) {
                // Fallback: choose any with max l, then find ancestor by scanning processed
                // but ideally shouldn't happen for valid tree metrics
                for (int w : processed) {
                    long long l = (dr[w] + dr[v] - d[w][v]) / 2;
                    if (l == D) { z = w; break; }
                }
            }
            long long wgt = dr[v] - D;
            if (z == -1) z = 1; // safeguard
            if (wgt < 0) wgt = 0; // safeguard
            edges.emplace_back(z, v, wgt);
            processed.push_back(v);
        }
        
        cout << "!";
        for (auto &e : edges) {
            int u, v;
            long long w;
            tie(u, v, w) = e;
            cout << " " << u << " " << v << " " << w;
        }
        cout << "\n";
    }
    return 0;
}
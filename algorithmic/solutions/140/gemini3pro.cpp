#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <set>

using namespace std;

typedef long long ll;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int b, k, w;
    if (!(cin >> b >> k >> w)) return 0;

    // S corresponds to the coordinate limit.
    // We place probes at corners (-S, -S) and (-S, S) to get x+y and x-y.
    // The max coordinate is 10^8, so S = 10^8 is suitable.
    ll S = 100000000;
    
    // Wave 1: Probe at (-S, -S). 
    // Distance = |x - (-S)| + |y - (-S)| = (x+S) + (y+S) = x + y + 2S
    // Valid since x, y >= -b >= -S.
    cout << "? 1 " << -S << " " << -S << endl;
    vector<ll> D1(k);
    for (int i = 0; i < k; ++i) cin >> D1[i];
    
    // Wave 2: Probe at (-S, S).
    // Distance = |x - (-S)| + |y - S| = (x+S) + (S-y) = x - y + 2S
    // Valid since x >= -b >= -S and y <= b <= S.
    cout << "? 1 " << -S << " " << S << endl;
    vector<ll> D2(k);
    for (int i = 0; i < k; ++i) cin >> D2[i];
    
    // Compute possible values for x+y (U) and x-y (V)
    vector<ll> U(k), V(k);
    for (int i = 0; i < k; ++i) U[i] = D1[i] - 2 * S;
    for (int i = 0; i < k; ++i) V[i] = D2[i] - 2 * S;

    // Initialize compatibility matrix based on parity and bounds
    // compatible[i][j] is true if U[i] and V[j] can form a valid point
    vector<vector<bool>> compatible(k, vector<bool>(k, false));
    for (int i = 0; i < k; ++i) {
        for (int j = 0; j < k; ++j) {
            ll sum = U[i];
            ll diff = V[j];
            // x+y and x-y must have the same parity (sum+diff = 2x)
            if (abs(sum % 2) != abs(diff % 2)) continue;
            
            ll x = (sum + diff) / 2;
            ll y = (sum - diff) / 2;
            
            // Check bounds
            if (abs(x) <= b && abs(y) <= b) {
                compatible[i][j] = true;
            }
        }
    }

    // Perform random queries to eliminate false candidates
    // We reserve 2 queries for the initial scan, so we can use up to w-2 more.
    // However, ~15-20 random queries are more than sufficient to disambiguate k=20 points.
    int max_random_queries = min(w - 2, 18);

    mt19937_64 rng(1337); 
    uniform_int_distribution<ll> coord_dist(-100000000, 100000000);

    for (int q = 0; q < max_random_queries; ++q) {
        ll qx = coord_dist(rng);
        ll qy = coord_dist(rng);
        
        cout << "? 1 " << qx << " " << qy << endl;
        
        vector<ll> D_new(k);
        multiset<ll> D_set;
        for (int i = 0; i < k; ++i) {
            cin >> D_new[i];
            D_set.insert(D_new[i]);
        }

        // Filter compatible pairs
        for (int i = 0; i < k; ++i) {
            for (int j = 0; j < k; ++j) {
                if (!compatible[i][j]) continue;
                
                ll x = (U[i] + V[j]) / 2;
                ll y = (U[i] - V[j]) / 2;
                ll d = abs(x - qx) + abs(y - qy);
                
                // If the calculated distance is not in the returned multiset, this pair is invalid
                if (D_set.find(d) == D_set.end()) {
                    compatible[i][j] = false;
                }
            }
        }
    }

    // Build adjacency list for bipartite matching
    // Left side nodes: indices of U (0..k-1)
    // Right side nodes: indices of V (0..k-1)
    vector<vector<int>> adj(k);
    for (int i = 0; i < k; ++i) {
        for (int j = 0; j < k; ++j) {
            if (compatible[i][j]) {
                adj[i].push_back(j);
            }
        }
    }

    // Find perfect matching using DFS
    // match[v] stores the index of U matched to V[v]
    vector<int> match(k, -1);
    
    auto dfs = [&](auto&& self, int u, vector<bool>& vis) -> bool {
        for (int v : adj[u]) {
            if (vis[v]) continue;
            vis[v] = true;
            if (match[v] < 0 || self(self, match[v], vis)) {
                match[v] = u;
                return true;
            }
        }
        return false;
    };

    for (int i = 0; i < k; ++i) {
        vector<bool> vis(k, false);
        dfs(dfs, i, vis);
    }

    // Output results
    cout << "!";
    for (int j = 0; j < k; ++j) {
        if (match[j] != -1) {
            int i = match[j];
            ll x = (U[i] + V[j]) / 2;
            ll y = (U[i] - V[j]) / 2;
            cout << " " << x << " " << y;
        }
    }
    cout << endl;

    return 0;
}
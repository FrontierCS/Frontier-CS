#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, k;
    long long m;
    double eps;
    if (!(cin >> n >> m >> k >> eps)) return 0;
    
    vector<vector<int>> adj(n);
    adj.reserve(n);
    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue; // ignore self-loops
        --u; --v;
        if (u < 0 || u >= n || v < 0 || v >= n) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Capacity per part due to balance constraint
    int ideal = (n + k - 1) / k; // ceil(n/k)
    int cap = (int)floor((1.0 + eps) * ideal);
    if (cap <= 0) cap = 1;
    
    // Order vertices by degree descending
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (adj[a].size() != adj[b].size()) return adj[a].size() > adj[b].size();
        return a < b;
    });
    
    // Partition assignment
    vector<int> part(n, -1);
    vector<int> psz(k, 0);
    
    // Random engine
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);
    
    vector<int> cnt(k, 0);
    vector<int> touched;
    touched.reserve(k);
    
    const double lambda = 1.0; // balance penalty weight
    
    for (int v : order) {
        // compute neighbor counts per part
        touched.clear();
        for (int u : adj[v]) {
            int pu = part[u];
            if (pu >= 0) {
                if (cnt[pu] == 0) touched.push_back(pu);
                cnt[pu]++;
            }
        }
        int bestp = -1;
        double bestscore = -1e100;
        // Try all parts; prefer those with capacity
        for (int p = 0; p < k; ++p) {
            if (psz[p] >= cap) continue;
            int neigh = 0;
            // if p in touched, neigh = cnt[p]
            // We can check quickly:
            // But since k may be bigger than touched, we just get cnt[p] directly
            neigh = cnt[p];
            double balance_pen = lambda * (double)psz[p] / (double)cap;
            // small random noise to break ties
            double noise = (double)(rng() & 0xFFFF) * 1e-6;
            double score = (double)neigh - balance_pen + noise * 1e-9;
            if (score > bestscore) {
                bestscore = score;
                bestp = p;
            }
        }
        if (bestp == -1) {
            // All full (shouldn't happen). Place to smallest size part.
            int pmin = 0;
            for (int p = 1; p < k; ++p) if (psz[p] < psz[pmin]) pmin = p;
            bestp = pmin;
        }
        part[v] = bestp;
        psz[bestp]++;
        // reset counts
        for (int p : touched) cnt[p] = 0;
    }
    
    // Simple local refinement: try to reduce edge cut by moving vertices with positive gain
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    shuffle(idx.begin(), idx.end(), rng);
    
    for (int v : idx) {
        touched.clear();
        for (int u : adj[v]) {
            int pu = part[u];
            if (pu >= 0) {
                if (cnt[pu] == 0) touched.push_back(pu);
                cnt[pu]++;
            }
        }
        int curp = part[v];
        int curSame = cnt[curp];
        int bestp = curp;
        int bestGain = 0;
        // consider only touched parts to move to (others have 0 neighbors, unlikely beneficial)
        for (int p : touched) {
            if (p == curp) continue;
            if (psz[p] >= cap) continue;
            int gain = cnt[p] - curSame;
            if (gain > bestGain) {
                bestGain = gain;
                bestp = p;
            }
        }
        if (bestp != curp && bestGain > 0) {
            part[v] = bestp;
            psz[curp]--;
            psz[bestp]++;
        }
        for (int p : touched) cnt[p] = 0;
    }
    
    // Output labels in 1..k
    for (int i = 0; i < n; ++i) {
        int p = part[i];
        if (p < 0) p = (int)(i % k);
        if (i) cout << ' ';
        cout << (p + 1);
    }
    cout << '\n';
    return 0;
}
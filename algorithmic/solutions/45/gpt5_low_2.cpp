#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, k;
    long long m;
    double eps;
    if (!(cin >> n >> m >> k >> eps)) return 0;

    vector<vector<int>> g(n);
    g.reserve(n);
    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue; // ignore self-loops
        --u; --v;
        if (u >= 0 && u < n && v >= 0 && v < n) {
            g[u].push_back(v);
            g[v].push_back(u);
        }
    }

    long long ideal = (n + k - 1) / k;
    long long cap = (long long)floor((1.0 + eps) * (double)ideal + 1e-12);
    if (cap < ideal) cap = ideal; // safety

    vector<int> part(n, 0);
    vector<int> partSize(k + 1, 0);
    int remaining = n;

    vector<int> inqMark(n, 0);
    int curMark = 1;

    queue<int> q;
    int currentPart = 1;
    int seedPtr = 0;

    while (remaining > 0 && currentPart <= k) {
        // Prepare for this part
        while (!q.empty()) q.pop();

        // BFS fill for current part up to cap
        while (partSize[currentPart] < cap && remaining > 0) {
            if (q.empty()) {
                // find next unassigned seed
                while (seedPtr < n && part[seedPtr] != 0) seedPtr++;
                if (seedPtr >= n) break; // no unassigned left
                q.push(seedPtr);
                inqMark[seedPtr] = curMark;
                ++seedPtr;
            }
            int v = q.front(); q.pop();
            if (part[v] != 0) continue;
            part[v] = currentPart;
            partSize[currentPart]++;
            remaining--;
            for (int w : g[v]) {
                if (w >= 0 && w < n && part[w] == 0 && inqMark[w] != curMark) {
                    inqMark[w] = curMark;
                    q.push(w);
                }
            }
        }

        curMark++; // move to next part's mark space
        currentPart++;
    }

    // If any unassigned remain (shouldn't, but in case of cap miscalc), assign round-robin within cap
    if (remaining > 0) {
        // Build list of parts with remaining capacity
        vector<int> nextPartIdx;
        nextPartIdx.reserve(k);
        for (int p = 1; p <= k; ++p) {
            if (partSize[p] < cap) nextPartIdx.push_back(p);
        }
        int idx = 0;
        for (int v = 0; v < n; ++v) {
            if (part[v] == 0) {
                while (idx < (int)nextPartIdx.size() && partSize[nextPartIdx[idx]] >= cap) idx++;
                if (idx >= (int)nextPartIdx.size()) break;
                int p = nextPartIdx[idx];
                part[v] = p;
                partSize[p]++;
                remaining--;
            }
        }
        // As a last resort (should not happen), assign any leftover ignoring cap to ensure valid output
        if (remaining > 0) {
            for (int v = 0; v < n && remaining > 0; ++v) {
                if (part[v] == 0) {
                    int p = 1;
                    // choose any p (1..k)
                    part[v] = p;
                    partSize[p]++;
                    remaining--;
                }
            }
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << part[i];
    }
    cout << '\n';
    return 0;
}
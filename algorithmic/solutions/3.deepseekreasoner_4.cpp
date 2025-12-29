#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> parent, sz;
    DSU(int n) {
        parent.resize(n+1);
        sz.resize(n+1);
        for (int i=1; i<=n; i++) parent[i] = i, sz[i] = 1;
    }
    int find(int x) {
        if (parent[x] == x) return x;
        return parent[x] = find(parent[x]);
    }
    bool unite(int a, int b) {
        a = find(a), b = find(b);
        if (a == b) return false;
        if (sz[a] < sz[b]) swap(a, b);
        parent[b] = a;
        sz[a] += sz[b];
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int subtask, n;
    cin >> subtask >> n;

    // Determine number of bits needed
    int L = 0;
    while ((1 << L) <= n) L++;
    // L queries
    vector<int> b(n+1, 0);   // b[i] will store the response bits as an integer

    for (int bit = 0; bit < L; ++bit) {
        vector<int> lst;
        for (int i = 1; i <= n; ++i) {
            if ((i >> bit) & 1) lst.push_back(i);
        }
        cout << lst.size();
        for (int x : lst) cout << ' ' << x;
        cout << endl;
        cout.flush();

        for (size_t idx = 0; idx < lst.size(); ++idx) {
            int resp;
            cin >> resp;
            if (resp) b[lst[idx]] |= (1 << bit);
        }
    }

    // Reconstruct the cycle
    DSU dsu(n);
    vector<int> degree(n+1, 0);
    vector<bool> available(n+1, true);  // degree < 2
    vector<vector<int>> adj(n+1);
    int edges_added = 0;

    // Helper to enumerate submasks
    auto enumerate_submasks = [&](int mask, vector<int>& out) {
        out.clear();
        int submask = mask;
        while (submask) {
            out.push_back(submask);
            submask = (submask - 1) & mask;
        }
        out.push_back(0);
    };

    for (int i = 1; i <= n; ++i) {
        int target = b[i];
        vector<vector<int>> candidates;

        if (target == 0) {
            candidates.push_back({});   // empty set
        } else {
            // Single neighbor candidate
            if (target <= n && target < i && available[target]) {
                candidates.push_back({target});
            }
            // Pair candidates: enumerate first part
            vector<int> submasks;
            enumerate_submasks(target, submasks);
            for (int s : submasks) {
                if (s == 0) continue;
                if (s > n || s >= i || !available[s]) continue;
                int remaining = target ^ s;  // bits in target not in s
                // Now we need t such that (s | t) == target.
                // t must have all bits of remaining, and can have any subset of s.
                // Enumerate t_sub as submask of s
                vector<int> t_subs;
                enumerate_submasks(s, t_subs);
                for (int t_sub : t_subs) {
                    int t = remaining | t_sub;
                    if (t == 0) continue;
                    if (t > n || t >= i || !available[t]) continue;
                    if (t == s) continue;   // would be same as single
                    candidates.push_back({s, t});
                }
            }
        }

        // Filter candidates
        vector<vector<int>> valid;
        for (auto& S : candidates) {
            // Check degree: already ensured by available[].
            // Check cycle creation
            int cycles = 0;
            for (int j : S) {
                if (dsu.find(i) == dsu.find(j)) cycles++;
            }
            if (cycles > 1) continue;
            if (cycles == 1 && edges_added + (int)S.size() != n) continue;
            if (edges_added + (int)S.size() > n) continue;
            valid.push_back(S);
        }

        vector<int> chosen;
        if (!valid.empty()) {
            // Prefer larger sets to add more edges
            for (auto& S : valid) {
                if (S.size() == 2) {
                    chosen = S;
                    break;
                }
            }
            if (chosen.empty()) chosen = valid[0];
        } else {
            // Fallback: assume no smaller neighbors if target==0, else assume target itself if possible.
            if (target == 0) chosen = {};
            else if (target <= n && target < i) chosen = {target};
            else chosen = {};
        }

        // Add edges
        for (int j : chosen) {
            degree[i]++; degree[j]++;
            adj[i].push_back(j);
            adj[j].push_back(i);
            dsu.unite(i, j);
            if (degree[j] == 2) available[j] = false;
            edges_added++;
        }
        if (degree[i] == 2) available[i] = false;
    }

    // Build the cycle starting from 1
    vector<int> cycle;
    cycle.push_back(1);
    int prev = 1, cur = adj[1][0];
    while (cur != 1) {
        cycle.push_back(cur);
        int nxt = (adj[cur][0] == prev) ? adj[cur][1] : adj[cur][0];
        prev = cur;
        cur = nxt;
    }

    cout << -1;
    for (int x : cycle) cout << ' ' << x;
    cout << endl;
    cout.flush();

    return 0;
}
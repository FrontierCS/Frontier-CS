#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;
    vector<vector<int>> adj(n + 1);
    vector<int> indeg(n + 1, 0);
    vector<pair<int,int>> edges(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        edges[i] = {a, b};
        adj[a].push_back(b);
        indeg[b]++;
    }

    // Topological order (Kahn's algorithm)
    queue<int> q;
    for (int i = 1; i <= n; ++i) {
        if (indeg[i] == 0) q.push(i);
    }
    vector<int> topo;
    topo.reserve(n);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        topo.push_back(u);
        for (int v : adj[u]) {
            if (--indeg[v] == 0) q.push(v);
        }
    }
    if ((int)topo.size() != n) {
        // Graph should be a DAG, but if not, just fill with 1..n
        topo.clear();
        for (int i = 1; i <= n; ++i) topo.push_back(i);
    }

    // Make complete DAG according to topo: add all forward edges
    long long K = 1LL * n * (n - 1) / 2;
    cout << K << '\n';
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            cout << "+ " << topo[i] << ' ' << topo[j] << '\n';
        }
    }
    cout.flush();

    // Precompute mapping nimber -> vertex (after complete DAG)
    // nimber of topo[pos] = n - (pos+1), since pos is 0-indexed
    // So vertex for nimber M is topo[n - 1 - M].
    vector<int> nim_to_vertex(n);
    for (int pos = 0; pos < n; ++pos) {
        int g = n - 1 - pos;
        nim_to_vertex[g] = topo[pos];
    }

    // Precompute vertices for powers of two nimbers
    vector<int> powVerts;
    for (int b = 0; (1 << b) < n; ++b) {
        int M = (1 << b);
        powVerts.push_back(nim_to_vertex[M]);
    }

    // T rounds
    for (int round = 0; round < T; ++round) {
        bool found = false;
        for (int M = 0; M < n; ++M) {
            // Build multiset S such that XOR of nimbers equals M
            if (M == 0) {
                cout << "? 0" << '\n';
            } else {
                vector<int> S;
                for (int b = 0; (1 << b) <= M; ++b) {
                    if (M & (1 << b)) {
                        if (b < (int)powVerts.size())
                            S.push_back(powVerts[b]);
                    }
                }
                cout << "? " << S.size();
                for (int x : S) cout << ' ' << x;
                cout << '\n';
            }
            cout.flush();

            string ans;
            if (!(cin >> ans)) return 0;
            if (ans == "Lose") {
                int v = nim_to_vertex[M];
                cout << "! " << v << '\n';
                cout.flush();
                string verdict;
                if (!(cin >> verdict)) return 0;
                if (verdict == "Wrong") return 0;
                found = true;
                break;
            } else if (ans == "Wrong") {
                return 0;
            } else if (ans == "Correct") {
                // Unexpected, but handle gracefully
                continue;
            } else {
                // "Win" or "Draw" (Draw shouldn't occur with complete DAG)
                continue;
            }
        }
        if (!found) {
            // Fallback (shouldn't happen)
            int v = topo[0];
            cout << "! " << v << '\n';
            cout.flush();
            string verdict;
            if (!(cin >> verdict)) return 0;
            if (verdict == "Wrong") return 0;
        }
    }
    return 0;
}
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    vector<pair<int, int>> edges(M);
    vector<vector<int>> adj(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    const int Q = 35;
    vector<int> received(Q);
    vector<vector<bitset<10001>>> reach(Q, vector<bitset<10001>>(N));
    for (int q = 0; q < Q; q++) {
        vector<int> choice(M);
        for (int i = 0; i < M; i++) {
            long long seed = (long long)i * 1103515245LL + 12345LL + q;
            choice[i] = (seed >> 16) & 1;
        }
        cout << 0;
        for (int c : choice) cout << " " << c;
        cout << endl;
        cout.flush();
        int x;
        cin >> x;
        received[q] = x;
        vector<vector<int>> dir_adj(N);
        for (int i = 0; i < M; i++) {
            int u = edges[i].first, v = edges[i].second;
            int ch = choice[i];
            if (ch == 0) {
                dir_adj[u].push_back(v);
            } else {
                dir_adj[v].push_back(u);
            }
        }
        for (int s = 0; s < N; s++) {
            vector<bool> vis(N, false);
            queue<int> qu;
            qu.push(s);
            vis[s] = true;
            reach[q][s][s] = 1;
            while (!qu.empty()) {
                int u = qu.front(); qu.pop();
                for (int v : dir_adj[u]) {
                    if (!vis[v]) {
                        vis[v] = true;
                        qu.push(v);
                        reach[q][s][v] = 1;
                    }
                }
            }
        }
    }
    vector<pair<int, int>> candidates;
    for (int a = 0; a < N; a++) {
        bitset<10001> cand;
        cand.set(0, N);
        for (int q = 0; q < Q; q++) {
            if (received[q]) {
                cand &= reach[q][a];
            } else {
                bitset<10001> not_reach = ~reach[q][a];
                not_reach >>= 0; not_reach <<= (10001 - N); not_reach >>= (10001 - N);
                cand &= not_reach;
            }
        }
        for (int b = cand._Find_first(); b < N; b = cand._Find_next(b)) {
            if (b != a) {
                candidates.emplace_back(a, b);
            }
        }
    }
    assert(candidates.size() == 1);
    auto [A, B] = candidates[0];
    cout << 1 << " " << A << " " << B << endl;
    cout.flush();
    return 0;
}
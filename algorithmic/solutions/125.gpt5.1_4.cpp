#include <bits/stdc++.h>
using namespace std;

// Interactive query helper
int query(int x) {
    cout << "? " << x << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int M = 2 * N;

    const int T = 11;          // number of passes
    const int TOT2 = T - 1;    // bits for grouping (excluding first pass)
    const int MAXT = T;

    // Generate permutations and position arrays
    vector<vector<int>> perm(T, vector<int>(M));
    vector<vector<int>> pos(T, vector<int>(M + 1));
    vector<int> base(M);
    iota(base.begin(), base.end(), 1);

    mt19937 rng(712367);
    for (int t = 0; t < T; ++t) {
        perm[t] = base;
        shuffle(perm[t].begin(), perm[t].end(), rng);
        for (int i = 0; i < M; ++i) {
            pos[t][perm[t][i]] = i;
        }
    }

    // bits[t][i] : orientation bit for index i in pass t
    static unsigned char bits[MAXT][86001];

    int current_r = 0; // S is initially empty, so r=0

    // Perform T passes
    for (int t = 0; t < T; ++t) {
        if (t % 2 == 0) {
            // Insertion pass: S is empty at start
            for (int k = 0; k < M; ++k) {
                int idx = perm[t][k];
                int r = query(idx);
                int delta = r - current_r; // should be 0 or +1
                unsigned char orient = (delta == 1) ? 1 : 0; // 1 if earlier than partner
                bits[t][idx] = orient;
                current_r = r;
            }
            // S now full, r should be N
        } else {
            // Removal pass: S is full at start
            for (int k = 0; k < M; ++k) {
                int idx = perm[t][k];
                int r = query(idx);
                int delta = r - current_r; // should be 0 or -1
                unsigned char orient = (delta == 0) ? 1 : 0; // 1 if earlier than partner
                bits[t][idx] = orient;
                current_r = r;
            }
            // S now empty, r should be 0
        }
    }

    // Offline reconstruction

    // Partition into left/right using first pass bit
    vector<int> leftVerts, rightVerts;
    leftVerts.reserve(N);
    rightVerts.reserve(N);
    vector<int> idL(M + 1, 0), idR(M + 1, 0);

    for (int i = 1; i <= M; ++i) {
        if (bits[0][i] == 1) {
            int id = (int)leftVerts.size();
            leftVerts.push_back(i);
            idL[i] = id + 1; // 1-based
        } else {
            int id = (int)rightVerts.size();
            rightVerts.push_back(i);
            idR[i] = id + 1;
        }
    }

    // Safety: should have N each side
    if ((int)leftVerts.size() != N || (int)rightVerts.size() != N) {
        // Fallback (should never happen)
        for (int i = 1; i <= M; i += 2) {
            cout << "! " << i << " " << i + 1 << endl;
            cout.flush();
        }
        return 0;
    }

    // Group by codes from passes 1..T-1
    int maskAll = (1 << TOT2) - 1;
    int G = 1 << TOT2;
    vector<vector<int>> groupL(G), groupR(G);

    for (int idx = 0; idx < N; ++idx) {
        int v = leftVerts[idx];
        int code = 0;
        for (int t = 1; t < T; ++t) {
            if (bits[t][v]) code |= (1 << (t - 1));
        }
        groupL[code].push_back(idx + 1); // store left ID (1-based)
    }

    for (int idx = 0; idx < N; ++idx) {
        int v = rightVerts[idx];
        int code = 0;
        for (int t = 1; t < T; ++t) {
            if (bits[t][v]) code |= (1 << (t - 1));
        }
        groupR[code].push_back(idx + 1); // store right ID (1-based)
    }

    // Build bipartite graph
    vector<vector<int>> adj(N + 1);
    for (int m = 0; m <= maskAll; ++m) {
        int comp = (~m) & maskAll;
        const auto &Llist = groupL[m];
        const auto &Rlist = groupR[comp];
        if (Llist.empty() || Rlist.empty()) continue;

        for (int lID : Llist) {
            int i = leftVerts[lID - 1];
            for (int rID : Rlist) {
                int j = rightVerts[rID - 1];

                bool ok = true;
                for (int t = 0; t < T; ++t) {
                    bool earlier_i = (pos[t][i] < pos[t][j]);
                    if (bits[t][i]) {
                        if (!earlier_i) { ok = false; break; }
                    } else {
                        if (earlier_i) { ok = false; break; }
                    }
                }
                if (ok) {
                    adj[lID].push_back(rID);
                }
            }
        }
    }

    // Hopcroft-Karp for maximum matching on bipartite graph
    const int INF = 1e9;
    vector<int> dist(N + 1);
    vector<int> matchL(N + 1, 0), matchR(N + 1, 0);

    auto bfs = [&]() -> bool {
        queue<int> q;
        for (int u = 1; u <= N; ++u) {
            if (matchL[u] == 0) {
                dist[u] = 0;
                q.push(u);
            } else {
                dist[u] = INF;
            }
        }
        int distInf = INF;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            if (dist[u] >= distInf) continue;
            for (int v : adj[u]) {
                int mu = matchR[v];
                if (mu == 0) {
                    distInf = dist[u] + 1;
                } else if (dist[mu] == INF) {
                    dist[mu] = dist[u] + 1;
                    q.push(mu);
                }
            }
        }
        return distInf != INF;
    };

    function<bool(int)> dfs = [&](int u) -> bool {
        for (int v : adj[u]) {
            int mu = matchR[v];
            if (mu == 0 || (dist[mu] == dist[u] + 1 && dfs(mu))) {
                matchL[u] = v;
                matchR[v] = u;
                return true;
            }
        }
        dist[u] = INF;
        return false;
    };

    int matching = 0;
    while (bfs()) {
        for (int u = 1; u <= N; ++u) {
            if (matchL[u] == 0 && dfs(u)) {
                ++matching;
            }
        }
    }

    // If something goes wrong, fall back (should be extremely unlikely)
    if (matching != N) {
        for (int i = 1; i <= M; i += 2) {
            cout << "! " << i << " " << i + 1 << endl;
            cout.flush();
        }
        return 0;
    }

    // Output pairs based on matching
    for (int lID = 1; lID <= N; ++lID) {
        int rID = matchL[lID];
        int a = leftVerts[lID - 1];
        int b = rightVerts[rID - 1];
        cout << "! " << a << " " << b << endl;
        cout.flush();
    }

    return 0;
}
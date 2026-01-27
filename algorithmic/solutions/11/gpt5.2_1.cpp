#include <bits/stdc++.h>
using namespace std;

static inline int dirIdx(char c) {
    switch (c) {
        case 'L': return 0;
        case 'R': return 1;
        case 'U': return 2;
        case 'D': return 3;
    }
    return -1;
}

static inline char dirChar(int d) {
    static const char dc[4] = {'L','R','U','D'};
    return dc[d];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<string> g(n);
    for (int i = 0; i < n; i++) cin >> g[i];

    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;

    vector<vector<int>> id(n, vector<int>(m, -1));
    vector<pair<int,int>> pos;
    pos.reserve(n * m);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (g[i][j] == '1') {
                id[i][j] = (int)pos.size();
                pos.push_back({i, j});
            }
        }
    }
    int N = (int)pos.size();
    if (N == 0) {
        cout << "-1\n";
        return 0;
    }

    int startId = id[sr][sc];
    int exitId = id[er][ec];

    vector<array<int,4>> nxt(N);
    static const int dr[4] = {0, 0, -1, 1};
    static const int dc[4] = {-1, 1, 0, 0};
    for (int u = 0; u < N; u++) {
        auto [r,c] = pos[u];
        for (int d = 0; d < 4; d++) {
            int nr = r + dr[d], nc = c + dc[d];
            if (0 <= nr && nr < n && 0 <= nc && nc < m && id[nr][nc] != -1) nxt[u][d] = id[nr][nc];
            else nxt[u][d] = u;
        }
    }

    // Connectivity check: must be able to reach all blank cells from start.
    vector<char> vis(N, 0);
    deque<int> dq;
    vis[startId] = 1;
    dq.push_back(startId);
    int cnt = 1;
    while (!dq.empty()) {
        int u = dq.front(); dq.pop_front();
        for (int d = 0; d < 4; d++) {
            int v = nxt[u][d];
            if (v != u && !vis[v]) {
                vis[v] = 1;
                dq.push_back(v);
                cnt++;
            }
        }
    }
    if (cnt != N) {
        cout << "-1\n";
        return 0;
    }

    // Build predecessor lists for reverse BFS on pair automaton.
    array<vector<vector<int>>, 4> pre;
    for (int d = 0; d < 4; d++) pre[d].assign(N, {});
    for (int u = 0; u < N; u++) {
        for (int d = 0; d < 4; d++) {
            int v = nxt[u][d];
            pre[d][v].push_back(u);
        }
    }

    int N2 = N * N;
    vector<int> dist(N2, -1);
    vector<int> nextPair(N2, -1);
    vector<uint8_t> action(N2, 255);

    // Multi-source BFS from diagonals in reversed pair graph.
    vector<int> q;
    q.reserve(N2);
    for (int i = 0; i < N; i++) {
        int idx = i * N + i;
        dist[idx] = 0;
        nextPair[idx] = idx;
        q.push_back(idx);
    }
    size_t head = 0;
    while (head < q.size()) {
        int cur = q[head++];
        int x = cur / N;
        int y = cur % N;
        int nd = dist[cur] + 1;

        for (int d = 0; d < 4; d++) {
            const auto &px = pre[d][x];
            const auto &py = pre[d][y];
            for (int u : px) {
                int base = u * N;
                for (int v : py) {
                    int pred = base + v;
                    if (dist[pred] != -1) continue;
                    dist[pred] = nd;
                    action[pred] = (uint8_t)d;
                    nextPair[pred] = cur;
                    q.push_back(pred);
                }
            }
        }
    }

    // If not all pairs are mergeable, give up (assume no solution).
    for (int u = 0; u < N; u++) {
        int base = u * N;
        for (int v = 0; v < N; v++) {
            if (dist[base + v] == -1) {
                cout << "-1\n";
                return 0;
            }
        }
    }

    auto buildReset = [&](bool globalScan, string &W, int &sink) -> bool {
        vector<int> curSet(N);
        iota(curSet.begin(), curSet.end(), 0);
        W.clear();
        W.reserve(600000);

        while (curSet.size() > 1) {
            int a = -1, b = -1, bestD = INT_MAX;
            int sz = (int)curSet.size();

            if (!globalScan) {
                a = curSet[0];
                int abase = a * N;
                for (int i = 1; i < sz; i++) {
                    int cand = curSet[i];
                    int d = dist[abase + cand];
                    if (d < bestD) {
                        bestD = d;
                        b = cand;
                    }
                }
            } else {
                for (int i = 0; i < sz; i++) {
                    int u = curSet[i];
                    int ubase = u * N;
                    for (int j = i + 1; j < sz; j++) {
                        int v = curSet[j];
                        int d = dist[ubase + v];
                        if (d < bestD) {
                            bestD = d;
                            a = u;
                            b = v;
                            if (bestD == 1) break;
                        }
                    }
                    if (bestD == 1) break;
                }
            }

            if (bestD < 0 || bestD == INT_MAX || a < 0 || b < 0) return false;

            int p = a * N + b;
            for (int step = 0; step < bestD; step++) {
                int d = (int)action[p];
                char ch = dirChar(d);
                W.push_back(ch);

                // Apply this move to all states in the current image-set.
                for (int i = 0; i < sz; i++) curSet[i] = nxt[curSet[i]][d];

                p = nextPair[p];

                if ((int)W.size() > 700000) {
                    // Early stop: too long, likely won't fit final palindrome within 1e6.
                    // Continue anyway; caller can retry with global scan.
                }
            }

            sort(curSet.begin(), curSet.end());
            curSet.erase(unique(curSet.begin(), curSet.end()), curSet.end());
        }

        sink = curSet[0];
        return true;
    };

    string W;
    int sink = -1;
    if (!buildReset(false, W, sink)) {
        cout << "-1\n";
        return 0;
    }

    // Compute shortest path from sink to exitId.
    auto shortestPath = [&](int src, int dst) -> string {
        vector<int> par(N, -1);
        vector<char> parMove(N, 0);
        deque<int> qq;
        par[src] = src;
        qq.push_back(src);
        while (!qq.empty()) {
            int u = qq.front(); qq.pop_front();
            if (u == dst) break;
            for (int d = 0; d < 4; d++) {
                int v = nxt[u][d];
                if (v == u) continue;
                if (par[v] != -1) continue;
                par[v] = u;
                parMove[v] = dirChar(d);
                qq.push_back(v);
            }
        }
        if (par[dst] == -1) return string(); // should not happen in connected graph
        string pth;
        int cur = dst;
        while (cur != src) {
            pth.push_back(parMove[cur]);
            cur = par[cur];
        }
        reverse(pth.begin(), pth.end());
        return pth;
    };

    string P = shortestPath(sink, exitId);
    string R = W + P;

    // If too long, try global pair selection strategy to reduce word length.
    // Need total length <= 1e6: ans = reverse(R) + T + reverse(T) + R => 2|R| + 2|T|
    // |T| <= 2*(N-1) <= 1798.
    auto estimateMaxR = [&]() -> int { return 500000 - 2000; };

    if ((int)R.size() > estimateMaxR()) {
        string W2;
        int sink2 = -1;
        if (buildReset(true, W2, sink2)) {
            string P2 = shortestPath(sink2, exitId);
            string R2 = W2 + P2;
            if (R2.size() < R.size()) {
                sink = sink2;
                W.swap(W2);
                R.swap(R2);
            }
        }
    }

    // Compute position x after applying reverse(R) from startId.
    int x = startId;
    for (auto it = R.rbegin(); it != R.rend(); ++it) {
        x = nxt[x][dirIdx(*it)];
    }

    // Build DFS tour T from x that visits all nodes (on a spanning tree).
    vector<vector<pair<int,int>>> adj(N);
    adj.assign(N, {});
    for (int u = 0; u < N; u++) {
        for (int d = 0; d < 4; d++) {
            int v = nxt[u][d];
            if (v != u) adj[u].push_back({v, d});
        }
    }

    vector<char> seen2(N, 0);
    static const int opp[4] = {1, 0, 3, 2};
    string T;
    T.reserve(max(0, 2 * (N - 1)));

    function<void(int)> dfs = [&](int u) {
        seen2[u] = 1;
        for (auto [v, d] : adj[u]) {
            if (seen2[v]) continue;
            T.push_back(dirChar(d));
            dfs(v);
            T.push_back(dirChar(opp[d]));
        }
    };
    dfs(x);

    long long totalLen = 2LL * (long long)R.size() + 2LL * (long long)T.size();
    if (totalLen > 1000000LL) {
        cout << "-1\n";
        return 0;
    }

    string revR = R;
    reverse(revR.begin(), revR.end());
    string revT = T;
    reverse(revT.begin(), revT.end());

    cout << revR << T << revT << R << "\n";
    return 0;
}
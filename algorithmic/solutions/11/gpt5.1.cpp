#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> g(n);
    for (int i = 0; i < n; ++i) cin >> g[i];

    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;

    const int dr[4] = {0, 0, -1, 1};
    const int dc[4] = {-1, 1, 0, 0};
    const char dcch[4] = {'L', 'R', 'U', 'D'};

    // Map blank cells to ids
    vector<vector<int>> id(n, vector<int>(m, -1));
    int N = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (g[i][j] == '1')
                id[i][j] = N++;

    if (id[sr][sc] == -1 || id[er][ec] == -1) {
        cout << -1 << '\n';
        return 0;
    }

    if (N == 0) {
        cout << -1 << '\n';
        return 0;
    }

    int sId = id[sr][sc];
    int eId = id[er][ec];

    // Connectivity check: all blanks reachable from start and exit reachable
    vector<int> vis(N, 0);
    queue<int> q;
    vis[sId] = 1;
    q.push(sId);
    while (!q.empty()) {
        int v = q.front(); q.pop();
        int r = -1, c = -1;
        // recover coordinates by scanning - precompute pos arrays for speed
    }
    // Precompute positions for each id
    vector<int> rid(N), cid(N);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (id[i][j] != -1) {
                rid[id[i][j]] = i;
                cid[id[i][j]] = j;
            }

    // BFS connectivity
    fill(vis.begin(), vis.end(), 0);
    q.push(sId);
    vis[sId] = 1;
    int reachCnt = 1;
    while (!q.empty()) {
        int v = q.front(); q.pop();
        int r = rid[v], c = cid[v];
        for (int d = 0; d < 4; ++d) {
            int nr = r + dr[d], nc = c + dc[d];
            if (nr < 0 || nr >= n || nc < 0 || nc >= m) continue;
            if (g[nr][nc] != '1') continue;
            int to = id[nr][nc];
            if (!vis[to]) {
                vis[to] = 1;
                ++reachCnt;
                q.push(to);
            }
        }
    }
    if (!vis[eId] || reachCnt != N) {
        cout << -1 << '\n';
        return 0;
    }

    // Build transition function delta[v][dir]
    vector<array<int,4>> delta(N);
    for (int v = 0; v < N; ++v) {
        int r = rid[v], c = cid[v];
        for (int d = 0; d < 4; ++d) {
            int nr = r + dr[d], nc = c + dc[d];
            if (nr < 0 || nr >= n || nc < 0 || nc >= m || g[nr][nc] != '1')
                delta[v][d] = v; // stay
            else
                delta[v][d] = id[nr][nc];
        }
    }

    // Preimage lists: pre[y][d] = {x | delta[x][d] == y}
    vector<array<vector<int>,4>> pre(N);
    for (int x = 0; x < N; ++x) {
        for (int d = 0; d < 4; ++d) {
            int y = delta[x][d];
            pre[y][d].push_back(x);
        }
    }

    int NN = N * N;
    const int INF = -1;
    vector<int> dist(NN, INF), prev_state(NN, -1);
    vector<char> prev_chr(NN, 0);

    auto idxOf = [N](int a, int b) {
        return a * N + b;
    };

    int startIdx = idxOf(sId, eId);
    queue<int> qq;
    dist[startIdx] = 0;
    qq.push(startIdx);

    bool found = false;
    bool evenCenter = false;
    int finishIdx = -1;
    char centerChar = 0;

    while (!qq.empty() && !found) {
        int cur = qq.front(); qq.pop();
        int a = cur / N;
        int b = cur % N;

        // Even-length palindrome: meet at same vertex
        if (a == b) {
            found = true;
            evenCenter = true;
            finishIdx = cur;
            break;
        }

        // Odd-length palindrome: check if there is direct edge a --c--> b
        for (int d = 0; d < 4; ++d) {
            if (delta[a][d] == b) {
                found = true;
                evenCenter = false;
                finishIdx = cur;
                centerChar = dcch[d];
                break;
            }
        }
        if (found) break;

        // Expand BFS on pairs
        for (int d = 0; d < 4; ++d) {
            int a2 = delta[a][d];
            for (int b2 : pre[b][d]) {
                int nxt = idxOf(a2, b2);
                if (dist[nxt] == INF) {
                    dist[nxt] = dist[cur] + 1;
                    prev_state[nxt] = cur;
                    prev_chr[nxt] = dcch[d];
                    qq.push(nxt);
                }
            }
        }
    }

    if (!found) {
        cout << -1 << '\n';
        return 0;
    }

    // Reconstruct prefix u
    vector<char> u;
    int cur = finishIdx;
    while (cur != startIdx) {
        u.push_back(prev_chr[cur]);
        cur = prev_state[cur];
    }
    reverse(u.begin(), u.end());

    string ans;
    if (evenCenter) {
        ans.reserve(u.size() * 2);
        for (char c : u) ans.push_back(c);
        for (int i = (int)u.size() - 1; i >= 0; --i) ans.push_back(u[i]);
    } else {
        ans.reserve(u.size() * 2 + 1);
        for (char c : u) ans.push_back(c);
        ans.push_back(centerChar);
        for (int i = (int)u.size() - 1; i >= 0; --i) ans.push_back(u[i]);
    }

    if (ans.size() > 1000000u) {
        cout << -1 << '\n';
        return 0;
    }

    cout << ans << '\n';
    return 0;
}
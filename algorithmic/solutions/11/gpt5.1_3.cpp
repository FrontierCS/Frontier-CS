#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];

    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;

    if (sr < 0 || sr >= n || sc < 0 || sc >= m ||
        er < 0 || er >= n || ec < 0 || ec >= m ||
        grid[sr][sc] != '1' || grid[er][ec] != '1') {
        cout << "-1\n";
        return 0;
    }

    // Map blank cells to ids
    vector<vector<int>> id(n, vector<int>(m, -1));
    vector<pair<int,int>> pos;
    pos.reserve(n*m);
    int N = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (grid[i][j] == '1') {
                id[i][j] = N++;
                pos.emplace_back(i, j);
            }
        }
    }

    int sId = id[sr][sc];
    int eId = id[er][ec];

    // Connectivity check (ignores palindrome requirement, just feasibility)
    {
        vector<vector<int>> vis(n, vector<int>(m, 0));
        queue<pair<int,int>> q;
        vis[sr][sc] = 1;
        q.push({sr, sc});
        int dr[4] = {0, 0, -1, 1};
        int dc[4] = {-1, 1, 0, 0};
        while (!q.empty()) {
            auto [r, c] = q.front(); q.pop();
            for (int k = 0; k < 4; ++k) {
                int nr = r + dr[k], nc = c + dc[k];
                if (nr < 0 || nr >= n || nc < 0 || nc >= m) continue;
                if (grid[nr][nc] != '1') continue;
                if (!vis[nr][nc]) {
                    vis[nr][nc] = 1;
                    q.push({nr, nc});
                }
            }
        }
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < m; ++j)
                if (grid[i][j] == '1' && !vis[i][j]) {
                    cout << "-1\n";
                    return 0;
                }
    }

    if (N == 0) {
        cout << "-1\n";
        return 0;
    }

    // Build directed graph of moves (including self-loops)
    const int DIRS = 4;
    int dr[DIRS] = {0, 0, -1, 1}; // L, R, U, D
    int dc[DIRS] = {-1, 1, 0, 0};
    char dch[DIRS] = {'L', 'R', 'U', 'D'};

    vector<array<int,DIRS>> nxt(N);
    for (int u = 0; u < N; ++u) {
        int r = pos[u].first;
        int c = pos[u].second;
        for (int k = 0; k < DIRS; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            int v;
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1')
                v = id[nr][nc];
            else
                v = u; // stay
            nxt[u][k] = v;
        }
    }

    // Build incoming adjacency by label
    vector<array<vector<int>,DIRS>> in_adj(N);
    for (int u = 0; u < N; ++u) {
        for (int k = 0; k < DIRS; ++k) {
            int v = nxt[u][k];
            in_adj[v][k].push_back(u);
        }
    }

    int totalStates = N * N;
    const int INF = (int)1e9;
    vector<int> dist(totalStates, INF);
    vector<short> pu(totalStates, -1), pv(totalStates, -1);
    vector<char> pc(totalStates, -1);

    queue<int> q;

    // Base: center at vertices (even-length palindromes)
    for (int u = 0; u < N; ++u) {
        int idx = u * N + u;
        dist[idx] = 0;
        q.push(idx);
    }

    // Base: direct edges (odd-length palindromes), exclude self-loops since dist[u][u]=0 is better
    for (int u = 0; u < N; ++u) {
        for (int k = 0; k < DIRS; ++k) {
            int v = nxt[u][k];
            if (u == v) continue; // self-loop gives length 0 already
            int idx = u * N + v;
            if (dist[idx] > 1) {
                dist[idx] = 1;
                pu[idx] = -1;
                pv[idx] = -1;
                pc[idx] = (char)k;
                q.push(idx);
            }
        }
    }

    // BFS in product graph from centers outward
    while (!q.empty()) {
        int cur = q.front(); q.pop();
        int dcur = dist[cur];
        int x = cur / N;
        int y = cur % N;

        for (int k = 0; k < DIRS; ++k) {
            const auto &vecX = in_adj[x][k]; // all x0 with edge x0->x label k
            int y0 = nxt[y][k];             // y->y0 label k
            for (int x0 : vecX) {
                int idx2 = x0 * N + y0;
                if (dist[idx2] > dcur + 2) {
                    dist[idx2] = dcur + 2;
                    pu[idx2] = (short)x;
                    pv[idx2] = (short)y;
                    pc[idx2] = (char)k;
                    q.push(idx2);
                }
            }
        }
    }

    int targetIdx = sId * N + eId;
    if (dist[targetIdx] >= INF || dist[targetIdx] > 1000000) {
        cout << "-1\n";
        return 0;
    }

    // Reconstruct palindrome string from sId to eId
    vector<char> outer;
    char center_char = 0;
    bool has_center = false;
    int idx = targetIdx;

    while (true) {
        if (dist[idx] == 0) {
            break; // center is a vertex, no middle char
        }
        if (pu[idx] == -1) {
            // base direct edge: single center char
            center_char = dch[(int)pc[idx]];
            has_center = true;
            break;
        }
        int dir = (int)pc[idx];
        outer.push_back(dch[dir]);
        int x = pu[idx];
        int y = pv[idx];
        idx = x * N + y;
    }

    string S;
    S.reserve(outer.size() * 2 + (has_center ? 1 : 0));
    for (char ch : outer) S.push_back(ch);
    if (has_center) S.push_back(center_char);
    for (int i = (int)outer.size() - 1; i >= 0; --i) S.push_back(outer[i]);

    if ((int)S.size() > 1000000) {
        cout << "-1\n";
        return 0;
    }

    // Verify simulation: palindrome and end position (should hold), and coverage (may fail)
    auto moveDirIndex = [&](char c) -> int {
        if (c == 'L') return 0;
        if (c == 'R') return 1;
        if (c == 'U') return 2;
        if (c == 'D') return 3;
        return -1;
    };

    // Check palindrome property explicitly
    bool isPal = true;
    for (int i = 0, j = (int)S.size() - 1; i < j; ++i, --j) {
        if (S[i] != S[j]) { isPal = false; break; }
    }
    if (!isPal) {
        cout << "-1\n";
        return 0;
    }

    vector<char> visitedCell(N, 0);
    int curId = sId;
    visitedCell[curId] = 1;
    for (char c : S) {
        int dir = moveDirIndex(c);
        if (dir < 0) { cout << "-1\n"; return 0; }
        curId = nxt[curId][dir];
        visitedCell[curId] = 1;
    }

    if (curId != eId) {
        cout << "-1\n";
        return 0;
    }

    // Ensure all blank cells are visited; if not, declare no solution (heuristic limitation)
    for (int i = 0; i < N; ++i) {
        if (!visitedCell[i]) {
            cout << "-1\n";
            return 0;
        }
    }

    cout << S << '\n';
    return 0;
}
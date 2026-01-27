#include <bits/stdc++.h>
using namespace std;

static inline int oppDir(int d) {
    if (d == 0) return 1;
    if (d == 1) return 0;
    if (d == 2) return 3;
    return 2;
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
    vector<pair<int,int>> cells;
    cells.reserve(n*m);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (g[i][j] == '1') {
                id[i][j] = (int)cells.size();
                cells.push_back({i,j});
            }
        }
    }
    int N = (int)cells.size();
    int start = id[sr][sc];
    int exitId = id[er][ec];

    // Connectivity check: all blank cells must be in one component.
    vector<char> vis(N, 0);
    queue<int> q;
    vis[start] = 1;
    q.push(start);
    int dr4[4] = {0, 0, -1, 1};
    int dc4[4] = {-1, 1, 0, 0};
    while (!q.empty()) {
        int v = q.front(); q.pop();
        auto [r,c] = cells[v];
        for (int d = 0; d < 4; d++) {
            int nr = r + dr4[d], nc = c + dc4[d];
            if (nr < 0 || nr >= n || nc < 0 || nc >= m) continue;
            if (g[nr][nc] != '1') continue;
            int u = id[nr][nc];
            if (!vis[u]) {
                vis[u] = 1;
                q.push(u);
            }
        }
    }
    for (int i = 0; i < N; i++) {
        if (!vis[i]) {
            cout << "-1\n";
            return 0;
        }
    }

    // Build deterministic transitions with "stay on invalid move".
    static const char dirChar[4] = {'L','R','U','D'};
    vector<array<int,4>> nxt(N);
    for (int v = 0; v < N; v++) {
        auto [r,c] = cells[v];
        for (int d = 0; d < 4; d++) {
            int nr = r + dr4[d], nc = c + dc4[d];
            if (nr < 0 || nr >= n || nc < 0 || nc >= m || g[nr][nc] != '1') {
                nxt[v][d] = v;
            } else {
                nxt[v][d] = id[nr][nc];
            }
        }
    }

    // Predecessor lists: for each state and direction, up to 2 predecessors in this grid automaton.
    // preList[state][dir][k], preCnt[state][dir]
    vector<array<array<int,2>,4>> preList(N);
    vector<array<uint8_t,4>> preCnt(N);
    for (int s = 0; s < N; s++) for (int d = 0; d < 4; d++) preCnt[s][d] = 0;

    for (int u = 0; u < N; u++) {
        for (int d = 0; d < 4; d++) {
            int v = nxt[u][d];
            uint8_t &cnt = preCnt[v][d];
            if (cnt < 2) preList[v][d][cnt] = u;
            cnt++;
        }
    }

    // Build shortest "merge word" distances and parent pointers in pair automaton (u,v) -> (nxt[u][d], nxt[v][d]).
    const int P = N * N;
    vector<int> parent(P, -1);
    vector<uint8_t> parDir(P, 255);
    vector<int> dist(P, -1);

    vector<int> bfs;
    bfs.reserve(P);
    for (int i = 0; i < N; i++) {
        int pid = i * N + i;
        dist[pid] = 0;
        parent[pid] = pid;
        parDir[pid] = 255;
        bfs.push_back(pid);
    }

    size_t head = 0;
    while (head < bfs.size()) {
        int cur = bfs[head++];
        int x = cur / N;
        int y = cur % N;
        int nd = dist[cur] + 1;

        for (int d = 0; d < 4; d++) {
            uint8_t cx = preCnt[x][d];
            uint8_t cy = preCnt[y][d];
            if (cx == 0 || cy == 0) continue;

            for (uint8_t ix = 0; ix < min<uint8_t>(cx, 2); ix++) {
                int px = preList[x][d][ix];
                for (uint8_t iy = 0; iy < min<uint8_t>(cy, 2); iy++) {
                    int py = preList[y][d][iy];
                    int pred = px * N + py;
                    if (dist[pred] != -1) continue;
                    dist[pred] = nd;
                    parent[pred] = cur;
                    parDir[pred] = (uint8_t)d;
                    bfs.push_back(pred);
                }
            }
        }
    }

    auto getMergeWord = [&](int a, int b) -> string {
        int pid = a * N + b;
        if (dist[pid] < 0) return string(); // indicates impossible
        string w;
        w.reserve((size_t)dist[pid]);
        while (parent[pid] != pid) {
            uint8_t d = parDir[pid];
            w.push_back(dirChar[d]);
            pid = parent[pid];
        }
        return w;
    };

    int char2dir[256];
    for (int i = 0; i < 256; i++) char2dir[i] = -1;
    char2dir[(unsigned char)'L'] = 0;
    char2dir[(unsigned char)'R'] = 1;
    char2dir[(unsigned char)'U'] = 2;
    char2dir[(unsigned char)'D'] = 3;

    // Synchronize all states to one state using greedy merging.
    vector<int> curSet(N);
    iota(curSet.begin(), curSet.end(), 0);
    string resetWord;
    resetWord.reserve(200000);

    while ((int)curSet.size() > 1) {
        int r = curSet[0];
        int bestIdx = -1;
        int bestDist = INT_MAX;
        for (int i = 1; i < (int)curSet.size(); i++) {
            int s = curSet[i];
            int d = dist[r * N + s];
            if (d < 0) {
                cout << "-1\n";
                return 0;
            }
            if (d < bestDist) {
                bestDist = d;
                bestIdx = i;
                if (bestDist == 0) break;
            }
        }
        int s = curSet[bestIdx];
        string w = getMergeWord(r, s);
        if (w.empty() && r != s) {
            cout << "-1\n";
            return 0;
        }

        if (resetWord.size() + w.size() > 600000) { // safety; final palindrome doubles W
            cout << "-1\n";
            return 0;
        }
        resetWord += w;

        // Apply w to all states in current set.
        for (char ch : w) {
            int d = char2dir[(unsigned char)ch];
            for (int &st : curSet) st = nxt[st][d];
        }
        sort(curSet.begin(), curSet.end());
        curSet.erase(unique(curSet.begin(), curSet.end()), curSet.end());
    }
    int syncState = curSet[0];

    // Shortest path from syncState to exitId.
    vector<int> prev(N, -1);
    vector<int> prevDir(N, -1);
    queue<int> q2;
    prev[syncState] = syncState;
    q2.push(syncState);
    while (!q2.empty()) {
        int v = q2.front(); q2.pop();
        if (v == exitId) break;
        for (int d = 0; d < 4; d++) {
            int u = nxt[v][d];
            if (u == v) continue;
            if (prev[u] != -1) continue;
            prev[u] = v;
            prevDir[u] = d;
            q2.push(u);
        }
    }
    if (prev[exitId] == -1) {
        cout << "-1\n";
        return 0;
    }
    string pathToExit;
    {
        int cur = exitId;
        while (cur != syncState) {
            int d = prevDir[cur];
            pathToExit.push_back(dirChar[d]);
            cur = prev[cur];
        }
        reverse(pathToExit.begin(), pathToExit.end());
    }

    string W = resetWord + pathToExit;
    if (W.size() > 500000) {
        cout << "-1\n";
        return 0;
    }

    // Compute s0 = apply(reverse(W), start)
    int s0 = start;
    for (int i = (int)W.size() - 1; i >= 0; i--) {
        int d = char2dir[(unsigned char)W[i]];
        s0 = nxt[s0][d];
    }

    // Build adjacency for DFS traversal.
    vector<vector<pair<int,int>>> adj(N);
    for (int v = 0; v < N; v++) {
        adj[v].reserve(4);
        for (int d = 0; d < 4; d++) {
            int u = nxt[v][d];
            if (u != v) adj[v].push_back({d, u});
        }
    }

    // DFS traversal X from s0 visiting all states; returns to s0.
    string X;
    X.reserve(2 * max(0, N - 1));
    vector<char> seen(N, 0);
    struct Frame { int v; int enterDir; int it; };
    vector<Frame> st;
    st.reserve(N);
    seen[s0] = 1;
    st.push_back({s0, -1, 0});
    while (!st.empty()) {
        Frame &f = st.back();
        if (f.it >= (int)adj[f.v].size()) {
            int enter = f.enterDir;
            st.pop_back();
            if (enter != -1) X.push_back(dirChar[oppDir(enter)]);
            continue;
        }
        auto [d, to] = adj[f.v][f.it++];
        if (!seen[to]) {
            seen[to] = 1;
            X.push_back(dirChar[d]);
            st.push_back({to, d, 0});
        }
    }

    // Ensure all visited (should, since connected)
    for (int i = 0; i < N; i++) {
        if (!seen[i]) {
            // As a fallback, this shouldn't happen; treat as impossible.
            cout << "-1\n";
            return 0;
        }
    }

    string revW = W;
    reverse(revW.begin(), revW.end());
    string revX = X;
    reverse(revX.begin(), revX.end());

    size_t totalLen = 2ull * (W.size() + X.size());
    if (totalLen > 1000000ull) {
        cout << "-1\n";
        return 0;
    }

    string ans;
    ans.reserve(totalLen);
    ans += revW;
    ans += X;
    ans += revX;
    ans += W;

    cout << ans << "\n";
    return 0;
}
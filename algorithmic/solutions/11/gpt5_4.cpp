#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::steady_clock::time_point st;
    Timer() { st = chrono::steady_clock::now(); }
    double elapsed() const {
        return chrono::duration<double>(chrono::steady_clock::now() - st).count();
    }
};

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

    // Map cells to ids
    vector<vector<int>> id(n, vector<int>(m, -1));
    int V = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (g[i][j] == '1') id[i][j] = V++;

    if (id[sr][sc] == -1 || id[er][ec] == -1) {
        cout << -1 << '\n';
        return 0;
    }

    // Check all blanks are reachable from start
    vector<int> dr = {0, 0, -1, 1};
    vector<int> dc = {-1, 1, 0, 0};
    vector<char> dirChar = {'L', 'R', 'U', 'D'};
    vector<vector<int>> neighbors(V);
    int start = id[sr][sc], exit_id = id[er][ec];

    vector<int> vis(V, 0);
    queue<int> q;
    q.push(start);
    vis[start] = 1;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        // decode u to r,c
        // We need reverse mapping:
        // Build once
    }
    // Build reverse map
    vector<pair<int,int>> rid(V);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (id[i][j] != -1)
                rid[id[i][j]] = {i, j};

    // Build neighbors for BFS reachability and later use
    for (int u = 0; u < V; ++u) {
        auto [r, c] = rid[u];
        for (int k = 0; k < 4; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && id[nr][nc] != -1) {
                neighbors[u].push_back(id[nr][nc]);
            }
        }
    }
    // BFS reachability
    fill(vis.begin(), vis.end(), 0);
    q.push(start);
    vis[start] = 1;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : neighbors[u]) if (!vis[v]) { vis[v] = 1; q.push(v); }
    }
    // Count blanks
    int blanks = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (g[i][j] == '1') blanks++;
    int reachCnt = 0;
    for (int u = 0; u < V; ++u) if (vis[u]) reachCnt++;
    if (reachCnt != blanks || !vis[exit_id]) {
        cout << -1 << '\n';
        return 0;
    }

    // Build transition functions for moves with "stay if blocked"
    // trans[dir][u] -> v
    vector<array<int,4>> trans(V);
    for (int u = 0; u < V; ++u) {
        auto [r, c] = rid[u];
        for (int k = 0; k < 4; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && id[nr][nc] != -1) trans[u][k] = id[nr][nc];
            else trans[u][k] = u; // stay
        }
    }

    auto applySeq = [&](const string &S, int pos)->int{
        int u = pos;
        for (char ch : S) {
            int k = 0;
            if (ch == 'L') k = 0;
            else if (ch == 'R') k = 1;
            else if (ch == 'U') k = 2;
            else if (ch == 'D') k = 3;
            u = trans[u][k];
        }
        return u;
    };

    // Build DFS traversal path X that visits all vertices and returns to start
    string X;
    vector<int> seen(V, 0);
    // We'll randomize neighbor order a bit but keep deterministic first attempt
    vector<int> order = {0,1,2,3}; // L, R, U, D
    // We'll try multiple randomized DFS orders if needed
    Timer timer;
    string answer;

    auto build_dfs_path = [&](vector<int> ord)->string{
        string path;
        vector<int> used(V, 0);
        function<void(int)> dfs = [&](int u){
            used[u] = 1;
            auto [r,c] = rid[u];
            for (int idx : ord) {
                int nr = r + dr[idx], nc = c + dc[idx];
                if (nr >= 0 && nr < n && nc >= 0 && nc < m && id[nr][nc] != -1) {
                    int v = id[nr][nc];
                    if (!used[v]) {
                        path.push_back(dirChar[idx]);
                        dfs(v);
                        // backtrack
                        int backIdx = (idx ^ 1); // 0<->1, 2<->3
                        path.push_back(dirChar[backIdx]);
                    }
                }
            }
        };
        dfs(start);
        return path;
    };

    // Precompute reverse map for ease
    auto reverse_str = [&](const string &s)->string{
        string t = s;
        reverse(t.begin(), t.end());
        for (char &ch : t) {
            if (ch == 'L') ch = 'R';
            else if (ch == 'R') ch = 'L';
            else if (ch == 'U') ch = 'D';
            else if (ch == 'D') ch = 'U';
        }
        return t;
    };

    // Search function for palindromic F
    auto find_pal_F = [&](const string &X, int p, const vector<char> &letters, int maxT, string &F)->bool {
        // Build reverse(X) mapping for all states to check T-set
        string revX = reverse_str(X);
        vector<int> finalPos(V);
        for (int u = 0; u < V; ++u) finalPos[u] = applySeq(revX, u);
        vector<char> stackMoves;
        vector<int> posAfterPrefix; posAfterPrefix.reserve(maxT+1);

        vector<char> idxToChar = {'L','R','U','D'};
        vector<int> target(V, 0);
        for (int u = 0; u < V; ++u) if (finalPos[u] == exit_id) target[u] = 1;

        bool found = false;
        string outF;

        function<bool(int,int)> dfs = [&](int depth, int t)->bool{
            if (timer.elapsed() > 0.95) return false; // time guard
            if (depth == t) {
                int cur = posAfterPrefix.back();
                // even palindrome
                int ce = cur;
                for (int i = t - 1; i >= 0; --i) {
                    int k = 0;
                    char ch = stackMoves[i];
                    if (ch == 'L') k = 0;
                    else if (ch == 'R') k = 1;
                    else if (ch == 'U') k = 2;
                    else if (ch == 'D') k = 3;
                    ce = trans[ce][k];
                }
                if (target[ce]) {
                    outF.clear();
                    outF.reserve(2*t);
                    for (int i = 0; i < t; ++i) outF.push_back(stackMoves[i]);
                    for (int i = t-1; i >= 0; --i) {
                        char ch = stackMoves[i];
                        if (ch == 'L') outF.push_back('L');
                        else if (ch == 'R') outF.push_back('R');
                        else if (ch == 'U') outF.push_back('U');
                        else if (ch == 'D') outF.push_back('D');
                    }
                    F = outF;
                    return true;
                }
                // odd palindrome: try center dir
                for (int d = 0; d < 4; ++d) {
                    int co = trans[cur][d];
                    for (int i = t - 1; i >= 0; --i) {
                        int k = 0;
                        char ch = stackMoves[i];
                        if (ch == 'L') k = 0;
                        else if (ch == 'R') k = 1;
                        else if (ch == 'U') k = 2;
                        else if (ch == 'D') k = 3;
                        co = trans[co][k];
                    }
                    if (target[co]) {
                        outF.clear();
                        outF.reserve(2*t+1);
                        for (int i = 0; i < t; ++i) outF.push_back(stackMoves[i]);
                        outF.push_back(idxToChar[d]);
                        for (int i = t-1; i >= 0; --i) {
                            char ch = stackMoves[i];
                            if (ch == 'L') outF.push_back('L');
                            else if (ch == 'R') outF.push_back('R');
                            else if (ch == 'U') outF.push_back('U');
                            else if (ch == 'D') outF.push_back('D');
                        }
                        F = outF;
                        return true;
                    }
                }
                return false;
            } else {
                for (int d = 0; d < 4; ++d) {
                    char ch = idxToChar[d];
                    stackMoves.push_back(ch);
                    int prev = posAfterPrefix.back();
                    int next = trans[prev][d];
                    posAfterPrefix.push_back(next);
                    if (dfs(depth+1, t)) return true;
                    posAfterPrefix.pop_back();
                    stackMoves.pop_back();
                }
                return false;
            }
        };

        // Iterative deepening
        for (int t = 0; t <= maxT; ++t) {
            stackMoves.clear();
            posAfterPrefix.clear();
            posAfterPrefix.push_back(p);
            if (dfs(0, t)) return true;
            if (timer.elapsed() > 0.97) break;
        }
        return false;
    };

    // Attempt multiple DFS orders and pal F depths until time limit
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<int> baseOrder = {0,1,2,3}; // L R U D
    vector<vector<int>> tryOrders;
    tryOrders.push_back({0,1,2,3});
    tryOrders.push_back({1,0,3,2});
    tryOrders.push_back({2,3,0,1});
    tryOrders.push_back({3,2,1,0});
    // Add some random orders
    for (int t = 0; t < 8; ++t) {
        vector<int> ord = {0,1,2,3};
        shuffle(ord.begin(), ord.end(), rng);
        tryOrders.push_back(ord);
    }

    bool solutionFound = false;
    for (auto &ord : tryOrders) {
        if (timer.elapsed() > 0.98) break;
        // Build DFS path X
        string Xcand = build_dfs_path(ord);
        // Validate that Xcand visits all vertices: due to DFS, yes.
        // Ensure we returned to start:
        int posAfterX = applySeq(Xcand, start);
        if (posAfterX != start) {
            // Should not happen; but if it does, skip
            continue;
        }
        // Search palindromic F
        string F;
        int maxT = 10;
        if (find_pal_F(Xcand, start, dirChar, maxT, F)) {
            string revX = reverse_str(Xcand);
            string S = Xcand + F + revX;
            // Validate by simulation:
            int finalPos = applySeq(S, start);
            // Also verify visits all blanks:
            vector<int> visitedV(V, 0);
            int u = start;
            visitedV[u] = 1;
            for (char ch : S) {
                int k = 0;
                if (ch == 'L') k = 0;
                else if (ch == 'R') k = 1;
                else if (ch == 'U') k = 2;
                else if (ch == 'D') k = 3;
                u = trans[u][k];
                visitedV[u] = 1;
            }
            int viscount = 0;
            for (int i = 0; i < V; ++i) if (visitedV[i]) viscount++;
            if (finalPos == exit_id && viscount == V && (int)S.size() <= 1000000) {
                cout << S << '\n';
                solutionFound = true;
                break;
            }
        }
    }

    if (!solutionFound) {
        // As a fallback, try a slightly larger maxT with one more random order if time allows
        if (timer.elapsed() < 0.98) {
            vector<int> ord = {0,1,2,3};
            shuffle(ord.begin(), ord.end(), rng);
            string Xcand = build_dfs_path(ord);
            int posAfterX = applySeq(Xcand, start);
            if (posAfterX == start) {
                string F;
                int maxT = 12;
                if (find_pal_F(Xcand, start, dirChar, maxT, F)) {
                    string revX = reverse_str(Xcand);
                    string S = Xcand + F + revX;
                    int finalPos = applySeq(S, start);
                    vector<int> visitedV(V, 0);
                    int u = start; visitedV[u] = 1;
                    for (char ch : S) {
                        int k = 0;
                        if (ch == 'L') k = 0;
                        else if (ch == 'R') k = 1;
                        else if (ch == 'U') k = 2;
                        else if (ch == 'D') k = 3;
                        u = trans[u][k];
                        visitedV[u] = 1;
                    }
                    int viscount = 0;
                    for (int i = 0; i < V; ++i) if (visitedV[i]) viscount++;
                    if (finalPos == exit_id && viscount == V && (int)S.size() <= 1000000) {
                        cout << S << '\n';
                        solutionFound = true;
                    }
                }
            }
        }
    }

    if (!solutionFound) {
        cout << -1 << '\n';
    }
    return 0;
}
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

    // Map cells to state ids
    vector<vector<int>> id(n, vector<int>(m, -1));
    vector<pair<int,int>> cells;
    int N = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (grid[i][j] == '1') {
                id[i][j] = N++;
                cells.push_back({i,j});
            }
    if (id[sr][sc] == -1 || id[er][ec] == -1) {
        cout << -1 << '\n';
        return 0;
    }
    int S = id[sr][sc], E = id[er][ec];

    // Build transition function
    int dr[4] = {0, 0, -1, 1};
    int dc[4] = {-1, 1, 0, 0};
    char dch[4] = {'L','R','U','D'};
    int opp[4] = {1,0,3,2};
    vector<array<int,4>> T(N);
    for (int idx = 0; idx < N; ++idx) {
        auto [r,c] = cells[idx];
        for (int d = 0; d < 4; ++d) {
            int nr = r + dr[d], nc = c + dc[d];
            if (nr>=0 && nr<n && nc>=0 && nc<m && grid[nr][nc]=='1') T[idx][d] = id[nr][nc];
            else T[idx][d] = idx; // blocked -> stay
        }
    }

    // Check connectivity from S to all blanks
    vector<int> vis(N, 0);
    queue<int> q;
    q.push(S); vis[S]=1;
    while(!q.empty()){
        int u=q.front(); q.pop();
        for (int d=0; d<4; ++d) {
            int v = T[u][d];
            if (v != u && !vis[v]) { vis[v]=1; q.push(v); }
        }
    }
    int reachable = accumulate(vis.begin(), vis.end(), 0);
    if (reachable != N) {
        cout << -1 << '\n';
        return 0;
    }

    // Precompute adjacency list (actual moves only)
    vector<array<int,4>> nbr(N);
    for (int u=0; u<N; ++u) for (int d=0; d<4; ++d) nbr[u][d] = T[u][d];

    auto build_A = [&](array<int,4> order)->string{
        string A;
        vector<int> seen(N,0);
        function<void(int)> dfs = [&](int u){
            seen[u]=1;
            for (int k=0;k<4;++k){
                int d = order[k];
                int v = nbr[u][d];
                if (v != u && !seen[v]) {
                    A.push_back(dch[d]);
                    dfs(v);
                    A.push_back(dch[opp[d]]);
                }
            }
        };
        dfs(S);
        // If some nodes were not visited due to DFS order? Shouldn't happen as graph is connected
        return A;
    };

    auto apply_seq = [&](int st, const string &seq)->int{
        int cur = st;
        for(char c: seq){
            int di = (c=='L'?0:c=='R'?1:c=='U'?2:3);
            cur = T[cur][di];
        }
        return cur;
    };

    auto reverse_str = [&](const string &x)->string{
        string y = x;
        reverse(y.begin(), y.end());
        return y;
    };

    auto now = chrono::steady_clock::now;
    auto start_time = now();
    auto time_elapsed_ms = [&](){
        return chrono::duration_cast<chrono::milliseconds>(now() - start_time).count();
    };
    const long long TIME_LIMIT_MS = 900; // be safe under 1s

    mt19937 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    // Try multiple attempts with different DFS neighbor orders
    int attempts = 0;
    while (time_elapsed_ms() < TIME_LIMIT_MS) {
        attempts++;
        array<int,4> order = {0,1,2,3};
        if (attempts > 1) {
            shuffle(order.begin(), order.end(), rng);
        }
        string A = build_A(order);
        // Build reverse(A)
        string RA = reverse_str(A);

        // Compute hmap: final state after applying RA from any state
        vector<int> hmap(N);
        for (int st=0; st<N; ++st) {
            int cur = st;
            for (char c: RA) {
                int di = (c=='L'?0:c=='R'?1:c=='U'?2:3);
                cur = T[cur][di];
            }
            hmap[st] = cur;
        }
        vector<char> preOk(N, 0);
        for (int st=0; st<N; ++st) if (hmap[st]==E) preOk[st]=1;

        // If empty B works
        if (preOk[S]) {
            string Sres = A + RA;
            cout << Sres << '\n';
            return 0;
        }

        // Search for small palindromic B mapping S -> p, with preOk[p]
        string bestB;
        bool found = false;

        auto search_B = [&](int Lmax)->bool{
            // L=0 separately
            // Even length 0
            if (preOk[S]) { bestB=""; return true; }
            // Odd length 1
            for (int c=0;c<4;++c){
                int v = T[S][c];
                if (preOk[v]) { bestB = string(1, dch[c]); return true; }
            }

            // Enumerate halves
            vector<int> half;
            vector<int> state_stack;
            function<bool(int,int,int)> rec = [&](int depth, int L, int cur_state)->bool{
                if ((int)time_elapsed_ms() >= TIME_LIMIT_MS) return false;
                if (depth == L) {
                    // compute even
                    int v = cur_state;
                    for (int i=L-1;i>=0;--i) v = T[v][half[i]];
                    if (preOk[v]) {
                        string B; B.reserve(2*L);
                        for (int x: half) B.push_back(dch[x]);
                        for (int i=L-1;i>=0;--i) B.push_back(dch[half[i]]);
                        bestB = B;
                        return true;
                    }
                    // odd with center
                    for (int c=0;c<4;++c){
                        int u = T[cur_state][c];
                        int v2 = u;
                        for (int i=L-1;i>=0;--i) v2 = T[v2][half[i]];
                        if (preOk[v2]) {
                            string B; B.reserve(2*L+1);
                            for (int x: half) B.push_back(dch[x]);
                            B.push_back(dch[c]);
                            for (int i=L-1;i>=0;--i) B.push_back(dch[half[i]]);
                            bestB = B;
                            return true;
                        }
                    }
                    return false;
                } else {
                    for (int d=0; d<4; ++d) {
                        half.push_back(d);
                        int ns = T[cur_state][d];
                        if (rec(depth+1, L, ns)) return true;
                        half.pop_back();
                    }
                    return false;
                }
            };

            for (int L=1; L<=10; ++L) {
                if ((int)time_elapsed_ms() >= TIME_LIMIT_MS) break;
                half.clear();
                if (rec(0, L, S)) return true;
            }
            return false;
        };

        if (search_B(10)) {
            string RA2 = RA;
            string Sres;
            Sres.reserve(A.size() + bestB.size() + RA2.size());
            Sres += A;
            Sres += bestB;
            Sres += RA2;
            if ((int)Sres.size() <= 1000000) {
                cout << Sres << '\n';
                return 0;
            }
        }
        // else try another attempt
    }

    cout << -1 << '\n';
    return 0;
}
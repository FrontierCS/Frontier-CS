#include <bits/stdc++.h>
using namespace std;

static const int MAXNM = 30;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> g(n);
    for (int i = 0; i < n; i++) cin >> g[i];

    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;

    vector<int> id(n * m, -1);
    vector<pair<int,int>> pos;
    pos.reserve(n * m);

    int startId = -1, exitId = -1;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (g[i][j] == '1') {
                int idx = (int)pos.size();
                id[i * m + j] = idx;
                pos.push_back({i, j});
            }
        }
    }
    int N = (int)pos.size();
    if (N == 0) {
        cout << "-1\n";
        return 0;
    }

    startId = id[sr * m + sc];
    exitId  = id[er * m + ec];

    if (startId < 0 || exitId < 0) {
        cout << "-1\n";
        return 0;
    }

    // Directions: 0=L, 1=R, 2=U, 3=D
    const int dx[4] = {0, 0, -1, 1};
    const int dy[4] = {-1, 1, 0, 0};
    const int opp[4] = {1, 0, 3, 2};
    const char dirChar[4] = {'L','R','U','D'};
    int charToDir[128];
    for (int i = 0; i < 128; i++) charToDir[i] = -1;
    for (int d = 0; d < 4; d++) charToDir[(int)dirChar[d]] = d;

    // Build deterministic transitions over blank cells
    vector<array<int,4>> nxt(N);
    for (int u = 0; u < N; u++) {
        auto [x, y] = pos[u];
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx >= 0 && nx < n && ny >= 0 && ny < m && g[nx][ny] == '1') {
                nxt[u][d] = id[nx * m + ny];
            } else {
                nxt[u][d] = u;
            }
        }
    }

    // Connectivity check (adjacency graph where move actually changes position)
    vector<char> vis(N, 0);
    queue<int> q;
    vis[startId] = 1;
    q.push(startId);
    int reached = 1;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int v = nxt[u][d];
            if (v != u && !vis[v]) {
                vis[v] = 1;
                q.push(v);
                reached++;
            }
        }
    }
    if (reached != N || !vis[exitId]) {
        cout << "-1\n";
        return 0;
    }

    // Predecessors for each direction
    vector<vector<int>> pred(4, vector<int>()); // unused
    vector<vector<vector<int>>> preds(4, vector<vector<int>>(N));
    for (int u = 0; u < N; u++) {
        for (int d = 0; d < 4; d++) {
            int v = nxt[u][d];
            preds[d][v].push_back(u);
        }
    }

    auto buildTour = [&](array<int,4> order) -> string {
        vector<char> seen(N, 0);
        struct Frame { int u; int it; int inDir; };
        vector<Frame> st;
        st.reserve(N);
        string tour;
        tour.reserve(max(0, 2 * (N - 1)));

        seen[startId] = 1;
        st.push_back({startId, 0, -1});

        while (!st.empty()) {
            int u = st.back().u;
            int &it = st.back().it;
            bool advanced = false;

            while (it < 4) {
                int d = order[it++];
                int v = nxt[u][d];
                if (v == u) continue;
                if (!seen[v]) {
                    seen[v] = 1;
                    tour.push_back(dirChar[d]);
                    st.push_back({v, 0, d});
                    advanced = true;
                    break;
                }
            }
            if (advanced) continue;

            st.pop_back();
            if (!st.empty()) {
                int d = st.back().u; (void)d;
                int inD = st.back().it; (void)inD;
                int backDir = opp[st.back().it]; (void)backDir;
                // Actually back direction is opposite of direction used to reach current node.
                // That direction is stored in the popped frame's inDir.
                // So store popped frame before popping.
            }
        }

        // Rebuild with correct backtracking (above simplified incorrectly)
        // We'll implement again properly.
        tour.clear();
        fill(seen.begin(), seen.end(), 0);
        st.clear();

        seen[startId] = 1;
        st.push_back({startId, 0, -1});

        while (!st.empty()) {
            Frame &fr = st.back();
            int u = fr.u;
            if (fr.it < 4) {
                int d = order[fr.it++];
                int v = nxt[u][d];
                if (v == u) continue;
                if (!seen[v]) {
                    seen[v] = 1;
                    tour.push_back(dirChar[d]);
                    st.push_back({v, 0, d});
                }
            } else {
                int inDir = fr.inDir;
                st.pop_back();
                if (!st.empty() && inDir != -1) {
                    tour.push_back(dirChar[opp[inDir]]);
                }
            }
        }

        return tour;
    };

    // Build palindrome BFS (even and odd) over pair states
    int P = N * N;
    vector<int> distEven(P, -1), parentEven(P, -1);
    vector<uint8_t> wrapEven(P, 255);

    vector<int> distOdd(P, -1), parentOdd(P, -1);
    vector<uint8_t> wrapOdd(P, 255), centerOdd(P, 255);

    auto bfsParity = [&](bool odd) {
        vector<int> &dist = odd ? distOdd : distEven;
        vector<int> &par = odd ? parentOdd : parentEven;
        vector<uint8_t> &wrap = odd ? wrapOdd : wrapEven;

        vector<int> que;
        que.reserve(P);
        int head = 0;

        if (!odd) {
            for (int i = 0; i < N; i++) {
                int idx = i * N + i;
                dist[idx] = 0;
                par[idx] = -1;
                wrap[idx] = 255;
                que.push_back(idx);
            }
        } else {
            for (int i = 0; i < N; i++) {
                for (int d = 0; d < 4; d++) {
                    int j = nxt[i][d];
                    int idx = i * N + j;
                    if (dist[idx] == -1) {
                        dist[idx] = 0;
                        par[idx] = -1;
                        wrap[idx] = 255;
                        centerOdd[idx] = (uint8_t)d;
                        que.push_back(idx);
                    }
                }
            }
        }

        while (head < (int)que.size()) {
            int idx = que[head++];
            int a = idx / N;
            int b = idx - a * N;
            int nd = dist[idx] + 1;

            for (int d = 0; d < 4; d++) {
                int b2 = nxt[b][d]; // successor on the right
                auto &paList = preds[d][a]; // predecessors on the left
                for (int pa : paList) {
                    int idx2 = pa * N + b2;
                    if (dist[idx2] == -1) {
                        dist[idx2] = nd;
                        par[idx2] = idx;
                        wrap[idx2] = (uint8_t)d;
                        que.push_back(idx2);
                    }
                }
            }
        }
    };

    bfsParity(false);
    bfsParity(true);

    auto bestLenAndParity = [&](int u, int v, int &parityOut) -> long long {
        long long best = (long long)4e18;
        int idx = u * N + v;
        int bestParity = -1;

        if (distEven[idx] != -1) {
            long long len = 2LL * distEven[idx];
            if (len < best) { best = len; bestParity = 0; }
        }
        if (distOdd[idx] != -1) {
            long long len = 2LL * distOdd[idx] + 1;
            if (len < best) { best = len; bestParity = 1; }
        }
        parityOut = bestParity;
        return best;
    };

    auto buildPalindrome = [&](int u, int v, int parity) -> string {
        string left;
        int idx = u * N + v;
        if (parity == 0) {
            int wraps = distEven[idx];
            if (wraps < 0) return string();
            left.reserve(wraps);
            while (parentEven[idx] != -1) {
                uint8_t d = wrapEven[idx];
                left.push_back(dirChar[d]);
                idx = parentEven[idx];
            }
            string res;
            res.reserve((size_t)2 * left.size());
            res += left;
            for (int i = (int)left.size() - 1; i >= 0; i--) res.push_back(left[i]);
            return res;
        } else {
            int wraps = distOdd[idx];
            if (wraps < 0) return string();
            left.reserve(wraps);
            while (parentOdd[idx] != -1) {
                uint8_t d = wrapOdd[idx];
                left.push_back(dirChar[d]);
                idx = parentOdd[idx];
            }
            uint8_t c = centerOdd[idx];
            string res;
            res.reserve((size_t)2 * left.size() + 1);
            res += left;
            res.push_back(dirChar[c]);
            for (int i = (int)left.size() - 1; i >= 0; i--) res.push_back(left[i]);
            return res;
        }
    };

    // Candidate tours
    vector<array<int,4>> orders;
    orders.push_back({1,3,0,2}); // R D L U
    orders.push_back({0,2,1,3}); // L U R D
    orders.push_back({2,0,3,1}); // U L D R
    orders.push_back({3,1,2,0}); // D R U L

    vector<string> tours;
    tours.reserve(orders.size());
    for (auto &ord : orders) tours.push_back(buildTour(ord));

    // Build short loops at start (that keep you at start)
    vector<string> loops;
    loops.push_back("");
    for (int d = 0; d < 4; d++) {
        if (nxt[startId][d] == startId) {
            loops.push_back(string(1, dirChar[d]));
        }
    }
    for (int d = 0; d < 4; d++) {
        if (nxt[startId][d] != startId) {
            string s;
            s.push_back(dirChar[d]);
            s.push_back(dirChar[opp[d]]);
            loops.push_back(s);
        }
    }
    sort(loops.begin(), loops.end());
    loops.erase(unique(loops.begin(), loops.end()), loops.end());
    stable_sort(loops.begin(), loops.end(), [](const string &a, const string &b){
        if (a.size() != b.size()) return a.size() < b.size();
        return a < b;
    });

    int K = (int)min<size_t>(loops.size(), 5);

    long long bestTotal = (long long)4e18;
    string bestX;
    int bestT = -1;
    int bestParity = -1;

    vector<int> mark(N, 0);

    auto evalCandidate = [&](const string &X) {
        // Compute preimage set: states t such that delta(t, reverse(X)) = exit
        // Equivalent to preimage of exit under X read forward.
        vector<int> cur;
        cur.reserve(N);
        cur.push_back(exitId);
        int stamp = 1;
        mark[exitId] = stamp;

        for (char ch : X) {
            int d = charToDir[(int)ch];
            if (d < 0) return;
            stamp++;
            vector<int> nxtList;
            nxtList.reserve(N);
            for (int s : cur) {
                for (int p : preds[d][s]) {
                    if (mark[p] != stamp) {
                        mark[p] = stamp;
                        nxtList.push_back(p);
                    }
                }
            }
            cur.swap(nxtList);
            if (cur.empty()) break;
        }
        if (cur.empty()) return;

        for (int t : cur) {
            int parity;
            long long lenM = bestLenAndParity(startId, t, parity);
            if (parity == -1) continue;
            long long total = 2LL * (long long)X.size() + lenM;
            if (total <= 1000000LL && total < bestTotal) {
                bestTotal = total;
                bestX = X;
                bestT = t;
                bestParity = parity;
            }
        }
    };

    for (const string &tour : tours) {
        for (int i = 0; i < K; i++) {
            for (int j = 0; j < K; j++) {
                string X;
                X.reserve(loops[i].size() + tour.size() + loops[j].size());
                X += loops[i];
                X += tour;
                X += loops[j];
                evalCandidate(X);
            }
        }
    }

    if (bestT == -1) {
        cout << "-1\n";
        return 0;
    }

    string M = buildPalindrome(startId, bestT, bestParity);
    string revX = bestX;
    reverse(revX.begin(), revX.end());

    string out;
    out.reserve((size_t)bestX.size() + (size_t)M.size() + (size_t)revX.size());
    out += bestX;
    out += M;
    out += revX;

    if (out.size() > 1000000ULL) {
        cout << "-1\n";
        return 0;
    }

    cout << out << "\n";
    return 0;
}
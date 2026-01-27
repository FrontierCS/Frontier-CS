#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int N;
    int T;
    vector<uint8_t> initBoard;
    int init_er, init_ec;

    inline int idx(int r, int c) const { return r * N + c; }

    int calcLargestTree(const vector<uint8_t>& g) const {
        int NN = N * N;
        vector<char> vis(NN, 0), incomp(NN, 0);
        int best = 0;
        auto hasEdge = [&](int a, int b, int dir) -> bool {
            // dir: 0 up,1 down,2 left,3 right (a to b)
            uint8_t ta = g[a], tb = g[b];
            if (ta == 0 || tb == 0) return false;
            if (dir == 0) return (ta & 2) && (tb & 8);
            if (dir == 1) return (ta & 8) && (tb & 2);
            if (dir == 2) return (ta & 1) && (tb & 4);
            return (ta & 4) && (tb & 1);
        };
        for (int s = 0; s < NN; ++s) {
            if (g[s] == 0 || vis[s]) continue;
            // BFS over matched edges
            queue<int> q;
            vector<int> comp;
            vis[s] = 1;
            q.push(s);
            comp.push_back(s);
            while (!q.empty()) {
                int u = q.front(); q.pop();
                int r = u / N, c = u % N;
                if (r > 0) {
                    int v = u - N;
                    if (!vis[v] && hasEdge(u, v, 0)) { vis[v] = 1; q.push(v); comp.push_back(v); }
                }
                if (r + 1 < N) {
                    int v = u + N;
                    if (!vis[v] && hasEdge(u, v, 1)) { vis[v] = 1; q.push(v); comp.push_back(v); }
                }
                if (c > 0) {
                    int v = u - 1;
                    if (!vis[v] && hasEdge(u, v, 2)) { vis[v] = 1; q.push(v); comp.push_back(v); }
                }
                if (c + 1 < N) {
                    int v = u + 1;
                    if (!vis[v] && hasEdge(u, v, 3)) { vis[v] = 1; q.push(v); comp.push_back(v); }
                }
            }
            for (int v : comp) incomp[v] = 1;
            int E = 0;
            for (int u : comp) {
                int r = u / N, c = u % N;
                if (r + 1 < N) {
                    int v = u + N;
                    if (incomp[v] && hasEdge(u, v, 1)) ++E;
                }
                if (c + 1 < N) {
                    int v = u + 1;
                    if (incomp[v] && hasEdge(u, v, 3)) ++E;
                }
            }
            int V = (int)comp.size();
            if (E == V - 1) best = max(best, V);
            for (int v : comp) incomp[v] = 0;
        }
        return best;
    }

    inline void applyMove(vector<uint8_t>& g, int& er, int& ec, char mv) const {
        int r = er, c = ec;
        if (mv == 'U') {
            int nr = r - 1, nc = c;
            swap(g[idx(r, c)], g[idx(nr, nc)]);
            er = nr; ec = nc;
        } else if (mv == 'D') {
            int nr = r + 1, nc = c;
            swap(g[idx(r, c)], g[idx(nr, nc)]);
            er = nr; ec = nc;
        } else if (mv == 'L') {
            int nr = r, nc = c - 1;
            swap(g[idx(r, c)], g[idx(nr, nc)]);
            er = nr; ec = nc;
        } else if (mv == 'R') {
            int nr = r, nc = c + 1;
            swap(g[idx(r, c)], g[idx(nr, nc)]);
            er = nr; ec = nc;
        }
    }

    inline char revMove(char m) const {
        if (m == 'U') return 'D';
        if (m == 'D') return 'U';
        if (m == 'L') return 'R';
        if (m == 'R') return 'L';
        return 0;
    }

    string solve() {
        // Time limit control
        auto start = chrono::high_resolution_clock::now();
        const double TIME_LIMIT = 1.90; // seconds

        // Initial best is current board
        string best_path, path;
        int best_S = calcLargestTree(initBoard);

        // Random engine
        std::mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

        // Working state
        vector<uint8_t> g = initBoard;
        int er = init_er, ec = init_ec;

        while (true) {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - start).count();
            if (elapsed > TIME_LIMIT) break;

            // Choose next move randomly among legal moves (optionally avoid immediate reverse)
            vector<char> allowed;
            if (er > 0) allowed.push_back('U');
            if (er + 1 < N) allowed.push_back('D');
            if (ec > 0) allowed.push_back('L');
            if (ec + 1 < N) allowed.push_back('R');

            char prev = path.empty() ? 0 : path.back();
            char revp = revMove(prev);
            vector<char> choices;
            for (char m : allowed) if (m != revp) choices.push_back(m);
            if (choices.empty()) choices = allowed;

            char mv = choices[rng() % choices.size()];
            applyMove(g, er, ec, mv);
            path.push_back(mv);

            int S = calcLargestTree(g);
            if (S > best_S || (S == best_S && path.size() < best_path.size())) {
                best_S = S;
                best_path = path;
                if (best_S == N * N - 1) {
                    // Optional: could stop early if perfect
                    // But continue may find even shorter; to be safe with time, keep going.
                }
            }

            if ((int)path.size() >= T) {
                // Restart from initial
                g = initBoard;
                er = init_er; ec = init_ec;
                path.clear();
            }
        }

        return best_path;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, T;
    if (!(cin >> N >> T)) {
        cout << "\n";
        return 0;
    }
    vector<uint8_t> board(N * N);
    int er = -1, ec = -1;
    for (int i = 0; i < N; ++i) {
        string s; cin >> s;
        for (int j = 0; j < N; ++j) {
            char ch = s[j];
            int v = 0;
            if ('0' <= ch && ch <= '9') v = ch - '0';
            else if ('a' <= ch && ch <= 'f') v = 10 + ch - 'a';
            else if ('A' <= ch && ch <= 'F') v = 10 + ch - 'A';
            board[i * N + j] = (uint8_t)v;
            if (v == 0) { er = i; ec = j; }
        }
    }
    if (er == -1) {
        cout << "\n";
        return 0;
    }

    Solver solver;
    solver.N = N;
    solver.T = T;
    solver.initBoard = board;
    solver.init_er = er;
    solver.init_ec = ec;

    string ans = solver.solve();
    cout << ans << "\n";
    return 0;
}
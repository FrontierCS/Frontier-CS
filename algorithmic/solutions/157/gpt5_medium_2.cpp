#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int N;
    int T;
    vector<vector<int>> board; // -1 for empty, else 1..15 for tile mask
    int er, ec; // empty position
    mt19937_64 rng;

    Solver() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);
        rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    inline bool inb(int r, int c) const { return (0 <= r && r < N && 0 <= c && c < N); }

    bool has_edge(int i, int j, int ni, int nj) const {
        if (!inb(i,j) || !inb(ni,nj)) return false;
        if (board[i][j] < 0 || board[ni][nj] < 0) return false;
        int a = board[i][j];
        int b = board[ni][nj];
        int di = ni - i, dj = nj - j;
        if (di == 1 && dj == 0) { // down
            return ((a & 8) && (b & 2));
        } else if (di == -1 && dj == 0) { // up
            return ((a & 2) && (b & 8));
        } else if (di == 0 && dj == 1) { // right
            return ((a & 4) && (b & 1));
        } else if (di == 0 && dj == -1) { // left
            return ((a & 1) && (b & 4));
        }
        return false;
    }

    int compute_score() const {
        vector<vector<char>> vis(N, vector<char>(N, 0));
        int best = 0;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (board[i][j] < 0 || vis[i][j]) continue;
                // BFS to get component
                queue<pair<int,int>> q;
                vector<pair<int,int>> comp;
                vis[i][j] = 1;
                q.push({i,j});
                comp.push_back({i,j});
                while (!q.empty()) {
                    auto [r,c] = q.front(); q.pop();
                    static const int dr[4] = {-1,1,0,0};
                    static const int dc[4] = {0,0,-1,1};
                    for (int d = 0; d < 4; ++d) {
                        int nr = r + dr[d], nc = c + dc[d];
                        if (!inb(nr,nc)) continue;
                        if (board[nr][nc] < 0) continue;
                        if (!has_edge(r,c,nr,nc)) continue;
                        if (!vis[nr][nc]) {
                            vis[nr][nc] = 1;
                            q.push({nr,nc});
                            comp.push_back({nr,nc});
                        }
                    }
                }
                int V = (int)comp.size();
                int E = 0;
                for (auto &p : comp) {
                    int r = p.first, c = p.second;
                    // count right and down edges to avoid double counting
                    if (c + 1 < N && board[r][c+1] >= 0 && has_edge(r,c,r,c+1)) ++E;
                    if (r + 1 < N && board[r+1][c] >= 0 && has_edge(r,c,r+1,c)) ++E;
                }
                if (E == V - 1) best = max(best, V);
            }
        }
        return best;
    }

    inline void applyMove(char mv) {
        int dr = 0, dc = 0;
        if (mv == 'U') { dr = -1; dc = 0; }
        else if (mv == 'D') { dr = 1; dc = 0; }
        else if (mv == 'L') { dr = 0; dc = -1; }
        else if (mv == 'R') { dr = 0; dc = 1; }
        int nr = er + dr, nc = ec + dc;
        // assume legal
        swap(board[er][ec], board[nr][nc]);
        er = nr; ec = nc;
    }

    inline char opp(char mv) {
        if (mv == 'U') return 'D';
        if (mv == 'D') return 'U';
        if (mv == 'L') return 'R';
        if (mv == 'R') return 'L';
        return '?';
    }

    void solve() {
        cin >> N >> T;
        board.assign(N, vector<int>(N, 0));
        er = ec = -1;
        for (int i = 0; i < N; ++i) {
            string s; cin >> s;
            for (int j = 0; j < N; ++j) {
                char c = s[j];
                if (c == '0') {
                    board[i][j] = -1;
                    er = i; ec = j;
                } else if ('1' <= c && c <= '9') {
                    board[i][j] = c - '0';
                } else {
                    board[i][j] = 10 + (c - 'a');
                }
            }
        }
        string ops, bestOps;
        int currScore = compute_score();
        int bestScore = currScore;
        size_t bestLen = 0;
        char lastAcc = '?';

        uniform_real_distribution<double> ur01(0.0, 1.0);

        for (int step = 0; step < T; ++step) {
            // build allowed moves
            array<char,4> all = {'U','D','L','R'};
            vector<char> cand;
            if (er > 0) cand.push_back('U');
            if (er < N-1) cand.push_back('D');
            if (ec > 0) cand.push_back('L');
            if (ec < N-1) cand.push_back('R');
            if (cand.empty()) break;
            // avoid immediate backtracking if possible
            if (lastAcc != '?') {
                char rev = opp(lastAcc);
                if (cand.size() > 1) {
                    auto it = find(cand.begin(), cand.end(), rev);
                    if (it != cand.end()) cand.erase(it);
                }
            }
            char mv = cand[rng() % cand.size()];
            applyMove(mv);
            int newScore = compute_score();
            // Simple acceptance: improve or random small chance
            bool accept = false;
            if (newScore >= currScore) accept = true;
            else {
                // annealed probability
                double temp = 1.0 + 0.0; // constant small temperature
                double prob = exp(double(newScore - currScore) / temp);
                if (ur01(rng) < prob * 0.05) accept = true; // scaled down
            }
            if (accept) {
                ops.push_back(mv);
                currScore = newScore;
                lastAcc = mv;
                if (currScore > bestScore) {
                    bestScore = currScore;
                    bestLen = ops.size();
                    if (bestScore == N*N - 1) break; // full tree achieved
                }
            } else {
                // revert
                applyMove(opp(mv));
            }
        }
        if (bestLen == 0) {
            cout << "\n";
        } else {
            cout << ops.substr(0, bestLen) << "\n";
        }
    }
};

int main() {
    Solver s;
    s.solve();
    return 0;
}
#include <bits/stdc++.h>
using namespace std;

struct Score {
    int S;       // size of largest tree component
    int cycles;  // total cycle excess across components
    int edges;   // total number of edges in the whole graph
};

struct Solver {
    int N;
    int T;
    vector<int> a; // grid flattened, -1 for empty
    int br, bc;    // blank row/col
    int blankIdx;
    string ans;
    mt19937 rng;

    Solver() {
        rng.seed((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    inline int idx(int r, int c) const { return r * N + c; }

    inline char opp(char d) const {
        if (d == 'U') return 'D';
        if (d == 'D') return 'U';
        if (d == 'L') return 'R';
        if (d == 'R') return 'L';
        return '?';
    }

    bool applyMove(char d) {
        int r = br, c = bc;
        if (d == 'U') {
            if (r == 0) return false;
            int i1 = idx(r, c), i2 = idx(r - 1, c);
            a[i1] = a[i2];
            a[i2] = -1;
            br = r - 1;
            blankIdx = i2;
            return true;
        } else if (d == 'D') {
            if (r == N - 1) return false;
            int i1 = idx(r, c), i2 = idx(r + 1, c);
            a[i1] = a[i2];
            a[i2] = -1;
            br = r + 1;
            blankIdx = i2;
            return true;
        } else if (d == 'L') {
            if (c == 0) return false;
            int i1 = idx(r, c), i2 = idx(r, c - 1);
            a[i1] = a[i2];
            a[i2] = -1;
            bc = c - 1;
            blankIdx = i2;
            return true;
        } else if (d == 'R') {
            if (c == N - 1) return false;
            int i1 = idx(r, c), i2 = idx(r, c + 1);
            a[i1] = a[i2];
            a[i2] = -1;
            bc = c + 1;
            blankIdx = i2;
            return true;
        }
        return false;
    }

    vector<char> validMovesExcludeOpp(char last) const {
        vector<char> mv;
        if (br > 0) mv.push_back('U');
        if (br < N - 1) mv.push_back('D');
        if (bc > 0) mv.push_back('L');
        if (bc < N - 1) mv.push_back('R');
        if (last != 0) {
            char o = opp(last);
            vector<char> mv2;
            for (char ch : mv) if (ch != o) mv2.push_back(ch);
            if (!mv2.empty()) return mv2;
        }
        return mv;
    }

    inline bool connLR(int id, int nid, int val, int nval, bool leftSide) const {
        // leftSide true: check left edge (id has left=1, nid has right=4)
        // else right edge (id has right=4, nid has left=1)
        if (nval == -1) return false;
        if (leftSide) return (val & 1) && (nval & 4);
        else return (val & 4) && (nval & 1);
    }
    inline bool connUD(int id, int nid, int val, int nval, bool upSide) const {
        // upSide true: check up edge (id has up=2, nid has down=8)
        // else down edge (id has down=8, nid has up=2)
        if (nval == -1) return false;
        if (upSide) return (val & 2) && (nval & 8);
        else return (val & 8) && (nval & 2);
    }

    Score computeScore() const {
        int NN = N*N;
        vector<int> deg(NN, 0);
        long long e2total = 0;
        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N; ++c) {
                int id = idx(r,c);
                int val = a[id];
                if (val == -1) continue;
                int d = 0;
                if (c > 0) {
                    int nid = id - 1;
                    int nval = a[nid];
                    if (connLR(id, nid, val, nval, true)) d++;
                }
                if (r > 0) {
                    int nid = id - N;
                    int nval = a[nid];
                    if (connUD(id, nid, val, nval, true)) d++;
                }
                if (c + 1 < N) {
                    int nid = id + 1;
                    int nval = a[nid];
                    if (connLR(id, nid, val, nval, false)) d++;
                }
                if (r + 1 < N) {
                    int nid = id + N;
                    int nval = a[nid];
                    if (connUD(id, nid, val, nval, false)) d++;
                }
                deg[id] = d;
                e2total += d;
            }
        }
        vector<char> vis(NN, 0);
        int bestTree = 0;
        long long cyclesSum = 0;
        deque<int> dq;
        for (int i = 0; i < NN; ++i) {
            if (a[i] == -1 || vis[i]) continue;
            // BFS component
            int nodes = 0;
            long long e2local = 0;
            vis[i] = 1;
            dq.clear();
            dq.push_back(i);
            while (!dq.empty()) {
                int u = dq.front(); dq.pop_front();
                nodes++;
                e2local += deg[u];
                int r = u / N, c = u % N;
                int val = a[u];
                // left
                if (c > 0) {
                    int v = u - 1;
                    if (!vis[v] && connLR(u, v, val, a[v], true)) { vis[v] = 1; dq.push_back(v); }
                }
                // up
                if (r > 0) {
                    int v = u - N;
                    if (!vis[v] && connUD(u, v, val, a[v], true)) { vis[v] = 1; dq.push_back(v); }
                }
                // right
                if (c + 1 < N) {
                    int v = u + 1;
                    if (!vis[v] && connLR(u, v, val, a[v], false)) { vis[v] = 1; dq.push_back(v); }
                }
                // down
                if (r + 1 < N) {
                    int v = u + N;
                    if (!vis[v] && connUD(u, v, val, a[v], false)) { vis[v] = 1; dq.push_back(v); }
                }
            }
            long long edgesLocal = e2local / 2;
            if (edgesLocal == nodes - 1) {
                if (nodes > bestTree) bestTree = nodes;
            } else if (edgesLocal > nodes - 1) {
                cyclesSum += (edgesLocal - (nodes - 1));
            }
        }
        Score s;
        s.S = bestTree;
        s.cycles = (int)cyclesSum;
        s.edges = (int)(e2total / 2);
        return s;
    }

    inline bool better(const Score &a, const Score &b) const {
        if (a.S != b.S) return a.S > b.S;
        if (a.cycles != b.cycles) return a.cycles < b.cycles;
        if (a.edges != b.edges) return a.edges > b.edges;
        return false;
    }

    char chooseMove(char last) {
        vector<char> cand = validMovesExcludeOpp(last);
        if (cand.empty()) {
            // shouldn't happen, but fallback to any valid move
            if (br > 0) cand.push_back('U');
            if (br < N - 1) cand.push_back('D');
            if (bc > 0) cand.push_back('L');
            if (bc < N - 1) cand.push_back('R');
        }

        // Small probability random to escape plateaus
        uniform_real_distribution<double> urd(0.0, 1.0);
        if (urd(rng) < 0.02) {
            uniform_int_distribution<int> uid(0, (int)cand.size() - 1);
            return cand[uid(rng)];
        }

        // 2-step lookahead
        Score best2 = {-1, INT_MAX, -1};
        vector<char> bestMoves;
        for (char m1 : cand) {
            if (!applyMove(m1)) continue;
            Score s1 = computeScore();

            vector<char> cand2 = validMovesExcludeOpp(m1);
            if (cand2.empty()) {
                // if no move except opposite, allow it
                cand2 = validMovesExcludeOpp(0);
            }
            Score bestS2 = s1; // at least s1 if no further moves
            bool any = false;
            for (char m2 : cand2) {
                if (!applyMove(m2)) continue;
                Score s2 = computeScore();
                if (!any || better(s2, bestS2)) {
                    bestS2 = s2;
                    any = true;
                }
                applyMove(opp(m2)); // revert m2
            }
            // if no next move (shouldn't), bestS2 remains s1
            if (better(bestS2, best2)) {
                best2 = bestS2;
                bestMoves.clear();
                bestMoves.push_back(m1);
            } else if (!better(best2, bestS2)) {
                bestMoves.push_back(m1);
            }
            applyMove(opp(m1)); // revert m1
        }
        if (bestMoves.empty()) {
            // fallback random among cand
            uniform_int_distribution<int> uid(0, (int)cand.size() - 1);
            return cand[uid(rng)];
        } else {
            uniform_int_distribution<int> uid(0, (int)bestMoves.size() - 1);
            return bestMoves[uid(rng)];
        }
    }

    void solve() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        cin >> N >> T;
        vector<string> s(N);
        for (int i = 0; i < N; ++i) {
            cin >> s[i];
        }
        a.assign(N * N, 0);
        br = bc = -1;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                char ch = s[i][j];
                int v;
                if (ch == '0') {
                    v = -1; // empty
                    br = i; bc = j;
                } else if ('1' <= ch && ch <= '9') {
                    v = ch - '0';
                } else if ('a' <= ch && ch <= 'f') {
                    v = ch - 'a' + 10;
                } else if ('A' <= ch && ch <= 'F') {
                    v = ch - 'A' + 10;
                } else {
                    v = -1;
                }
                a[idx(i,j)] = v;
            }
        }
        blankIdx = idx(br, bc);

        Score bestScore = computeScore();
        int bestK = 0;
        ans.clear();

        char last = 0;

        int targetAll = N * N - 1;
        for (int step = 0; step < T; ++step) {
            char mv = chooseMove(last);
            bool ok = applyMove(mv);
            if (!ok) {
                // fallback: choose any legal move
                vector<char> cand;
                if (br > 0) cand.push_back('U');
                if (br < N - 1) cand.push_back('D');
                if (bc > 0) cand.push_back('L');
                if (bc < N - 1) cand.push_back('R');
                if (cand.empty()) break;
                uniform_int_distribution<int> uid(0, (int)cand.size() - 1);
                mv = cand[uid(rng)];
                applyMove(mv);
            }
            ans.push_back(mv);
            last = mv;

            Score cur = computeScore();
            if (cur.S > bestScore.S) {
                bestScore = cur;
                bestK = (int)ans.size();
                if (bestScore.S == targetAll) break; // achieved full tree, stop to minimize K
            } else if (cur.S == bestScore.S && cur.S == targetAll) {
                // if we reached full tree at smaller K, update
                if (bestK == 0 || (int)ans.size() < bestK) {
                    bestScore = cur;
                    bestK = (int)ans.size();
                    break;
                }
            }
        }

        if (bestK == 0) {
            // If never improved over initial, optionally try a few random small moves
            // but it's okay to output empty
            cout << "\n";
        } else {
            cout << string(ans.begin(), ans.begin() + bestK) << "\n";
        }
    }
};

int main() {
    Solver solver;
    solver.solve();
    return 0;
}
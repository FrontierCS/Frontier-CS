#include <bits/stdc++.h>
using namespace std;

struct XorShift {
    uint64_t x = 88172645463325252ULL;
    XorShift() {
        uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        x ^= seed + 0x9e3779b97f4a7c15ULL;
        for (int i = 0; i < 10; i++) nextU64();
    }
    uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    double nextDouble() { return (nextU64() >> 11) * (1.0 / 9007199254740992.0); } // [0,1)
    int nextInt(int n) { return (int)(nextU64() % (uint64_t)n); }
};

struct DSU {
    int n;
    vector<int> p, sz, edges;
    DSU(int n=0): n(n), p(n), sz(n), edges(n) {}
    int find(int a) {
        while (p[a] != a) {
            p[a] = p[p[a]];
            a = p[a];
        }
        return a;
    }
    void init(const vector<int>& board) {
        for (int i = 0; i < n; i++) {
            p[i] = i;
            sz[i] = (board[i] != 0) ? 1 : 0;
            edges[i] = 0;
        }
    }
    void addEdge(int a, int b) {
        int ra = find(a), rb = find(b);
        if (ra == rb) {
            edges[ra] += 1;
            return;
        }
        if (sz[ra] < sz[rb]) swap(ra, rb);
        p[rb] = ra;
        sz[ra] += sz[rb];
        edges[ra] += edges[rb] + 1;
    }
};

static inline char opp(char c) {
    if (c == 'U') return 'D';
    if (c == 'D') return 'U';
    if (c == 'L') return 'R';
    return 'L';
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, T;
    cin >> N >> T;
    vector<int> board(N * N, 0);
    int er = -1, ec = -1;
    for (int i = 0; i < N; i++) {
        string s;
        cin >> s;
        for (int j = 0; j < N; j++) {
            char c = s[j];
            int v = 0;
            if ('0' <= c && c <= '9') v = c - '0';
            else v = 10 + (c - 'a');
            board[i * N + j] = v;
            if (v == 0) {
                er = i; ec = j;
            }
        }
    }

    DSU dsu(N * N);

    auto evalScore = [&]() -> int {
        dsu.init(board);
        for (int r = 0; r < N; r++) {
            for (int c = 0; c < N; c++) {
                int idx = r * N + c;
                int t = board[idx];
                if (t == 0) continue;
                if (c + 1 < N) {
                    int idx2 = idx + 1;
                    int t2 = board[idx2];
                    if (t2 != 0 && (t & 4) && (t2 & 1)) dsu.addEdge(idx, idx2);
                }
                if (r + 1 < N) {
                    int idx2 = idx + N;
                    int t2 = board[idx2];
                    if (t2 != 0 && (t & 8) && (t2 & 2)) dsu.addEdge(idx, idx2);
                }
            }
        }
        int best = 1;
        for (int i = 0; i < N * N; i++) {
            if (dsu.p[i] == i && dsu.sz[i] > 0) {
                if (dsu.edges[i] == dsu.sz[i] - 1) best = max(best, dsu.sz[i]);
            }
        }
        return best;
    };

    auto canMove = [&](char mv) -> bool {
        if (mv == 'U') return er > 0;
        if (mv == 'D') return er + 1 < N;
        if (mv == 'L') return ec > 0;
        return ec + 1 < N;
    };

    auto doMove = [&](char mv) {
        int nr = er, nc = ec;
        if (mv == 'U') nr--;
        else if (mv == 'D') nr++;
        else if (mv == 'L') nc--;
        else nc++;
        int a = er * N + ec;
        int b = nr * N + nc;
        swap(board[a], board[b]);
        er = nr; ec = nc;
    };

    XorShift rng;

    int curScore = evalScore();
    int bestScore = curScore;
    string moves, bestMoves;

    char lastMove = 0;

    double tStart = 2.5;
    double tEnd = 0.25;

    for (int step = 0; step < T; step++) {
        double alpha = (T <= 1) ? 1.0 : (double)step / (double)(T - 1);
        double temp = tStart * (1.0 - alpha) + tEnd * alpha;

        array<char,4> dirs = {'U','D','L','R'};
        vector<char> cand;
        cand.reserve(4);
        for (char d : dirs) if (canMove(d)) cand.push_back(d);
        if (cand.empty()) break;

        vector<int> scores(cand.size());
        int mx = -1;
        for (int i = 0; i < (int)cand.size(); i++) {
            char d = cand[i];
            doMove(d);
            int s = evalScore();
            doMove(opp(d));
            scores[i] = s;
            mx = max(mx, s);
        }

        vector<double> w(cand.size(), 0.0);
        double sumw = 0.0;
        char rev = lastMove ? opp(lastMove) : 0;

        for (int i = 0; i < (int)cand.size(); i++) {
            double ex = exp((scores[i] - mx) / max(1e-9, temp));
            if (rev && cand[i] == rev) ex *= 0.1;
            w[i] = ex;
            sumw += ex;
        }

        int chosen = 0;
        if (sumw <= 0.0) {
            chosen = rng.nextInt((int)cand.size());
        } else {
            double r = rng.nextDouble() * sumw;
            double acc = 0.0;
            for (int i = 0; i < (int)cand.size(); i++) {
                acc += w[i];
                if (r <= acc) { chosen = i; break; }
            }
        }

        char d = cand[chosen];
        doMove(d);
        curScore = scores[chosen];
        moves.push_back(d);
        lastMove = d;

        if (curScore > bestScore || (curScore == bestScore && moves.size() < bestMoves.size())) {
            bestScore = curScore;
            bestMoves = moves;
            if (bestScore == N * N - 1) break;
        }
    }

    cout << bestMoves << "\n";
    return 0;
}
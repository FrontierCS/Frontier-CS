#include <bits/stdc++.h>
using namespace std;

struct Solver9 {
    static constexpr int K = 9;
    static constexpr int STATES = 362880; // 9!
    array<int, K + 1> fact{};
    vector<int> parent;
    vector<uint8_t> moveFromParent;
    vector<array<uint8_t, K>> permOfRank;

    Solver9() {
        fact[0] = 1;
        for (int i = 1; i <= K; i++) fact[i] = fact[i - 1] * i;
        parent.assign(STATES, -1);
        moveFromParent.assign(STATES, 255);
        permOfRank.resize(STATES);
        bfs();
    }

    static inline void applyMove(array<uint8_t, K> &p, int mv) {
        if (mv == 0) { // A left rotate [0..7]
            uint8_t t = p[0];
            for (int i = 0; i < 7; i++) p[i] = p[i + 1];
            p[7] = t;
        } else if (mv == 1) { // A right rotate [0..7]
            uint8_t t = p[7];
            for (int i = 7; i > 0; i--) p[i] = p[i - 1];
            p[0] = t;
        } else if (mv == 2) { // B left rotate [1..8]
            uint8_t t = p[1];
            for (int i = 1; i < 8; i++) p[i] = p[i + 1];
            p[8] = t;
        } else { // mv == 3, B right rotate [1..8]
            uint8_t t = p[8];
            for (int i = 8; i > 1; i--) p[i] = p[i - 1];
            p[1] = t;
        }
    }

    inline int rankPerm(const array<uint8_t, K> &p) const {
        bool used[K] = {false};
        int rank = 0;
        for (int i = 0; i < K; i++) {
            int cnt = 0;
            for (int v = 0; v < (int)p[i]; v++) if (!used[v]) cnt++;
            rank += cnt * fact[K - 1 - i];
            used[p[i]] = true;
        }
        return rank;
    }

    void bfs() {
        array<uint8_t, K> id{};
        for (int i = 0; i < K; i++) id[i] = (uint8_t)i;
        int r0 = rankPerm(id);
        parent[r0] = r0;
        permOfRank[r0] = id;

        queue<int> q;
        q.push(r0);

        while (!q.empty()) {
            int cur = q.front(); q.pop();
            const auto &p = permOfRank[cur];
            for (int mv = 0; mv < 4; mv++) {
                auto np = p;
                applyMove(np, mv);
                int nr = rankPerm(np);
                if (parent[nr] == -1) {
                    parent[nr] = cur;
                    moveFromParent[nr] = (uint8_t)mv;
                    permOfRank[nr] = np;
                    q.push(nr);
                }
            }
        }

        // Optional safety check: ensure full coverage
        // int vis = 0; for (int i = 0; i < STATES; i++) if (parent[i] != -1) vis++;
        // if (vis != STATES) cerr << "Warning: BFS visited " << vis << " states\n";
    }

    // returns moves to transform given rank to identity rank 0 (identity permutation 0..8)
    vector<int> pathToIdentity(int rank) const {
        vector<int> moves;
        // identity rank for [0..8] is 0 in Lehmer ranking
        // but our BFS started from identity and stored parent pointers; parent[0] should be reachable.
        while (rank != 0) {
            int mv = moveFromParent[rank];
            int inv = (mv == 0 ? 1 : mv == 1 ? 0 : mv == 2 ? 3 : 2);
            moves.push_back(inv);
            rank = parent[rank];
        }
        return moves;
    }
};

struct Op {
    int l, r, dir; // dir: 0 left, 1 right
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    vector<Op> ops;

    auto rotate_left = [&](int l, int r) {
        int tmp = a[l];
        for (int i = l; i < r; i++) {
            a[i] = a[i + 1];
            pos[a[i]] = i;
        }
        a[r] = tmp;
        pos[tmp] = r;
    };

    auto rotate_right = [&](int l, int r) {
        int tmp = a[r];
        for (int i = r; i > l; i--) {
            a[i] = a[i - 1];
            pos[a[i]] = i;
        }
        a[l] = tmp;
        pos[tmp] = l;
    };

    int x;
    if (n >= 9) x = 8;
    else x = 2;

    if (x == 2) {
        for (int v = 1; v <= n; v++) {
            while (pos[v] > v) {
                int p = pos[v];
                int l = p - 1, r = p;
                ops.push_back({l, r, 1});
                rotate_right(l, r);
            }
        }
    } else {
        // x == 8, leave last 9 elements for BFS
        int L = n - 9; // sort positions 1..L
        for (int i = 1; i <= L; i++) {
            while (pos[i] != i) {
                int p = pos[i];
                if (p - 7 >= i) {
                    int l = p - 7, r = p;
                    ops.push_back({l, r, 1});
                    rotate_right(l, r);
                } else {
                    int l = i, r = i + 7;
                    ops.push_back({l, r, 0});
                    rotate_left(l, r);
                }
            }
        }

        // Solve the suffix of length 9 using BFS on moves within two overlapping windows
        int s = n - 8; // 1-indexed start of suffix length 9
        Solver9 solver;
        array<uint8_t, 9> p{};
        int base = n - 8;
        for (int j = 0; j < 9; j++) {
            int v = a[s + j];
            p[j] = (uint8_t)(v - base);
        }
        int rank = solver.rankPerm(p);
        auto moves = solver.pathToIdentity(rank);
        for (int mv : moves) {
            if (mv == 0) { // A left: [s, s+7]
                ops.push_back({s, s + 7, 0});
                rotate_left(s, s + 7);
            } else if (mv == 1) { // A right
                ops.push_back({s, s + 7, 1});
                rotate_right(s, s + 7);
            } else if (mv == 2) { // B left: [s+1, s+8]
                ops.push_back({s + 1, s + 8, 0});
                rotate_left(s + 1, s + 8);
            } else { // mv == 3, B right
                ops.push_back({s + 1, s + 8, 1});
                rotate_right(s + 1, s + 8);
            }
        }
    }

    // Output (two lines for x and m; valid as whitespace-separated)
    cout << x << "\n" << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.dir << "\n";
    }

    return 0;
}
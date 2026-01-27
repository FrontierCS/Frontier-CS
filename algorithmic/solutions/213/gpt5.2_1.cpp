#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, dir; // dir: 0 left, 1 right
};

struct SuffixSolver {
    int x;              // window length
    int k;              // k = x+1
    int totalStates;    // k!
    vector<int> parent; // parent state id in BFS tree from identity
    vector<int> pmove;  // move index used from parent -> this
    vector<array<uint8_t, 9>> permOf; // store perms for k<=9
    vector<array<int, 4>> trans;      // transitions for 4 moves

    static int fact(int n) {
        int r = 1;
        for (int i = 2; i <= n; i++) r *= i;
        return r;
    }

    int encode(const uint8_t *p) const {
        // Lehmer code, O(k^2), k<=9
        static int factorial[10];
        factorial[0] = 1;
        for (int i = 1; i <= 9; i++) factorial[i] = factorial[i-1] * i;

        int code = 0;
        for (int i = 0; i < k; i++) {
            int cnt = 0;
            for (int j = i + 1; j < k; j++) if (p[j] < p[i]) cnt++;
            code += cnt * factorial[k - 1 - i];
        }
        return code;
    }

    array<uint8_t, 9> unrank(int id) const {
        static int factorial[10];
        factorial[0] = 1;
        for (int i = 1; i <= 9; i++) factorial[i] = factorial[i-1] * i;

        array<uint8_t, 9> p{};
        array<uint8_t, 9> nums{};
        for (int i = 0; i < k; i++) nums[i] = (uint8_t)i;

        int rem = id;
        for (int i = 0; i < k; i++) {
            int f = factorial[k - 1 - i];
            int idx = rem / f;
            rem %= f;
            p[i] = nums[idx];
            for (int j = idx; j < k - 1 - i; j++) nums[j] = nums[j + 1];
        }
        return p;
    }

    array<uint8_t, 9> applyMove(const array<uint8_t, 9>& p, int mv) const {
        // mv: 0 start=1 left, 1 start=1 right, 2 start=2 left, 3 start=2 right (1-based in description)
        int start = (mv < 2 ? 0 : 1);    // 0-based
        int dir = (mv & 1);             // 0 left, 1 right
        array<uint8_t, 9> q = p;
        int l = start;
        int r = start + x - 1;          // inclusive, within [0..k-1]
        if (dir == 0) { // left
            uint8_t tmp = q[l];
            for (int i = l; i < r; i++) q[i] = q[i + 1];
            q[r] = tmp;
        } else { // right
            uint8_t tmp = q[r];
            for (int i = r; i > l; i--) q[i] = q[i - 1];
            q[l] = tmp;
        }
        return q;
    }

    bool build(int _x) {
        x = _x;
        k = x + 1;
        if (k > 9) return false;
        totalStates = fact(k);

        permOf.assign(totalStates, {});
        for (int id = 0; id < totalStates; id++) permOf[id] = unrank(id);

        trans.assign(totalStates, {});
        for (int id = 0; id < totalStates; id++) {
            for (int mv = 0; mv < 4; mv++) {
                auto q = applyMove(permOf[id], mv);
                trans[id][mv] = encode(q.data());
            }
        }

        parent.assign(totalStates, -1);
        pmove.assign(totalStates, -1);

        array<uint8_t, 9> ident{};
        for (int i = 0; i < k; i++) ident[i] = (uint8_t)i;
        int id0 = encode(ident.data());

        deque<int> dq;
        parent[id0] = -2;
        dq.push_back(id0);
        int vis = 1;

        while (!dq.empty()) {
            int v = dq.front(); dq.pop_front();
            for (int mv = 0; mv < 4; mv++) {
                int u = trans[v][mv];
                if (parent[u] != -1) continue;
                parent[u] = v;
                pmove[u] = mv;
                dq.push_back(u);
                vis++;
            }
        }
        return vis == totalStates;
    }

    vector<int> solveMovesToIdentity(const vector<int>& perm0based) const {
        array<uint8_t, 9> p{};
        for (int i = 0; i < k; i++) p[i] = (uint8_t)perm0based[i];
        int cur = encode(p.data());

        array<uint8_t, 9> ident{};
        for (int i = 0; i < k; i++) ident[i] = (uint8_t)i;
        int id0 = encode(ident.data());

        vector<int> moves;
        while (cur != id0) {
            int par = parent[cur];
            int mv = pmove[cur]; // par -> cur
            int inv = mv ^ 1;    // inverse toggles dir
            moves.push_back(inv);
            cur = par;
        }
        return moves;
    }
};

static inline void applyShift(vector<int>& a, vector<int>& pos, int l, int x, int dir) {
    int r = l + x - 1;
    if (dir == 0) { // left
        int tmp = a[l];
        for (int i = l; i < r; i++) a[i] = a[i + 1];
        a[r] = tmp;
    } else { // right
        int tmp = a[r];
        for (int i = r; i > l; i--) a[i] = a[i - 1];
        a[l] = tmp;
    }
    for (int i = l; i <= r; i++) pos[a[i]] = i;
}

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

    auto doOp = [&](int l, int x, int dir) {
        ops.push_back({l, l + x - 1, dir});
        applyShift(a, pos, l, x, dir);
    };

    if (n == 1) {
        cout << 1 << "\n" << 0 << "\n";
        return 0;
    }

    int x = -1;
    SuffixSolver solver;
    bool hasSolver = false;

    if (n < 7) {
        x = 2;
        // Bubble sort with adjacent swaps
        for (int val = 1; val <= n; val++) {
            while (pos[val] > val) {
                int p = pos[val];
                doOp(p - 1, x, 0); // swap via left rotation
            }
        }
    } else {
        // Prefer x=6, fallback x=8 if needed
        int cand = 6;
        bool ok = solver.build(cand);
        if (!ok) {
            if (n >= 9) {
                cand = 8;
                ok = solver.build(cand);
            }
        }
        if (!ok) {
            // Fallback for small n
            x = 2;
            for (int val = 1; val <= n; val++) {
                while (pos[val] > val) {
                    int p = pos[val];
                    doOp(p - 1, x, 0);
                }
            }
        } else {
            x = cand;
            hasSolver = true;

            int k = x + 1;
            int limit = n - k;      // sort positions 1..limit
            int L = limit + 1;      // suffix start, length k

            for (int i = 1; i <= limit; i++) {
                int p = pos[i];
                while (p - (x - 1) >= i) {
                    int l = p - x + 1;
                    doOp(l, x, 1); // right rotation moves target left by x-1
                    p = pos[i];
                }
                while (p > i) {
                    doOp(i, x, 0); // left rotation shifts target one left
                    p = pos[i];
                }
            }

            // Solve suffix of length k using precomputed BFS
            vector<int> perm0(k);
            for (int t = 0; t < k; t++) perm0[t] = a[L + t] - L; // 0..k-1
            vector<int> moves = solver.solveMovesToIdentity(perm0);

            for (int mv : moves) {
                int start = (mv < 2 ? 1 : 2); // local start 1 or 2
                int dir = (mv & 1);           // 0 left, 1 right
                int l = L + (start - 1);
                doOp(l, x, dir);
            }
        }
    }

    // Output
    cout << x << "\n" << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.dir << "\n";
    }

    return 0;
}
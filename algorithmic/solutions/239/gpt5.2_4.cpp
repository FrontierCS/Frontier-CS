#include <bits/stdc++.h>
using namespace std;

struct Op {
    int u, c, v;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    int N = n + 1;

    if (n <= 3) {
        cout << 0 << "\n";
        return 0;
    }

    auto evalB = [&](int B) -> long long {
        int t = (N + B - 1) / B;
        long long internal = 0;
        vector<int> sz(t);
        for (int k = 0; k < t; k++) {
            int L = k * B;
            int R = min(N - 1, (k + 1) * B - 1);
            sz[k] = R - L + 1;
            long long s = sz[k];
            if (s >= 3) internal += (s - 1) * (s - 2) / 2;
        }
        long long cross = (t >= 3) ? 1LL * (t - 1) * (t - 2) / 2 : 0;
        long long helper = 0;
        for (int k = 1; k < t; k++) if (sz[k] > 1) helper++;
        return internal + cross + helper;
    };

    int bestB = 1;
    long long bestM = (1LL << 62);
    for (int B = 1; B <= N; B++) {
        long long m = evalB(B);
        if (m < bestM) {
            bestM = m;
            bestB = B;
        }
    }

    struct Block { int L, R; };
    vector<Block> blocks;
    for (int L = 0; L < N; L += bestB) {
        int R = min(N - 1, L + bestB - 1);
        blocks.push_back({L, R});
    }
    int t = (int)blocks.size();
    vector<int> S(t), E(t), sz(t);
    for (int i = 0; i < t; i++) {
        S[i] = blocks[i].L;
        E[i] = blocks[i].R;
        sz[i] = E[i] - S[i] + 1;
    }

    vector<Op> ops;
    ops.reserve((size_t)bestM + 1024);

    // 1) Complete edges within each block (excluding existing adjacent edges).
    for (int bi = 0; bi < t; bi++) {
        int L = S[bi], R = E[bi];
        for (int u = L; u <= R - 2; u++) {
            for (int v = u + 2; v <= R; v++) {
                ops.push_back({u, v - 1, v}); // u->(v-1) and (v-1)->v already, add u->v
            }
        }
    }

    // 2) Helper edges between consecutive block ends: E[p] -> E[p+1] (if not already an initial edge).
    for (int p = 0; p + 1 < t; p++) {
        if (E[p] + 1 == E[p + 1]) continue; // already initial edge
        ops.push_back({E[p], S[p + 1], E[p + 1]}); // E[p]->S[p+1] initial, S[p+1]->E[p+1] exists
    }

    // 3) Cross edges: E[p] -> S[q] for q >= p+2
    for (int q = 2; q < t; q++) {
        for (int p = q - 2; p >= 0; p--) {
            ops.push_back({E[p], E[p + 1], S[q]}); // E[p]->E[p+1] (helper or initial), E[p+1]->S[q] already
        }
    }

    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.u << " " << op.c << " " << op.v << "\n";
    }
    return 0;
}
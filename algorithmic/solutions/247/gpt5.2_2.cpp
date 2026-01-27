#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int N;
    vector<long long> A, B;
    vector<pair<int,int>> ops;

    void apply_op(int i, int j) { // 0-based, i<j
        long long ai = A[i], aj = A[j];
        A[i] = aj - 1;
        A[j] = ai + 1;
        ops.emplace_back(i + 1, j + 1);
    }

    // Transfer 1 unit from `from` to `to`: A[from]--, A[to]++,
    // while keeping other positions unchanged.
    // Requires |from-to| >= 2.
    void transfer1(int from, int to) {
        if (from == to) return;
        int u = from + 1, v = to + 1; // to 1-based for reasoning
        int a = min(u, v), c = max(u, v);
        if (c - a < 2) {
            // Should not happen in our construction.
            // Fallback to something valid but may break correctness; assert in debug.
            // We'll still avoid UB.
            return;
        }
        int b = a + 1; // guaranteed a < b < c
        // Convert back to 0-based for apply_op
        int A0 = a - 1, B0 = b - 1, C0 = c - 1;

        if (u > v) {
            // transfer from c to a (since from is the larger index = c)
            // W = (a,b)(b,c)(a,b)(a,c) gives +1 at a and -1 at c
            apply_op(A0, B0);
            apply_op(B0, C0);
            apply_op(A0, B0);
            apply_op(A0, C0);
        } else {
            // transfer from a to c (since from is the smaller index = a)
            // inverse(W) = (a,c)(a,b)(b,c)(a,b)
            apply_op(A0, C0);
            apply_op(A0, B0);
            apply_op(B0, C0);
            apply_op(A0, B0);
        }
    }

    bool solveN2() {
        if (A == B) {
            cout << "Yes\n0\n";
            return true;
        }
        vector<long long> A2 = A;
        // only operation (1,2)
        long long a0 = A2[0], a1 = A2[1];
        A2[0] = a1 - 1;
        A2[1] = a0 + 1;
        if (A2 == B) {
            cout << "Yes\n1\n1 2\n";
            return true;
        }
        cout << "No\n";
        return true;
    }

    bool solveN3_BFS() {
        long long S = A[0] + A[1] + A[2];
        if (B[0] + B[1] + B[2] != S) {
            cout << "No\n";
            return true;
        }

        const int minV = -1000;
        const int maxV = 1300;
        const int R = maxV - minV + 1;
        const int SZ = R * R;

        auto inRange = [&](long long x) -> bool { return minV <= x && x <= maxV; };
        auto idxOf = [&](int a, int b) -> int { return (a - minV) * R + (b - minV); };

        auto decode = [&](int idx, int &a, int &b, int &c) {
            a = idx / R + minV;
            b = idx % R + minV;
            c = (int)(S - a - b);
        };

        int sa = (int)A[0], sb = (int)A[1], sc = (int)A[2];
        int ta = (int)B[0], tb = (int)B[1], tc = (int)B[2];

        if (!inRange(sa) || !inRange(sb) || !inRange(sc) || !inRange(ta) || !inRange(tb) || !inRange(tc)) {
            cout << "No\n";
            return true;
        }
        if (sa + sb + sc != S || ta + tb + tc != S) {
            cout << "No\n";
            return true;
        }

        int sidx = idxOf(sa, sb);
        int tidx = idxOf(ta, tb);

        vector<int> parent(SZ, -1);
        vector<unsigned short> dist(SZ, (unsigned short)65535);
        vector<unsigned char> how(SZ, 255);

        deque<int> q;
        dist[sidx] = 0;
        parent[sidx] = sidx;
        q.push_back(sidx);

        auto tryPush = [&](int cur, int na, int nb, int nc, unsigned char opCode) {
            if (!inRange(na) || !inRange(nb) || !inRange(nc)) return;
            if (na + nb + nc != S) return;
            int nidx = idxOf(na, nb);
            if (dist[nidx] != 65535) return;
            dist[nidx] = dist[cur] + 1;
            parent[nidx] = cur;
            how[nidx] = opCode;
            q.push_back(nidx);
        };

        while (!q.empty() && dist[tidx] == 65535) {
            int cur = q.front();
            q.pop_front();
            int a, b, c;
            decode(cur, a, b, c);

            // (1,2): (a,b,c) -> (b-1, a+1, c)
            tryPush(cur, b - 1, a + 1, c, 0);
            // (1,3): (a,b,c) -> (c-1, b, a+1)
            tryPush(cur, c - 1, b, a + 1, 1);
            // (2,3): (a,b,c) -> (a, c-1, b+1)
            tryPush(cur, a, c - 1, b + 1, 2);
        }

        if (dist[tidx] == 65535) {
            cout << "No\n";
            return true;
        }

        vector<pair<int,int>> path;
        int cur = tidx;
        while (cur != sidx) {
            unsigned char op = how[cur];
            if (op == 0) path.emplace_back(1, 2);
            else if (op == 1) path.emplace_back(1, 3);
            else path.emplace_back(2, 3);
            cur = parent[cur];
        }
        reverse(path.begin(), path.end());

        cout << "Yes\n" << path.size() << "\n";
        for (auto &e : path) cout << e.first << " " << e.second << "\n";
        return true;
    }

    bool solveNge4() {
        long long sumA = 0, sumB = 0;
        for (int i = 0; i < N; i++) sumA += A[i], sumB += B[i];
        if (sumA != sumB) {
            cout << "No\n";
            return true;
        }

        // Fix positions 2..N-2 using reservoir at N
        for (int i = 1; i <= N - 3; i++) { // 0-based: position i+1 in 1-based
            while (A[i] < B[i]) transfer1(N - 1, i); // N -> i
            while (A[i] > B[i]) transfer1(i, N - 1); // i -> N
        }

        // Fix position N-1 using reservoir at 1
        int idxN1 = N - 2; // 0-based for position N-1
        while (A[idxN1] < B[idxN1]) transfer1(0, idxN1); // 1 -> N-1
        while (A[idxN1] > B[idxN1]) transfer1(idxN1, 0); // N-1 -> 1

        // Fix position 1 (and thus N automatically) using transfers between 1 and N
        while (A[0] < B[0]) transfer1(N - 1, 0); // N -> 1
        while (A[0] > B[0]) transfer1(0, N - 1); // 1 -> N

        // Now should match exactly.
        // (Optional safety check omitted)
        cout << "Yes\n" << ops.size() << "\n";
        for (auto &p : ops) cout << p.first << " " << p.second << "\n";
        return true;
    }

    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        cin >> N;
        A.assign(N, 0);
        B.assign(N, 0);
        for (int i = 0; i < N; i++) cin >> A[i];
        for (int i = 0; i < N; i++) cin >> B[i];

        if (N == 2) { solveN2(); return; }
        if (N == 3) { solveN3_BFS(); return; }
        solveNge4();
    }
};

int main() {
    Solver s;
    s.run();
    return 0;
}
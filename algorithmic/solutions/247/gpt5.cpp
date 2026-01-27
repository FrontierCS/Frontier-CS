#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<long long> A(N+1), B(N+1);
    for (int i = 1; i <= N; ++i) cin >> A[i];
    for (int i = 1; i <= N; ++i) cin >> B[i];
    long long sA = 0, sB = 0;
    for (int i = 1; i <= N; ++i) { sA += A[i]; sB += B[i]; }
    if (sA != sB) {
        cout << "No\n";
        return 0;
    }
    // Special case N == 2
    if (N == 2) {
        if (A[1] == B[1] && A[2] == B[2]) {
            cout << "Yes\n0\n";
            return 0;
        }
        long long c1 = A[2] - 1;
        long long c2 = A[1] + 1;
        if (c1 == B[1] && c2 == B[2]) {
            cout << "Yes\n1\n1 2\n";
            return 0;
        }
        cout << "No\n";
        return 0;
    }

    // For N >= 3, we can always achieve using transfers via an anchor index.
    // We'll implement transfer T(to, from) using 4 operations:
    // O(to, from); then pure swap(to, from) using a buffer t outside [min, max] with 3 O's.
    vector<pair<int,int>> ops;
    auto add_op = [&](int i, int j){
        if (i > j) swap(i, j);
        ops.emplace_back(i, j);
    };
    auto getBufferOutside = [&](int a, int b)->int{
        int mn = min(a, b), mx = max(a, b);
        if (mn > 1) return 1;
        if (mx < N) return N;
        // Should not happen with our anchor choice
        // Fallback (though not expected): find any outside if exists
        for (int t = 1; t <= N; ++t) {
            if (t != a && t != b && (t < mn || t > mx)) return t;
        }
        // As a last resort (should never happen), pick any different index
        for (int t = 1; t <= N; ++t) {
            if (t != a && t != b) return t;
        }
        return 1; // dummy
    };
    auto pure_swap = [&](int x, int y, int t){
        int mn = min(x, y), mx = max(x, y);
        if (t < mn) {
            // pattern: O(t, mx), O(t, mn), O(t, mx)
            add_op(t, mx);
            add_op(t, mn);
            add_op(t, mx);
        } else if (t > mx) {
            // pattern: O(mn, t), O(mx, t), O(mn, t)
            add_op(mn, t);
            add_op(mx, t);
            add_op(mn, t);
        } else {
            // t between x and y: find an outside buffer and chain two swaps
            // We'll perform: swap(x, y) using t_outside by first swapping x with t, then t with y, then x with t again.
            // But to keep correctness, we can recursively handle with an outside buffer u.
            int u = (mn > 1) ? 1 : N;
            if (u == x || u == y) u = (u == 1 ? N : 1);
            // Now perform sequence that swaps x and y using buffers t and u
            // swap(x, u) using t_outside of [min(x,u), max(x,u)]
            int t1 = getBufferOutside(x, u);
            // ensure t1 != x and t1 != u
            if (t1 == x || t1 == u) {
                for (int cand = 1; cand <= N; ++cand) {
                    if (cand != x && cand != u && (cand < min(x,u) || cand > max(x,u))) { t1 = cand; break; }
                }
            }
            pure_swap(x, u, t1);
            // swap(u, y) with buffer outside
            int t2 = getBufferOutside(u, y);
            if (t2 == u || t2 == y) {
                for (int cand = 1; cand <= N; ++cand) {
                    if (cand != u && cand != y && (cand < min(u,y) || cand > max(u,y))) { t2 = cand; break; }
                }
            }
            pure_swap(u, y, t2);
            // swap(x, u) again to place u back
            t1 = getBufferOutside(x, u);
            if (t1 == x || t1 == u) {
                for (int cand = 1; cand <= N; ++cand) {
                    if (cand != x && cand != u && (cand < min(x,u) || cand > max(x,u))) { t1 = cand; break; }
                }
            }
            pure_swap(x, u, t1);
            return;
        }
    };
    auto transfer = [&](int to, int from){
        // realize T(to, from)
        add_op(to, from); // O(to, from) = S∘T
        int t = getBufferOutside(to, from);
        pure_swap(to, from, t); // apply S to revert swap, net T
    };

    // Choose anchor s = 2 (since N >= 3, index 2 exists and is not extreme enough)
    int s = 2;

    vector<long long> diff(N+1);
    for (int i = 1; i <= N; ++i) diff[i] = B[i] - A[i];

    // First, move all surplus to anchor s
    for (int j = 1; j <= N; ++j) {
        if (j == s) continue;
        if (diff[j] < 0) {
            long long d = -diff[j];
            for (long long k = 0; k < d; ++k) {
                transfer(s, j);
            }
            diff[s] -= d;
            diff[j] += d;
        }
    }
    // Then, distribute from anchor s to deficits
    for (int i = 1; i <= N; ++i) {
        if (i == s) continue;
        if (diff[i] > 0) {
            long long d = diff[i];
            for (long long k = 0; k < d; ++k) {
                transfer(i, s);
            }
            diff[s] += d;
            diff[i] -= d;
        }
    }
    // After these, diff should be all zeros
    bool ok = true;
    for (int i = 1; i <= N; ++i) if (diff[i] != 0) ok = false;
    if (!ok) {
        // Fallback: shouldn't happen
        cout << "No\n";
        return 0;
    }

    cout << "Yes\n";
    cout << (int)ops.size() << "\n";
    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}
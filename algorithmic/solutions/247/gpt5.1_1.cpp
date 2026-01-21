#include <bits/stdc++.h>
using namespace std;

int N;
vector<long long> A, B;
vector<pair<int,int>> ops;

// Apply one operation (i, j) with i<j
void apply_op(int i, int j) {
    if (i > j) swap(i, j);
    long long ai = A[i], aj = A[j];
    A[i] = aj - 1;
    A[j] = ai + 1;
    ops.emplace_back(i, j);
}

// Swap values at indices x and y using helper h (all distinct, N>=3)
void do_swap(int x, int y, int h) {
    if (x == y) return;
    int idx[3] = {x, y, h};
    int s[3] = {idx[0], idx[1], idx[2]};
    sort(s, s+3);
    int s0 = s[0], s1 = s[1], s2 = s[2];

    bool is01 = ((x == s0 && y == s1) || (x == s1 && y == s0));
    bool is12 = ((x == s1 && y == s2) || (x == s2 && y == s1));
    // else {s0, s2}
    if (is01) {
        // swap(s0,s1): S_ab
        apply_op(s1, s2);
        apply_op(s0, s2);
        apply_op(s1, s2);
    } else if (is12) {
        // swap(s1,s2): S_bc
        apply_op(s0, s2);
        apply_op(s0, s1);
        apply_op(s0, s2);
    } else {
        // swap(s0,s2): S_ac = S_ab S_bc S_ab
        // S_ab
        apply_op(s1, s2);
        apply_op(s0, s2);
        apply_op(s1, s2);
        // S_bc
        apply_op(s0, s2);
        apply_op(s0, s1);
        apply_op(s0, s2);
        // S_ab
        apply_op(s1, s2);
        apply_op(s0, s2);
        apply_op(s1, s2);
    }
}

// Transfer 1 unit from index 'from' to index 'to'
void transfer(int from, int to) {
    if (from == to) return;
    // choose helper
    int h = -1;
    for (int k = 1; k <= N; ++k) {
        if (k != from && k != to) {
            h = k;
            break;
        }
    }
    int p = min(from, to);
    int q = max(from, to);
    if (from == p) {
        // from smaller to larger: T(p->q) = O(p,q) ∘ S(p,q)  => do S then O
        do_swap(p, q, h);
        apply_op(p, q);
    } else {
        // from larger to smaller: T(q->p) = S(p,q) ∘ O(p,q)  => do O then S
        apply_op(p, q);
        do_swap(p, q, h);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    cin >> N;
    A.assign(N+1, 0);
    B.assign(N+1, 0);
    for (int i = 1; i <= N; ++i) cin >> A[i];
    for (int i = 1; i <= N; ++i) cin >> B[i];
    
    long long sumA = 0, sumB = 0;
    for (int i = 1; i <= N; ++i) {
        sumA += A[i];
        sumB += B[i];
    }
    if (sumA != sumB) {
        cout << "No\n";
        return 0;
    }
    
    if (N == 2) {
        if (A[1] == B[1] && A[2] == B[2]) {
            cout << "Yes\n0\n";
            return 0;
        } else {
            long long a1 = A[1], a2 = A[2];
            long long na1 = a2 - 1, na2 = a1 + 1;
            if (na1 == B[1] && na2 == B[2]) {
                cout << "Yes\n1\n1 2\n";
                return 0;
            } else {
                cout << "No\n";
                return 0;
            }
        }
    }
    
    // N >= 3
    for (int i = 1; i <= N; ++i) {
        while (A[i] < B[i]) {
            int j = -1;
            for (int k = 1; k <= N; ++k) {
                if (k == i) continue;
                if (A[k] > B[k]) {
                    j = k;
                    break;
                }
            }
            if (j == -1) {
                cout << "No\n";
                return 0;
            }
            transfer(j, i);
        }
    }
    
    // verify
    bool ok = true;
    for (int i = 1; i <= N; ++i) {
        if (A[i] != B[i]) { ok = false; break; }
    }
    if (!ok) {
        cout << "No\n";
        return 0;
    }
    
    cout << "Yes\n";
    cout << ops.size() << "\n";
    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}
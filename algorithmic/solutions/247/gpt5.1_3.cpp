#include <bits/stdc++.h>
using namespace std;

int N;
vector<long long> A, B;
vector<pair<int,int>> ops;

inline void apply_op(int i, int j) {
    if (i > j) swap(i, j); // ensure i < j
    long long ai = A[i-1];
    long long aj = A[j-1];
    A[i-1] = aj - 1;
    A[j-1] = ai + 1;
    ops.emplace_back(i, j);
}

// swap indices i and i+1 without changing others
inline void swap_adj(int i) { // 1 <= i <= N-1
    int j = i + 1;
    int k = (i > 1 ? 1 : N); // helper index
    if (k < i) { // k < i < j
        apply_op(k, i);
        apply_op(k, j);
        apply_op(k, i);
    } else { // i < j < k
        apply_op(i, k);
        apply_op(j, k);
        apply_op(i, k);
    }
}

// move 1 unit from i to i+1
inline void move_right(int i) { // 1 <= i < N
    swap_adj(i);        // S_{i,i+1}
    apply_op(i, i+1);   // T_{i,i+1}; total = Add_{i,i+1}
}

// move 1 unit from i+1 to i
inline void move_left(int i) { // 1 <= i < N
    apply_op(i, i+1);   // T_{i,i+1}
    swap_adj(i);        // S_{i,i+1}; total = Add_{i+1,i}
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N;
    A.assign(N, 0);
    B.assign(N, 0);
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < N; ++i) cin >> B[i];

    long long sumA = 0, sumB = 0;
    for (int i = 0; i < N; ++i) { sumA += A[i]; sumB += B[i]; }

    if (N == 2) {
        if (sumA != sumB) {
            cout << "No\n";
            return 0;
        }
        if (A[0] == B[0] && A[1] == B[1]) {
            cout << "Yes\n0\n";
            return 0;
        }
        long long a1 = A[0], a2 = A[1];
        long long t1 = a2 - 1, t2 = a1 + 1;
        if (t1 == B[0] && t2 == B[1]) {
            cout << "Yes\n1\n1 2\n";
            return 0;
        } else {
            cout << "No\n";
            return 0;
        }
    }

    if (sumA != sumB) {
        cout << "No\n";
        return 0;
    }

    ops.clear();

    for (int i = 0; i < N-1; ++i) {
        while (A[i] < B[i]) {
            move_left(i + 1);  // move from i+1 to i
        }
        while (A[i] > B[i]) {
            move_right(i + 1); // move from i to i+1
        }
    }
    // Now A[N-1] should equal B[N-1] automatically if sums are equal

    cout << "Yes\n";
    cout << ops.size() << "\n";
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << "\n";
    }

    return 0;
}
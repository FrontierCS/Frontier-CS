#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<long long> A(N + 1), B(N + 1);
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

    vector<pair<int,int>> ops;

    auto op = [&](int i, int j) {
        // i < j must hold
        long long ai = A[i], aj = A[j];
        A[i] = aj - 1;
        A[j] = ai + 1;
        ops.emplace_back(i, j);
    };

    if (N == 2) {
        if (A[1] == B[1] && A[2] == B[2]) {
            cout << "Yes\n0\n";
            return 0;
        }
        long long a1 = A[1], a2 = A[2];
        long long a1p = a2 - 1, a2p = a1 + 1;
        if (a1p == B[1] && a2p == B[2]) {
            cout << "Yes\n1\n1 2\n";
        } else {
            cout << "No\n";
        }
        return 0;
    }

    // N >= 3
    vector<long long> prefA(N + 1), prefB(N + 1);
    for (int i = 1; i <= N; ++i) {
        prefA[i] = prefA[i - 1] + A[i];
        prefB[i] = prefB[i - 1] + B[i];
    }

    vector<long long> D(N + 1);
    for (int i = 1; i <= N - 1; ++i) {
        D[i] = prefB[i] - prefA[i];
    }

    auto swp = [&](int i, int j, int p) {
        // swap A[i] and A[j] using pivot p (p < i or p > j)
        if (p < i) {
            op(p, i);
            op(p, j);
            op(p, i);
        } else { // p > j
            op(i, p);
            op(j, p);
            op(i, p);
        }
    };

    for (int k = 1; k <= N - 1; ++k) {
        long long dk = D[k];
        if (dk > 0) {
            int pivot = (k > 1 ? 1 : N); // pivot outside {k, k+1}
            for (long long t = 0; t < dk; ++t) {
                // move 1 from k+1 to k: T_left = S ∘ O (O then swap)
                op(k, k + 1);
                swp(k, k + 1, pivot);
            }
        } else if (dk < 0) {
            long long cnt = -dk;
            int pivot = (k > 1 ? 1 : N);
            for (long long t = 0; t < cnt; ++t) {
                // move 1 from k to k+1: T_right = O ∘ S (swap then O)
                swp(k, k + 1, pivot);
                op(k, k + 1);
            }
        }
    }

    // Optional sanity check (can be commented out)
    // for (int i = 1; i <= N; ++i) {
    //     if (A[i] != B[i]) {
    //         // Should not happen
    //     }
    // }

    cout << "Yes\n";
    cout << ops.size() << "\n";
    for (auto &pr : ops) {
        cout << pr.first << " " << pr.second << "\n";
    }
    return 0;
}
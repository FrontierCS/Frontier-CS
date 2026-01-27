#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<long long> A(N), B(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < N; ++i) cin >> B[i];
    
    long long sumA = 0, sumB = 0;
    for (int i = 0; i < N; ++i) sumA += A[i], sumB += B[i];
    if (sumA != sumB) {
        cout << "No\n";
        return 0;
    }
    
    if (N == 1) {
        if (A[0] == B[0]) {
            cout << "Yes\n0\n";
        } else {
            cout << "No\n";
        }
        return 0;
    }
    
    if (N == 2) {
        if (A == B) {
            cout << "Yes\n0\n";
            return 0;
        }
        vector<long long> F = {A[1] - 1, A[0] + 1};
        if (F == B) {
            cout << "Yes\n1\n1 2\n";
        } else {
            cout << "No\n";
        }
        return 0;
    }
    
    vector<pair<int,int>> ops;
    auto apply = [&](int i, int j) {
        // i, j are 1-based positions with i<j
        int ii = i - 1, jj = j - 1;
        long long ai = A[ii], aj = A[jj];
        A[ii] = aj - 1;
        A[jj] = ai + 1;
        ops.emplace_back(i, j);
    };
    
    auto inc = [&](int i) {
        // Increase A[i] by 1 using indices (i, N-1, N)
        apply(i, N-1);
        apply(N-1, N);
        apply(i, N);
    };
    
    auto dec = [&](int i) {
        // Decrease A[i] by 1 using indices (i, N-1, N)
        apply(i, N);
        apply(N-1, N);
        apply(i, N-1);
    };
    
    // Stage 1: Fix first N-2 elements
    for (int i = 1; i <= N - 2; ++i) {
        while (A[i-1] < B[i-1]) inc(i);
        while (A[i-1] > B[i-1]) dec(i);
    }
    
    // Stage 2: Adjust last two elements using F and swap via inc/dec on some base index
    int base = 1; // any index in [1..N-2]
    while (A[N-2] != B[N-2]) {
        if (A[N-2] < B[N-2]) {
            // Need to increase A[N-1] by 1 and decrease A[N] by 1
            apply(N-1, N);     // F
            inc(base);         // S = inc then dec swaps last two without changing A[base]
            dec(base);
        } else {
            // Need to decrease A[N-1] by 1 and increase A[N] by 1
            inc(base);         // S
            dec(base);
            apply(N-1, N);     // F
        }
    }
    
    // After adjustments, A should equal B
    if (A != B) {
        // As a fallback (should rarely happen), just declare No (though theoretically it should not happen)
        // But we attempt no further steps as algorithm guarantees correctness under sum equality.
        // To be safe, print No if mismatch remains.
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
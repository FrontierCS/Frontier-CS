#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<int> A(N), B(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < N; ++i) cin >> B[i];

    long long sumA = accumulate(A.begin(), A.end(), 0LL);
    long long sumB = accumulate(B.begin(), B.end(), 0LL);
    if (sumA != sumB) {
        cout << "No\n";
        return 0;
    }

    if (A == B) {
        cout << "Yes\n0\n";
        return 0;
    }

    vector<pair<int, int>> ops;
    vector<int> cur = A;
    const int MAX_STEPS = 100000;
    const int NO_IMPROVE_LIMIT = 5000;
    int no_improve = 0;
    mt19937 rng(12345); // fixed seed for determinism

    auto diff_sum = [&]() -> long long {
        long long s = 0;
        for (int i = 0; i < N; ++i) s += abs(cur[i] - B[i]);
        return s;
    };

    long long cur_diff = diff_sum();

    for (int step = 0; step < MAX_STEPS; ++step) {
        if (cur == B) {
            cout << "Yes\n";
            cout << ops.size() << '\n';
            for (auto& p : ops)
                cout << p.first + 1 << ' ' << p.second + 1 << '\n';
            return 0;
        }

        int best_i = -1, best_j = -1;
        long long best_delta = -1;

        // Try all pairs (i,j) with i<j
        for (int i = 0; i < N; ++i) {
            for (int j = i + 1; j < N; ++j) {
                int new_i = cur[j] - 1;
                int new_j = cur[i] + 1;
                long long new_diff = cur_diff
                    - abs(cur[i] - B[i]) - abs(cur[j] - B[j])
                    + abs(new_i - B[i]) + abs(new_j - B[j]);
                long long delta = cur_diff - new_diff;
                if (delta > best_delta) {
                    best_delta = delta;
                    best_i = i;
                    best_j = j;
                }
            }
        }

        if (best_delta <= 0) {
            ++no_improve;
            if (no_improve > NO_IMPROVE_LIMIT) break;
            // Try a random move
            uniform_int_distribution<int> dist(0, N - 1);
            int i, j;
            do {
                i = dist(rng);
                j = dist(rng);
            } while (i >= j);
            best_i = i;
            best_j = j;
        } else {
            no_improve = 0;
        }

        // Apply the move
        int tmp_i = cur[best_i];
        int tmp_j = cur[best_j];
        cur[best_i] = tmp_j - 1;
        cur[best_j] = tmp_i + 1;
        ops.emplace_back(best_i, best_j);
        cur_diff = diff_sum(); // update diff sum
    }

    cout << "No\n";
    return 0;
}
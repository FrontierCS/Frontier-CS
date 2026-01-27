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
    
    auto printNo = []() {
        cout << "No\n";
    };
    
    long long sumA = 0, sumB = 0;
    for (int i = 1; i <= N; ++i) { sumA += A[i]; sumB += B[i]; }
    
    vector<pair<int,int>> ops;
    
    if (N == 2) {
        if (sumA != sumB) {
            printNo();
            return 0;
        }
        if (A[1] == B[1] && A[2] == B[2]) {
            cout << "Yes\n0\n";
            return 0;
        }
        // One operation T_12
        long long x = A[1], y = A[2];
        long long nx = y - 1, ny = x + 1;
        if (nx == B[1] && ny == B[2]) {
            cout << "Yes\n1\n1 2\n";
            return 0;
        } else {
            printNo();
            return 0;
        }
    }
    
    if (sumA != sumB) {
        printNo();
        return 0;
    }
    
    // Helper lambdas to add operations
    auto addSwap = [&](int i, int j, int k) {
        // Produces pure swap S_ij using index k outside both i and j
        if (i > j) swap(i, j);
        if (k > j) {
            ops.emplace_back(i, k);
            ops.emplace_back(j, k);
            ops.emplace_back(i, k);
        } else if (k < i) {
            ops.emplace_back(k, j);
            ops.emplace_back(k, i);
            ops.emplace_back(k, j);
        } else {
            // Should not happen
        }
    };
    
    auto add_R_forward = [&](int i, int j) {
        // dec A[i] by 1, inc A[j] by 1, with i < j
        if (j < N) {
            int k = N;
            addSwap(i, j, k);
            ops.emplace_back(i, j);
        } else {
            if (i > 1) {
                int k = 1;
                addSwap(i, j, k);
                ops.emplace_back(i, j);
            } else {
                // i == 1, j == N: use middle index m
                int m = 2;
                ops.emplace_back(i, j);
                ops.emplace_back(i, m);
                ops.emplace_back(m, j);
                ops.emplace_back(i, m);
            }
        }
    };
    
    auto add_R_reverse = [&](int i, int j) {
        // dec A[j] by 1, inc A[i] by 1, with i < j
        if (j < N) {
            int k = N;
            ops.emplace_back(i, j);
            addSwap(i, j, k);
        } else {
            if (i > 1) {
                int k = 1;
                ops.emplace_back(i, j);
                addSwap(i, j, k);
            } else {
                // i == 1, j == N: use middle index m
                int m = 2;
                ops.emplace_back(i, m);
                ops.emplace_back(m, j);
                ops.emplace_back(i, m);
                ops.emplace_back(i, j);
            }
        }
    };
    
    auto transfer_one = [&](int from, int to) {
        if (from == to) return;
        if (from < to) {
            add_R_forward(from, to);
        } else {
            // from > to
            add_R_reverse(to, from);
        }
    };
    
    vector<long long> d(N + 1);
    for (int i = 1; i <= N; ++i) d[i] = B[i] - A[i];
    
    vector<pair<int,long long>> need, have;
    for (int i = 1; i <= N; ++i) {
        if (d[i] > 0) need.emplace_back(i, d[i]);
        else if (d[i] < 0) have.emplace_back(i, -d[i]);
    }
    
    size_t p = 0, q = 0;
    while (p < need.size() && q < have.size()) {
        int to = need[p].first;
        int from = have[q].first;
        long long t = min(need[p].second, have[q].second);
        for (long long s = 0; s < t; ++s) {
            transfer_one(from, to);
        }
        need[p].second -= t;
        have[q].second -= t;
        if (need[p].second == 0) ++p;
        if (have[q].second == 0) ++q;
    }
    
    cout << "Yes\n";
    cout << ops.size() << "\n";
    for (auto &pr : ops) {
        cout << pr.first << " " << pr.second << "\n";
    }
    return 0;
}
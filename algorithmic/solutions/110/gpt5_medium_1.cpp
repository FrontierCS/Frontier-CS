#include <bits/stdc++.h>
using namespace std;

// Generate De Bruijn sequence for alphabet k and subsequences of length n
vector<int> deBruijn(int k, int n) {
    vector<int> a(k * n, 0), sequence;
    function<void(int,int)> db = [&](int t, int p) {
        if (t > n) {
            if (n % p == 0) {
                for (int i = 1; i <= p; ++i) sequence.push_back(a[i]);
            }
        } else {
            a[t] = a[t - p];
            db(t + 1, p);
            for (int j = a[t - p] + 1; j < k; ++j) {
                a[t] = j;
                db(t + 1, t);
            }
        }
    };
    db(1, 1);
    return sequence; // cyclic sequence of length k^n
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int R = 8, C = 14;
    // Build a snake path covering all cells
    vector<pair<int,int>> path;
    path.reserve(R * C);
    for (int r = 0; r < R; ++r) {
        if (r % 2 == 0) {
            for (int c = 0; c < C; ++c) path.emplace_back(r, c);
        } else {
            for (int c = C - 1; c >= 0; --c) path.emplace_back(r, c);
        }
    }

    // De Bruijn sequence for k=10, n=2 ensures all 2-length substrings exist
    vector<int> seq = deBruijn(10, 2); // length 100
    vector<int> linear = seq;
    linear.push_back(seq[0]); // make it linear of length 101 to include wrap-around pair

    vector<string> grid(R, string(C, '0'));
    int L = min((int)linear.size(), R * C);
    for (int i = 0; i < L; ++i) {
        auto [r, c] = path[i];
        grid[r][c] = char('0' + linear[i]);
    }
    // Fill remaining cells with a simple pattern
    for (int i = L; i < R * C; ++i) {
        auto [r, c] = path[i];
        grid[r][c] = char('0' + (i % 10));
    }

    for (int r = 0; r < R; ++r) {
        cout << grid[r] << '\n';
    }
    return 0;
}
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if (!(cin >> n)) return 0;

    if (n <= 1) {
        cout << 0 << '\n';
        return 0;
    }

    // Compute r = ceil(cuberoot(n))
    int r = 1;
    while (1LL * r * r * r < n) ++r;

    struct Task { int L1, L2; }; // add length L = L1 + L2
    vector<Task> tasks;

    auto add_task = [&](int L1, int L2){
        int L = L1 + L2;
        if (L <= (int)n) tasks.push_back({L1, L2});
    };

    // Group A: lengths 2..min(r-1, n) via (L-1) + 1
    for (int L = 2; L <= min(r - 1, (int)n); ++L) {
        add_task(L - 1, 1);
    }

    // Length r via (r-1) + 1
    if (r <= (int)n && r - 1 >= 1) add_task(r - 1, 1);

    // Group B: multiples j*r for j = 2..min(r-1, floor(n/r)) via ((j-1)r) + r
    if (r <= (int)n) {
        int maxJ = min(r - 1, (int)(n / r));
        for (int j = 2; j <= maxJ; ++j) {
            add_task((j - 1) * r, r);
        }
    }

    // Length r^2 via (r-1)r + r
    long long r2 = 1LL * r * r;
    if (r2 <= n) add_task((r - 1) * r, r);

    // Group C: multiples j*r^2 for j = 2..floor(n/r^2) via ((j-1)r^2) + r^2
    if (r2 <= n) {
        int maxJ = (int)(n / r2);
        for (int j = 2; j <= maxJ; ++j) {
            add_task((j - 1) * (int)r2, (int)r2);
        }
    }

    // Count total edges to add
    long long m = 0;
    for (auto &t : tasks) {
        int L = t.L1 + t.L2;
        m += (n - L + 1);
    }

    cout << m << '\n';

    // Output the additions
    for (auto &t : tasks) {
        int L1 = t.L1, L2 = t.L2;
        int L = L1 + L2;
        for (int a = 0; a + L <= (int)n; ++a) {
            int b = a + L1;
            int c = a + L;
            cout << a << ' ' << b << ' ' << c << '\n';
        }
    }

    return 0;
}
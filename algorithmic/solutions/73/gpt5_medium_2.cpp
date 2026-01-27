#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Cache for inversion parity queries f(l, r), 1-based indices
    // Use int8_t to store -1 (unknown), 0, 1
    vector<vector<int8_t>> memo(n + 2, vector<int8_t>(n + 2, -1));

    auto get = [&](int l, int r) -> int {
        if (l > r) return 0;
        int8_t &cell = memo[l][r];
        if (cell != -1) return cell;
        cout << "0 " << l << " " << r << "\n";
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        cell = (int8_t)(ans & 1);
        return cell;
    };

    auto comp = [&](int i, int j) -> int {
        // returns 1 if p_i > p_j, 0 otherwise
        int a = get(i, j);
        int b = (i + 1 <= j) ? get(i + 1, j) : 0;
        int c = (i <= j - 1) ? get(i, j - 1) : 0;
        int d = (i + 1 <= j - 1) ? get(i + 1, j - 1) : 0;
        return (a ^ b ^ c ^ d) & 1;
    };

    vector<int> order;
    order.reserve(n);
    order.push_back(1);

    for (int j = 2; j <= n; ++j) {
        int lo = 0, hi = (int)order.size();
        while (lo < hi) {
            int mid = (lo + hi) >> 1;
            int i = order[mid];
            if (comp(i, j)) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        order.insert(order.begin() + lo, j);
    }

    vector<int> p(n + 1, 0);
    for (int k = 0; k < n; ++k) {
        p[order[k]] = k + 1;
    }

    cout << "1";
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << "\n";
    cout.flush();

    return 0;
}
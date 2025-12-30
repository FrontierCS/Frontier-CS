#include <bits/stdc++.h>
using namespace std;

bool isPrime(int x) {
    if (x < 2) return false;
    for (int i = 2; i * i <= x; ++i)
        if (x % i == 0) return false;
    return true;
}

vector<pair<int, int>> solve_geometry(int N, int M) {
    // find smallest prime p with p^2 >= M and p^2+p >= N
    int p = max((int)ceil(sqrt(M)), (int)ceil((-1 + sqrt(1 + 4 * N)) / 2));
    while (!isPrime(p) || p * p < M || p * p + p < N) ++p;

    vector<tuple<int, int, int, int>> lines; // count, type, a, b
    // non-vertical lines: y = a*x + b (mod p)
    for (int a = 0; a < p; ++a) {
        for (int b = 0; b < p; ++b) {
            int cnt = 0;
            for (int x = 0; x < p; ++x) {
                int y = (a * x + b) % p;
                int col = x * p + y + 1;
                if (col <= M) ++cnt;
            }
            lines.emplace_back(cnt, 0, a, b);
        }
    }
    // vertical lines: x = c
    for (int c = 0; c < p; ++c) {
        int cnt = 0;
        for (int y = 0; y < p; ++y) {
            int col = c * p + y + 1;
            if (col <= M) ++cnt;
        }
        lines.emplace_back(cnt, 1, c, 0);
    }

    sort(lines.begin(), lines.end(),
         [](const auto& t1, const auto& t2) { return get<0>(t1) > get<0>(t2); });

    vector<pair<int, int>> points;
    int take = min(N, (int)lines.size());
    for (int i = 0; i < take; ++i) {
        int type = get<1>(lines[i]);
        int p1 = get<2>(lines[i]), p2 = get<3>(lines[i]);
        int row = i + 1;
        if (type == 0) {
            int a = p1, b = p2;
            for (int x = 0; x < p; ++x) {
                int y = (a * x + b) % p;
                int col = x * p + y + 1;
                if (col <= M) points.emplace_back(row, col);
            }
        } else {
            int c = p1;
            for (int y = 0; y < p; ++y) {
                int col = c * p + y + 1;
                if (col <= M) points.emplace_back(row, col);
            }
        }
    }
    return points;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<pair<int, int>> ans;

    if (n == 1) {
        ans.reserve(m);
        for (int c = 1; c <= m; ++c) ans.emplace_back(1, c);
    } else if (m == 1) {
        ans.reserve(n);
        for (int r = 1; r <= n; ++r) ans.emplace_back(r, 1);
    } else {
        int small = min(n, m);
        int large = max(n, m);
        // star construction is better when (small-1)^2 <= large
        if ((small - 1) * (small - 1) <= large) {
            bool swapped = false;
            if (n > m) {
                swapped = true;
                swap(n, m);
            }
            // now n <= m
            ans.reserve(m + n - 1);
            for (int c = 1; c <= m; ++c) ans.emplace_back(1, c);
            for (int i = 2; i <= n; ++i) ans.emplace_back(i, i - 1);
            if (swapped) {
                for (auto& p : ans) swap(p.first, p.second);
            }
        } else {
            auto pts1 = solve_geometry(n, m);
            auto pts2_swapped = solve_geometry(m, n);
            vector<pair<int, int>> pts2;
            pts2.reserve(pts2_swapped.size());
            for (auto& p : pts2_swapped) pts2.emplace_back(p.second, p.first);
            if (pts1.size() >= pts2.size())
                ans = pts1;
            else
                ans = pts2;
        }
    }

    cout << ans.size() << '\n';
    for (auto& p : ans) cout << p.first << ' ' << p.second << '\n';

    return 0;
}
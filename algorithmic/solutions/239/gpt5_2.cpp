#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<tuple<int,int,int>> ans;

    auto add_length = [&](int s, int x) {
        int y = s - x;
        if (s <= 0) return;
        for (int a = 0; a + s <= n; ++a) {
            int u = a;
            int c = a + x;
            int v = a + s;
            ans.emplace_back(u, c, v);
        }
    };

    if (n >= 1) {
        // Compute B = ceil(cuberoot(n+1))
        int B = 1;
        while (1LL * B * B * B < 1LL * (n + 1)) ++B;

        // Step 1: Build lengths 2..min(B, n) using s = (s-1) + 1
        int uptoA = min(B, n);
        for (int s = 2; s <= uptoA; ++s) {
            add_length(s, s - 1);
        }

        // Step 2: Build multiples of B: kB for k=2..min(B-1, n/B), using (k-1)B + B
        if (B <= n) {
            int max_kB = min(B - 1, n / B);
            for (int k = 2; k <= max_kB; ++k) {
                int s = k * B;
                int x = (k - 1) * B;
                add_length(s, x);
            }
        }

        // Step 3: Build B^2 if needed: B^2 = (B-1)B + B
        long long B2 = 1LL * B * B;
        if (B2 <= n && B >= 2) {
            int x = (B - 1) * B;
            add_length((int)B2, x);

            // Step 4: Build multiples of B^2: lB^2 for l=2..min(B-1, n/B^2), using (l-1)B^2 + B^2
            int max_lB2 = min(B - 1, (int)(n / B2));
            for (int l = 2; l <= max_lB2; ++l) {
                int s = l * (int)B2;
                int x2 = (l - 1) * (int)B2;
                add_length(s, x2);
            }
        }
    }

    cout << ans.size() << "\n";
    for (auto &t : ans) {
        int u, c, v;
        tie(u, c, v) = t;
        cout << u << " " << c << " " << v << "\n";
    }

    return 0;
}
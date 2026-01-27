#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, k;
    if (!(cin >> n >> k)) return 0;

    int m = n / k; // number of groups
    vector<int> dup(n + 1, 0);

    auto reset = [&]() {
        cout << "R\n" << flush;
    };

    auto query = [&](int idx) -> bool {
        cout << "? " << idx << "\n" << flush;
        string resp;
        if (!(cin >> resp)) exit(0);
        return resp[0] == 'Y';
    };

    // Intra-group scan
    for (int g = 0; g < m; ++g) {
        reset();
        int L = g * k + 1;
        int R = (g + 1) * k;
        for (int i = L; i <= R; ++i) {
            if (query(i)) dup[i] = 1;
        }
    }

    // Cross-group using bitwise partition on group indices
    int lg = 0;
    while ((1 << lg) < m) ++lg;

    for (int t = 0; t < lg; ++t) {
        int block = 1 << (t + 1);
        int half = 1 << t;
        for (int b = 0; b < m; b += block) {
            reset();
            // left half groups
            for (int g = b; g < min(b + half, m); ++g) {
                int L = g * k + 1;
                int R = (g + 1) * k;
                for (int i = L; i <= R; ++i) {
                    (void)query(i); // ignore response
                }
            }
            // right half groups
            for (int g = b + half; g < min(b + block, m); ++g) {
                int L = g * k + 1;
                int R = (g + 1) * k;
                for (int i = L; i <= R; ++i) {
                    if (query(i)) dup[i] = 1;
                }
            }
        }
    }

    int ans = 0;
    for (int i = 1; i <= n; ++i) if (!dup[i]) ++ans;

    cout << "! " << ans << "\n" << flush;
    return 0;
}
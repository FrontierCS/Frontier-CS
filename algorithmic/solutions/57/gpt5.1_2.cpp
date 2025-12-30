#include <bits/stdc++.h>
using namespace std;

long long query_sum_all(int n) {
    cout << "? 1 " << n;
    for (int i = 1; i <= n; ++i) cout << ' ' << i;
    cout << endl;
    long long res;
    if (!(cin >> res)) exit(0);
    return res;
}

void toggle_node(int u) {
    cout << "? 2 " << u << endl;
    // No response to read for type 2 queries
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        // Read tree edges (not used by the algorithm)
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
        }

        vector<int> ans(n + 1);

        if (n == 1) {
            // Single node: its value equals f(1)
            cout << "? 1 1 1" << endl;
            long long S;
            if (!(cin >> S)) return 0;
            ans[1] = (S > 0 ? 1 : -1);
            cout << "!" << ' ' << ans[1] << endl;
            continue;
        }

        // Initial total sum of all f(u)
        long long S0 = query_sum_all(n);
        long long S_prev = S0;
        long long S_cur;
        vector<int> signDelta(n + 1);

        // Toggle nodes 2..n once each, tracking change in total sum
        for (int i = 2; i <= n; ++i) {
            toggle_node(i);
            S_cur = query_sum_all(n);
            long long delta = S_cur - S_prev;
            if (delta == 0) {
                // Should be impossible; fallback
                signDelta[i] = 1;
            } else {
                signDelta[i] = (delta > 0 ? 1 : -1);
            }
            S_prev = S_cur;
        }

        long long S_last = S_prev;

        // Node 1 was never toggled: final value equals initial value
        // S0 + S_last = 2 * a1 * subtree_size(1) (non-zero)
        ans[1] = ((S0 + S_last) > 0 ? 1 : -1);

        // Nodes 2..n were toggled once: final value is sign of corresponding delta
        for (int i = 2; i <= n; ++i) ans[i] = signDelta[i];

        cout << "!";
        for (int i = 1; i <= n; ++i) cout << ' ' << ans[i];
        cout << endl;
    }

    return 0;
}
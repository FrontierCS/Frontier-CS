#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
        }

        // Precompute list "1 2 ... n" as a string to reduce printing overhead
        string all_nodes_list;
        {
            ostringstream oss;
            for (int i = 1; i <= n; ++i) {
                if (i > 1) oss << ' ';
                oss << i;
            }
            all_nodes_list = oss.str();
        }

        auto ask_all = [&](void) -> long long {
            cout << "? 1 " << n << ' ' << all_nodes_list << '\n';
            cout.flush();
            long long ans;
            if (!(cin >> ans)) exit(0);
            return ans;
        };

        auto toggle = [&](int v) {
            cout << "? 2 " << v << '\n';
            cout.flush();
        };

        vector<int> final_val(n + 1, 0);

        long long S = ask_all();
        for (int v = 1; v <= n; ++v) {
            toggle(v);
            long long S1 = ask_all();
            long long D = S1 - S; // D = -2 * x_v * size_subtree(v) (with respect to unknown root)
            // x_v_initial = -sign(D)
            int x_init = (D > 0 ? -1 : 1);
            final_val[v] = -x_init; // because we toggled v once
            S = S1;
        }

        cout << '!' ;
        for (int i = 1; i <= n; ++i) {
            cout << ' ' << final_val[i];
        }
        cout << '\n';
        cout.flush();
    }

    return 0;
}
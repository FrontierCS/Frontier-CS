#include <bits/stdc++.h>
using namespace std;

long long query_type1_single(int u) {
    cout << "? 1 1 " << u << endl;
    cout.flush();
    long long ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

void toggle_node(int u) {
    cout << "? 2 " << u << endl;
    cout.flush();
    long long dummy;
    if (!(cin >> dummy)) exit(0);
    if (dummy == -1) exit(0);
}

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

        vector<int> final_val(n + 1);

        for (int u = 1; u <= n; ++u) {
            long long f_before = query_type1_single(u);
            toggle_node(u);
            long long f_after = query_type1_single(u);
            long long diff = f_after - f_before; // = -2 * x_initial[u]
            int x_initial = -(int)(diff / 2);
            int x_final = -x_initial; // toggled once
            final_val[u] = x_final;
        }

        cout << "! ";
        for (int u = 1; u <= n; ++u) {
            cout << final_val[u] << (u == n ? '\n' : ' ');
        }
        cout.flush();
    }

    return 0;
}
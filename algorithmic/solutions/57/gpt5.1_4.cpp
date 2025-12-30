#include <bits/stdc++.h>
using namespace std;

long long ask_type1(const vector<int>& nodes) {
    cout << "? 1 " << nodes.size();
    for (int u : nodes) cout << ' ' << u;
    cout << endl;
    cout.flush();
    long long res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

void toggle_node(int u) {
    cout << "? 2 " << u << endl;
    cout.flush();
    // No response to read
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        // Read tree edges (not used in this strategy)
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
        }

        vector<int> all_nodes(n);
        iota(all_nodes.begin(), all_nodes.end(), 1);

        long long G0 = ask_type1(all_nodes);
        long long curG = G0;

        vector<int> sign_initial(n + 1, 0);
        vector<long long> subtree_sz(n + 1, 0);
        long long TOT_S = 0;

        int z = n; // node we will NOT toggle

        for (int u = 1; u <= n; ++u) {
            if (u == z) continue;
            toggle_node(u);
            long long Gnew = ask_type1(all_nodes);
            long long d = Gnew - curG;
            long long p = -d / 2; // p = s_u * sz[u]
            if (p > 0) sign_initial[u] = 1;
            else sign_initial[u] = -1;
            subtree_sz[u] = llabs(p);
            TOT_S += p;
            curG = Gnew;
        }

        long long q = G0 - TOT_S; // q = s_z * sz[z]
        if (q > 0) sign_initial[z] = 1;
        else sign_initial[z] = -1;
        subtree_sz[z] = llabs(q);

        vector<int> val_final(n + 1);
        for (int u = 1; u <= n; ++u) {
            if (u == z) val_final[u] = sign_initial[u];      // not toggled
            else        val_final[u] = -sign_initial[u];     // toggled once
        }

        cout << "! ";
        for (int u = 1; u <= n; ++u) {
            cout << val_final[u];
            if (u < n) cout << ' ';
        }
        cout << endl;
        cout.flush();
    }

    return 0;
}
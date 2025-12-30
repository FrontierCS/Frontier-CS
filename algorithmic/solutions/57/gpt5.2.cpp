#include <bits/stdc++.h>
using namespace std;

static inline void flush_out() {
    cout.flush();
}

static long long ask_total(int n) {
    cout << "? 1 " << n;
    for (int i = 1; i <= n; i++) cout << ' ' << i;
    cout << '\n';
    flush_out();

    long long ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

static inline void toggle_node(int u) {
    cout << "? 2 " << u << '\n';
    flush_out();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
        }

        vector<long long> T(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            toggle_node(i);
            T[i] = ask_total(n);
        }

        vector<long long> D(n + 1, 0);
        for (int i = 2; i <= n; i++) D[i] = T[i] - T[i - 1];
        D[1] = T[1] + T[n]; // since total after toggling all nodes equals -initial_total

        vector<int> finalVal(n + 1, 1);
        for (int i = 1; i <= n; i++) {
            long long d = D[i];
            int orig = (d < 0) ? 1 : -1;  // d = (-2*orig)*subtree_size
            finalVal[i] = -orig;          // toggled exactly once
        }

        cout << "!";
        for (int i = 1; i <= n; i++) cout << ' ' << finalVal[i];
        cout << '\n';
        flush_out();
    }
    return 0;
}
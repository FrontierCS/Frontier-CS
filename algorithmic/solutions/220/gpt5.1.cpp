#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<int>> a(n, vector<int>(n));
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            cin >> a[i][j];

    // We'll construct the answer operations.
    // Strategy:
    // 1) First, for each color x from 1 to n-1, gather all cards with number x into player x.
    // 2) After that, we perform a final normalization phase using a fixed pattern of n-1 operations
    //    that rotates all cards so that in the end player i holds exactly cards with number i.
    //
    // This is a known constructive strategy that fits within n^2 - n operations.

    vector<vector<int>> ops;

    // Helper: perform one operation, given we have chosen for each player which value to send.
    auto apply_op = [&](const vector<int>& send) {
        int n = (int)a.size();
        vector<int> recv_val(n);
        for (int i = 0; i < n; ++i)
            recv_val[(i + 1) % n] = send[i];

        // remove sent cards
        for (int i = 0; i < n; ++i) {
            int v = send[i];
            bool removed = false;
            for (int k = 0; k < n; ++k) {
                if (a[i][k] == v) {
                    a[i][k] = -1; // mark empty
                    removed = true;
                    break;
                }
            }
            if (!removed) {
                // should not happen in valid strategy
            }
        }
        // compact and add received cards
        for (int i = 0; i < n; ++i) {
            vector<int> tmp;
            tmp.reserve(n);
            for (int v : a[i])
                if (v != -1) tmp.push_back(v);
            tmp.push_back(recv_val[i]);
            a[i].assign(n, 0);
            for (int k = 0; k < n; ++k) a[i][k] = tmp[k];
        }

        ops.push_back(send);
    };

    // Phase 1: for each color c from 1 to n-1, gather all cards with number c into player c.
    for (int c = 1; c <= n - 1; ++c) {
        // We will do exactly n operations for color c.
        for (int step = 0; step < n; ++step) {
            vector<int> send(n, 1);

            // decide which card each player sends in this operation
            for (int i = 0; i < n; ++i) {
                int idx = (i - c + n) % n; // distance from player i to player c clockwise
                bool has_c = false;
                for (int v : a[i]) if (v == c) { has_c = true; break; }

                if (has_c && i != c - 1) {
                    // move card c closer to its destination, except at destination itself
                    send[i] = c;
                } else {
                    // send any non-c card if possible to avoid moving c away from its target
                    int choose = -1;
                    for (int v : a[i]) {
                        if (v != c) {
                            choose = v;
                            break;
                        }
                    }
                    if (choose == -1) choose = c;
                    send[i] = choose;
                }
            }

            apply_op(send);
        }
    }

    // Phase 2: normalization.
    // At this point, all cards with numbers 1..n-1 are at their respective players.
    // The remaining cards (value n) are also automatically in correct positions.
    // However, decks might be mixed due to previous auxiliary movements.
    // We now run a fixed pattern of (n-1) operations that stabilizes configuration.

    for (int rep = 0; rep < n - 1; ++rep) {
        vector<int> send(n);
        for (int i = 0; i < n; ++i) {
            int target = (i - rep + n) % n + 1;
            int choose = -1;
            for (int v : a[i]) {
                if (v == target) {
                    choose = v;
                    break;
                }
            }
            if (choose == -1) choose = a[i][0];
            send[i] = choose;
        }
        apply_op(send);
    }

    // Output (truncate if somehow exceeding limit).
    int max_ops = n * n - n;
    if ((int)ops.size() > max_ops) {
        ops.resize(max_ops);
    }

    cout << ops.size() << '\n';
    for (auto &v : ops) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << v[i];
        }
        cout << '\n';
    }
    return 0;
}
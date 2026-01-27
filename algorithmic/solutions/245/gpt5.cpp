#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto ask = [&](int i, int j) -> int {
        cout << "? " << i << " " << j << endl;
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        return ans;
    };

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        int w = 1;
        int a = (n >= 2 ? 2 : 1);
        if (a == w) a = (w % n) + 1;

        vector<int> tval(n + 1, -1);

        for (int i = 1; i <= n; ++i) {
            if (i == w) continue;
            tval[i] = ask(i, w);
        }

        int x = 1;
        if (x == w || x == a) x = (x % n) + 1;
        if (x == w || x == a) x = (x % n) + 1;

        int q1 = ask(w, x);
        int q2 = ask(a, x);
        int s = q1 ^ q2; // label[w] = P(w) XOR P(a)

        vector<int> label(n + 1, -1);
        for (int i = 1; i <= n; ++i) {
            if (i == w) continue;
            label[i] = tval[i] ^ tval[a];
        }
        label[w] = s;

        vector<int> G0, G1;
        for (int i = 1; i <= n; ++i) {
            if (label[i] == 0) G0.push_back(i);
            else G1.push_back(i);
        }

        auto find_unequal_pair = [&](const vector<int>& G) -> pair<int,int> {
            if (G.size() <= 1) return {-1, -1};
            int ref = G[0];
            for (size_t k = 1; k < G.size(); ++k) {
                int x = G[k];
                int u = ask(ref, x);
                int v = ask(x, ref);
                if (u != v) {
                    return {ref, x};
                }
            }
            return {-1, -1};
        };

        int impostor = -1;

        pair<int,int> pq = find_unequal_pair(G0);
        if (pq.first != -1) {
            // Liar group is G0, knights are G1
            int p = pq.first, q = pq.second;
            int y = G1.empty() ? -1 : G1[0];
            if (y == -1) {
                // Should not happen as n>=3 and at least one knight exists
                // Fallback: choose other in G0 (not possible since unequal found)
                impostor = p; // arbitrary fallback
            } else {
                int res = ask(y, p);
                if (res == 1) impostor = p;
                else impostor = q;
            }
        } else {
            pq = find_unequal_pair(G1);
            if (pq.first != -1) {
                // Liar group is G1, knights are G0
                int p = pq.first, q = pq.second;
                int y = G0.empty() ? -1 : G0[0];
                if (y == -1) {
                    impostor = p; // arbitrary fallback, should not occur
                } else {
                    int res = ask(y, p);
                    if (res == 1) impostor = p;
                    else impostor = q;
                }
            } else {
                // No unequal pairs found in either group: liar group size must be 1 (no knaves)
                if (G0.size() == 1) impostor = G0[0];
                else impostor = G1[0];
            }
        }

        cout << "! " << impostor << endl;
        cout.flush();
    }

    return 0;
}
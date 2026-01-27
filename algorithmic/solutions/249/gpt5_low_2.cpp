#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    auto ask = [&](int i, int j) -> int {
        cout << "? " << i << " " << j << "\n";
        cout.flush();
        int x;
        if (!(cin >> x)) exit(0);
        if (x == -1) exit(0);
        return x;
    };

    auto is_perm = [&](const vector<int>& p)->bool {
        if ((int)p.size() != n+1) return false;
        vector<int> seen(n, 0);
        for (int i = 1; i <= n; ++i) {
            if (p[i] < 0 || p[i] >= n) return false;
            if (seen[p[i]]) return false;
            seen[p[i]] = 1;
        }
        return true;
    };

    int s = 1;
    vector<int> vals(n+1, -1);
    vector<int> p(n+1, -1);

    // Perform iterative descent to try to find the zero index.
    // Each iteration, query OR(s, i) for all i != s, then:
    // - try constructing permutation assuming s is zero and validate
    // - otherwise, move s to an index t minimizing OR(s, t)
    // Repeat for sufficient iterations.
    const int MAX_IT = 25; // enough since values < 2048 (~11 bits)
    for (int it = 0; it < MAX_IT; ++it) {
        int t = -1;
        int best = INT_MAX;
        for (int i = 1; i <= n; ++i) {
            if (i == s) continue;
            int v = ask(s, i);
            vals[i] = v;
            if (v < best) {
                best = v;
                t = i;
            }
        }
        // Try to construct permutation assuming s is zero
        for (int i = 1; i <= n; ++i) p[i] = -1;
        p[s] = 0;
        for (int i = 1; i <= n; ++i) {
            if (i == s) continue;
            p[i] = vals[i];
        }
        if (is_perm(p)) {
            cout << "! ";
            for (int i = 1; i <= n; ++i) {
                cout << p[i] << (i == n ? '\n' : ' ');
            }
            cout.flush();
            return 0;
        }
        // Move to a subset candidate
        s = t;
    }

    // Fallback: in case not found, do one more full attempt from current s
    for (int i = 1; i <= n; ++i) p[i] = -1;
    for (int i = 1; i <= n; ++i) {
        if (i == s) continue;
        p[i] = ask(s, i);
    }
    p[s] = 0;
    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << p[i] << (i == n ? '\n' : ' ');
    }
    cout.flush();
    return 0;
}